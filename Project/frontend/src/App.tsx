import { useCallback, useEffect, useMemo, useState } from "react";
import droneBiteLogo from "./assets/dronebite-logo.png";
import {
  AlertTriangle,
  ArrowLeft,
  CheckCircle2,
  CreditCard,
  Minus,
  Plus,
  Receipt,
  RotateCcw,
  Store,
  Truck,
  Utensils,
  XCircle
} from "lucide-react";

type MenuItem = {
  name: string;
  price: number;
};

type CartItem = MenuItem & {
  quantity: number;
};

type Restaurant = {
  id: number;
  name: string;
  items: MenuItem[];
};

type DeliveryStage = {
  key: string;
  label: string;
  message: string;
};

type ViewScreen = "restaurants" | "menu" | "tracking";

type AppState = {
  selectedRestaurant: string | null;
  selectedItems: CartItem[];
  cartTotal: number;
  paymentState: string;
  paymentPhase: string;
  droneState: string;
  deliveryStages: DeliveryStage[];
  deliveryStageIndex: number;
  deliveryMessage: string;
  deliveryTrackingStarted: boolean;
  paymentRequested: boolean;
  paymentMessage: string;
  orderDetails: string;
  cartItemCount: number;
  restaurantLocked: boolean;
  canCheckout: boolean;
  canDecidePayment: boolean;
};

type RestaurantsResponse = {
  restaurants: Restaurant[];
};

const API_BASE = import.meta.env.VITE_API_BASE ?? "";
const SCREEN_SEQUENCE: ViewScreen[] = ["restaurants", "menu", "tracking"];
const TRACKING_PHASES = new Set(["approved", "declined", "cancelled"]);
const DELIVERY_TIMELINE: DeliveryStage[] = [
  {
    key: "to_restaurant",
    label: "Drone in flight to restaurant",
    message: "Your drone is on the way to the restaurant."
  },
  {
    key: "at_restaurant",
    label: "Drone at restaurant and waiting for food",
    message: "The drone has arrived and is waiting for the kitchen handoff."
  },
  {
    key: "food_loaded",
    label: "Food loaded into drone",
    message: "Your food is packed and loaded for delivery."
  },
  {
    key: "to_customer",
    label: "Drone in flight to delivery location",
    message: "The drone is heading to your delivery location."
  }
];

async function requestJson<T>(
  path: string,
  options: RequestInit = {},
  signal?: AbortSignal
): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    ...options,
    signal,
    headers: {
      ...(options.body ? { "Content-Type": "application/json" } : {}),
      ...options.headers
    }
  });

  if (!response.ok) {
    let message = `Request failed with ${response.status}`;
    try {
      const body = (await response.json()) as { detail?: string };
      if (body.detail) {
        message = body.detail;
      }
    } catch {
      // Keep the HTTP status fallback.
    }
    throw new Error(message);
  }

  return response.json() as Promise<T>;
}

function isMissingEndpointError(error: unknown) {
  if (!(error instanceof Error)) {
    return false;
  }
  return (
    error.message === "Not Found" || error.message.includes("Request failed with 404")
  );
}

function formatKr(value: number) {
  return `${value} kr`;
}

function getCuisineHint(restaurantName: string, items: MenuItem[]) {
  const content = `${restaurantName} ${items.map((item) => item.name).join(" ")}`
    .toLowerCase()
    .trim();

  if (/(pizza|pasta|lasagna|risotto)/.test(content)) {
    return "Italian comfort food";
  }
  if (/(sushi|ramen|tempura|udon|poke)/.test(content)) {
    return "Japanese kitchen";
  }
  if (/(burger|fries|bbq|wings|wrap)/.test(content)) {
    return "Street food favorites";
  }
  if (/(salad|bowl|veggie|avocado)/.test(content)) {
    return "Fresh bowls and greens";
  }
  if (/(taco|burrito|quesadilla|nacho)/.test(content)) {
    return "Mexican classics";
  }
  return "Meals prepared for drone pickup";
}

