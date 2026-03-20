"""Font API routes — /fonts/* endpoints."""

from __future__ import annotations

import base64
import io
import json
from pathlib import Path
from typing import Any

from fastapi import APIRouter, File, Form, Query, Request, UploadFile
from fastapi.responses import JSONResponse

from src.api.models.common import API_RESPONSES, API_RESPONSES_WITH_404
from src.logging_config import get_logger

logger = get_logger("api.fonts")

router = APIRouter(prefix="/fonts", tags=["fonts"])

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
FONTS_DIR = PROJECT_ROOT / "fonts"
USER_FONTS_DIR = FONTS_DIR / "user"
FONT_OVERRIDES_FILE = PROJECT_ROOT / "config" / "font_overrides.json"

ALLOWED_FONT_EXTENSIONS = {".bdf", ".ttf", ".otf"}
DESIGN_TOKENS = {"xs": 8, "sm": 10, "md": 12, "lg": 16, "xl": 20, "xxl": 24}


# ---- helpers ----------------------------------------------------------------


def _error(error_code: str, message: str, status: int = 400) -> JSONResponse:
    return JSONResponse(
        {"status": "error", "error_code": error_code, "message": message},
        status_code=status,
    )


def _success(data: Any = None, message: str | None = None) -> dict[str, Any]:
    resp: dict[str, Any] = {"status": "success"}
    if data is not None:
        resp["data"] = data
    if message is not None:
        resp["message"] = message
    return resp


def _scan_fonts(directory: Path) -> list[dict[str, Any]]:
    """Scan a directory for font files and return metadata."""
    fonts: list[dict[str, Any]] = []
    if not directory.exists():
        return fonts
    for path in sorted(directory.iterdir()):
        if path.is_file() and path.suffix.lower() in ALLOWED_FONT_EXTENSIONS:
            fonts.append(
                {
                    "filename": path.name,
                    "family": path.stem,
                    "format": path.suffix.lstrip(".").lower(),
                    "size_bytes": path.stat().st_size,
                    "path": str(path.relative_to(PROJECT_ROOT)),
                }
            )
    return fonts


def _read_overrides() -> dict[str, Any]:
    if FONT_OVERRIDES_FILE.exists():
        try:
            data: dict[str, Any] = json.loads(FONT_OVERRIDES_FILE.read_text())
            return data
        except (json.JSONDecodeError, OSError) as exc:
            logger.warning("Failed to read font overrides: %s", exc)
    return {}


def _write_overrides(data: dict) -> None:
    """Write font_overrides.json."""
    FONT_OVERRIDES_FILE.parent.mkdir(parents=True, exist_ok=True)
    FONT_OVERRIDES_FILE.write_text(json.dumps(data, indent=2))


# ---- routes -----------------------------------------------------------------


@router.get("/catalog", response_model=None, responses=API_RESPONSES)
async def get_font_catalog() -> dict[str, Any] | JSONResponse:
    """List available font files from system and user directories."""
    try:
        system_fonts = _scan_fonts(FONTS_DIR)
        user_fonts = _scan_fonts(USER_FONTS_DIR)
        return _success(data={"catalog": {"system": system_fonts, "user": user_fonts}})
    except Exception as exc:
        logger.error("Failed to scan font catalog: %s", exc)
        return _error("FONT_ERROR", str(exc), 500)


@router.get("/tokens", response_model=None, responses=API_RESPONSES)
async def get_design_tokens() -> dict[str, Any] | JSONResponse:
    """Return hardcoded design token sizes."""
    return _success(data={"tokens": DESIGN_TOKENS})


@router.get("/overrides", response_model=None, responses=API_RESPONSES)
async def get_font_overrides() -> dict[str, Any] | JSONResponse:
    """Read font overrides configuration."""
    try:
        overrides = _read_overrides()
        return _success(data={"overrides": overrides})
    except Exception as exc:
        logger.error("Failed to read font overrides: %s", exc)
        return _error("FONT_ERROR", str(exc), 500)


@router.post("/overrides", response_model=None, responses=API_RESPONSES)
async def save_font_overrides(request: Request) -> dict[str, Any] | JSONResponse:
    """Write font overrides configuration."""
    try:
        body = await request.json()
    except Exception:
        return _error("INVALID_INPUT", "Request body must be valid JSON")

    try:
        _write_overrides(body)
        return _success(message="Font overrides saved")
    except Exception as exc:
        logger.error("Failed to save font overrides: %s", exc)
        return _error("FONT_ERROR", str(exc), 500)


