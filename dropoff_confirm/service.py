from __future__ import annotations

from typing import Callable, Optional

from stmpy import Driver

from .config import DropoffConfig
from .controller import DropoffConfirmationController
from .machine import build_dropoff_machine


class DropoffConfirmationService:
    def __init__(
        self,
        config: DropoffConfig,
        status_callback: Optional[Callable[[str], None]] = None,
        notification_callback: Optional[Callable[[str], None]] = None,
        issue_callback: Optional[Callable[[str], None]] = None,
    ) -> None:
        self.controller = DropoffConfirmationController(
            config,
            status_callback=status_callback,
            notification_callback=notification_callback,
            issue_callback=issue_callback,
        )
        pickup_retry_timeout_ms = (
            config.pickup_retry_timeout_ms
            if config.pickup_retry_timeout_ms
            else config.confirmation_timeout_ms
        )
        self.machine = build_dropoff_machine(
            self.controller,
            flight_to_pickup_timeout_ms=config.flight_to_pickup_timeout_ms,
            pickup_retry_timeout_ms=pickup_retry_timeout_ms,
        )
        self.controller.stm = self.machine
        self.driver = Driver()
        self.driver.add_machine(self.machine)

    def start(self) -> None:
        self.driver.start()

    def stop(self) -> None:
        self.controller.shutdown()
        self.driver.stop()

    @property
    def state(self) -> str:
        return self.controller.current_state

    @property
    def status(self) -> str:
        return self.controller.current_status

    @property
    def led_on(self) -> bool:
        return bool(getattr(self.controller.led, "is_lit", False))

    @property
    def led_mode(self) -> str:
        return self.controller.led_mode
