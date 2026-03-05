#!/bin/bash
echo "⚠  DEPRECATED: stop_display.sh is deprecated. Use: matrix service stop" >&2
echo "   This script will be removed in a future release." >&2

# Get the current user
CURRENT_USER=$(whoami)

echo "Stopping LED Matrix Display Service for user: $CURRENT_USER..."

# Stop the service
sudo systemctl stop ledmatrix.service

# Check the status
echo "Service status:"
sudo systemctl status ledmatrix.service

echo ""
echo "LED Matrix Display Service has been stopped."
echo ""
echo "To start the service again:"
echo "  sudo systemctl start ledmatrix.service" 