from __future__ import annotations

import threading
import time
from typing import Optional

try:
    from gpiozero import LED as GpioZeroLED
except Exception:
    GpioZeroLED = None

try:
    from sense_hat import SenseHat
except Exception:
    SenseHat = None


class MockLED:
    """Fallback LED used when running off Raspberry Pi hardware."""

    def __init__(self, pin: int) -> None:
        self.pin = pin
        self.is_lit = False
        self.is_blinking = False

    def on(self) -> None:
        self.is_blinking = False
        self.is_lit = True
        print(f"[MockLED] GPIO {self.pin}: ON")

    def off(self) -> None:
        self.is_blinking = False
        self.is_lit = False
        print(f"[MockLED] GPIO {self.pin}: OFF")

    def blink(
        self,
        on_time: float = 0.3,
        off_time: float = 0.3,
        n: Optional[int] = None,
        background: bool = True,
    ) -> None:
        del on_time, off_time, n, background
        self.is_blinking = True
        self.is_lit = True
        print(f"[MockLED] GPIO {self.pin}: BLINKING")

    def close(self) -> None:
        return None


class MockStateDisplay:
    """Fallback display used when Sense HAT is unavailable."""

    def __init__(self) -> None:
        self.last_state = "blank"
        self.last_message = ""

    def show_state(self, state: str) -> None:
        display_overrides = {
            "in_flight_to_pickup": "ACTIVATED",
        }
        self.last_state = state
        self.last_message = display_overrides.get(state, state.replace("_", " ").upper())
        print(f"[MockDisplay] state={state} message='{self.last_message}'")

    def clear(self) -> None:
        self.last_state = "blank"
        self.last_message = ""
        print("[MockDisplay] cleared")

    def close(self) -> None:
        return None


class SenseHatStateDisplay:
    """Sense HAT 8x8 LED matrix state display."""

    _STATE_STYLE = {
        "created": {"text": "CREATED", "color": (180, 180, 180)},
        "waiting_for_drone": {"text": "WAITING FOR DRONE", "color": (0, 0, 255)},
        "in_flight_to_pickup": {"text": "ACTIVATED", "color": (0, 0, 255)},
        "at_pickup": {"text": "AT PICKUP", "color": (255, 255, 0)},
        "pickup_delayed": {"text": "PICKUP DELAYED", "color": (255, 128, 0)},
        "package_loaded": {"text": "PACKAGE LOADED", "color": (0, 255, 255)},
        "in_flight": {"text": "IN FLIGHT", "color": (0, 255, 0)},
        # Backward-compatible mappings from previous flow.
        "approaching_dropoff": {"text": "APPROACHING DROPOFF", "color": (0, 0, 255)},
        "waiting_for_confirmation": {
            "text": "WAITING FOR CONFIRMATION",
            "color": (255, 255, 0),
        },
        "releasing_package": {"text": "RELEASING PACKAGE", "color": (0, 255, 255)},
        "delivered": {"text": "DELIVERED", "color": (0, 255, 0)},
        "delivery_issue": {"text": "DELIVERY ISSUE", "color": (255, 0, 0)},
    }

    def __init__(self) -> None:
        self._sense = SenseHat()
        self.last_state = "blank"
        self.last_message = ""
        self._current_color = (255, 255, 255)
        self._scroll_speed = 0.11
        self._loop_pause_s = 0.35
        self._state_lock = threading.Lock()
        self._stop_event = threading.Event()
        self._loop_thread = threading.Thread(
            target=self._scroll_loop,
            name="sensehat-state-scroll",
            daemon=True,
        )
        self._sense.clear()
        self._loop_thread.start()

    def show_state(self, state: str) -> None:
        style = self._STATE_STYLE.get(
            state, {"text": state.replace("_", " ").upper(), "color": (255, 255, 255)}
        )
        with self._state_lock:
            self.last_state = state
            self.last_message = style["text"]
            self._current_color = style["color"]

    def _scroll_loop(self) -> None:
        while not self._stop_event.is_set():
            with self._state_lock:
                message = self.last_message
                color = self._current_color
                speed = self._scroll_speed
                pause_s = self._loop_pause_s
            if not message:
                time.sleep(0.1)
                continue
            self._sense.show_message(
                message,
                scroll_speed=speed,
                text_colour=list(color),
                back_colour=[0, 0, 0],
            )
            slept = 0.0
            while slept < pause_s and not self._stop_event.is_set():
                time.sleep(0.05)
                slept += 0.05

    def clear(self) -> None:
        with self._state_lock:
            self.last_state = "blank"
            self.last_message = ""
            self._current_color = (255, 255, 255)
        self._sense.clear()

    def close(self) -> None:
        self._stop_event.set()
        if self._loop_thread.is_alive():
            self._loop_thread.join(timeout=1.0)
        self._sense.clear()


def create_led(pin: int, force_mock_led: bool):
    if force_mock_led or GpioZeroLED is None:
        return MockLED(pin)
    try:
        return GpioZeroLED(pin)
    except Exception:
        return MockLED(pin)


def create_state_display(force_mock_display: bool):
    if force_mock_display or SenseHat is None:
        return MockStateDisplay()
    try:
        return SenseHatStateDisplay()
    except Exception:
        return MockStateDisplay()
