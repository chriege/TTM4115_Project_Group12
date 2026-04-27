import json
import os
import time
import paho.mqtt.client as mqtt
from stmpy import Machine, Driver

MQTT_HOST = os.getenv("KOMSYS_MQTT_HOST", "mqtt20.iik.ntnu.no")
MQTT_PORT = int(os.getenv("KOMSYS_MQTT_PORT", "1883"))
MQTT_KEEPALIVE = int(os.getenv("KOMSYS_MQTT_KEEPALIVE", "60"))
REQUEST_TOPIC = os.getenv("KOMSYS_REQUEST_TOPIC", "app/order/request")
RESPONSE_TOPIC = os.getenv("KOMSYS_RESPONSE_TOPIC", "backend/order/status")
PICKUP_TOPIC_PREFIX = os.getenv("KOMSYS_PICKUP_TOPIC_PREFIX", "komsys/pickup_dispatch")
PICKUP_TOPIC_PREFIX_CLEAN = PICKUP_TOPIC_PREFIX.strip("/")
DEFAULT_PICKUP_ORDER_ID = os.getenv("KOMSYS_PICKUP_ORDER_ID", "ORDER-001")


class OrderHandling:
    def __init__(self, mqtt_client, gui_callback=None):
        self.mqtt_client = mqtt_client
        self.gui_callback = gui_callback

    def confirmOrder(self):
        print("[Order] Order confirmed")
        if self.gui_callback:
            self.gui_callback("order_state", "OrderConfirmed")

    def cancelOrder(self):
        print("[Order] Order cancelled")
        if self.gui_callback:
            self.gui_callback("order_state", "OrderCancelled")


class PaymentHandling:
    def __init__(
        self,
        mqtt_client,
        gui_callback=None,
        pickup_arrived_callback=None,
        pickup_order_id_callback=None,
    ):
        self.mqtt_client = mqtt_client
        self.gui_callback = gui_callback
        self.phase = "idle"
        self.pickup_arrived_callback = pickup_arrived_callback or (lambda order_id: None)
        self.pickup_order_id_callback = pickup_order_id_callback or (
            lambda: DEFAULT_PICKUP_ORDER_ID
        )

    def setPending(self):
        print("[Payment] Awaiting payment")
        self.phase = "awaiting"
        if self.gui_callback:
            self.gui_callback("payment_state", "Waiting for payment")

    def markCancelled(self):
        print("[Payment] Payment cancelled")
        self.phase = "cancelled"
        if self.gui_callback:
            self.gui_callback("payment_state", "Payment cancelled")

    def markDenied(self):
        print("[Payment] Payment denied")
        self.phase = "denied"
        if self.gui_callback:
            self.gui_callback("payment_state", "Payment denied")

    def markAccepted(self):
        print("[Payment] Payment accepted")
        self.phase = "accepted"
        if self.gui_callback:
            self.gui_callback("payment_state", "Payment accepted")
        self.pickup_arrived_callback(self.pickup_order_id_callback())


