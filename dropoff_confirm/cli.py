from __future__ import annotations

import argparse
import threading
import time

from .config import DropoffConfig, MqttConfig
from .mqtt_bridge import DropoffMqttBridge
from .service import DropoffConfirmationService


def _handle_primary_button_action(service: DropoffConfirmationService) -> None:
    current_state = service.state

    if current_state in {"at_pickup", "pickup_delayed"}:
        accepted = service.controller.submit_customer_code("")
        if accepted:
            print("[Shortcut] package_loaded accepted.")
        else:
            print("[Shortcut] Ignored: drone is not ready for package loading.")
        return

    if current_state == "package_loaded":
        service.controller.event_takeoff_confirmed()
        print("[Shortcut] takeoff_confirmed sent.")
        return

    print(
        "[Shortcut] Ignored: primary button is only active at pickup "
        "(for package_loaded) or after package load (for takeoff)."
    )


def _start_mqtt_stdin_shortcuts(service: DropoffConfirmationService) -> threading.Event:
    stop_event = threading.Event()

    def _loop() -> None:
        while not stop_event.is_set():
            try:
                raw = input().strip().lower()
            except (EOFError, KeyboardInterrupt):
                break

            if raw in {"", "package_loaded", "loaded", "enter"}:
                _handle_primary_button_action(service)
            elif raw in {"not_ready", "retry"}:
                service.controller.last_issue_reason = "not_ready"
                service.controller.event_not_ready()
                print("[Shortcut] not_ready sent.")
            elif raw in {"takeoff", "takeoff_confirmed"}:
                service.controller.event_takeoff_confirmed()
                print("[Shortcut] takeoff_confirmed sent.")
            elif raw in {"reset"}:
                service.controller.event_reset()
                print("[Shortcut] reset sent.")
            elif raw in {"state"}:
                print(
                    f"state={service.state} status={service.status} led_on={service.led_on} led_mode={service.led_mode}"
                )
            elif raw in {"help", "?"}:
                print(
                    "Shortcuts: [Enter]=context action (package_loaded/takeoff) | "
                    "not_ready | takeoff | reset | state"
                )
            elif raw:
                print(
                    f"[Shortcut] Unknown input '{raw}'. Press Enter for context action or type 'help'."
                )

    thread = threading.Thread(
        target=_loop,
        name="pickup-mqtt-stdin-shortcuts",
        daemon=True,
    )
    thread.start()
    return stop_event


def run_cli(args: argparse.Namespace) -> None:
    config = DropoffConfig(
        order_id=args.order_id,
        led_pin=args.led_pin,
        flight_to_pickup_timeout_ms=args.flight_to_pickup_timeout_ms,
        pickup_retry_timeout_ms=args.pickup_retry_timeout_ms,
        # Keep these legacy args accepted, even though use case 3 does not use them.
        confirmation_code=str(args.code),
        confirmation_timeout_ms=args.pickup_retry_timeout_ms,
        max_code_attempts=args.max_attempts,
        force_mock_led=args.force_mock_led,
        force_mock_display=args.force_mock_display,
    )
    service = DropoffConfirmationService(config)
    service.start()

    print("Pickup dispatch machine started.")
    print(
        "Commands: pickup_arrived | not_ready | package_loaded | takeoff_confirmed | reset | "
        "state | quit"
    )

    try:
        while True:
            raw = input("> ").strip()
            if not raw:
                continue

            parts = raw.split(maxsplit=1)
            command = parts[0].lower()
            arg = parts[1] if len(parts) > 1 else ""

            if command in {"pickup_arrived", "arrive"}:
                service.controller.event_pickup_arrived()
            elif command in {"not_ready", "failed", "unresolved"}:
                if arg:
                    service.controller.last_issue_reason = arg
                service.controller.event_not_ready()
            elif command in {"package_loaded", "loaded", "code"}:
                service.controller.event_package_loaded()
            elif command in {"takeoff_confirmed", "confirmed"}:
                service.controller.event_takeoff_confirmed()
            elif command in {"reset"}:
                service.controller.event_reset()
            elif command == "state":
                print(
                    f"state={service.state} status={service.status} led_on={service.led_on} led_mode={service.led_mode}"
                )
            elif command in {"quit", "exit"}:
                break
            else:
                print("Unknown command.")
    finally:
        service.stop()


