from __future__ import annotations

from collections.abc import Callable
from contextlib import asynccontextmanager
from threading import RLock
from typing import Any, Protocol

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from resturrant import RESTAURANTS
from user import BackendController, DEFAULT_PICKUP_ORDER_ID


DELIVERY_STAGES = [
    {
        "key": "to_restaurant",
        "label": "1. Drone in flight to restaurant",
        "message": "Drone is in flight to the restaurant.",
    },
    {
        "key": "at_restaurant",
        "label": "2. Drone at restaurant and waiting for food",
        "message": "Drone has arrived and is waiting while food is prepared.",
    },
    {
        "key": "food_loaded",
        "label": "3. Food loaded into drone",
        "message": "Food has been loaded into the drone.",
    },
    {
        "key": "to_customer",
        "label": "4. Drone in flight to delivery location",
        "message": "Drone is now on the way to delivery location.",
    },
]


class ControllerProtocol(Protocol):
    def start(self) -> None:
        ...

    def stop(self) -> None:
        ...

    def send_trigger(self, trigger_name: str, machine_name: str) -> bool:
        ...

    def set_pickup_order_id(self, order_id: str) -> None:
        ...


class SelectRestaurantRequest(BaseModel):
    restaurantName: str


class AddItemRequest(BaseModel):
    itemName: str


class RemoveItemRequest(BaseModel):
    itemName: str