class BackendController:
    def __init__(self, gui_callback=None, pickup_order_id=DEFAULT_PICKUP_ORDER_ID):
        self.gui_callback = gui_callback
        self.pickup_order_id = pickup_order_id

        self.mqtt_client = mqtt.Client(client_id="Backend_Group12_Payments")
        self.mqtt_client.on_connect = self.on_connect
        self.mqtt_client.on_message = self.on_message

        self.driver = Driver()
        self.order_handler = OrderHandling(self.mqtt_client, gui_callback)
        self.payment_handler = PaymentHandling(
            self.mqtt_client,
            gui_callback,
            pickup_arrived_callback=self.publish_pickup_arrived,
            pickup_order_id_callback=self.get_pickup_order_id,
        )

        self._setup_order_machine()
        self._setup_payment_machine()

    def _setup_order_machine(self):
        transitions = [
            {"source": "initial", "target": "Browsing"},
            {"source": "Browsing", "target": "CartReview", "trigger": "proceedToCart"},
            {"source": "CartReview", "target": "Cancelled", "trigger": "cancelOrder"},
            {"source": "CartReview", "target": "ReadyForPayment", "trigger": "confirmOrder"},
            {"source": "Browsing", "target": "Browsing", "trigger": "resetOrder"},
            {"source": "CartReview", "target": "Browsing", "trigger": "resetOrder"},
            {"source": "ReadyForPayment", "target": "Browsing", "trigger": "resetOrder"},
            {"source": "Cancelled", "target": "Browsing", "trigger": "resetOrder"},
        ]

        states = [
            {"name": "Browsing"},
            {"name": "CartReview"},
            {"name": "ReadyForPayment"},
            {"name": "Cancelled"},
        ]

        self.stm_order = Machine(
            name="stm_order",
            transitions=transitions,
            states=states,
            obj=self.order_handler,
        )
        self.order_handler.stm = self.stm_order
        self.driver.add_machine(self.stm_order)

    def _setup_payment_machine(self):
        transitions = [
            {"source": "initial", "target": "Idle"},
            {"source": "Idle", "target": "AwaitingPayment", "trigger": "checkoutStarted"},
            {"source": "AwaitingPayment", "target": "Cancelled", "trigger": "orderCancelled"},
            {"source": "AwaitingPayment", "target": "Cancelled", "trigger": "t"},
            {"source": "AwaitingPayment", "target": "PaymentFailed", "trigger": "paymentDeclined"},
            {"source": "AwaitingPayment", "target": "Paid", "trigger": "paymentApproved"},
            {"source": "Paid", "target": "Idle", "trigger": "resetPayment"},
            {"source": "PaymentFailed", "target": "Idle", "trigger": "resetPayment"},
            {"source": "Cancelled", "target": "Idle", "trigger": "resetPayment"},
            {"source": "AwaitingPayment", "target": "Idle", "trigger": "resetPayment"},
        ]

        states = [
            {"name": "Idle"},
            {
                "name": "AwaitingPayment",
                "entry": "start_timer('t', 180000); setPending",
                "exit": "stop_timer('t')",
            },
            {"name": "Cancelled", "entry": "markCancelled"},
            {"name": "PaymentFailed", "entry": "markDenied"},
            {"name": "Paid", "entry": "markAccepted"},
        ]

        self.stm_payment = Machine(
            name="stm_payment",
            transitions=transitions,
            states=states,
            obj=self.payment_handler,
        )
        self.payment_handler.stm = self.stm_payment
        self.driver.add_machine(self.stm_payment)

    def on_connect(self, client, userdata, flags, rc):
        print(f"[MQTT] Connected. Listening for requests on: '{REQUEST_TOPIC}'")
        client.subscribe(REQUEST_TOPIC)
        pickup_event_topic = f"{PICKUP_TOPIC_PREFIX_CLEAN}/+/event/#"
        print(f"[MQTT] Subscribed to pickup events on: '{pickup_event_topic}'")
        client.subscribe(pickup_event_topic)

    def _forward_pickup_event_to_gui(self, topic, payload):
        topic_clean = (topic or "").strip("/")
        prefix = f"{PICKUP_TOPIC_PREFIX_CLEAN}/"
        if not topic_clean.startswith(prefix):
            return False

        parts = topic_clean[len(prefix) :].split("/")
        if len(parts) < 3 or parts[1] != "event":
            return False

        order_id = parts[0]
        event_type = parts[2]
        current_order_id = str(self.get_pickup_order_id() or DEFAULT_PICKUP_ORDER_ID)
        if order_id != current_order_id:
            return True

        try:
            data = json.loads(payload) if payload else {}
            if not isinstance(data, dict):
                data = {}
        except json.JSONDecodeError:
            data = {}

        if event_type == "status":
            raw_state = data.get("state")
            raw_status = data.get("status")
            raw_reason = data.get("reason")

            state = str(raw_state).strip() if raw_state not in (None, "") else ""
            status = str(raw_status).strip() if raw_status not in (None, "") else ""
            reason = str(raw_reason).strip() if raw_reason not in (None, "") else ""

            if state:
                drone_state = state
            elif status:
                drone_state = status.lower()
            else:
                drone_state = "unknown"

            if state == "pickup_delayed" and reason:
                drone_state = f"{state} ({reason})"

            if self.gui_callback:
                self.gui_callback("drone_state", drone_state)
            return True

        if event_type == "issue":
            raw_issue_message = data.get("message")
            issue_message = (
                str(raw_issue_message).strip()
                if raw_issue_message not in (None, "")
                else ""
            )
            if issue_message and self.gui_callback:
                self.gui_callback("drone_state", f"pickup_delayed ({issue_message})")
            return True

        return True

    def on_message(self, client, userdata, msg):
        payload = msg.payload.decode("utf-8", errors="ignore")
        if self._forward_pickup_event_to_gui(msg.topic, payload):
            return

        try:
            data = json.loads(payload)
            print(f"\n[MQTT] Message received: {data}")
            action = data.get("action")

            if action == "checkout_begins":
                self.driver.send("checkoutStarted", "stm_payment")
            elif action == "payment_approved":
                self.driver.send("paymentApproved", "stm_payment")
            elif action == "payment_declined":
                self.driver.send("paymentDeclined", "stm_payment")
            elif action == "cancel_order":
                self.driver.send("orderCancelled", "stm_payment")

        except json.JSONDecodeError:
            print("[Error] Invalid JSON received")

    def start(self):
        self.driver.start()
        self.mqtt_client.connect(MQTT_HOST, MQTT_PORT, MQTT_KEEPALIVE)
        self.mqtt_client.loop_start()

    def stop(self):
        self.driver.stop()
        self.mqtt_client.loop_stop()
        self.mqtt_client.disconnect()

    def get_pickup_order_id(self):
        return self.pickup_order_id

    def set_pickup_order_id(self, order_id):
        if order_id:
            self.pickup_order_id = str(order_id)

    def publish_pickup_arrived(self, order_id):
        if not order_id:
            order_id = DEFAULT_PICKUP_ORDER_ID

        topic = f"{PICKUP_TOPIC_PREFIX}/{order_id}/command/pickup_arrived"
        payload = {
            "orderId": order_id,
            "action": "pickup_arrived",
            "source": "ordering_system",
        }

        self.mqtt_client.publish(topic, json.dumps(payload), qos=1, retain=False)
        self.mqtt_client.publish(
            RESPONSE_TOPIC,
            json.dumps(
                {
                    "orderId": order_id,
                    "status": "DISPATCHED_TO_PICKUP",
                    "topic": topic,
                }
            ),
            qos=1,
            retain=False,
        )

        print(f"[MQTT] Published pickup_arrived for {order_id} to {topic}")

    def publish_pickup_reset(self, order_id):
        if not order_id:
            order_id = DEFAULT_PICKUP_ORDER_ID

        topic = f"{PICKUP_TOPIC_PREFIX}/{order_id}/command/reset"
        payload = {
            "orderId": order_id,
            "action": "reset",
            "source": "ordering_system",
        }

        self.mqtt_client.publish(topic, json.dumps(payload), qos=1, retain=False)
        self.mqtt_client.publish(
            RESPONSE_TOPIC,
            json.dumps(
                {
                    "orderId": order_id,
                    "status": "DISPATCH_RESET",
                    "topic": topic,
                }
            ),
            qos=1,
            retain=False,
        )

        print(f"[MQTT] Published pickup reset for {order_id} to {topic}")

    def send_trigger(self, trigger_name, machine_name):
        if machine_name == "stm_payment" and trigger_name == "checkoutStarted":
            self.payment_handler.phase = "awaiting_requested"

        if (
            machine_name == "stm_payment"
            and trigger_name in {"paymentApproved", "paymentDeclined"}
            and self.stm_payment.state != "AwaitingPayment"
            and self.payment_handler.phase != "awaiting_requested"
        ):
            print(
                "[Payment] Ignored "
                f"{trigger_name}: payment state is {self.stm_payment.state}"
            )
            if self.gui_callback:
                self.gui_callback("payment_state", "Payment cancelled")
            return False

        try:
            self.driver.send(trigger_name, machine_name)
        except Exception as exc:
            print(f"[StateMachine] Failed to send {trigger_name} to {machine_name}: {exc}")
            return False

        if machine_name == "stm_payment" and trigger_name == "resetPayment":
            self.publish_pickup_reset(self.get_pickup_order_id())
            self.payment_handler.phase = "idle"

        return True


if __name__ == "__main__":
    controller = BackendController()
    controller.start()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nShutting down system...")
        controller.stop()
