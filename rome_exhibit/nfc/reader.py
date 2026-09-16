"""
NFC reader hardware wrapper.

Wraps the PN532 reader so the rest of the app only ever calls
scan_once() and gets back a tag's UID (or None if nothing's there).
Nothing else in the app needs to know this is SPI/PN532-specific.
"""

try:
    import board
    import busio
    from digitalio import DigitalInOut
    from adafruit_pn532.spi import PN532_SPI
    LIBRARIES_AVAILABLE = True
except (ImportError, NotImplementedError):
    # This happens on a laptop, or on the Pi before the libraries are
    # installed / SPI is enabled. The app should still run - it just
    # won't get real scans until this is fixed.
    LIBRARIES_AVAILABLE = False


class NFCReader:
    def __init__(self, cs_pin_name="D5"):
        self.pn532 = None

        if not LIBRARIES_AVAILABLE:
            print("[nfc] adafruit-circuitpython-pn532 / blinka not installed - "
                  "NFC reader disabled, running without hardware")
            return

        try:
            spi = busio.SPI(board.SCK, board.MOSI, board.MISO)
            cs_pin = DigitalInOut(getattr(board, cs_pin_name))
            self.pn532 = PN532_SPI(spi, cs_pin, debug=False)
            ic, ver, rev, support = self.pn532.firmware_version
            print(f"[nfc] PN532 connected - firmware v{ver}.{rev}")
            self.pn532.SAM_configuration()
        except Exception as err:
            print(f"[nfc] could not connect to PN532 ({err}) - "
                  "check wiring and that SPI is enabled")
            self.pn532 = None

    @property
    def is_connected(self):
        return self.pn532 is not None

    def scan_once(self, timeout=0.2):
        """Look for a tag right now.

        Returns the tag's UID as an uppercase hex string like
        'A1B2C3D4', or None if no tag is present or the reader
        isn't connected.
        """
        if not self.pn532:
            return None
        try:
            uid = self.pn532.read_passive_target(timeout=timeout)
        except Exception as err:
            print(f"[nfc] read error: {err}")
            return None
        if uid is None:
            return None
        return uid.hex().upper()
