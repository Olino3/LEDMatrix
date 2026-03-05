#!/bin/bash
echo "⚠  DEPRECATED: start_display.sh is deprecated. Use: matrix service start" >&2
echo "   This script will be removed in a future release." >&2

# Get the current user
CURRENT_USER=$(whoami)

echo "Starting LED Matrix Display Service for user: $CURRENT_USER..."

# Start the service
sudo systemctl start ledmatrix.service

# Check the status
echo "Service status:"
sudo systemctl status ledmatrix.service

echo ""
echo "LED Matrix Display Service has been started."
echo ""
echo "To stop the service:"
echo "  sudo systemctl stop ledmatrix.service" 