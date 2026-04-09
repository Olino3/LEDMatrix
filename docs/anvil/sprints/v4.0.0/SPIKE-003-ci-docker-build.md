# SPIKE-003 — CI Pipeline for Docker Image Build

> **For Claude:** Use `superpowers:writing-plans` before touching any files. Use `superpowers:test-driven-development` for any logic you add.

**Status:** Open
**Phase:** v4.0.0 — Containerization
**Type:** Chore
**Depends on:** [DOCK-001](DOCK-001-dockerfile-multi-stage.md)
**Blocks:** _(none)_

---

## Context

With a Dockerfile in the repository, the CI pipeline should verify that the Docker image builds successfully on every push/PR. Optionally, tagged releases could push the built image to a container registry (GitHub Container Registry).

This SPIKE sets up the GitHub Actions workflow for Docker image builds and investigates multi-architecture build support (ARM for Pi + x86 for dev).

---

## Acceptance Criteria

- [ ] GitHub Actions workflow file exists for Docker builds
- [ ] Workflow triggers on pushes to `develop` and PRs that modify Docker-related files
- [ ] `docker build` runs successfully in CI
- [ ] Build failures block PR merge
- [ ] (Optional) Tagged releases push image to GitHub Container Registry

---

## Implementation Checklist

### 1. Create GitHub Actions workflow

- [ ] Create `.github/workflows/docker-build.yml`
- [ ] Trigger on push to `develop` and PRs modifying: `Dockerfile`, `compose.yml`, `compose.dev.yml`, `.dockerignore`
- [ ] Use `docker/setup-buildx-action` for advanced build features
- [ ] Use `docker/build-push-action` to build the image
- [ ] Set `push: false` for PR builds (build-only, no push)

### 2. Add build caching

- [ ] Use GitHub Actions cache for Docker layers
- [ ] Configure `cache-from` and `cache-to` in the build action

### 3. (Optional) Multi-arch build

- [ ] Investigate `docker buildx build --platform linux/arm64,linux/amd64`
- [ ] Document whether the Dockerfile supports multi-arch (Node and Python base images do)
- [ ] Note if rgbmatrix compilation is architecture-specific

### 4. (Optional) Registry push on release

- [ ] On tag push (`v*`), push to `ghcr.io/olino3/ledmatrix:TAG`
- [ ] Use `docker/login-action` with `GITHUB_TOKEN`

### 5. Commit

```bash
git add .github/workflows/docker-build.yml
git commit -m "ci(docker): add GitHub Actions workflow for Docker image builds"
```

---

## Verification Steps

```bash
# 1. Workflow file exists
test -f .github/workflows/docker-build.yml && echo "OK: workflow exists"

# 2. Workflow triggers on Dockerfile changes
grep -q "Dockerfile" .github/workflows/docker-build.yml && echo "OK: Dockerfile trigger"

# 3. Local build still works
docker build -t ledmatrix:ci-test . && echo "OK: local build" || echo "SKIP: Docker not available"
```

---

## Notes

- This is a SPIKE ticket. The primary output is a working CI workflow file.
- Multi-arch builds are nice-to-have but add significant CI time. Start with x86-only (for build validation) and add ARM later.
- The CI workflow should NOT run the container (that requires Pi hardware or emulator X11). It only verifies the build succeeds.
- GitHub Container Registry (`ghcr.io`) is free for public repos. Private repos have storage limits.
- Consider adding a `docker compose config` validation step to catch YAML errors in the Compose files.
