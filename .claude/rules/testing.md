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

## CLI Test Safety (CRITICAL)

- CLI tests that invoke destructive commands (`uninstall`, `clean`, `fix permissions`) **MUST** mock all filesystem and subprocess operations to prevent real-world damage
- Specifically mock: `shutil.rmtree`, `Path.unlink`, `Path.mkdir`, `os.chmod`, `os.chown`, `subprocess.run` for any command that modifies the system
- Use `tmp_path` fixture for any test that creates/deletes files — NEVER operate on real project paths
- `CliRunner(mix_stderr=False)` is NOT supported in Click 8.x — use `CliRunner()` instead
- When testing commands that call `click.confirm()`, pass `input="y\n"` or `input="n\n"` to CliRunner
- When testing commands with `sys.exit()`, use `catch_exceptions=True` (default) and check `result.exit_code`

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
