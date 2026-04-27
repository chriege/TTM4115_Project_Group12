from collections.abc import Callable

import pytest
from fastapi.testclient import TestClient

from api_server import DEFAULT_PICKUP_ORDER_ID, create_app


class FakeController:
    def __init__(self, gui_callback: Callable[[str, str], None]):
        self.gui_callback = gui_callback
        self.triggers: list[tuple[str, str]] = []
        self.pickup_order_id = None
        self.started = False
        self.stopped = False
        self.next_send_result = True

    def start(self) -> None:
        self.started = True

    def stop(self) -> None:
        self.stopped = True

    def send_trigger(self, trigger_name: str, machine_name: str) -> bool:
        self.triggers.append((trigger_name, machine_name))
        return self.next_send_result

    def set_pickup_order_id(self, order_id: str) -> None:
        self.pickup_order_id = order_id


@pytest.fixture
def client_and_controller():
    app = create_app(lambda callback: FakeController(callback))
    with TestClient(app) as client:
        yield client, app.state.controller, app.state.frontend_session


def test_restaurants_endpoint_returns_restaurants(client_and_controller):
    client, controller, _ = client_and_controller

    response = client.get("/restaurants")

    assert response.status_code == 200
    restaurants = response.json()["restaurants"]
    assert controller.started is True
    assert {restaurant["name"] for restaurant in restaurants} == {
        "Pizza Palace",
        "Burger Queen",
    }
    assert restaurants[0]["items"]


def test_add_same_item_increments_quantity(client_and_controller):
    client, _, _ = client_and_controller

    select_response = client.post(
        "/order/select-restaurant",
        json={"restaurantName": "Pizza Palace"},
    )
    first_add = client.post("/order/add-item", json={"itemName": "Margherita"})
    second_add = client.post("/order/add-item", json={"itemName": "Margherita"})

    assert select_response.status_code == 200
    assert first_add.status_code == 200
    assert second_add.status_code == 200
    state = second_add.json()
    assert state["selectedRestaurant"] == "Pizza Palace"
    assert state["selectedItems"] == [
        {"name": "Margherita", "price": 150, "quantity": 2}
    ]
    assert state["cartTotal"] == 300
    assert state["cartItemCount"] == 2
    assert state["restaurantLocked"] is True
    assert state["canCheckout"] is True


def test_cart_rejects_items_from_multiple_restaurants(client_and_controller):
    client, _, _ = client_and_controller
    client.post("/order/select-restaurant", json={"restaurantName": "Pizza Palace"})
    client.post("/order/add-item", json={"itemName": "Margherita"})

    switch_response = client.post(
        "/order/select-restaurant",
        json={"restaurantName": "Burger Queen"},
    )

    assert switch_response.status_code == 409
    assert switch_response.json()["detail"] == (
        "Reset the cart before ordering from another restaurant"
    )
    state = client.get("/state").json()
    assert state["selectedRestaurant"] == "Pizza Palace"
    assert state["selectedItems"] == [
        {"name": "Margherita", "price": 150, "quantity": 1}
    ]
    assert state["cartTotal"] == 150


def test_remove_item_decrements_quantity_and_clears_line_when_zero(client_and_controller):
    client, _, _ = client_and_controller

    client.post("/order/select-restaurant", json={"restaurantName": "Pizza Palace"})
    client.post("/order/add-item", json={"itemName": "Margherita"})
    client.post("/order/add-item", json={"itemName": "Margherita"})

    first_remove = client.post("/order/remove-item", json={"itemName": "Margherita"})
    assert first_remove.status_code == 200
    state = first_remove.json()
    assert state["selectedItems"] == [
        {"name": "Margherita", "price": 150, "quantity": 1}
    ]
    assert state["cartTotal"] == 150
    assert state["cartItemCount"] == 1
    assert state["restaurantLocked"] is True

    second_remove = client.post("/order/remove-item", json={"itemName": "Margherita"})
    assert second_remove.status_code == 200
    state = second_remove.json()
    assert state["selectedItems"] == []
    assert state["cartTotal"] == 0
    assert state["cartItemCount"] == 0
    assert state["restaurantLocked"] is False
    assert state["canCheckout"] is False


def test_remove_item_rejects_when_not_in_cart(client_and_controller):
    client, _, _ = client_and_controller

    response = client.post("/order/remove-item", json={"itemName": "Margherita"})

    assert response.status_code == 400
    assert response.json()["detail"] == "Cart is empty"


def test_checkout_uses_pyqt_trigger_sequence(client_and_controller):
    client, controller, _ = client_and_controller
    client.post("/order/select-restaurant", json={"restaurantName": "Pizza Palace"})
    client.post("/order/add-item", json={"itemName": "Pepperoni"})

    response = client.post("/order/checkout")

    assert response.status_code == 200
    assert controller.triggers == [
        ("proceedToCart", "stm_order"),
        ("confirmOrder", "stm_order"),
        ("checkoutStarted", "stm_payment"),
    ]
    assert controller.pickup_order_id == DEFAULT_PICKUP_ORDER_ID
    state = response.json()
    assert state["paymentRequested"] is True
    assert state["paymentState"] == "Pending payment"
    assert state["paymentPhase"] == "pending"
    assert state["canDecidePayment"] is True


