from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from compensation_hub.db.models import Employee
from compensation_hub.seed.dataset import build_seed_dataset

DATASET = build_seed_dataset(employee_count=60)


def test_health(client: TestClient) -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "compensation-hub-api"}


def test_list_employees_paginates_in_name_order(seeded_client: TestClient) -> None:
    response = seeded_client.get("/employees", params={"page": 2, "page_size": 10})

    assert response.status_code == 200
    body = response.json()
    assert body["page"] == 2
    assert body["page_size"] == 10
    assert body["total_items"] == 60
    assert body["total_pages"] == 6
    assert len(body["items"]) == 10

    expected_names = sorted((e.full_name, e.employee_code) for e in DATASET.employees)[10:20]
    assert [(i["full_name"], i["employee_code"]) for i in body["items"]] == expected_names


def test_list_employees_includes_current_compensation(seeded_client: TestClient) -> None:
    body = seeded_client.get("/employees", params={"search": "EMP00001"}).json()

    assert body["total_items"] == 1
    employee = DATASET.employees[0]
    assert body["items"][0]["compensation"] == {
        "annual_salary": str(employee.annual_salary),
        "currency_code": employee.currency_code,
    }


def test_list_employees_defaults_to_first_page_of_25(seeded_client: TestClient) -> None:
    body = seeded_client.get("/employees").json()

    assert body["page"] == 1
    assert body["page_size"] == 25
    assert len(body["items"]) == 25


def test_list_employees_empty_page_beyond_results(seeded_client: TestClient) -> None:
    body = seeded_client.get("/employees", params={"page": 50}).json()

    assert body["items"] == []
    assert body["total_items"] == 60
    assert body["total_pages"] == 3


def test_list_employees_rejects_invalid_pagination(seeded_client: TestClient) -> None:
    assert seeded_client.get("/employees", params={"page": 0}).status_code == 422
    assert seeded_client.get("/employees", params={"page_size": 0}).status_code == 422
    assert seeded_client.get("/employees", params={"page_size": 101}).status_code == 422
    assert seeded_client.get("/employees", params={"page": "abc"}).status_code == 422


def test_search_matches_name_case_insensitively(seeded_client: TestClient) -> None:
    target = DATASET.employees[3]
    fragment = target.full_name.split()[0].lower()

    body = seeded_client.get("/employees", params={"search": fragment}).json()

    expected = sorted(e.employee_code for e in DATASET.employees if fragment in e.full_name.lower())
    assert sorted(i["employee_code"] for i in body["items"]) == expected
    assert body["total_items"] == len(expected)


def test_search_matches_employee_code(seeded_client: TestClient) -> None:
    body = seeded_client.get("/employees", params={"search": "emp0004"}).json()

    assert sorted(i["employee_code"] for i in body["items"]) == [f"EMP0004{n}" for n in range(10)]
    assert body["total_items"] == 10


def test_search_treats_like_wildcards_literally(seeded_client: TestClient) -> None:
    assert seeded_client.get("/employees", params={"search": "%"}).json()["total_items"] == 0
    assert seeded_client.get("/employees", params={"search": "_"}).json()["total_items"] == 0


def test_filters_combine(seeded_client: TestClient) -> None:
    sample = DATASET.employees[0]
    expected = {
        e.employee_code
        for e in DATASET.employees
        if e.country == sample.country and e.department == sample.department
    }

    body = seeded_client.get(
        "/employees",
        params={"country": sample.country, "department": sample.department, "page_size": 100},
    ).json()

    assert {i["employee_code"] for i in body["items"]} == expected
    assert body["total_items"] == len(expected)


def test_job_title_filter(seeded_client: TestClient) -> None:
    sample = DATASET.employees[0]
    expected = {e.employee_code for e in DATASET.employees if e.job_title == sample.job_title}

    body = seeded_client.get(
        "/employees", params={"job_title": sample.job_title, "page_size": 100}
    ).json()

    assert {i["employee_code"] for i in body["items"]} == expected


def test_search_filters_and_pagination_combine_without_loading_everything(
    seeded_client: TestClient,
) -> None:
    sample = DATASET.employees[0]
    fragment = sample.full_name.split()[0].lower()
    matching = sorted(
        (e.full_name, e.employee_code)
        for e in DATASET.employees
        if fragment in e.full_name.lower() and e.country == sample.country
    )

    first = seeded_client.get(
        "/employees",
        params={"search": fragment, "country": sample.country, "page_size": 1, "page": 1},
    ).json()
    last = seeded_client.get(
        "/employees",
        params={
            "search": fragment,
            "country": sample.country,
            "page_size": 1,
            "page": len(matching),
        },
    ).json()

    assert first["total_items"] == len(matching)
    assert first["total_pages"] == len(matching)
    assert len(first["items"]) == 1
    assert (first["items"][0]["full_name"], first["items"][0]["employee_code"]) == matching[0]
    assert (last["items"][0]["full_name"], last["items"][0]["employee_code"]) == matching[-1]


def test_unknown_filter_value_returns_empty_page(seeded_client: TestClient) -> None:
    body = seeded_client.get("/employees", params={"country": "Atlantis"}).json()

    assert body["items"] == []
    assert body["total_items"] == 0
    assert body["total_pages"] == 1


def test_filter_options_list_distinct_sorted_values(seeded_client: TestClient) -> None:
    body = seeded_client.get("/employees/filter-options").json()

    assert body["countries"] == sorted({e.country for e in DATASET.employees})
    assert body["departments"] == sorted({e.department for e in DATASET.employees})
    assert body["job_titles"] == sorted({e.job_title for e in DATASET.employees})


def test_get_employee_returns_details_and_compensation(
    seeded_client: TestClient, db_session: Session
) -> None:
    employee_id = db_session.scalar(select(Employee.id).where(Employee.employee_code == "EMP00002"))
    expected = DATASET.employees[1]

    response = seeded_client.get(f"/employees/{employee_id}")

    assert response.status_code == 200
    assert response.json() == {
        "id": employee_id,
        "employee_code": "EMP00002",
        "full_name": expected.full_name,
        "country": expected.country,
        "department": expected.department,
        "job_title": expected.job_title,
        "compensation": {
            "annual_salary": str(expected.annual_salary),
            "currency_code": expected.currency_code,
        },
    }


def test_get_employee_without_compensation_returns_null_compensation(
    client: TestClient, db_session: Session
) -> None:
    employee = Employee(
        employee_code="EMP99999",
        full_name="No Pay Yet",
        country="United States",
        department="Finance",
        job_title="Accountant",
    )
    db_session.add(employee)
    db_session.commit()

    body = client.get(f"/employees/{employee.id}").json()

    assert body["compensation"] is None


def test_get_missing_employee_returns_404(seeded_client: TestClient) -> None:
    response = seeded_client.get("/employees/999999")

    assert response.status_code == 404
    assert response.json() == {"detail": "Employee 999999 not found"}


def test_get_employee_rejects_non_integer_id(seeded_client: TestClient) -> None:
    assert seeded_client.get("/employees/not-an-id").status_code == 422


def test_salary_is_serialized_as_exact_decimal_string(seeded_client: TestClient) -> None:
    body = seeded_client.get("/employees", params={"search": "EMP00001"}).json()

    salary = body["items"][0]["compensation"]["annual_salary"]
    assert isinstance(salary, str)
    assert Decimal(salary) == DATASET.employees[0].annual_salary
