from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Optional


@dataclass
class DropoffConfig:
    order_id: str
    confirmation_code: str = ""
    led_pin: int = 17
    confirmation_timeout_ms: int = 60000
    max_code_attempts: int = 3
    flight_to_pickup_timeout_ms: int = 8000
    pickup_retry_timeout_ms: int = 60000
    force_mock_led: bool = False
    force_mock_display: bool = False


@dataclass
class MqttConfig:
    host: str = os.getenv("KOMSYS_MQTT_HOST", "mqtt20.iik.ntnu.no")
    port: int = int(os.getenv("KOMSYS_MQTT_PORT", "1883"))
    keepalive: int = int(os.getenv("KOMSYS_MQTT_KEEPALIVE", "60"))
    topic_prefix: str = os.getenv("KOMSYS_PICKUP_TOPIC_PREFIX", "komsys/pickup_dispatch")
    client_id: Optional[str] = None
    username: Optional[str] = None
    password: Optional[str] = None
    qos: int = int(os.getenv("KOMSYS_MQTT_QOS", "1"))