class FrontendSession:
    def __init__(self, controller: ControllerProtocol):
        self.controller = controller
        self._lock = RLock()
        self.delivery_stage_index_map = {
            stage["key"]: index for index, stage in enumerate(DELIVERY_STAGES)
        }
        self._reset_local_state()

    def _reset_local_state(self) -> None:
        self.selected_restaurant: str | None = None
        self.selected_items: list[dict[str, Any]] = []
        self.cart_total = 0
        self.pickup_order_id = DEFAULT_PICKUP_ORDER_ID
        self.payment_requested = False
        self.payment_state = "Waiting"
        self.drone_state = "Waiting for order"
        self._latest_drone_state_raw = ""
        self.delivery_stage_index = -1
        self.delivery_tracking_started = False
        self.delivery_message = "Waiting for payment approval before drone dispatch."
        self.payment_message = "No payment request."
        self.order_details = "No order submitted."

    def restaurants(self) -> dict[str, Any]:
        return {
            "restaurants": [
                {
                    "id": restaurant["id"],
                    "name": name,
                    "items": restaurant["items"],
                }
                for name, restaurant in RESTAURANTS.items()
            ]
        }

    def state(self) -> dict[str, Any]:
        with self._lock:
            payment_phase = self._payment_phase()
            return {
                "selectedRestaurant": self.selected_restaurant,
                "selectedItems": list(self.selected_items),
                "cartTotal": self.cart_total,
                "paymentState": self.payment_state,
                "paymentPhase": payment_phase,
                "droneState": self.drone_state,
                "deliveryStages": DELIVERY_STAGES,
                "deliveryStageIndex": self.delivery_stage_index,
                "deliveryMessage": self.delivery_message,
                "deliveryTrackingStarted": self.delivery_tracking_started,
                "paymentRequested": self.payment_requested,
                "paymentMessage": self.payment_message,
                "orderDetails": self.order_details,
                "cartItemCount": self._cart_item_count(),
                "restaurantLocked": len(self.selected_items) > 0,
                "canCheckout": len(self.selected_items) > 0 and not self.payment_requested,
                "canDecidePayment": self.payment_requested and payment_phase == "pending",
            }

    def select_restaurant(self, restaurant_name: str) -> dict[str, Any]:
        if restaurant_name not in RESTAURANTS:
            raise HTTPException(status_code=404, detail="Restaurant not found")

        with self._lock:
            if self.payment_requested:
                raise HTTPException(
                    status_code=409,
                    detail="Reset the current order before changing restaurants",
                )
            if self.selected_items and restaurant_name != self.selected_restaurant:
                raise HTTPException(
                    status_code=409,
                    detail="Reset the cart before ordering from another restaurant",
                )

            self.selected_restaurant = restaurant_name
            if not self.selected_items:
                self.cart_total = 0
                self.order_details = "No order submitted."
            return self.state()

    def add_item(self, item_name: str) -> dict[str, Any]:
        with self._lock:
            if self.payment_requested:
                raise HTTPException(
                    status_code=409,
                    detail="Reset the current order before changing the cart",
                )
            if not self.selected_restaurant:
                raise HTTPException(status_code=400, detail="Select a restaurant first")

            restaurant_items = RESTAURANTS[self.selected_restaurant]["items"]
            item = next(
                (menu_item for menu_item in restaurant_items if menu_item["name"] == item_name),
                None,
            )
            if not item:
                raise HTTPException(status_code=404, detail="Menu item not found")

            selected_item = next(
                (selected for selected in self.selected_items if selected["name"] == item_name),
                None,
            )
            if selected_item:
                selected_item["quantity"] += 1
            else:
                self.selected_items.append(
                    {"name": item["name"], "price": item["price"], "quantity": 1}
                )

            self._recalculate_cart_total()

            return self.state()

    def remove_item(self, item_name: str) -> dict[str, Any]:
        with self._lock:
            if self.payment_requested:
                raise HTTPException(
                    status_code=409,
                    detail="Reset the current order before changing the cart",
                )
            if not self.selected_items:
                raise HTTPException(status_code=400, detail="Cart is empty")

            selected_item = next(
                (selected for selected in self.selected_items if selected["name"] == item_name),
                None,
            )
            if not selected_item:
                raise HTTPException(status_code=404, detail="Item not found in cart")

            selected_item["quantity"] -= 1
            if selected_item["quantity"] <= 0:
                self.selected_items = [
                    selected for selected in self.selected_items if selected["name"] != item_name
                ]

            self._recalculate_cart_total()
            return self.state()

    def checkout(self) -> dict[str, Any]:
        with self._lock:
            if not self.selected_items:
                raise HTTPException(status_code=400, detail="Cart is empty")
            order_details = self._build_order_details_text()

        self.controller.send_trigger("proceedToCart", "stm_order")
        self.controller.send_trigger("confirmOrder", "stm_order")
        self.controller.set_pickup_order_id(DEFAULT_PICKUP_ORDER_ID)
        self.controller.send_trigger("checkoutStarted", "stm_payment")

        with self._lock:
            self.pickup_order_id = DEFAULT_PICKUP_ORDER_ID
            self.payment_requested = True
            self.payment_state = "Pending payment"
            self.order_details = order_details
            self._reset_delivery_tracking("Waiting for payment approval before drone dispatch.")
            self._refresh_payment_feedback()
            return self.state()

    def approve_payment(self) -> dict[str, Any]:
        with self._lock:
            if not self.payment_requested or self._payment_phase() != "pending":
                self._mark_payment_cancelled("Payment request expired. Drone dispatch cancelled.")
                return self.state()

        sent = self.controller.send_trigger("paymentApproved", "stm_payment")
        if not sent:
            with self._lock:
                self._mark_payment_cancelled("Payment request expired. Drone dispatch cancelled.")
                return self.state()

        with self._lock:
            self.payment_message = "Approval sent. Waiting for backend confirmation."
            return self.state()

    def decline_payment(self) -> dict[str, Any]:
        sent = self.controller.send_trigger("paymentDeclined", "stm_payment")
        if not sent:
            with self._lock:
                self._mark_payment_cancelled("Payment request expired. Drone dispatch cancelled.")
                return self.state()

        with self._lock:
            self.payment_state = "Payment declined"
            self._reset_delivery_tracking("Payment declined. Drone dispatch cancelled.")
            self._refresh_payment_feedback()
            return self.state()

    def reset(self) -> dict[str, Any]:
        self.controller.send_trigger("resetOrder", "stm_order")
        self.controller.send_trigger("resetPayment", "stm_payment")

        with self._lock:
            self._reset_local_state()
            return self.state()

    def update_from_backend_callback(self, state_type: str, state_name: str) -> None:
        with self._lock:
            readable_state = (state_name or "").replace("_", " ")

            if state_type == "payment_state":
                self.payment_state = readable_state
                self._refresh_payment_feedback()
                payment_phase = self._payment_phase()
                if payment_phase == "approved":
                    self._start_delivery_tracking()
                elif payment_phase == "declined":
                    self._reset_delivery_tracking("Payment declined. Drone dispatch cancelled.")
                elif payment_phase == "cancelled":
                    self._reset_delivery_tracking(
                        "Payment request expired. Drone dispatch cancelled."
                    )
                elif payment_phase == "pending" and not self.delivery_tracking_started:
                    self._reset_delivery_tracking(
                        "Waiting for payment approval before drone dispatch."
                    )
            elif state_type == "drone_state":
                raw_drone_state = (state_name or "").strip()
                self.drone_state = raw_drone_state.replace("_", " ")
                self._latest_drone_state_raw = raw_drone_state
                if not self.delivery_tracking_started:
                    return
                self._update_delivery_from_drone_state(raw_drone_state)

    def _payment_phase(self) -> str:
        payment_state = self.payment_state.lower()

        if any(token in payment_state for token in ("approved", "accepted", "success")):
            return "approved"
        if any(token in payment_state for token in ("cancelled", "canceled", "expired", "timeout")):
            return "cancelled"
        if any(token in payment_state for token in ("declined", "denied", "rejected", "failed")):
            return "declined"
        if any(token in payment_state for token in ("pending", "waiting", "started")):
            return "pending"
        return "unknown"

    def _cart_item_count(self) -> int:
        return sum(selected["quantity"] for selected in self.selected_items)

    def _recalculate_cart_total(self) -> None:
        self.cart_total = sum(
            selected["price"] * selected["quantity"] for selected in self.selected_items
        )

    def _refresh_payment_feedback(self) -> None:
        if not self.payment_requested:
            self.payment_message = "No payment request."
            return

        phase = self._payment_phase()
        if phase == "approved":
            self.payment_message = "Payment approved. Drone delivery should continue."
        elif phase == "declined":
            self.payment_message = "Payment declined. Start a new order to retry."
        elif phase == "cancelled":
            self.payment_message = (
                "Payment request is no longer active. Start a new order to retry."
            )
        else:
            self.payment_message = "Payment request is still pending."

    def _mark_payment_cancelled(self, delivery_message: str) -> None:
        self.payment_state = "Payment cancelled"
        self._reset_delivery_tracking(delivery_message)
        self._refresh_payment_feedback()

    def _reset_delivery_tracking(self, message: str | None = None) -> None:
        self.delivery_tracking_started = False
        self.delivery_stage_index = -1
        self.delivery_message = message or "Waiting for payment approval before drone dispatch."

    def _start_delivery_tracking(self) -> None:
        if self.delivery_tracking_started:
            return

        self.delivery_tracking_started = True
        self.delivery_message = "Payment approved. Waiting for drone state updates from MQTT."
        if self._latest_drone_state_raw:
            self._update_delivery_from_drone_state(self._latest_drone_state_raw)

    def _set_delivery_stage(
        self,
        stage_key: str,
        *,
        force: bool = False,
        message_override: str | None = None,
    ) -> None:
        if stage_key not in self.delivery_stage_index_map:
            return

        target_index = self.delivery_stage_index_map[stage_key]
        if not force and target_index < self.delivery_stage_index:
            return

        self.delivery_stage_index = target_index
        self.delivery_message = message_override or DELIVERY_STAGES[target_index]["message"]

    def _update_delivery_from_drone_state(self, drone_state_text: str) -> None:
        state_text = (drone_state_text or "").strip().lower()
        base_state = state_text.split(" (")[0]
        reason = ""
        if "(" in state_text and ")" in state_text:
            reason = state_text[state_text.find("(") + 1 : state_text.rfind(")")].strip()

        if base_state in {
            "dispatch_requested",
            "dispatched_to_pickup",
            "in_flight_to_pickup",
            "to_restaurant",
        }:
            self._set_delivery_stage("to_restaurant")
        elif base_state == "at_pickup":
            self._set_delivery_stage("at_restaurant")
        elif base_state == "pickup_delayed":
            message = "Restaurant is not ready. Drone is waiting at pickup."
            if reason:
                message = f"Restaurant is not ready ({reason}). Drone is waiting at pickup."
            self._set_delivery_stage("at_restaurant", force=True, message_override=message)
        elif base_state == "package_loaded":
            self._set_delivery_stage("food_loaded")
        elif base_state == "in_flight":
            self._set_delivery_stage("to_customer")

    def _build_order_details_text(self) -> str:
        if not self.selected_restaurant:
            return "No order submitted."

        item_count = self._cart_item_count()
        item_word = "item" if item_count == 1 else "items"
        return (
            f"Restaurant: {self.selected_restaurant}\n"
            f"Items: {item_count} {item_word}\n"
            f"Total: {self.cart_total} kr"
        )