function getMenuDescription(itemName: string) {
  const item = itemName.toLowerCase();
  if (/(burger|wrap|sandwich)/.test(item)) {
    return "Hand-crafted and packed hot for quick delivery.";
  }
  if (/(salad|bowl)/.test(item)) {
    return "Fresh ingredients with balanced flavor.";
  }
  if (/(pizza|pasta|noodle)/.test(item)) {
    return "Kitchen favorite prepared to order.";
  }
  if (/(dessert|cake|cookie|brownie)/.test(item)) {
    return "Sweet finish delivered with care.";
  }
  return "Prepared fresh and ready for drone handoff.";
}

function getCartItem(state: AppState | null, itemName: string) {
  return state?.selectedItems.find((item) => item.name === itemName) ?? null;
}

function toFriendlyText(value: string | null | undefined) {
  if (!value) {
    return "Waiting for updates";
  }

  const normalized = value.replace(/_/g, " ").replace(/\s+/g, " ").trim();
  if (!normalized) {
    return "Waiting for updates";
  }
  return normalized.charAt(0).toUpperCase() + normalized.slice(1);
}

function toFriendlyDeliveryMessage(value: string | null | undefined) {
  if (!value) {
    return "Delivery updates will appear here.";
  }

  const normalized = value.trim();
  if (!normalized) {
    return "Delivery updates will appear here.";
  }

  const lowered = normalized.toLowerCase();
  if (lowered.includes("mqtt")) {
    return "Payment approved. Waiting for the drone to report its first movement.";
  }
  return normalized;
}

function isTrackingScreenState(state: AppState) {
  return (
    state.paymentRequested ||
    state.deliveryTrackingStarted ||
    TRACKING_PHASES.has(state.paymentPhase)
  );
}

type HeaderProps = {
  currentScreen: ViewScreen;
  itemCount: number;
  cartTotal: number;
  onReset: () => Promise<void>;
  resetDisabled: boolean;
};

function AppHeader({
  currentScreen,
  itemCount,
  cartTotal,
  onReset,
  resetDisabled
}: HeaderProps) {
  const orderActive = itemCount > 0 || currentScreen === "tracking";

  return (
    <header className="app-header">
      <div className="brand-lockup">
        <img className="brand-logo" src={droneBiteLogo} alt="DroneBite logo" />
      </div>
      <div className="header-controls">
        {currentScreen === "restaurants" ? (
          <p className="header-note">Drone pickup available from selected kitchens.</p>
        ) : (
          <div className="header-summary">
            <Receipt size={16} />
            <span>
              {itemCount} item{itemCount === 1 ? "" : "s"} | {formatKr(cartTotal)}
            </span>
          </div>
        )}
        {orderActive ? (
          <button
            className="button-secondary reset-button"
            type="button"
            onClick={onReset}
            disabled={resetDisabled}
          >
            <RotateCcw size={16} />
            New order
          </button>
        ) : null}
      </div>
    </header>
  );
}

type StepIndicatorProps = {
  currentScreen: ViewScreen;
  canNavigateTo: Record<ViewScreen, boolean>;
  onStepSelect: (screen: ViewScreen) => void;
};

function StepIndicator({
  currentScreen,
  canNavigateTo,
  onStepSelect
}: StepIndicatorProps) {
  const activeStep = SCREEN_SEQUENCE.indexOf(currentScreen);

  return (
    <nav className="step-indicator" aria-label="Order progress">
      {SCREEN_SEQUENCE.map((screen, index) => {
        const completed = index < activeStep;
        const active = index === activeStep;
        const enabled = active || canNavigateTo[screen];
        return (
          <button
            key={screen}
            type="button"
            className={`step-chip${active ? " active" : ""}${completed ? " done" : ""}`}
            onClick={() => onStepSelect(screen)}
            disabled={!enabled}
            aria-current={active ? "step" : undefined}
          >
            <span className="step-index">{index + 1}</span>
            <span className="step-label">
              {screen === "restaurants" && "Restaurant"}
              {screen === "menu" && "Menu & cart"}
              {screen === "tracking" && "Tracking"}
            </span>
          </button>
        );
      })}
    </nav>
  );
}

type RestaurantSelectionProps = {
  restaurants: Restaurant[];
  state: AppState | null;
  busyAction: string | null;
  onSelectRestaurant: (restaurantName: string) => Promise<void>;
};

