# CLI Development

Applies to: `scripts/matrix_cli.py`, `test/test_matrix_cli*.py`

## Dev Environment

The host is Fedora immutable. CLI verification and tests require the distrobox. The `.venv` is ephemeral — always chain `uv sync` before any venv command:
```bash
# Verify CLI
distrobox enter debian-trixie -- bash -c 'uv sync --extra test --extra dev --extra emulator && .venv/bin/python scripts/matrix_cli.py --help'

# Run CLI tests
distrobox enter debian-trixie -- bash -c 'uv sync --extra test --extra dev --extra emulator && EMULATOR=true .venv/bin/pytest test/test_matrix_cli*.py -q --override-ini="addopts="'
```

**Syntax-only checks work on the host** (no distrobox needed):
```bash
python3 -c "import ast; ast.parse(open('scripts/matrix_cli.py').read()); print('OK')"
```

## matrix_cli.py Structure

The CLI is a single-file Click application at `scripts/matrix_cli.py` (~2800 lines). Code is organized in sections:

1. Imports and constants (lines 1-80)
2. Helper functions (`_is_raspberry_pi()`, `_run()`, `_sync_venv()`, etc.)
3. Command definitions in order: `run`, `web`, `setup`, hardware helpers, `install` (with `--full` steps), `doctor`, `logs`, `service`, `plugin` group, `store` group, `diagnose` group, `fix`/`clean` groups, `network` group, `uninstall`
4. Entry point (`if __name__ == "__main__": cli()`)

## Adding New Commands

- New command groups go BEFORE the `# Entry point` section
- Each group gets a section header: `# ---------------------------------------------------------------------------`
- Use existing helpers: `_is_raspberry_pi()`, `_run()`, `_run_install_script()`, `LEDMATRIX_ROOT`, `console`, `PLUGINS_DIR`
- Pi-only commands must detect non-Pi and exit gracefully (not error)

## Branching

- The default working branch is `develop` — ALL feature branches and worktrees MUST branch from `develop`
- `main` is protected and does NOT contain `scripts/matrix_cli.py` or other develop-only files
- When using `isolation: "worktree"` for agents, be aware the worktree branches from the current repo HEAD — if HEAD is `main`, the agent won't have develop-only files

## Key Constants Available

| Name | Type | Description |
|------|------|-------------|
| `LEDMATRIX_ROOT` | `Path` | Resolved project root (via `__file__`) |
| `PLUGINS_DIR` | `Path` | `LEDMATRIX_ROOT / "plugins"` |
| `API_BASE` | `str` | `"http://localhost:5000/api/v3"` |
| `console` | `Console` | Rich Console instance |
| `_venv_python` | `Path` | `.venv/bin/python3` |

## Click Version Compatibility

This project uses Click 8.x:
- `CliRunner(mix_stderr=False)` is NOT supported — use `CliRunner()`
- `click.confirm()` works normally
- Use `@click.pass_context` for groups that need `ctx.invoked_subcommand`

## Test File Convention

Each CLI feature area gets its own test file:
- `test/test_matrix_cli.py` — core commands (doctor, install, setup, etc.)
- `test/test_matrix_cli_hardware.py` — `--hardware` flag
- `test/test_matrix_cli_diagnose.py` — `diagnose` group
- `test/test_matrix_cli_fix_clean.py` — `fix` and `clean` groups
- `test/test_matrix_cli_network.py` — `network` group
- `test/test_matrix_cli_uninstall.py` — `uninstall` command
- `test/test_matrix_cli_install_pi.py` — Pi-specific install tests