def create_app(
    controller_factory: Callable[[Callable[[str, str], None]], ControllerProtocol]
    | None = None,
) -> FastAPI:
    controller_factory = controller_factory or BackendController

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        session_holder: dict[str, FrontendSession] = {}

        def gui_callback(state_type: str, state_name: str) -> None:
            session_holder["session"].update_from_backend_callback(state_type, state_name)

        controller = controller_factory(gui_callback)
        session = FrontendSession(controller)
        session_holder["session"] = session
        app.state.controller = controller
        app.state.frontend_session = session

        controller.start()
        try:
            yield
        finally:
            controller.stop()

    app = FastAPI(title="DroneBite API", lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    def session() -> FrontendSession:
        return app.state.frontend_session

    @app.get("/restaurants")
    def get_restaurants() -> dict[str, Any]:
        return session().restaurants()

    @app.get("/state")
    def get_state() -> dict[str, Any]:
        return session().state()

    @app.post("/order/select-restaurant")
    def select_restaurant(payload: SelectRestaurantRequest) -> dict[str, Any]:
        return session().select_restaurant(payload.restaurantName)

    @app.post("/order/add-item")
    def add_item(payload: AddItemRequest) -> dict[str, Any]:
        return session().add_item(payload.itemName)

    @app.post("/order/remove-item")
    def remove_item(payload: RemoveItemRequest) -> dict[str, Any]:
        return session().remove_item(payload.itemName)

    @app.post("/order/checkout")
    def checkout() -> dict[str, Any]:
        return session().checkout()

    @app.post("/payment/approve")
    def approve_payment() -> dict[str, Any]:
        return session().approve_payment()

    @app.post("/payment/decline")
    def decline_payment() -> dict[str, Any]:
        return session().decline_payment()

    @app.post("/reset")
    def reset() -> dict[str, Any]:
        return session().reset()

    return app


app = create_app()