function RestaurantSelectionScreen({
  restaurants,
  state,
  busyAction,
  onSelectRestaurant
}: RestaurantSelectionProps) {
  return (
    <section className="screen-card">
      <div className="screen-header">
        <p className="screen-kicker">Step 1</p>
        <h2>Choose a restaurant</h2>
        <p>Drone pickup is available from these partner kitchens.</p>
      </div>

      <div className="restaurant-grid">
        {restaurants.length ? (
          restaurants.map((restaurant) => {
            const selected = state?.selectedRestaurant === restaurant.name;
            const locked = Boolean(state?.restaurantLocked && !selected);
            const disabled = locked || state?.paymentRequested || busyAction === "select";

            return (
              <article
                key={restaurant.id}
                className={`restaurant-card${selected ? " selected" : ""}${locked ? " locked" : ""}`}
              >
                <div className="restaurant-meta">
                  <div>
                    <h3>{restaurant.name}</h3>
                    <p>{getCuisineHint(restaurant.name, restaurant.items)}</p>
                  </div>
                  <span className="restaurant-count">{restaurant.items.length} menu items</span>
                </div>
                <button
                  className="button-primary"
                  type="button"
                  onClick={() => onSelectRestaurant(restaurant.name)}
                  disabled={disabled}
                  title={
                    locked
                      ? "Start a new order before switching to another restaurant."
                      : undefined
                  }
                >
                  <Store size={16} />
                  View menu
                </button>
              </article>
            );
          })
        ) : (
          <div className="empty-state">Loading restaurants...</div>
        )}
      </div>
    </section>
  );
}

type MenuScreenProps = {
  selectedRestaurant: Restaurant | null;
  selectedRestaurantName: string | null;
  state: AppState | null;
  busyAction: string | null;
  onBack: () => void;
  onAddItem: (itemName: string) => Promise<void>;
  onRemoveItem: (itemName: string) => Promise<void>;
  onCheckout: () => Promise<void>;
  onReset: () => Promise<void>;
};

function MenuScreen({
  selectedRestaurant,
  selectedRestaurantName,
  state,
  busyAction,
  onBack,
  onAddItem,
  onRemoveItem,
  onCheckout,
  onReset
}: MenuScreenProps) {
  return (
    <section className="screen-card menu-screen">
      <div className="screen-header menu-header">
        <button className="button-ghost back-button" type="button" onClick={onBack}>
          <ArrowLeft size={16} />
          Back to restaurants
        </button>
        <p className="screen-kicker">Step 2</p>
        <h2>{selectedRestaurantName ?? "Menu"}</h2>
      </div>

      <div className="menu-layout">
        <div className="menu-listing">
          <div className="section-title">
            <Utensils size={18} />
            <h3>Available dishes</h3>
          </div>
          <div className="menu-grid">
            {selectedRestaurant ? (
              selectedRestaurant.items.map((item) => {
                const quantity = getCartItem(state, item.name)?.quantity ?? 0;
                return (
                  <article key={item.name} className="menu-card">
                    <div className="menu-copy">
                      <h4>{item.name}</h4>
                      <p>{getMenuDescription(item.name)}</p>
                    </div>
                    <div className="menu-actions">
                      <strong>{formatKr(item.price)}</strong>
                      <button
                        className="button-primary"
                        type="button"
                        onClick={() => onAddItem(item.name)}
                        disabled={state?.paymentRequested || busyAction === "add-item"}
                      >
                        <Plus size={16} />
                        Add
                      </button>
                    </div>
                    {quantity > 0 ? <span className="quantity-pill">In cart: {quantity}</span> : null}
                  </article>
                );
              })
            ) : (
              <div className="empty-state">
                Menu is loading. Select this restaurant again if data does not appear.
              </div>
            )}
          </div>
        </div>

        <aside className="cart-panel" aria-label="Cart summary">
          <div className="section-title">
            <Receipt size={18} />
            <h3>Your cart</h3>
          </div>
          <div className="cart-lines">
            {state?.selectedItems.length ? (
              state.selectedItems.map((item) => (
                <div className="cart-line" key={item.name}>
                  <span>
                    {item.name}
                    <small>x{item.quantity}</small>
                  </span>
                  <div className="cart-line-actions">
                    <strong>{formatKr(item.price * item.quantity)}</strong>
                    <button
                      className="line-remove"
                      type="button"
                      onClick={() => onRemoveItem(item.name)}
                      disabled={state?.paymentRequested || busyAction === "remove-item"}
                      aria-label={`Remove one ${item.name} from cart`}
                    >
                      <Minus size={14} />
                    </button>
                  </div>
                </div>
              ))
            ) : (
              <p className="muted-copy">Add items from the menu to begin checkout.</p>
            )}
          </div>

          <div className="cart-total">
            <span>Total</span>
            <strong>{formatKr(state?.cartTotal ?? 0)}</strong>
          </div>

          <div className="cart-actions">
            <button
              className="button-primary checkout-button"
              type="button"
              onClick={onCheckout}
              disabled={!state?.canCheckout || busyAction === "checkout"}
            >
              <CreditCard size={16} />
              Checkout
            </button>
            <button
              className="button-secondary"
              type="button"
              onClick={onReset}
              disabled={busyAction === "reset"}
            >
              <RotateCcw size={16} />
              Start over
            </button>
          </div>
        </aside>
      </div>
    </section>
  );
}

