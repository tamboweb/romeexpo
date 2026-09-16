"""
Run this on its own (not part of the main app) to find out the UID of
a physical NFC tag, so you can add it to config/tag_map.json.

Usage:
    sudo venv/bin/python3 tools/scan_uid.py

(needs sudo because talking to the SPI hardware requires it)

Hold each tag against the reader one at a time. Write down the UID
it prints, and which artifact that physical tag belongs to.
"""

import sys
import time
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from nfc.reader import NFCReader  # noqa: E402


def main():
    reader = NFCReader()
    if not reader.is_connected:
        print("Could not connect to the PN532. Check:")
        print("  - wiring (SCK/MOSI/MISO/CS/GND/VCC)")
        print("  - that SPI is enabled (dietpi-config -> Advanced Options -> SPI)")
        print("  - that you ran this with sudo")
        return

    print("Ready. Hold a tag against the reader...")
    print("(press Ctrl+C to stop)\n")

    last_uid = None
    try:
        while True:
            uid = reader.scan_once(timeout=0.3)
            if uid and uid != last_uid:
                print(f"Tag detected -> UID: {uid}")
                last_uid = uid
            elif uid is None:
                last_uid = None
            time.sleep(0.1)
    except KeyboardInterrupt:
        print("\nStopped.")


if __name__ == "__main__":
    main()
