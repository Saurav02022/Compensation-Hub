-- Runs once when the PostgreSQL volume is first initialized.
-- The test database is separate because the test suite truncates its tables.
CREATE DATABASE compensation_hub_test OWNER compensation_hub;