def test_approve_sends_payment_approved_and_callback_marks_delivery_ready(
    client_and_controller,
):
    client, controller, session = client_and_controller
    client.post("/order/select-restaurant", json={"restaurantName": "Pizza Palace"})
    client.post("/order/add-item", json={"itemName": "Vegetarian"})
    client.post("/order/checkout")

    response = client.post("/payment/approve")
    session.update_from_backend_callback("payment_state", "Payment accepted")
    state = client.get("/state").json()

    assert response.status_code == 200
    assert ("paymentApproved", "stm_payment") in controller.triggers
    assert state["paymentPhase"] == "approved"
    assert state["deliveryTrackingStarted"] is True
    assert state["deliveryMessage"] == (
        "Payment approved. Waiting for drone state updates from MQTT."
    )


def test_decline_sends_payment_declined_and_resets_delivery(client_and_controller):
    client, controller, _ = client_and_controller
    client.post("/order/select-restaurant", json={"restaurantName": "Pizza Palace"})
    client.post("/order/add-item", json={"itemName": "BBQ Chicken"})
    client.post("/order/checkout")

    response = client.post("/payment/decline")

    assert response.status_code == 200
    assert ("paymentDeclined", "stm_payment") in controller.triggers
    state = response.json()
    assert state["paymentPhase"] == "declined"
    assert state["deliveryStageIndex"] == -1
    assert state["deliveryMessage"] == "Payment declined. Drone dispatch cancelled."


def test_drone_callback_before_payment_does_not_start_delivery_timeline(
    client_and_controller,
):
    client, _, session = client_and_controller

    session.update_from_backend_callback("drone_state", "waiting_for_drone")
    state = client.get("/state").json()

    assert state["droneState"] == "waiting for drone"
    assert state["deliveryTrackingStarted"] is False
    assert state["deliveryStageIndex"] == -1
    assert state["deliveryMessage"] == "Waiting for payment approval before drone dispatch."

    client.post("/order/select-restaurant", json={"restaurantName": "Pizza Palace"})
    client.post("/order/add-item", json={"itemName": "Margherita"})
    client.post("/order/checkout")
    session.update_from_backend_callback("drone_state", "dispatched_to_pickup")
    state = client.get("/state").json()

    assert state["droneState"] == "dispatched to pickup"
    assert state["deliveryTrackingStarted"] is False
    assert state["deliveryStageIndex"] == -1
    assert state["deliveryMessage"] == "Waiting for payment approval before drone dispatch."


def test_drone_update_arriving_before_payment_approval_is_applied_after_approval(
    client_and_controller,
):
    client, _, session = client_and_controller
    client.post("/order/select-restaurant", json={"restaurantName": "Pizza Palace"})
    client.post("/order/add-item", json={"itemName": "Margherita"})
    client.post("/order/checkout")

    session.update_from_backend_callback("drone_state", "in_flight_to_pickup")
    state = client.get("/state").json()
    assert state["deliveryTrackingStarted"] is False
    assert state["deliveryStageIndex"] == -1

    session.update_from_backend_callback("payment_state", "Payment accepted")
    state = client.get("/state").json()
    assert state["deliveryTrackingStarted"] is True
    assert state["deliveryStageIndex"] == 0
    assert state["deliveryMessage"] == "Drone is in flight to the restaurant."


def test_backend_drone_callbacks_drive_delivery_timeline(client_and_controller):
    client, _, session = client_and_controller
    client.post("/order/select-restaurant", json={"restaurantName": "Pizza Palace"})
    client.post("/order/add-item", json={"itemName": "Vegetarian"})
    client.post("/order/checkout")
    session.update_from_backend_callback("payment_state", "Payment accepted")

    session.update_from_backend_callback("drone_state", "waiting_for_drone")
    state = client.get("/state").json()
    assert state["deliveryStageIndex"] == -1
    assert state["deliveryMessage"] == (
        "Payment approved. Waiting for drone state updates from MQTT."
    )

    session.update_from_backend_callback("drone_state", "dispatched_to_pickup")
    state = client.get("/state").json()
    assert state["deliveryStageIndex"] == 0
    assert state["deliveryMessage"] == "Drone is in flight to the restaurant."

    session.update_from_backend_callback("drone_state", "pickup_delayed (kitchen busy)")
    state = client.get("/state").json()
    assert state["deliveryStageIndex"] == 1
    assert state["deliveryMessage"] == (
        "Restaurant is not ready (kitchen busy). Drone is waiting at pickup."
    )

    session.update_from_backend_callback("drone_state", "in_flight")
    state = client.get("/state").json()
    assert state["deliveryStageIndex"] == 3
    assert state["deliveryMessage"] == "Drone is now on the way to delivery location."


def test_reset_sends_reset_triggers_and_clears_frontend_state(client_and_controller):
    client, controller, session = client_and_controller
    client.post("/order/select-restaurant", json={"restaurantName": "Burger Queen"})
    client.post("/order/add-item", json={"itemName": "Classic Burger"})
    client.post("/order/checkout")
    session.update_from_backend_callback("drone_state", "in_flight")

    response = client.post("/reset")

    assert response.status_code == 200
    assert ("resetOrder", "stm_order") in controller.triggers
    assert ("resetPayment", "stm_payment") in controller.triggers
    state = response.json()
    assert state["selectedRestaurant"] is None
    assert state["selectedItems"] == []
    assert state["cartTotal"] == 0
    assert state["paymentRequested"] is False
    assert state["paymentState"] == "Waiting"
    assert state["droneState"] == "Waiting for order"
    assert state["deliveryStageIndex"] == -1
