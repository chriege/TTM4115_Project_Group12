from __future__ import annotations

from typing import Callable, Optional

from .config import DropoffConfig
from .hardware import create_led, create_state_display


class DropoffConfirmationController:
    """Business logic + actions for the pickup dispatch state machine."""

    def __init__(
        self,
        config: DropoffConfig,
        status_callback: Optional[Callable[[str], None]] = None,
        notification_callback: Optional[Callable[[str], None]] = None,
        issue_callback: Optional[Callable[[str], None]] = None,
    ) -> None:
        self.config = config
        self.stm = None
        self.current_state = "created"
        self.current_status = "WAITING_FOR_DRONE"
        self.led_mode = "OFF"
        self.last_issue_reason: Optional[str] = None
        self._status_callback = status_callback or (lambda status: print(f"[STATUS] {status}"))
        self._notification_callback = notification_callback or (
            lambda message: print(f"[NOTIFY] {message}")
        )
        self._issue_callback = issue_callback or (lambda message: print(f"[ISSUE] {message}"))
        self.led = create_led(config.led_pin, config.force_mock_led)
        self.state_display = create_state_display(config.force_mock_display)
        self._clear_display()

    def set_callbacks(
        self,
        status_callback: Optional[Callable[[str], None]] = None,
        notification_callback: Optional[Callable[[str], None]] = None,
        issue_callback: Optional[Callable[[str], None]] = None,
    ) -> None:
        if status_callback is not None:
            self._status_callback = status_callback
        if notification_callback is not None:
            self._notification_callback = notification_callback
        if issue_callback is not None:
            self._issue_callback = issue_callback

    # state tracking helpers
    def set_state_waiting_for_drone(self) -> None:
        self.last_issue_reason = None
        self.current_state = "waiting_for_drone"
        self.current_status = "WAITING_FOR_DRONE"
        self._status_callback(self.current_status)
        self._clear_display()

    def set_state_in_flight_to_pickup(self) -> None:
        self.last_issue_reason = None
        self.current_state = "in_flight_to_pickup"
        self._show_state(self.current_state)

    def set_state_at_pickup(self) -> None:
        self.last_issue_reason = None
        self.current_state = "at_pickup"
        self._show_state(self.current_state)

    def set_state_pickup_delayed(self) -> None:
        self.current_state = "pickup_delayed"
        self._show_state(self.current_state)

    def set_state_package_loaded(self) -> None:
        self.last_issue_reason = None
        self.current_state = "package_loaded"
        self._show_state(self.current_state)

    def set_state_in_flight(self) -> None:
        self.last_issue_reason = None
        self.current_state = "in_flight"
        self._show_state(self.current_state)

    # machine actions from diagram
    def set_status_at_pickup(self) -> None:
        self.current_status = "AT_PICKUP"
        self._status_callback(self.current_status)

    def set_status_to_restaurant(self) -> None:
        self.current_status = "TO_RESTAURANT"
        self._status_callback(self.current_status)

    def notify_heading_to_restaurant(self) -> None:
        self._notification_callback(
            f"Drone dispatched to restaurant for order {self.config.order_id}."
        )

    def notify_restaurant_ready(self) -> None:
        self._notification_callback(
            f"Drone is at pickup for order {self.config.order_id}. Restaurant can load package."
        )

    def set_status_pickup_delayed(self) -> None:
        self.current_status = "PICKUP_DELAYED"
        self._status_callback(self.current_status)

    def hold_position(self) -> None:
        self._notification_callback(
            f"Order {self.config.order_id} not ready. Holding position and retrying pickup."
        )

    def authorize_takeoff(self) -> None:
        self.current_status = "PACKAGE_LOADED"
        self.led_on_solid()
        self._status_callback(self.current_status)
        self._notification_callback(
            f"Package loaded for order {self.config.order_id}. Authorizing takeoff."
        )

    def set_status_in_flight(self) -> None:
        self.current_status = "IN_FLIGHT"
        self.led_off()
        self._status_callback(self.current_status)

    def notify_in_flight(self) -> None:
        self._notification_callback(f"Order {self.config.order_id} is now in flight.")

    def led_off(self) -> None:
        self.led_mode = "OFF"
        self.led.off()

    def led_blink_waiting(self) -> None:
        self.led_mode = "BLINKING"
        blink_fn = getattr(self.led, "blink", None)
        if callable(blink_fn):
            blink_fn(on_time=0.3, off_time=0.3, background=True)
            return
        self.led.on()

    def led_on_solid(self) -> None:
        self.led_mode = "ON"
        self.led.on()

    def mark_complete(self) -> None:
        if self.stm is not None:
            self.stm.send("workflow_completed")

    # public events for pickup dispatch flow
    def event_pickup_arrived(self) -> None:
        self._send("pickup_arrived")

    def event_not_ready(self) -> None:
        self._send("not_ready")

    def event_package_loaded(self) -> None:
        self._send("package_loaded")

    def event_takeoff_confirmed(self) -> None:
        self._send("takeoff_confirmed")

    def event_reset(self) -> None:
        self._send("reset")

    # Backward-compatible aliases from the previous dropoff flow.
    def event_arrived_at_dropoff(self) -> None:
        self.event_pickup_arrived()

    def submit_customer_code(self, code: str) -> bool:
        del code
        if self.current_state not in {"at_pickup", "pickup_delayed"}:
            self._notification_callback(
                "Signal ignored: machine is not at pickup."
            )
            return False
        self.event_package_loaded()
        return True

    def event_dropoff_confirmed(self) -> None:
        self.event_takeoff_confirmed()

    def event_dropoff_failed(self, reason: str = "not_ready") -> None:
        self.last_issue_reason = reason
        self.event_not_ready()

    def event_unresolved_dropoff(self, reason: str = "not_ready") -> None:
        self.last_issue_reason = reason
        self.event_not_ready()

    def shutdown(self) -> None:
        self.led_off()
        close_fn = getattr(self.led, "close", None)
        if callable(close_fn):
            close_fn()
        display_close_fn = getattr(self.state_display, "close", None)
        if callable(display_close_fn):
            display_close_fn()

    def _show_state(self, state: str) -> None:
        show_state_fn = getattr(self.state_display, "show_state", None)
        if callable(show_state_fn):
            show_state_fn(state)

    def _clear_display(self) -> None:
        clear_fn = getattr(self.state_display, "clear", None)
        if callable(clear_fn):
            clear_fn()
            return

        show_state_fn = getattr(self.state_display, "show_state", None)
        if callable(show_state_fn):
            show_state_fn("")

    def _send(self, trigger: str) -> None:
        if self.stm is None:
            raise RuntimeError("State machine not attached to controller.")
        self.stm.send(trigger)
