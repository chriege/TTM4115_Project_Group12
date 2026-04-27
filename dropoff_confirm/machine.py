from __future__ import annotations

from stmpy import Machine

from .controller import DropoffConfirmationController


def build_dropoff_machine(
    controller: DropoffConfirmationController,
    flight_to_pickup_timeout_ms: int | None = None,
    pickup_retry_timeout_ms: int | None = None,
    confirmation_timeout_ms: int | None = None,
) -> Machine:
    effective_flight_to_pickup_timeout_ms = (
        flight_to_pickup_timeout_ms
        if flight_to_pickup_timeout_ms is not None
        else 8000
    )
    effective_retry_timeout_ms = (
        pickup_retry_timeout_ms
        if pickup_retry_timeout_ms is not None
        else confirmation_timeout_ms
        if confirmation_timeout_ms is not None
        else 60000
    )
    states = [
        {
            "name": "waiting_for_drone",
            "entry": "set_state_waiting_for_drone; led_off",
        },
        {
            "name": "in_flight_to_pickup",
            "entry": (
                "set_state_in_flight_to_pickup; "
                "set_status_to_restaurant; "
                "notify_heading_to_restaurant; "
                f'start_timer("t_arrive_pickup", {effective_flight_to_pickup_timeout_ms})'
            ),
            "exit": 'stop_timer("t_arrive_pickup")',
        },
        {
            "name": "at_pickup",
            "entry": (
                "set_state_at_pickup; "
                "led_blink_waiting; "
                "set_status_at_pickup; "
                "notify_restaurant_ready; "
            ),
        },
        {
            "name": "pickup_delayed",
            "entry": (
                "set_state_pickup_delayed; "
                "set_status_pickup_delayed; "
                "hold_position; "
                f'start_timer("t_pickup_retry", {effective_retry_timeout_ms})'
            ),
            "exit": 'stop_timer("t_pickup_retry")',
        },
        {
            "name": "package_loaded",
            "entry": "set_state_package_loaded; authorize_takeoff",
        },
        {
            "name": "in_flight",
            "entry": (
                "set_state_in_flight; "
                "set_status_in_flight; "
                "notify_in_flight"
            ),
        },
        {"name": "final"},
    ]

    transitions = [
        {"source": "initial", "target": "waiting_for_drone"},
        {
            "trigger": "pickup_arrived",
            "source": "waiting_for_drone",
            "target": "in_flight_to_pickup",
        },
        {
            "trigger": "t_arrive_pickup",
            "source": "in_flight_to_pickup",
            "target": "at_pickup",
        },
        {
            "trigger": "not_ready",
            "source": "at_pickup",
            "target": "pickup_delayed",
        },
        {
            "trigger": "t_pickup_retry",
            "source": "pickup_delayed",
            "target": "at_pickup",
        },
        {
            "trigger": "package_loaded",
            "source": "at_pickup",
            "target": "package_loaded",
        },
        {
            "trigger": "package_loaded",
            "source": "pickup_delayed",
            "target": "package_loaded",
        },
        {
            "trigger": "takeoff_confirmed",
            "source": "package_loaded",
            "target": "in_flight",
        },
        {
            "trigger": "reset",
            "source": "waiting_for_drone",
            "target": "waiting_for_drone",
        },
        {
            "trigger": "reset",
            "source": "in_flight_to_pickup",
            "target": "waiting_for_drone",
        },
        {
            "trigger": "reset",
            "source": "at_pickup",
            "target": "waiting_for_drone",
        },
        {
            "trigger": "reset",
            "source": "pickup_delayed",
            "target": "waiting_for_drone",
        },
        {
            "trigger": "reset",
            "source": "package_loaded",
            "target": "waiting_for_drone",
        },
        {
            "trigger": "reset",
            "source": "in_flight",
            "target": "waiting_for_drone",
        },
        {
            "trigger": "workflow_completed",
            "source": "in_flight",
            "target": "final",
        },
    ]

    return Machine(
        name=f"pickup_dispatch_{controller.config.order_id}",
        transitions=transitions,
        states=states,
        obj=controller,
    )
