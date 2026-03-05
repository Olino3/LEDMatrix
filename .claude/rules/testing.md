# Test Quality

Applies to: `test/**/*`

## Rules

- Use fixtures from `conftest.py` — do not create ad-hoc mocks when a fixture exists.
- Assertions must verify behavior, not just call counts: assert on return values and side effects.
- Each test method tests exactly one behavior.
- Use markers: `@pytest.mark.unit` / `.integration` / `.hardware` / `.slow` / `.plugin`
- Plugin mock patch target: `manager.<ClassName>` — NOT the full module path (e.g., `transit.stops_db.StopsDatabase`).
- Do not write tests that pass without asserting anything meaningful.
- Coverage must not drop below the current baseline; raise it for modules you touch.

## Known Pre-existing Failures (do not fix unless explicitly tasked)

7 failures exist in the baseline: mock attribute errors, tkinter import issues, web API 503 responses. These are unrelated to display logic.

## Running Tests

```bash
# Standard — ignores plugin tests, applies emulator
EMULATOR=true .venv/bin/pytest test/ -q --override-ini="addopts=" --ignore=test/plugins

# With coverage
EMULATOR=true .venv/bin/pytest test/ --cov=src --cov-report=term-missing

# Specific test
EMULATOR=true .venv/bin/pytest test/test_<module>.py::TestClass::test_method -v
```
