"""Tests for FastAPI SPA (Angular) static file serving."""

from pathlib import Path
from unittest.mock import patch

import pytest

from src.api.main import create_app


@pytest.mark.unit
class TestSPAMount:
    """Test that FastAPI serves the Angular SPA correctly."""

    def _create_app_with_spa(self, tmp_path: Path):
        """Helper: create a fake SPA dist and build the FastAPI app.

        Patches PROJECT_ROOT so create_app() computes spa_dist_dir
        inside the function using the patched value.
        """
        # Create fake SPA dist structure
        browser_dir = tmp_path / "frontend" / "dist" / "ledmatrix" / "browser"
        browser_dir.mkdir(parents=True)
        index_html = browser_dir / "index.html"
        index_html.write_text("<html><body>Angular App</body></html>")
        # Create a fake JS asset to test static file serving
        (browser_dir / "main.js").write_text("console.log('app');")

        with patch("src.api.main.PROJECT_ROOT", tmp_path):
            app = create_app()

        return app

    def test_spa_catch_all_returns_index_html(self, tmp_path: Path):
        """Non-API, non-reserved paths return index.html for client-side routing."""
        from fastapi.testclient import TestClient

        app = self._create_app_with_spa(tmp_path)
        client = TestClient(app)

        response = client.get("/some/angular/route")
        assert response.status_code == 200
        assert "Angular App" in response.text

    def test_spa_serves_static_assets(self, tmp_path: Path):
        """Static files (JS, CSS) in the dist directory are served directly."""
        from fastapi.testclient import TestClient

        app = self._create_app_with_spa(tmp_path)
        client = TestClient(app)

        response = client.get("/main.js")
        assert response.status_code == 200
        assert "console.log" in response.text

    def test_spa_catch_all_does_not_intercept_api(self, tmp_path: Path):
        """API routes must NOT be intercepted by the SPA catch-all."""
        from fastapi.testclient import TestClient

        app = self._create_app_with_spa(tmp_path)
        client = TestClient(app)

        response = client.get("/api/v3/system/health")
        assert "Angular App" not in response.text

    def test_spa_catch_all_does_not_intercept_docs(self, tmp_path: Path):
        """OpenAPI docs must NOT be intercepted by the SPA catch-all."""
        from fastapi.testclient import TestClient

        app = self._create_app_with_spa(tmp_path)
        client = TestClient(app)

        response = client.get("/docs")
        assert response.status_code == 200
        assert "Angular App" not in response.text

    def test_spa_catch_all_does_not_intercept_v3(self, tmp_path: Path):
        """HTMX pages at /v3/ must NOT be intercepted by the SPA catch-all."""
        from fastapi.testclient import TestClient

        app = self._create_app_with_spa(tmp_path)
        client = TestClient(app)

        response = client.get("/v3")
        assert "Angular App" not in response.text

    def test_no_spa_mount_when_dist_missing(self, tmp_path: Path):
        """When frontend/dist doesn't exist, app should still work without SPA."""
        from fastapi.testclient import TestClient

        with patch("src.api.main.PROJECT_ROOT", tmp_path):
            app = create_app()

        client = TestClient(app)

        # Root should still redirect to /v3
        response = client.get("/", follow_redirects=False)
        assert response.status_code == 307