type TrackingScreenProps = {
  state: AppState | null;
  busyAction: string | null;
  onApprovePayment: () => Promise<void>;
  onDeclinePayment: () => Promise<void>;
  onReset: () => Promise<void>;
};

function TrackingScreen({
  state,
  busyAction,
  onApprovePayment,
  onDeclinePayment,
  onReset
}: TrackingScreenProps) {
  const activeStageIndex = state?.deliveryStageIndex ?? -1;
  const droneState = (state?.droneState ?? "").toLowerCase();
  const pickupDelayed =
    droneState.startsWith("pickup delayed") || droneState.startsWith("pickup_delayed");

  return (
    <section className="screen-card tracking-screen">
      <div className="screen-header">
        <p className="screen-kicker">Step 3</p>
        <h2>Delivery and payment tracking</h2>
        <p>Follow payment confirmation and live drone delivery progress.</p>
      </div>

      <div className="tracking-layout">
        <div className="tracking-main">
          <div className="status-grid">
            <article className="status-card">
              <div className="section-title">
                <CreditCard size={18} />
                <h3>Payment status</h3>
              </div>
              <strong className={`state-pill payment-${state?.paymentPhase ?? "unknown"}`}>
                {toFriendlyText(state?.paymentState)}
              </strong>
              <p>{toFriendlyText(state?.paymentMessage)}</p>
            </article>
          </div>

          <article className="timeline-card">
            <div className="section-title">
              <Truck size={18} />
              <h3>Delivery timeline</h3>
            </div>
            {pickupDelayed ? (
              <div className="delay-banner" role="status" aria-live="polite">
                <AlertTriangle size={16} />
                <div>
                  <strong>Delay at restaurant</strong>
                  <p>{toFriendlyDeliveryMessage(state?.deliveryMessage)}</p>
                </div>
              </div>
            ) : null}
            <ol className="timeline-list">
              {DELIVERY_TIMELINE.map((stage, index) => {
                const done = activeStageIndex > index;
                const active = activeStageIndex === index;
                return (
                  <li
                    key={stage.key}
                    className={`timeline-step${done ? " done" : ""}${active ? " active" : ""}`}
                  >
                    <span className="timeline-marker" aria-hidden="true" />
                    <div>
                      <strong>{stage.label}</strong>
                      <p>{stage.message}</p>
                    </div>
                  </li>
                );
              })}
            </ol>
          </article>
        </div>

        <aside className="tracking-side">
          <article className="receipt-card">
            <div className="section-title">
              <Receipt size={18} />
              <h3>Order summary</h3>
            </div>
            <p className="receipt-restaurant">{state?.selectedRestaurant ?? "No restaurant selected"}</p>
            <div className="cart-lines">
              {state?.selectedItems.length ? (
                state.selectedItems.map((item) => (
                  <div className="cart-line" key={item.name}>
                    <span>
                      {item.name}
                      <small>x{item.quantity}</small>
                    </span>
                    <strong>{formatKr(item.price * item.quantity)}</strong>
                  </div>
                ))
              ) : (
                <p className="muted-copy">No items in this order.</p>
              )}
            </div>
            <div className="cart-total">
              <span>Total</span>
              <strong>{formatKr(state?.cartTotal ?? 0)}</strong>
            </div>
          </article>

          <article className="terminal-card">
            <div className="section-title">
              <CreditCard size={18} />
              <h3>Demo payment terminal</h3>
            </div>
            <p>Use these controls to approve or decline the active payment request.</p>
            <div className="terminal-actions">
              <button
                className="button-primary approve-button"
                type="button"
                onClick={onApprovePayment}
                disabled={!state?.canDecidePayment || busyAction === "approve"}
              >
                <CheckCircle2 size={16} />
                Approve payment
              </button>
              <button
                className="button-secondary decline-button"
                type="button"
                onClick={onDeclinePayment}
                disabled={!state?.canDecidePayment || busyAction === "decline"}
              >
                <XCircle size={16} />
                Decline payment
              </button>
            </div>
          </article>

          <button
            className="button-secondary new-order-action"
            type="button"
            onClick={onReset}
            disabled={busyAction === "reset"}
          >
            <RotateCcw size={16} />
            Reset and start new order
          </button>
        </aside>
      </div>
    </section>
  );
}

