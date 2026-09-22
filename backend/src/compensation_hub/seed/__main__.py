import argparse
import sys

from compensation_hub.core.config import get_settings
from compensation_hub.db.session import create_database_engine, create_session_factory
from compensation_hub.seed.dataset import build_seed_dataset
from compensation_hub.seed.service import DatabaseAlreadySeededError, seed_database


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m compensation_hub.seed",
        description="Populate the database with the deterministic MVP dataset.",
    )
    parser.add_argument(
        "--reset",
        action="store_true",
        help="truncate existing employee, compensation, and FX data before seeding",
    )
    args = parser.parse_args(argv)

    engine = create_database_engine(str(get_settings().database_url))
    session_factory = create_session_factory(engine)
    try:
        with session_factory() as session:
            result = seed_database(session, build_seed_dataset(), reset=args.reset)
    except DatabaseAlreadySeededError as error:
        print(f"{error} Nothing was changed.", file=sys.stderr)
        return 1
    finally:
        engine.dispose()

    print(f"Seeded {result.employee_count} employees and {result.fx_rate_count} FX rates.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
