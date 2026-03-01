# Design: Matrix CLI Documentation

**Date:** 2026-03-01
**Status:** Approved

## Problem

The `matrix` developer CLI (`scripts/matrix_cli.py`) has no documentation. Developers must read the source to discover commands.

## Solution

Create `docs/MATRIX_CLI.md` — a standalone command reference doc — and add a brief "For Plugin Developers" section to `README.md` that links to it.

## docs/MATRIX_CLI.md Structure

1. **Intro** — 1–2 sentences describing the CLI's purpose.
2. **Installation** — symlink setup and dependency note.
3. **Quick Start** — 3 representative example commands.
4. **Command Reference**
   - Display commands: `run`, `web`, `logs`, `service`
   - Plugin commands: `new`, `link`, `unlink`, `status`, `list`, `render`, `install`, `uninstall`, `update`, `enable`, `disable`, `health`, `store`
5. **Notes** — which commands require the web interface running.

## README.md Change

Add a `<details>` block titled "For Plugin Developers" just before the closing "If you've read this far" line with: 1 sentence about the CLI, the install command, and a link to `docs/MATRIX_CLI.md`.
