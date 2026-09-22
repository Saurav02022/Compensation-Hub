"""Deterministic generation of the synthetic MVP dataset.

The generator is a pure function of its seed. It only draws from ``Random.random()``,
whose sequence for a given seed is guaranteed stable across Python versions, so the
same dataset is produced on every machine and every run.
"""

from collections.abc import Sequence
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal
from random import Random

DATASET_SEED = 20240101
EMPLOYEE_COUNT = 10_000


@dataclass(frozen=True)
class SeedFxRate:
    currency_code: str
    rate_to_usd: Decimal


@dataclass(frozen=True)
class SeedEmployee:
    employee_code: str
    full_name: str
    country: str
    department: str
    job_title: str
    annual_salary: Decimal
    currency_code: str


@dataclass(frozen=True)
class SeedDataset:
    fx_rates: tuple[SeedFxRate, ...]
    employees: tuple[SeedEmployee, ...]


@dataclass(frozen=True)
class _Country:
    name: str
    currency_code: str
    weight: int
    # Relative pay level applied to the USD job band before conversion to local currency.
    pay_factor: Decimal
    # Local-currency unit that salaries are rounded to, so amounts look like real offers.
    rounding_unit: Decimal


@dataclass(frozen=True)
class _JobTitle:
    title: str
    usd_min: int
    usd_max: int


@dataclass(frozen=True)
class _Department:
    name: str
    weight: int
    job_titles: tuple[_JobTitle, ...]


FX_RATES: tuple[SeedFxRate, ...] = (
    SeedFxRate("USD", Decimal("1.00000000")),
    SeedFxRate("GBP", Decimal("1.27000000")),
    SeedFxRate("EUR", Decimal("1.08000000")),
    SeedFxRate("INR", Decimal("0.01200000")),
    SeedFxRate("CAD", Decimal("0.74000000")),
    SeedFxRate("AUD", Decimal("0.66000000")),
    SeedFxRate("JPY", Decimal("0.00670000")),
    SeedFxRate("BRL", Decimal("0.20000000")),
    SeedFxRate("SGD", Decimal("0.74000000")),
)

COUNTRIES: tuple[_Country, ...] = (
    _Country("United States", "USD", 25, Decimal("1.00"), Decimal("500")),
    _Country("India", "INR", 20, Decimal("0.30"), Decimal("10000")),
    _Country("United Kingdom", "GBP", 12, Decimal("0.85"), Decimal("500")),
    _Country("Germany", "EUR", 10, Decimal("0.85"), Decimal("500")),
    _Country("Canada", "CAD", 8, Decimal("0.80"), Decimal("500")),
    _Country("France", "EUR", 6, Decimal("0.80"), Decimal("500")),
    _Country("Australia", "AUD", 6, Decimal("0.85"), Decimal("500")),
    _Country("Japan", "JPY", 5, Decimal("0.70"), Decimal("10000")),
    _Country("Brazil", "BRL", 4, Decimal("0.35"), Decimal("500")),
    _Country("Singapore", "SGD", 4, Decimal("0.80"), Decimal("500")),
)

DEPARTMENTS: tuple[_Department, ...] = (
    _Department(
        "Engineering",
        35,
        (
            _JobTitle("Software Engineer", 90_000, 140_000),
            _JobTitle("Senior Software Engineer", 130_000, 190_000),
            _JobTitle("Staff Engineer", 180_000, 250_000),
            _JobTitle("Engineering Manager", 170_000, 240_000),
            _JobTitle("QA Engineer", 70_000, 110_000),
            _JobTitle("Data Engineer", 100_000, 160_000),
        ),
    ),
    _Department(
        "Sales",
        15,
        (
            _JobTitle("Account Executive", 70_000, 120_000),
            _JobTitle("Sales Development Representative", 50_000, 75_000),
            _JobTitle("Sales Manager", 120_000, 180_000),
        ),
    ),
    _Department(
        "Customer Support",
        10,
        (
            _JobTitle("Customer Support Specialist", 45_000, 70_000),
            _JobTitle("Support Team Lead", 70_000, 100_000),
        ),
    ),
    _Department(
        "Product",
        8,
        (
            _JobTitle("Product Manager", 110_000, 170_000),
            _JobTitle("Senior Product Manager", 150_000, 210_000),
            _JobTitle("Product Analyst", 75_000, 115_000),
        ),
    ),
    _Department(
        "Operations",
        8,
        (
            _JobTitle("Operations Manager", 95_000, 145_000),
            _JobTitle("Operations Analyst", 65_000, 100_000),
        ),
    ),
    _Department(
        "Marketing",
        7,
        (
            _JobTitle("Marketing Manager", 85_000, 130_000),
            _JobTitle("Content Strategist", 65_000, 100_000),
            _JobTitle("Growth Marketer", 75_000, 120_000),
        ),
    ),
    _Department(
        "Finance",
        6,
        (
            _JobTitle("Financial Analyst", 70_000, 110_000),
            _JobTitle("Accountant", 60_000, 95_000),
            _JobTitle("Finance Manager", 120_000, 170_000),
        ),
    ),
    _Department(
        "Design",
        5,
        (
            _JobTitle("Product Designer", 85_000, 135_000),
            _JobTitle("Senior Product Designer", 120_000, 170_000),
            _JobTitle("UX Researcher", 90_000, 140_000),
        ),
    ),
    _Department(
        "Human Resources",
        4,
        (
            _JobTitle("HR Business Partner", 85_000, 130_000),
            _JobTitle("Recruiter", 60_000, 95_000),
            _JobTitle("HR Coordinator", 50_000, 70_000),
        ),
    ),
    _Department(
        "Legal",
        2,
        (
            _JobTitle("Legal Counsel", 130_000, 200_000),
            _JobTitle("Paralegal", 60_000, 90_000),
        ),
    ),
)

