import json
import time
import unittest

from dropoff_confirm_machine import (
    DropoffConfig,
    DropoffConfirmationService,
    DropoffMqttBridge,
    MqttConfig,
)


def wait_until(predicate, timeout_s=2.0, interval_s=0.02):
    start = time.time()
    while (time.time() - start) < timeout_s:
        if predicate():
            return True
        time.sleep(interval_s)
    return False


def status_payloads(fake_client, event_root):
    return [
        json.loads(entry["payload"])
        for entry in fake_client.published
        if entry["topic"] == f"{event_root}/status"
    ]


def latest_status_is(fake_client, event_root, status):
    payloads = status_payloads(fake_client, event_root)
    return bool(payloads) and payloads[-1]["status"] == status


class FakeMqttClient:
    def __init__(self):
        self.published = []
        self.subscriptions = []
        self.on_connect = None
        self.on_message = None
        self.on_disconnect = None

    def subscribe(self, topic, qos=0):
        self.subscriptions.append((topic, qos))

    def publish(self, topic, payload, qos=0, retain=False):
        self.published.append(
            {"topic": topic, "payload": payload, "qos": qos, "retain": retain}
        )


class DropoffMqttBridgeTests(unittest.TestCase):
    def test_mqtt_commands_drive_machine_success_flow(self):
        service = DropoffConfirmationService(
            DropoffConfig(
                order_id="M1",
                flight_to_pickup_timeout_ms=120,
                force_mock_led=True,
                force_mock_display=True,
                pickup_retry_timeout_ms=2000,
            )
        )
        fake_client = FakeMqttClient()
        bridge = DropoffMqttBridge(
            service,
            MqttConfig(topic_prefix="komsys/test"),
            mqtt_client=fake_client,
        )

        service.start()
        bridge.start()

        try:
            command_root = bridge.command_topic_root
            event_root = bridge.event_topic_root
            initial_status_payloads = status_payloads(fake_client, event_root)
            self.assertTrue(
                any(payload["status"] == "WAITING_FOR_DRONE" for payload in initial_status_payloads),
                "Bridge should publish WAITING_FOR_DRONE on startup.",
            )

            bridge.handle_topic_payload(f"{command_root}/pickup_arrived", "")
            self.assertTrue(
                wait_until(lambda: service.state == "in_flight_to_pickup"),
                "MQTT pickup_arrived did not trigger in_flight_to_pickup.",
            )
            self.assertEqual(service.status, "TO_RESTAURANT")
            self.assertTrue(
                wait_until(lambda: service.state == "at_pickup"),
                "MQTT pickup_arrived did not change state.",
            )
            self.assertTrue(
                wait_until(lambda: latest_status_is(fake_client, event_root, "AT_PICKUP")),
                "Bridge never published AT_PICKUP.",
            )
            self.assertEqual(status_payloads(fake_client, event_root)[-1]["status"], "AT_PICKUP")
            self.assertEqual(status_payloads(fake_client, event_root)[-1]["ledMode"], "BLINKING")

            bridge.handle_topic_payload(f"{command_root}/package_loaded", "")
            self.assertTrue(
                wait_until(lambda: service.state == "package_loaded"),
                "MQTT package_loaded did not change state.",
            )
            self.assertTrue(service.led_on)
            self.assertTrue(
                wait_until(lambda: latest_status_is(fake_client, event_root, "PACKAGE_LOADED")),
                "Bridge never published PACKAGE_LOADED.",
            )
            self.assertEqual(status_payloads(fake_client, event_root)[-1]["status"], "PACKAGE_LOADED")
            self.assertEqual(status_payloads(fake_client, event_root)[-1]["ledMode"], "ON")

            bridge.handle_topic_payload(f"{command_root}/takeoff_confirmed", "")
            self.assertTrue(
                wait_until(lambda: service.status == "IN_FLIGHT"),
                "MQTT takeoff_confirmed did not reach IN_FLIGHT.",
            )
            self.assertFalse(service.led_on)
            self.assertTrue(
                wait_until(lambda: latest_status_is(fake_client, event_root, "IN_FLIGHT")),
                "Bridge never published IN_FLIGHT.",
            )
            self.assertEqual(status_payloads(fake_client, event_root)[-1]["status"], "IN_FLIGHT")
            self.assertEqual(status_payloads(fake_client, event_root)[-1]["ledMode"], "OFF")

            topics = [entry["topic"] for entry in fake_client.published]
            self.assertIn(f"{event_root}/status", topics)

            payloads = status_payloads(fake_client, event_root)
            self.assertTrue(any(payload["status"] == "IN_FLIGHT" for payload in payloads))
        finally:
            bridge.stop()
            service.stop()

    def test_not_ready_reason_is_cleared_after_retry(self):
        service = DropoffConfirmationService(
            DropoffConfig(
                order_id="M2",
                flight_to_pickup_timeout_ms=80,
                pickup_retry_timeout_ms=80,
                force_mock_led=True,
                force_mock_display=True,
            )
        )
        fake_client = FakeMqttClient()
        bridge = DropoffMqttBridge(
            service,
            MqttConfig(topic_prefix="komsys/test"),
            mqtt_client=fake_client,
        )

        service.start()
        bridge.start()

        try:
            command_root = bridge.command_topic_root
            event_root = bridge.event_topic_root

            bridge.handle_topic_payload(f"{command_root}/pickup_arrived", "")
            self.assertTrue(wait_until(lambda: service.state == "at_pickup"))

            bridge.handle_topic_payload(
                f"{command_root}/not_ready",
                json.dumps({"reason": "food not ready"}),
            )
            self.assertTrue(wait_until(lambda: service.state == "pickup_delayed"))
            delayed_payload = status_payloads(fake_client, event_root)[-1]
            self.assertEqual(delayed_payload["status"], "PICKUP_DELAYED")
            self.assertEqual(delayed_payload["reason"], "food not ready")

            self.assertTrue(wait_until(lambda: service.state == "at_pickup"))
            self.assertTrue(
                wait_until(lambda: latest_status_is(fake_client, event_root, "AT_PICKUP")),
                "Bridge never published retried AT_PICKUP.",
            )
            retried_payload = status_payloads(fake_client, event_root)[-1]
            self.assertEqual(retried_payload["status"], "AT_PICKUP")
            self.assertIsNone(retried_payload["reason"])

            bridge.handle_topic_payload(f"{command_root}/package_loaded", "")
            self.assertTrue(wait_until(lambda: service.state == "package_loaded"))
            self.assertTrue(
                wait_until(lambda: latest_status_is(fake_client, event_root, "PACKAGE_LOADED")),
                "Bridge never published PACKAGE_LOADED.",
            )
            loaded_payload = status_payloads(fake_client, event_root)[-1]
            self.assertEqual(loaded_payload["status"], "PACKAGE_LOADED")
            self.assertIsNone(loaded_payload["reason"])
        finally:
            bridge.stop()
            service.stop()

    def test_reset_command_returns_machine_to_waiting_for_drone(self):
        service = DropoffConfirmationService(
            DropoffConfig(
                order_id="M3",
                flight_to_pickup_timeout_ms=60,
                force_mock_led=True,
                force_mock_display=True,
            )
        )
        fake_client = FakeMqttClient()
        bridge = DropoffMqttBridge(
            service,
            MqttConfig(topic_prefix="komsys/test"),
            mqtt_client=fake_client,
        )

        service.start()
        bridge.start()

        try:
            command_root = bridge.command_topic_root
            event_root = bridge.event_topic_root

            bridge.handle_topic_payload(f"{command_root}/pickup_arrived", "")
            self.assertTrue(wait_until(lambda: service.state == "at_pickup"))

            bridge.handle_topic_payload(f"{command_root}/package_loaded", "")
            self.assertTrue(wait_until(lambda: service.state == "package_loaded"))
            self.assertTrue(
                wait_until(lambda: latest_status_is(fake_client, event_root, "PACKAGE_LOADED"))
            )

            bridge.handle_topic_payload(f"{command_root}/reset", "")
            self.assertTrue(
                wait_until(lambda: service.state == "waiting_for_drone"),
                "MQTT reset did not return machine to waiting_for_drone.",
            )
            self.assertEqual(service.status, "WAITING_FOR_DRONE")
            self.assertTrue(
                wait_until(lambda: latest_status_is(fake_client, event_root, "WAITING_FOR_DRONE")),
                "Bridge never published WAITING_FOR_DRONE after reset.",
            )

            bridge.handle_topic_payload(f"{command_root}/pickup_arrived", "")
            self.assertTrue(
                wait_until(lambda: service.state == "in_flight_to_pickup"),
                "Machine did not accept pickup_arrived after reset.",
            )
        finally:
            bridge.stop()
            service.stop()


if __name__ == "__main__":
    unittest.main()
