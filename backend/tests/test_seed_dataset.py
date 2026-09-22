from decimal import Decimal

from compensation_hub.seed.dataset import (
    COUNTRIES,
    DATASET_SEED,
    DEPARTMENTS,
    EMPLOYEE_COUNT,
    build_seed_dataset,
)


def test_dataset_contains_expected_employee_count_with_unique_codes() -> None:
    dataset = build_seed_dataset()

    assert len(dataset.employees) == EMPLOYEE_COUNT == 10_000
    assert len({employee.employee_code for employee in dataset.employees}) == EMPLOYEE_COUNT
    assert dataset.employees[0].employee_code == "EMP00001"
    assert dataset.employees[-1].employee_code == "EMP10000"


def test_dataset_is_reproducible() -> None:
    assert build_seed_dataset() == build_seed_dataset()
    assert build_seed_dataset(seed=DATASET_SEED) == build_seed_dataset()


def test_different_seed_produces_different_dataset() -> None:
    assert build_seed_dataset(employee_count=50, seed=1) != build_seed_dataset(
        employee_count=50, seed=2
    )


def test_every_employee_currency_has_a_seeded_fx_rate() -> None:
    dataset = build_seed_dataset()
    seeded_currencies = {rate.currency_code for rate in dataset.fx_rates}

    assert {employee.currency_code for employee in dataset.employees} <= seeded_currencies
    assert len(seeded_currencies) == len(dataset.fx_rates)


def test_fx_rates_are_positive_and_usd_is_the_base_currency() -> None:
    dataset = build_seed_dataset()
    rates = {rate.currency_code: rate.rate_to_usd for rate in dataset.fx_rates}

    assert rates["USD"] == Decimal("1")
    assert all(rate > 0 for rate in rates.values())


def test_employee_currency_matches_country() -> None:
    dataset = build_seed_dataset()
    currency_by_country = {country.name: country.currency_code for country in COUNTRIES}

    assert all(
        employee.currency_code == currency_by_country[employee.country]
        for employee in dataset.employees
    )


def test_salaries_are_positive_decimals_with_two_decimal_places() -> None:
    dataset = build_seed_dataset()

    for employee in dataset.employees:
        assert isinstance(employee.annual_salary, Decimal)
        assert employee.annual_salary > 0
        assert employee.annual_salary == employee.annual_salary.quantize(Decimal("0.01"))


def test_job_titles_belong_to_their_departments() -> None:
    dataset = build_seed_dataset()
    titles_by_department = {
        department.name: {job.title for job in department.job_titles} for department in DEPARTMENTS
    }

    assert all(
        employee.job_title in titles_by_department[employee.department]
        for employee in dataset.employees
    )


def test_dataset_covers_every_country_and_department() -> None:
    dataset = build_seed_dataset()

    assert {employee.country for employee in dataset.employees} == {c.name for c in COUNTRIES}
    assert {employee.department for employee in dataset.employees} == {d.name for d in DEPARTMENTS}