FIRST_NAMES: tuple[str, ...] = (
    "Aarav", "Abigail", "Adam", "Aditi", "Aiko", "Alejandro", "Alice", "Amara", "Amelia",
    "Ananya", "Andre", "Anika", "Arjun", "Ava", "Beatriz", "Benjamin", "Bruno", "Camila",
    "Carlos", "Charlotte", "Chloe", "Chun", "Daniel", "David", "Deepak", "Diego", "Elena",
    "Elijah", "Emily", "Emma", "Ethan", "Fatima", "Felix", "Gabriel", "Grace", "Hana",
    "Hannah", "Haruto", "Henry", "Hiroshi", "Ibrahim", "Isabella", "Isha", "Jack", "Jacob",
    "James", "Jonas", "Julia", "Kavya", "Kenji", "Laila", "Leon", "Liam", "Lucas", "Luisa",
    "Maria", "Mateo", "Maya", "Mei", "Mia", "Michael", "Mohammed", "Naomi", "Nathan",
    "Neha", "Nikolai", "Noah", "Olivia", "Omar", "Oscar", "Paul", "Priya", "Rahul", "Ravi",
    "Rin", "Rohan", "Rosa", "Ruby", "Sakura", "Samuel", "Sanjay", "Sara", "Sebastian",
    "Sofia", "Sophie", "Sven", "Tanvi", "Thomas", "Tomas", "Valentina", "Vikram", "William",
    "Xin", "Yara", "Yuki", "Yusuf", "Zainab", "Zara", "Zoe", "Zhen",
)  # fmt: skip

LAST_NAMES: tuple[str, ...] = (
    "Adams", "Ahmed", "Ali", "Almeida", "Anderson", "Bailey", "Baker", "Becker", "Bernard",
    "Bhatt", "Brown", "Carter", "Chen", "Clark", "Costa", "Das", "Davis", "Dubois", "Evans",
    "Fischer", "Fournier", "Garcia", "Ghosh", "Gomes", "Gupta", "Hall", "Harris", "Hoffmann",
    "Hughes", "Ito", "Iyer", "Jackson", "Jensen", "Johnson", "Jones", "Joshi", "Kaur",
    "Khan", "Kim", "King", "Kobayashi", "Kumar", "Lambert", "Laurent", "Lee", "Lewis", "Lim",
    "Lopez", "Martin", "Martinez", "Mehta", "Meyer", "Miller", "Mitchell", "Moore", "Morgan",
    "Moreau", "Muller", "Murphy", "Nair", "Nakamura", "Nguyen", "Oliveira", "Ong", "Patel",
    "Pereira", "Perez", "Rao", "Reddy", "Reyes", "Ribeiro", "Roberts", "Robinson", "Rodrigues",
    "Rossi", "Roy", "Sato", "Schmidt", "Schneider", "Scott", "Sharma", "Silva", "Singh",
    "Smith", "Souza", "Suzuki", "Takahashi", "Tan", "Taylor", "Thompson", "Turner", "Walker",
    "Wang", "Watanabe", "Weber", "White", "Williams", "Wilson", "Wright", "Yamamoto", "Young",
)  # fmt: skip


def _pick[T](rng: Random, options: Sequence[T]) -> T:
    return options[int(rng.random() * len(options))]


def _pick_weighted[T](rng: Random, options: Sequence[T], weights: Sequence[int]) -> T:
    threshold = rng.random() * sum(weights)
    cumulative = 0
    for option, weight in zip(options, weights, strict=True):
        cumulative += weight
        if threshold < cumulative:
            return option
    return options[-1]


def _pick_int(rng: Random, low: int, high: int) -> int:
    return low + int(rng.random() * (high - low + 1))


def _local_salary(usd_amount: int, country: _Country, rate_to_usd: Decimal) -> Decimal:
    local_amount = Decimal(usd_amount) * country.pay_factor / rate_to_usd
    rounded_units = (local_amount / country.rounding_unit).to_integral_value(ROUND_HALF_UP)
    return (rounded_units * country.rounding_unit).quantize(Decimal("0.01"))


def build_seed_dataset(
    employee_count: int = EMPLOYEE_COUNT, seed: int = DATASET_SEED
) -> SeedDataset:
    rng = Random(seed)
    rates_by_currency = {rate.currency_code: rate.rate_to_usd for rate in FX_RATES}
    country_weights = [country.weight for country in COUNTRIES]
    department_weights = [department.weight for department in DEPARTMENTS]

    employees: list[SeedEmployee] = []
    for index in range(1, employee_count + 1):
        country = _pick_weighted(rng, COUNTRIES, country_weights)
        department = _pick_weighted(rng, DEPARTMENTS, department_weights)
        job_title = _pick(rng, department.job_titles)
        usd_amount = _pick_int(rng, job_title.usd_min, job_title.usd_max)
        full_name = f"{_pick(rng, FIRST_NAMES)} {_pick(rng, LAST_NAMES)}"
        employees.append(
            SeedEmployee(
                employee_code=f"EMP{index:05d}",
                full_name=full_name,
                country=country.name,
                department=department.name,
                job_title=job_title.title,
                annual_salary=_local_salary(
                    usd_amount, country, rates_by_currency[country.currency_code]
                ),
                currency_code=country.currency_code,
            )
        )

    return SeedDataset(fx_rates=FX_RATES, employees=tuple(employees))
