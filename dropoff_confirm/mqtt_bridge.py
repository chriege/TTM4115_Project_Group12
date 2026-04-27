from __future__ import annotations

import json

from .config import MqttConfig
from .service import DropoffConfirmationService

try:
    import paho.mqtt.client as mqtt
except Exception:
    mqtt = None


class DropoffMqttBridge:
    def __init__(
        self,
        service: DropoffConfirmationService,
        mqtt_config: MqttConfig,
        mqtt_client=None,
    ) -> None:
        self.service = service
        self.mqtt_config = mqtt_config
        self.client = mqtt_client
        self._owns_client = mqtt_client is None

        topic_prefix = mqtt_config.topic_prefix.strip("/")
        order_id = service.controller.config.order_id
        self.command_topic_root = f"{topic_prefix}/{order_id}/command"
        self.event_topic_root = f"{topic_prefix}/{order_id}/event"

        self.service.controller.set_callbacks(
            status_callback=self.publish_status_update,
            notification_callback=self.publish_notification,
            issue_callback=self.publish_issue,
        )

    def start(self) -> None:
        if self.client is None:
            if mqtt is None:
                raise RuntimeError(
                    "MQTT support requires paho-mqtt. Install with: python -m pip install paho-mqtt"
                )
            self.client = mqtt.Client(client_id=self.mqtt_config.client_id or "")

        if hasattr(self.client, "on_connect"):
            self.client.on_connect = self._on_connect
        if hasattr(self.client, "on_message"):
            self.client.on_message = self._on_message
        if hasattr(self.client, "on_disconnect"):
            self.client.on_disconnect = self._on_disconnect

        if self.mqtt_config.username:
            self.client.username_pw_set(
                self.mqtt_config.username, self.mqtt_config.password
            )

        if self._owns_client:
            self.client.connect(
                self.mqtt_config.host,
                self.mqtt_config.port,
                self.mqtt_config.keepalive,
            )
            self.client.loop_start()
        else:
            self._subscribe_command_topics()
            self._publish_lifecycle("bridge_started")
            self.publish_status_update(self.service.status)

    def stop(self) -> None:
        self._publish_lifecycle("bridge_stopped")
        if self.client is None:
            return
        if self._owns_client:
            if hasattr(self.client, "loop_stop"):
                self.client.loop_stop()
            if hasattr(self.client, "disconnect"):
                self.client.disconnect()

    def handle_topic_payload(self, topic: str, payload: str) -> None:
        if not topic.startswith(f"{self.command_topic_root}/"):
            return

        command = topic[len(self.command_topic_root) + 1 :]
        parsed_payload = self._parse_payload(payload)

        if command in {"pickup_arrived", "arrived_at_dropoff"}:
            self.service.controller.event_pickup_arrived()
        elif command in {"package_loaded"}:
            self.service.controller.event_package_loaded()
        elif command == "confirm_delivery":
            code = self._extract_code(parsed_payload)
            accepted = self.service.controller.submit_customer_code(str(code) if code else "")
            self._publish_json(
                f"{self.event_topic_root}/code_validation",
                {
                    "orderId": self.service.controller.config.order_id,
                    "accepted": accepted,
                },
            )
        elif command in {"not_ready", "dropoff_failed", "unresolved_dropoff"}:
            reason = self._extract_reason(parsed_payload, default="not_ready")
            self.service.controller.last_issue_reason = reason
            self.service.controller.event_not_ready()
        elif command in {"takeoff_confirmed", "dropoff_confirmed"}:
            self.service.controller.event_takeoff_confirmed()
        elif command == "reset":
            self.service.controller.event_reset()
        elif command == "state_request":
            self.publish_status_update(self.service.status)
            return
        else:
            self.publish_notification(f"Unknown command topic: {command}")
            return

    def publish_status_update(self, _status: str) -> None:
        self._publish_json(
            f"{self.event_topic_root}/status",
            {
                "orderId": self.service.controller.config.order_id,
                "status": self.service.status,
                "state": self.service.state,
                "ledOn": self.service.led_on,
                "ledMode": self.service.led_mode,
                "reason": self.service.controller.last_issue_reason,
            },
        )

    def publish_notification(self, message: str) -> None:
        self._publish_json(
            f"{self.event_topic_root}/notification",
            {
                "orderId": self.service.controller.config.order_id,
                "message": message,
            },
        )

    def publish_issue(self, message: str) -> None:
        self._publish_json(
            f"{self.event_topic_root}/issue",
            {
                "orderId": self.service.controller.config.order_id,
                "message": message,
            },
        )

    def _subscribe_command_topics(self) -> None:
        if self.client is None:
            return
        command_wildcard = f"{self.command_topic_root}/#"
        self.client.subscribe(command_wildcard, qos=self.mqtt_config.qos)

    def _publish_lifecycle(self, phase: str) -> None:
        self._publish_json(
            f"{self.event_topic_root}/lifecycle",
            {
                "orderId": self.service.controller.config.order_id,
                "phase": phase,
            },
        )

    def _publish_json(self, topic: str, payload: dict) -> None:
        if self.client is None:
            return
        self.client.publish(
            topic,
            payload=json.dumps(payload, ensure_ascii=True),
            qos=self.mqtt_config.qos,
            retain=False,
        )

    @staticmethod
    def _parse_payload(payload: str):
        text = (payload or "").strip()
        if not text:
            return {}
        try:
            value = json.loads(text)
            if isinstance(value, dict):
                return value
            return {"value": value}
        except json.JSONDecodeError:
            return {"value": text}

    @staticmethod
    def _extract_code(parsed_payload: dict):
        for key in ("code", "confirmation_code", "value"):
            if key in parsed_payload:
                return parsed_payload[key]
        return None

    @staticmethod
    def _extract_reason(parsed_payload: dict, default: str) -> str:
        for key in ("reason", "message", "value"):
            if key in parsed_payload and parsed_payload[key]:
                return str(parsed_payload[key])
        return default

    def _on_connect(self, _client, _userdata, _flags, rc):
        if rc == 0:
            self._subscribe_command_topics()
            self._publish_lifecycle("bridge_started")
            self.publish_status_update(self.service.status)

    def _on_disconnect(self, _client, _userdata, _rc):
        return None

    def _on_message(self, _client, _userdata, message):
        payload = ""
        try:
            payload = message.payload.decode("utf-8", errors="ignore")
        except Exception:
            payload = ""
        self.handle_topic_payload(message.topic, payload)