def run_mqtt(args: argparse.Namespace) -> None:
    config = DropoffConfig(
        order_id=args.order_id,
        led_pin=args.led_pin,
        flight_to_pickup_timeout_ms=args.flight_to_pickup_timeout_ms,
        pickup_retry_timeout_ms=args.pickup_retry_timeout_ms,
        confirmation_code=str(args.code),
        confirmation_timeout_ms=args.pickup_retry_timeout_ms,
        max_code_attempts=args.max_attempts,
        force_mock_led=args.force_mock_led,
        force_mock_display=args.force_mock_display,
    )
    service = DropoffConfirmationService(config)
    bridge = DropoffMqttBridge(
        service,
        MqttConfig(
            host=args.mqtt_host,
            port=args.mqtt_port,
            keepalive=args.mqtt_keepalive,
            topic_prefix=args.mqtt_topic_prefix,
            client_id=args.mqtt_client_id,
            username=args.mqtt_username,
            password=args.mqtt_password,
            qos=args.mqtt_qos,
        ),
    )
    service.start()
    bridge.start()
    shortcut_stop_event = None

    if not args.no_stdin_shortcuts:
        print("Terminal shortcuts enabled.")
        print("Press Enter for context action:")
        print("- at_pickup/pickup_delayed -> package_loaded")
        print("- package_loaded -> takeoff_confirmed")
        print("Other shortcuts: not_ready | takeoff | reset | state | help")
        shortcut_stop_event = _start_mqtt_stdin_shortcuts(service)

    print("Pickup dispatch machine started in MQTT mode.")
    print(f"MQTT broker: {args.mqtt_host}:{args.mqtt_port}")
    print(f"Subscribe commands under: {bridge.command_topic_root}/#")
    print(f"Published events under: {bridge.event_topic_root}/#")

    try:
        while True:
            time.sleep(1.0)
    except KeyboardInterrupt:
        pass
    finally:
        if shortcut_stop_event is not None:
            shortcut_stop_event.set()
        bridge.stop()
        service.stop()


def parse_args() -> argparse.Namespace:
    mqtt_defaults = MqttConfig()
    parser = argparse.ArgumentParser(
        description="Pickup dispatch state machine for Raspberry Pi."
    )
    parser.add_argument(
        "--mode", choices=["cli", "mqtt"], default="cli", help="Run CLI or MQTT mode."
    )
    parser.add_argument("--order-id", default="ORDER-001", help="Order id.")
    parser.add_argument("--led-pin", type=int, default=17, help="GPIO pin for LED.")
    parser.add_argument(
        "--flight-to-pickup-timeout-ms",
        type=int,
        default=8000,
        help="Simulated flight time from dispatch to pickup in milliseconds.",
    )
    parser.add_argument(
        "--pickup-retry-timeout-ms",
        "--timeout-ms",
        dest="pickup_retry_timeout_ms",
        type=int,
        default=60000,
        help="Retry timer in milliseconds for pickup_delayed -> at_pickup.",
    )
    parser.add_argument(
        "--code",
        default="",
        help="Legacy argument (ignored in pickup flow).",
    )
    parser.add_argument(
        "--max-attempts",
        type=int,
        default=3,
        help="Legacy argument (ignored in pickup flow).",
    )
    parser.add_argument(
        "--force-mock-led",
        action="store_true",
        help="Use mock LED even on Raspberry Pi.",
    )
    parser.add_argument(
        "--force-mock-display",
        action="store_true",
        help="Use mock state display even when Sense HAT is available.",
    )
    parser.add_argument(
        "--mqtt-host",
        default=mqtt_defaults.host,
        help="MQTT broker host.",
    )
    parser.add_argument(
        "--mqtt-port",
        type=int,
        default=mqtt_defaults.port,
        help="MQTT broker port.",
    )
    parser.add_argument(
        "--mqtt-keepalive",
        type=int,
        default=mqtt_defaults.keepalive,
        help="MQTT keepalive in seconds.",
    )
    parser.add_argument(
        "--mqtt-topic-prefix",
        default=mqtt_defaults.topic_prefix,
        help="Topic prefix used for command/event topics.",
    )
    parser.add_argument("--mqtt-client-id", default=None, help="Optional MQTT client id.")
    parser.add_argument("--mqtt-username", default=None, help="MQTT username.")
    parser.add_argument("--mqtt-password", default=None, help="MQTT password.")
    parser.add_argument(
        "--mqtt-qos",
        type=int,
        default=mqtt_defaults.qos,
        help="MQTT QoS level.",
    )
    parser.add_argument(
        "--no-stdin-shortcuts",
        action="store_true",
        help="Disable local terminal shortcuts in MQTT mode.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.mode == "mqtt":
        run_mqtt(args)
    else:
        run_cli(args)
