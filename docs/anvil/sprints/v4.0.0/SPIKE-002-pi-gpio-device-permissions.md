# SPIKE-002 — Pi GPIO and Device Permissions

> **For Claude:** Use `superpowers:writing-plans` before touching any files. Use `superpowers:test-driven-development` for any logic you add.

**Status:** Open
**Phase:** v4.0.0 — Containerization
**Type:** Chore
**Depends on:** [DOCK-003](DOCK-003-compose-production.md)
**Blocks:** _(none)_

---

## Context

Running the LED matrix display in a Docker container on Raspberry Pi requires access to GPIO pins and memory-mapped device files (`/dev/mem`, `/dev/gpiomem`). The ROADMAP specifies `--privileged` mode, but this grants the container full host access, which is a security concern.

This SPIKE investigates the minimum set of capabilities and device mappings needed for the LED matrix to function, with the goal of reducing the security surface compared to full `--privileged` mode.

---

## Acceptance Criteria

- [ ] Document which `/dev` devices the rgbmatrix library accesses
- [ ] Test `--privileged` mode and confirm LED matrix works in container
- [ ] Test minimal capabilities approach (`--cap-add`, `--device`) as alternative
- [ ] Document the recommended approach with security trade-offs
- [ ] Provide exact `compose.yml` device/capability configuration

---

## Implementation Checklist

### 1. Audit device access requirements

- [ ] Run `strace` on the display process to identify `/dev/*` file opens
- [ ] Document which devices are opened: `/dev/mem`, `/dev/gpiomem`, others
- [ ] Check if `rgbmatrix` uses `mmap()` for GPIO access (requires `SYS_RAWIO` capability)

### 2. Test privileged mode

- [ ] Run the container with `--privileged` on a Pi
- [ ] Confirm the LED matrix display works correctly
- [ ] Note any permission errors or warnings

### 3. Test minimal capabilities

- [ ] Try `--cap-add=SYS_RAWIO --device=/dev/mem --device=/dev/gpiomem`
- [ ] If that fails, try adding `--cap-add=DAC_OVERRIDE`
- [ ] Document which combination works and which does not

### 4. Document findings

- [ ] Write recommended configuration for `compose.yml`
- [ ] Note security implications of each approach
- [ ] Provide fallback instructions if minimal capabilities do not work

### 5. Commit

```bash
git add sprints/v4.0.0/SPIKE-002-pi-gpio-device-permissions.md
git commit -m "docs(docker): document Pi GPIO device permissions for containers"
```

---

## Verification Steps

These must be run on a Raspberry Pi with a connected LED matrix.

```bash
# 1. Privileged mode test
docker run --rm --privileged \
  -v /dev/mem:/dev/mem \
  ledmatrix:latest python run.py &
sleep 5 && echo "OK: display started" && kill %1

# 2. Minimal capabilities test
docker run --rm \
  --cap-add=SYS_RAWIO \
  --device=/dev/mem \
  --device=/dev/gpiomem \
  ledmatrix:latest python run.py &
sleep 5 && echo "OK: minimal caps work" && kill %1
```

---

## Notes

- This SPIKE requires physical Raspberry Pi hardware with a connected LED matrix. It cannot be fully tested in emulator mode.
- `--privileged` is the safe default that is known to work. The minimal capabilities approach is an optimization, not a requirement for Phase 4.
- If minimal capabilities work, update `compose.yml` in DOCK-003 to use them instead of `--privileged`. If not, document the finding and keep `--privileged`.
- Some Raspberry Pi OS configurations require the user to be in the `gpio` group. Inside a container running as root, this should not be an issue.
- Consider documenting `--security-opt=no-new-privileges` as an additional hardening measure.
