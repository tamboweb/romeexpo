"""
LED strip hardware wrapper.

Wraps rpi_ws281x so the rest of the app just calls
set_effect(mode, color_hex) or idle() / off(). Nothing else needs to
know this is a WS2812B strip on GPIO18.
"""

import threading
import time

try:
    from rpi_ws281x import PixelStrip, Color
    LIBRARY_AVAILABLE = True
except (ImportError, NotImplementedError):
    LIBRARY_AVAILABLE = False

LED_COUNT = 60          # how many LEDs are on your strip
LED_PIN = 18             # GPIO18 (PWM0) - standard pin for WS2812B on a Pi
LED_FREQ_HZ = 800000
LED_DMA = 10
LED_BRIGHTNESS = 120     # 0-255. Kept well under max - see brief: "should
                         # not constantly use maximum brightness"
LED_INVERT = False
LED_CHANNEL = 0


def hex_to_rgb(hex_color):
    hex_color = hex_color.lstrip('#')
    return tuple(int(hex_color[i:i + 2], 16) for i in (0, 2, 4))


class LightingController:
    def __init__(self):
        self.strip = None
        self._stop_event = threading.Event()
        self._thread = None

        if not LIBRARY_AVAILABLE:
            print("[lighting] rpi_ws281x not installed - LEDs disabled, "
                  "running without hardware")
            return

        try:
            self.strip = PixelStrip(LED_COUNT, LED_PIN, LED_FREQ_HZ, LED_DMA,
                                     LED_INVERT, LED_BRIGHTNESS, LED_CHANNEL)
            self.strip.begin()
        except Exception as err:
            print(f"[lighting] could not start LED strip ({err}) - "
                  "this usually means the app isn't running as root, "
                  "or the strip isn't wired to GPIO18")
            self.strip = None

    @property
    def is_connected(self):
        return self.strip is not None

    def _set_solid(self, rgb):
        if not self.strip:
            return
        r, g, b = rgb
        for i in range(self.strip.numPixels()):
            self.strip.setPixelColor(i, Color(r, g, b))
        self.strip.show()

    def _pulse(self, rgb, cycles=3):
        if not self.strip:
            return
        r, g, b = rgb
        for _ in range(cycles):
            for level in list(range(20, 101, 5)) + list(range(100, 19, -5)):
                if self._stop_event.is_set():
                    return
                factor = level / 100
                self._set_solid((int(r * factor), int(g * factor), int(b * factor)))
                time.sleep(0.03)

    def _stop_current_effect(self):
        self._stop_event.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=1)

    def set_effect(self, mode, color_hex):
        """Start the lighting effect for a scanned artifact."""
        self._stop_current_effect()
        self._stop_event = threading.Event()
        rgb = hex_to_rgb(color_hex)

        if mode == "ember":
            target = self._pulse
            args = (rgb, 3)
        else:
            # gold / amber / marble / anything else -> steady glow
            target = self._set_solid
            args = (rgb,)

        self._thread = threading.Thread(target=target, args=args, daemon=True)
        self._thread.start()

    def idle(self):
        """Dim warm glow shown while waiting for an artifact."""
        self.set_effect("solid", "#2A2018")

    def off(self):
        self._stop_current_effect()
        self._set_solid((0, 0, 0))