export default function App() {
  const [restaurants, setRestaurants] = useState<Restaurant[]>([]);
  const [state, setState] = useState<AppState | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busyAction, setBusyAction] = useState<string | null>(null);
  const [currentScreen, setCurrentScreen] = useState<ViewScreen>("restaurants");
  const [screenInitialized, setScreenInitialized] = useState(false);

  const selectedRestaurant = useMemo(
    () =>
      restaurants.find(
        (restaurant) => restaurant.name === state?.selectedRestaurant
      ) ?? null,
    [restaurants, state?.selectedRestaurant]
  );

  const refreshState = useCallback(
    async (signal?: AbortSignal) => {
      const nextState = await requestJson<AppState>("/state", {}, signal);
      setState(nextState);
      setError(null);
    },
    []
  );

  useEffect(() => {
    const controller = new AbortController();

    requestJson<RestaurantsResponse>("/restaurants", {}, controller.signal)
      .then((payload) => setRestaurants(payload.restaurants))
      .catch((nextError: Error) => {
        if (nextError.name !== "AbortError") {
          setError(nextError.message);
        }
      });

    return () => controller.abort();
  }, []);

  useEffect(() => {
    let cancelled = false;
    let activeController: AbortController | null = null;

    const pollState = async () => {
      activeController?.abort();
      activeController = new AbortController();
      try {
        const nextState = await requestJson<AppState>(
          "/state",
          {},
          activeController.signal
        );
        if (!cancelled) {
          setState(nextState);
          setError(null);
        }
      } catch (nextError) {
        if (
          !cancelled &&
          nextError instanceof Error &&
          nextError.name !== "AbortError"
        ) {
          setError(nextError.message);
        }
      }
    };

    pollState();
    const interval = window.setInterval(pollState, 750);

    return () => {
      cancelled = true;
      window.clearInterval(interval);
      activeController?.abort();
    };
  }, []);

  const runAction = useCallback(
    async (
      action: string,
      path: string,
      body?: unknown
    ): Promise<AppState | null> => {
      setBusyAction(action);
      try {
        const nextState = await requestJson<AppState>(path, {
          method: "POST",
          body: body ? JSON.stringify(body) : undefined
        });
        setState(nextState);
        setError(null);
        return nextState;
      } catch (nextError) {
        if (nextError instanceof Error) {
          setError(nextError.message);
        }
        return null;
      } finally {
        setBusyAction(null);
      }
    },
    []
  );

  useEffect(() => {
    if (!state) {
      return;
    }

    if (!screenInitialized) {
      setScreenInitialized(true);
      return;
    }

    const shouldTrack = isTrackingScreenState(state);

    if (!shouldTrack && currentScreen === "tracking") {
      setCurrentScreen(state.selectedRestaurant ? "menu" : "restaurants");
      return;
    }

    if (!shouldTrack && !state.selectedRestaurant && currentScreen !== "restaurants") {
      setCurrentScreen("restaurants");
    }
  }, [state, currentScreen, screenInitialized]);

  const handleSelectRestaurant = useCallback(
    async (restaurantName: string) => {
      const nextState = await runAction("select", "/order/select-restaurant", {
        restaurantName
      });
      if (nextState) {
        setCurrentScreen("menu");
      }
    },
    [runAction]
  );

  const handleAddItem = useCallback(
    async (itemName: string) => {
      await runAction("add-item", "/order/add-item", { itemName });
    },
    [runAction]
  );

  const handleRemoveItem = useCallback(
    async (itemName: string) => {
      setBusyAction("remove-item");
      try {
        const payload = { itemName };
        const candidatePaths = [
          "/order/remove-item",
          "/order/remove_item",
          "/order/remove"
        ];

        let nextState: AppState | null = null;
        for (const path of candidatePaths) {
          try {
            nextState = await requestJson<AppState>(path, {
              method: "POST",
              body: JSON.stringify(payload)
            });
            break;
          } catch (nextError) {
            if (isMissingEndpointError(nextError)) {
              continue;
            }
            throw nextError;
          }
        }

        if (!nextState) {
          throw new Error(
            "Cart remove endpoint is missing on backend. Restart the backend with the latest api_server.py."
          );
        }

        setState(nextState);
        setError(null);
      } catch (nextError) {
        if (nextError instanceof Error) {
          setError(nextError.message);
        } else {
          setError("Unable to remove item from cart.");
        }
      } finally {
        setBusyAction(null);
      }
    },
    []
  );

  const handleCheckout = useCallback(async () => {
    const nextState = await runAction("checkout", "/order/checkout");
    if (nextState) {
      setCurrentScreen("tracking");
    }
  }, [runAction]);

  const handleApprovePayment = useCallback(async () => {
    await runAction("approve", "/payment/approve");
  }, [runAction]);

  const handleDeclinePayment = useCallback(async () => {
    await runAction("decline", "/payment/decline");
  }, [runAction]);

  const handleReset = useCallback(async () => {
    const nextState = await runAction("reset", "/reset");
    if (nextState) {
      setCurrentScreen("restaurants");
    }
  }, [runAction]);

  const itemCount = state?.cartItemCount ?? 0;
  const cartTotal = state?.cartTotal ?? 0;
  const selectedRestaurantName = state?.selectedRestaurant ?? null;
  const selectedRestaurantLabel =
    selectedRestaurant?.name ?? selectedRestaurantName ?? null;
  const currentStepNumber = SCREEN_SEQUENCE.indexOf(currentScreen) + 1;
  const canNavigateTo = useMemo<Record<ViewScreen, boolean>>(
    () => ({
      restaurants: true,
      menu: Boolean(state?.selectedRestaurant),
      tracking: Boolean(state && isTrackingScreenState(state))
    }),
    [state]
  );

  const handleStepSelect = useCallback(
    (targetScreen: ViewScreen) => {
      if (targetScreen === currentScreen || !canNavigateTo[targetScreen]) {
        return;
      }
      setCurrentScreen(targetScreen);
    },
    [canNavigateTo, currentScreen]
  );

  return (
    <div className="app-shell">
      <a href="#main-content" className="skip-link">
        Skip to main content
      </a>

      <AppHeader
        currentScreen={currentScreen}
        itemCount={itemCount}
        cartTotal={cartTotal}
        onReset={handleReset}
        resetDisabled={busyAction === "reset"}
      />

      <div className="screen-status">
        <StepIndicator
          currentScreen={currentScreen}
          canNavigateTo={canNavigateTo}
          onStepSelect={handleStepSelect}
        />
        <p>Step {currentStepNumber} of 3</p>
      </div>

      {error ? <div className="error-banner">{error}</div> : null}

      <main className="screen-shell" id="main-content">
        {currentScreen === "restaurants" ? (
          <RestaurantSelectionScreen
            restaurants={restaurants}
            state={state}
            busyAction={busyAction}
            onSelectRestaurant={handleSelectRestaurant}
          />
        ) : null}

        {currentScreen === "menu" ? (
          <MenuScreen
            selectedRestaurant={selectedRestaurant}
            selectedRestaurantName={selectedRestaurantLabel}
            state={state}
            busyAction={busyAction}
            onBack={() => setCurrentScreen("restaurants")}
            onAddItem={handleAddItem}
            onRemoveItem={handleRemoveItem}
            onCheckout={handleCheckout}
            onReset={handleReset}
          />
        ) : null}

        {currentScreen === "tracking" ? (
          <TrackingScreen
            state={state}
            busyAction={busyAction}
            onApprovePayment={handleApprovePayment}
            onDeclinePayment={handleDeclinePayment}
            onReset={handleReset}
          />
        ) : null}
      </main>
    </div>
  );
}