@router.delete("/overrides/{element_key}", response_model=None, responses=API_RESPONSES_WITH_404)
async def delete_font_override(element_key: str) -> dict[str, Any] | JSONResponse:
    """Remove a single key from font overrides."""
    try:
        overrides = _read_overrides()
        if element_key not in overrides:
            return _error("NOT_FOUND", f"Override key '{element_key}' not found", 404)
        del overrides[element_key]
        _write_overrides(overrides)
        return _success(message=f"Override '{element_key}' removed")
    except Exception as exc:
        logger.error("Failed to delete font override '%s': %s", element_key, exc)
        return _error("FONT_ERROR", str(exc), 500)


@router.post("/upload", response_model=None, responses=API_RESPONSES)
async def upload_font(
    font_file: UploadFile = File(...),
    font_family: str | None = Form(None),
) -> dict[str, Any] | JSONResponse:
    """Upload a font file to the user fonts directory."""
    if not font_file.filename:
        return _error("INVALID_INPUT", "No filename provided")

    ext = Path(font_file.filename).suffix.lower()
    if ext not in ALLOWED_FONT_EXTENSIONS:
        return _error(
            "INVALID_INPUT",
            f"Invalid font format '{ext}'. Allowed: {', '.join(sorted(ALLOWED_FONT_EXTENSIONS))}",
        )

    # Determine target filename
    if font_family:
        safe_name = "".join(c for c in font_family if c.isalnum() or c in "-_.")
        target_name = f"{safe_name}{ext}"
    else:
        target_name = font_file.filename

    USER_FONTS_DIR.mkdir(parents=True, exist_ok=True)
    target_path = USER_FONTS_DIR / target_name

    try:
        content = await font_file.read()
        target_path.write_bytes(content)
        return _success(
            data={"filename": target_name, "path": str(target_path.relative_to(PROJECT_ROOT))},
            message=f"Font '{target_name}' uploaded successfully",
        )
    except Exception as exc:
        logger.error("Failed to upload font: %s", exc)
        return _error("FONT_ERROR", str(exc), 500)


@router.get("/preview", response_model=None, responses=API_RESPONSES)
async def preview_font(
    font: str = Query(..., description="Font filename or path"),
    text: str = Query("Hello", description="Text to render"),
    bg: str = Query("#000000", description="Background color"),
    fg: str = Query("#FFFFFF", description="Foreground color"),
    size: int = Query(16, description="Font size in pixels"),
) -> dict[str, Any] | JSONResponse:
    """Render a text preview using the specified font. Returns base64 PNG."""
    try:
        from PIL import Image, ImageDraw, ImageFont
    except ImportError:
        return _error("DEPENDENCY_MISSING", "Pillow (PIL) is not installed", 503)

    # Resolve font path
    font_path = None
    for search_dir in (USER_FONTS_DIR, FONTS_DIR):
        candidate = search_dir / font
        if candidate.exists():
            font_path = candidate
            break

    if font_path is None:
        # Try as absolute path within project
        candidate = PROJECT_ROOT / font
        if candidate.exists() and candidate.suffix.lower() in ALLOWED_FONT_EXTENSIONS:
            font_path = candidate

    try:
        pil_font: Any
        if font_path and font_path.suffix.lower() in (".ttf", ".otf"):
            pil_font = ImageFont.truetype(str(font_path), size)
        else:
            pil_font = ImageFont.load_default()

        img = Image.new("RGB", (max(len(text) * size, 64), size + 8), bg)
        draw = ImageDraw.Draw(img)
        draw.text((2, 2), text, fill=fg, font=pil_font)

        # Crop to content
        bbox = img.getbbox()
        if bbox:
            img = img.crop((0, 0, bbox[2] + 4, bbox[3] + 4))

        buf = io.BytesIO()
        img.save(buf, format="PNG")
        b64 = base64.b64encode(buf.getvalue()).decode()

        return _success(data={"image": b64, "format": "png", "encoding": "base64"})
    except Exception as exc:
        logger.error("Failed to generate font preview: %s", exc)
        return _error("FONT_ERROR", str(exc), 500)


@router.delete("/{font_family}", response_model=None, responses=API_RESPONSES_WITH_404)
async def delete_font(font_family: str) -> dict[str, Any] | JSONResponse:
    """Delete a user-uploaded font. System fonts cannot be deleted."""
    if not USER_FONTS_DIR.exists():
        return _error("NOT_FOUND", "No user fonts directory", 404)

    # Find matching file in user fonts directory
    deleted = []
    for path in USER_FONTS_DIR.iterdir():
        if path.is_file() and path.stem == font_family:
            path.unlink()
            deleted.append(path.name)

    if not deleted:
        return _error("NOT_FOUND", f"Font '{font_family}' not found in user fonts", 404)

    return _success(
        data={"deleted": deleted},
        message=f"Deleted font file(s): {', '.join(deleted)}",
    )
