import time
import unittest

from dropoff_confirm_machine import DropoffConfig, DropoffConfirmationService


def wait_until(predicate, timeout_s=2.0, interval_s=0.02):
    start = time.time()
    while (time.time() - start) < timeout_s:
        if predicate():
            return True
        time.sleep(interval_s)
    return False


class PickupDispatchTests(unittest.TestCase):
    def test_display_blank_until_pickup_arrived(self):
        service = DropoffConfirmationService(
            DropoffConfig(
                order_id="A0",
                flight_to_pickup_timeout_ms=120,
                pickup_retry_timeout_ms=2000,
                force_mock_led=True,
                force_mock_display=True,
            )
        )
        service.start()
        try:
            self.assertTrue(
                wait_until(lambda: service.state == "waiting_for_drone"),
                "Machine never entered waiting_for_drone.",
            )
            self.assertEqual(service.controller.state_display.last_message, "")
            self.assertFalse(service.led_on)

            service.controller.event_pickup_arrived()
            self.assertTrue(
                wait_until(lambda: service.state == "in_flight_to_pickup"),
                "Machine never entered in_flight_to_pickup.",
            )
            self.assertEqual(
                service.controller.state_display.last_state, "in_flight_to_pickup"
            )
            self.assertTrue(
                wait_until(lambda: service.state == "at_pickup"),
                "Machine never entered at_pickup.",
            )
            self.assertEqual(service.controller.state_display.last_message, "AT PICKUP")
        finally:
            service.stop()

    def test_success_path_goes_to_in_flight(self):
        service = DropoffConfirmationService(
            DropoffConfig(
                order_id="A1",
                flight_to_pickup_timeout_ms=120,
                pickup_retry_timeout_ms=2000,
                force_mock_led=True,
                force_mock_display=True,
            )
        )
        service.start()
        try:
            service.controller.event_pickup_arrived()
            self.assertTrue(
                wait_until(lambda: service.state == "in_flight_to_pickup"),
                "Machine never entered in_flight_to_pickup.",
            )
            self.assertEqual(service.status, "TO_RESTAURANT")
            self.assertEqual(service.controller.state_display.last_state, "in_flight_to_pickup")
            self.assertTrue(
                wait_until(lambda: service.state == "at_pickup"),
                "Machine never entered at_pickup.",
            )
            self.assertTrue(
                wait_until(lambda: service.status == "AT_PICKUP"),
                "Machine never produced AT_PICKUP status.",
            )
            self.assertEqual(service.status, "AT_PICKUP")
            self.assertEqual(service.led_mode, "BLINKING")
            self.assertEqual(service.controller.state_display.last_state, "at_pickup")

            service.controller.event_package_loaded()
            self.assertTrue(
                wait_until(lambda: service.state == "package_loaded"),
                "Machine never entered package_loaded.",
            )
            self.assertEqual(service.status, "PACKAGE_LOADED")
            self.assertTrue(service.led_on)
            self.assertEqual(service.led_mode, "ON")
            self.assertEqual(service.controller.state_display.last_state, "package_loaded")

            service.controller.event_takeoff_confirmed()
            self.assertTrue(
                wait_until(lambda: service.status == "IN_FLIGHT"),
                "Machine never produced IN_FLIGHT status.",
            )
            self.assertFalse(service.led_on)
            self.assertEqual(service.led_mode, "OFF")
            self.assertEqual(service.controller.state_display.last_state, "in_flight")
        finally:
            service.stop()

    def test_not_ready_timeout_retries_to_at_pickup(self):
        service = DropoffConfirmationService(
            DropoffConfig(
                order_id="A2",
                flight_to_pickup_timeout_ms=120,
                pickup_retry_timeout_ms=150,
                force_mock_led=True,
                force_mock_display=True,
            )
        )
        service.start()
        try:
            service.controller.event_pickup_arrived()
            self.assertTrue(
                wait_until(lambda: service.state == "in_flight_to_pickup"),
                "Machine never entered in_flight_to_pickup.",
            )
            self.assertTrue(
                wait_until(lambda: service.state == "at_pickup"),
                "Machine never entered at_pickup.",
            )
            service.controller.event_not_ready()
            self.assertTrue(
                wait_until(lambda: service.state == "pickup_delayed"),
                "Machine did not enter pickup_delayed after not_ready.",
            )
            self.assertEqual(service.status, "PICKUP_DELAYED")
            self.assertTrue(
                wait_until(lambda: service.state == "at_pickup"),
                "Machine did not retry back to at_pickup after timeout.",
            )
            self.assertEqual(service.status, "AT_PICKUP")
            self.assertEqual(service.led_mode, "BLINKING")
            self.assertEqual(service.controller.state_display.last_state, "at_pickup")
        finally:
            service.stop()


if __name__ == "__main__":
    unittest.main()
