#!/usr/bin/env python3
"""LED Matrix FastAPI Web Interface startup script.

Replaces web_interface/start.py as the entry point for the web service.
"""

import os
import socket
import subprocess
import sys
from pathlib import Path


def get_local_ips() -> list[str]:
    """Get list of local IP addresses the service will be accessible on."""
    ips: list[str] = []

    # Check if AP mode is active
    try:
        result = subprocess.run(
            ["systemctl", "is-active", "hostapd"],
            capture_output=True,
            text=True,
            timeout=2,
        )
        if result.returncode == 0 and result.stdout.strip() == "active":
            ips.append("192.168.4.1 (AP Mode)")
    except Exception:
        pass

    # Get IPs from hostname -I
    try:
        result = subprocess.run(
            ["hostname", "-I"],
            capture_output=True,
            text=True,
            timeout=2,
        )
        if result.returncode == 0:
            for ip in result.stdout.strip().split():
                ip = ip.strip()
                if ip and not ip.startswith("127.") and ip != "192.168.4.1":
                    ips.append(ip)
    except Exception:
        pass

    # Fallback: try socket method
    if not ips:
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            try:
                s.connect(("8.8.8.8", 80))
                ip = s.getsockname()[0]
                if ip and not ip.startswith("127."):
                    ips.append(ip)
            finally:
                s.close()
        except Exception:
            pass

    return ips if ips else ["localhost"]


def main() -> None:
    """Start the FastAPI application with uvicorn."""
    # Ensure project root is on sys.path
    project_root = Path(__file__).resolve().parent.parent.parent
    os.chdir(project_root)
    sys.path.insert(0, str(project_root))

    print("Starting LED Matrix Web Interface (FastAPI)...")
    print("Web server binding to: 0.0.0.0:5000")

    ips = get_local_ips()
    if ips:
        print("Access the interface at:")
        for ip in ips:
            if "AP Mode" in ip:
                print(f"  - http://192.168.4.1:5000 (AP Mode - connect to LEDMatrix-Setup WiFi)")
            else:
                print(f"  - http://{ip}:5000")
    else:
        print("  - http://localhost:5000 (local only)")

    import uvicorn

    uvicorn.run(
        "src.api.main:app",
        host="0.0.0.0",
        port=5000,
        log_level="info",
    )


if __name__ == "__main__":
    main()
