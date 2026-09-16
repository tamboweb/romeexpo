#!/usr/bin/env bash
#
# Ancient Rome Exhibit - installer
#
# Run this on the Pi, from inside the cloned repo folder:
#   sudo ./install.sh
#
# It installs Python dependencies, sets up the auto-start service, and
# tells you what's left to do by hand (wiring, tag UIDs, kiosk browser).

set -e

if [ "$EUID" -ne 0 ]; then
  echo "Please run this with sudo: sudo ./install.sh"
  exit 1
fi

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
echo "Installing from: $PROJECT_DIR"

echo ""
echo "== Enabling SPI (needed for the NFC reader) =="
if command -v dietpi-config >/dev/null 2>&1; then
  /boot/dietpi/func/dietpi-set_hardware spi enable || \
    echo "Could not enable SPI automatically - open dietpi-config > Advanced Options > SPI and enable it by hand."
else
  echo "dietpi-config not found - if this isn't DietPi, enable SPI yourself (e.g. raspi-config > Interface Options > SPI)."
fi

echo ""
echo "== Installing system packages =="
apt-get update
apt-get install -y python3-dev python3-pip python3-venv build-essential

echo ""
echo "== Setting up the Python environment =="
cd "$PROJECT_DIR"
python3 -m venv venv
"$PROJECT_DIR/venv/bin/pip" install --upgrade pip
"$PROJECT_DIR/venv/bin/pip" install -r requirements.txt

echo ""
echo "== Setting up the auto-start service =="
sed "s|/root/rome_exhibit|$PROJECT_DIR|g" "$PROJECT_DIR/systemd/rome-exhibit.service" \
  > /etc/systemd/system/rome-exhibit.service
systemctl daemon-reload
systemctl enable rome-exhibit.service
systemctl restart rome-exhibit.service

echo ""
echo "================================================================"
echo " Done! The server is running and will start automatically on boot."
echo ""
echo " Still to do by hand:"
echo "   1. Wire up the PN532 reader and WS2812B strip (see README.md)."
echo "   2. Find your tags' UIDs:"
echo "        sudo $PROJECT_DIR/venv/bin/python3 $PROJECT_DIR/tools/scan_uid.py"
echo "      then fill them into config/tag_map.json"
echo "   3. Install Chromium in kiosk mode: dietpi-software -> Chromium (ID 113)"
echo "      and set SOFTWARE_CHROMIUM_AUTOSTART_URL=http://localhost:5000"
echo "      in /boot/dietpi.txt, then sudo reboot."
echo "================================================================"
