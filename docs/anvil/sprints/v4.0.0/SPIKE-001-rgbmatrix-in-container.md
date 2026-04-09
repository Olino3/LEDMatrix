# SPIKE-001 — rgbmatrix Library in Container

> **For Claude:** Use `superpowers:writing-plans` before touching any files. Use `superpowers:test-driven-development` for any logic you add.

**Status:** Open
**Phase:** v4.0.0 — Containerization
**Type:** Chore
**Depends on:** [DOCK-001](DOCK-001-dockerfile-multi-stage.md)
**Blocks:** _(none)_

---

## Context

The `rgbmatrix` library (hzeller/rpi-rgb-led-matrix) is a C library with Python bindings that controls the LED matrix hardware on Raspberry Pi. It requires compilation from source with specific build flags and GPIO pin mappings. Installing it inside a Docker container is non-trivial because:

1. The library must be compiled against the container's Python version, not the host's.
2. It needs build tools (`gcc`, `make`, `python3-dev`) that should not remain in the final image.
3. The compiled `.so` file must match the ARM architecture of the Pi.

This SPIKE investigates the best approach for including `rgbmatrix` in the container image and documents the solution for DOCK-001 to implement.

---

## Acceptance Criteria

- [ ] Document how `rgbmatrix` is currently installed on bare-metal Pi
- [ ] Test at least two approaches for containerizing rgbmatrix:
  1. Compile from source in a Dockerfile build stage
  2. Pre-compiled wheel (if available for ARM/Python 3.12)
- [ ] Document the chosen approach with exact Dockerfile commands
- [ ] Verify the library imports successfully inside the container
- [ ] Document any Pi-specific build flags or GPIO configuration needed

---

## Implementation Checklist

### 1. Research current installation method

- [ ] Read `scripts/matrix_cli.py` install logic for rgbmatrix compilation steps
- [ ] Document the build flags, pin mappings, and compile commands used today
- [ ] Check if `rgbmatrix` is listed in `pyproject.toml` or installed separately

### 2. Test Dockerfile build-stage approach

- [ ] Create a test Dockerfile that clones `hzeller/rpi-rgb-led-matrix`
- [ ] Compile the Python bindings in a build stage with `python3-dev`, `gcc`, `make`
- [ ] Copy only the compiled `.so` and Python files to the final stage
- [ ] Test `python -c "import rgbmatrix"` in the final image

### 3. Evaluate pre-compiled wheel approach

- [ ] Check PyPI and GitHub releases for ARM-compatible wheels
- [ ] If available, test `pip install rgbmatrix` inside the container
- [ ] Compare image size and build time with the build-stage approach

### 4. Document findings

- [ ] Write a summary in this ticket's Notes section (or a separate doc)
- [ ] Provide the exact Dockerfile snippet for the chosen approach
- [ ] Note any architecture constraints (ARM-only vs. multi-arch)

### 5. Commit

```bash
git add sprints/v4.0.0/SPIKE-001-rgbmatrix-in-container.md
git commit -m "docs(docker): document rgbmatrix containerization approach"
```

---

## Verification Steps

Run these commands after investigation; document results in this ticket.

```bash
# On a Raspberry Pi with Docker:
# 1. Build the test image
docker build -f Dockerfile.rgbmatrix-test -t rgbmatrix-test .

# 2. Verify import works
docker run --rm rgbmatrix-test python -c "import rgbmatrix; print('OK')"

# 3. Check image size
docker images rgbmatrix-test --format "{{.Size}}"
```

---

## Notes

- This is a SPIKE (investigation) ticket. The output is documentation and a proven Dockerfile snippet, not production code.
- The `RGBMatrixEmulator` package (`rgbmatrixemulator` on PyPI) is a pure-Python drop-in that does NOT need hardware. It is already in `pyproject.toml` under `[project.optional-dependencies.emulator]`. The emulator path is the default for non-Pi builds.
- Multi-arch Docker builds (ARM + x86) are desirable but not required. The primary target is ARM (Raspberry Pi 4/5).
- If rgbmatrix cannot be easily containerized, an alternative is to install it on the host and mount it into the container via a volume. Document this as a fallback.
