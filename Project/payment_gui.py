import sys
from PyQt5.QtCore import QSize, QThread, Qt, pyqtSignal
from PyQt5.QtWidgets import (
    QApplication,
    QFrame,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QPushButton,
    QSizePolicy,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from resturrant import RESTAURANTS
from user import BackendController, DEFAULT_PICKUP_ORDER_ID


APP_STYLESHEET = """
QWidget {
    background-color: #FAF7F0;
    color: #102A2A;
    font-family: "Segoe UI";
    font-size: 14px;
}
QWidget#RootWidget {
    background-color: #FAF7F0;
}
QFrame#AppShell {
    background-color: #FAF7F0;
    border: none;
    border-radius: 0;
}
QFrame#TopBar {
    background-color: #006D5B;
    border-radius: 22px;
    border: 1px solid #0B7A68;
}
QLabel#BrandName {
    background: transparent;
    color: #FFFFFF;
    font-family: "Segoe UI Semibold";
    font-size: 22px;
}
QLabel#TopMeta {
    background: transparent;
    color: #D6F2EC;
    font-size: 13px;
}
QLabel#TopBadge {
    background-color: #FF9F1C;
    border: 1px solid #FFC46B;
    border-radius: 18px;
    color: #102A2A;
    font-family: "Segoe UI Semibold";
    padding: 8px 14px;
}
QLabel#PageTitle {
    color: #102A2A;
    font-family: "Segoe UI Semibold";
    font-size: 34px;
}
QLabel#PageSubtitle {
    color: #667085;
    font-size: 14px;
}
QFrame#StepRow {
    background-color: #FFFFFF;
    border: 1px solid #E6DED2;
    border-radius: 18px;
}
QLabel#StepChip {
    border-radius: 14px;
    font-family: "Segoe UI Semibold";
    font-size: 13px;
    padding: 9px 12px;
}
QLabel#StepChip[state="idle"] {
    background-color: #F7F2E9;
    color: #667085;
}
QLabel#StepChip[state="active"] {
    background-color: #006D5B;
    color: #ffffff;
}
QLabel#StepChip[state="done"] {
    background-color: #E5F6ED;
    color: #168A4A;
}
QLabel#DeliveryStep {
    border-left: 4px solid #E6DED2;
    border-top: 1px solid #EFE7DC;
    border-right: 1px solid #EFE7DC;
    border-bottom: 1px solid #EFE7DC;
    border-radius: 14px;
    font-size: 14px;
    padding: 12px 14px;
}
QLabel#DeliveryStep[state="idle"] {
    background-color: #FFFFFF;
    color: #667085;
}
QLabel#DeliveryStep[state="active"] {
    background-color: #E6F4F1;
    border-left: 4px solid #006D5B;
    color: #006D5B;
    font-family: "Segoe UI Semibold";
}
QLabel#DeliveryStep[state="done"] {
    background-color: #EAF8F0;
    border-left: 4px solid #168A4A;
    color: #168A4A;
}
QFrame#PageSurface {
    background-color: transparent;
    border: none;
    border-radius: 0;
}
QFrame#Card {
    background-color: #ffffff;
    border: 1px solid #E6DED2;
    border-radius: 18px;
}
QFrame#CardSubtle {
    background-color: #FFFFFF;
    border: 1px solid #E6DED2;
    border-radius: 18px;
}
QFrame#HeroCard {
    background-color: #006D5B;
    border: 1px solid #0B7A68;
    border-radius: 24px;
}
QFrame#HeroCard QLabel {
    background: transparent;
}
QFrame#RestaurantCard, QFrame#FoodItemCard {
    background-color: #FFFFFF;
    border: 1px solid #E6DED2;
    border-radius: 18px;
}
QFrame#RestaurantCard[selected="true"], QFrame#FoodItemCard[selected="true"] {
    background-color: #E6F4F1;
    border: 2px solid #006D5B;
}
QFrame#FoodIcon {
    background-color: #FFF1D8;
    border: 1px solid #FFD796;
    border-radius: 16px;
}
QFrame#OrderStatusHero {
    background-color: #102A2A;
    border: 1px solid #204141;
    border-radius: 22px;
}
QFrame#OrderStatusHero QLabel {
    background: transparent;
}
QFrame#StatusPill {
    background-color: #FFFFFF;
    border: 1px solid #E6DED2;
    border-radius: 16px;
}
QFrame#ReceiptCard {
    background-color: #FFFBF5;
    border: 1px solid #E6DED2;
    border-radius: 18px;
}
QFrame#ReceiptLine {
    background-color: #FFFFFF;
    border: 1px solid #EFE7DC;
    border-radius: 12px;
}
QFrame#MetricTile {
    background-color: #FFF4E2;
    border: 1px solid #FFD99D;
    border-radius: 16px;
}
QLabel#HeroTitle {
    color: #FFFFFF;
    font-family: "Segoe UI Semibold";
    font-size: 31px;
}
QLabel#HeroSubtitle {
    color: #D6F2EC;
    font-size: 15px;
}
QLabel#HeroBadge {
    background-color: #FF9F1C;
    border-radius: 16px;
    color: #102A2A;
    font-family: "Segoe UI Semibold";
    padding: 7px 12px;
}
QLabel#CardTitle {
    color: #102A2A;
    font-family: "Segoe UI Semibold";
    font-size: 22px;
}
QLabel#CardHint {
    color: #667085;
    font-size: 14px;
}
QLabel#RestaurantName {
    background: transparent;
    color: #102A2A;
    font-family: "Segoe UI Semibold";
    font-size: 20px;
}
QLabel#RestaurantMeta, QLabel#FoodMeta {
    background: transparent;
    color: #667085;
    font-size: 13px;
}
QLabel#FoodName {
    background: transparent;
    color: #102A2A;
    font-family: "Segoe UI Semibold";
    font-size: 18px;
}
QLabel#PriceText {
    background: transparent;
    color: #006D5B;
    font-family: "Segoe UI Semibold";
    font-size: 18px;
}
QLabel#AddPill {
    background-color: #FF9F1C;
    border-radius: 14px;
    color: #102A2A;
    font-family: "Segoe UI Semibold";
    padding: 6px 11px;
}
QLabel#MetricLabel {
    color: #667085;
    font-family: "Segoe UI Semibold";
    font-size: 12px;
}
QLabel#MetricValue {
    background: transparent;
    color: #006D5B;
    font-family: "Segoe UI Semibold";
    font-size: 30px;
}
QLabel#SummaryRestaurant {
    background: transparent;
    color: #102A2A;
    font-family: "Segoe UI Semibold";
    font-size: 17px;
}
QLabel#SummaryBig {
    background: transparent;
    color: #006D5B;
    font-family: "Segoe UI Semibold";
    font-size: 42px;
}
QLabel#SummaryLabel {
    background: transparent;
    color: #667085;
    font-family: "Segoe UI Semibold";
    font-size: 12px;
}
QLabel#SummaryValue {
    background: transparent;
    color: #102A2A;
    font-family: "Segoe UI Semibold";
    font-size: 15px;
}
QLabel#StatusLabel {
    background: transparent;
    color: #667085;
    font-family: "Segoe UI Semibold";
    font-size: 12px;
}
QLabel#StatusValue {
    background: transparent;
    color: #102A2A;
    font-family: "Segoe UI Semibold";
    font-size: 18px;
}
QLabel#MessageBox {
    background-color: #FFFFFF;
    border: 1px solid #E6DED2;
    border-radius: 14px;
    color: #344054;
    padding: 12px 14px;
}
QLabel#DialogTitle {
    color: #102A2A;
    font-family: "Segoe UI Semibold";
    font-size: 26px;
}
QLabel#DialogStatus {
    background-color: #E6F4F1;
    border: 1px solid #9BCFC6;
    border-radius: 16px;
    color: #006D5B;
    font-family: "Segoe UI Semibold";
    padding: 14px 16px;
}
QListWidget {
    background-color: transparent;
    border: none;
    outline: none;
    padding: 0px;
}
QListWidget::item {
    background-color: transparent;
    border: none;
    margin: 0px 0px 12px 0px;
    padding: 0px;
}
QListWidget::item:hover {
    background-color: transparent;
    border: none;
}
QListWidget::item:selected {
    background-color: transparent;
    border: none;
    color: #102A2A;
}
QPushButton {
    border: none;
    border-radius: 16px;
    font-family: "Segoe UI Semibold";
    font-size: 14px;
    padding: 13px 18px;
}
QPushButton#PrimaryButton {
    background-color: #006D5B;
    color: #ffffff;
}
QPushButton#PrimaryButton:hover {
    background-color: #005B4C;
}
QPushButton#PrimaryButton:pressed {
    background-color: #00473C;
}
QPushButton#SecondaryButton {
    background-color: #F0E8DC;
    color: #102A2A;
}
QPushButton#SecondaryButton:hover {
    background-color: #E6DED2;
}
QPushButton#GhostButton {
    background-color: transparent;
    border: 1px solid #006D5B;
    color: #006D5B;
}
QPushButton#GhostButton:hover {
    background-color: #E6F4F1;
}
QPushButton#DangerButton {
    background-color: #C2410C;
    color: #ffffff;
}
QPushButton#DangerButton:hover {
    background-color: #9A3412;
}
QPushButton:disabled {
    background-color: #D8D0C5;
    color: #FFFFFF;
}
"""


class BackendWorker(QThread):
    state_received = pyqtSignal(str, str)

    def __init__(self):
        super().__init__()
        self.controller = BackendController(gui_callback=self._emit_state)

    def _emit_state(self, state_type, state_name):
        self.state_received.emit(str(state_type), str(state_name))

    def run(self):
        self.controller.start()

    def stop(self):
        self.controller.stop()

    def send_order_trigger(self, trigger):
        return self.controller.send_trigger(trigger, "stm_order")

    def send_payment_trigger(self, trigger):
        return self.controller.send_trigger(trigger, "stm_payment")

    def set_pickup_order_id(self, order_id):
        self.controller.set_pickup_order_id(order_id)


class PaymentTerminalWindow(QMainWindow):
    def __init__(self, approve_callback, decline_callback):
        super().__init__()
        self.approve_callback = approve_callback
        self.decline_callback = decline_callback
        self.setWindowTitle("Payment Terminal")
        self.setGeometry(700, 170, 500, 340)
        self.setup_ui()

    def setup_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        root_layout = QVBoxLayout()
        root_layout.setContentsMargins(22, 22, 22, 22)
        root_layout.setSpacing(0)

        card = QFrame()
        card.setObjectName("ReceiptCard")
        card_layout = QVBoxLayout()
        card_layout.setContentsMargins(24, 22, 24, 22)
        card_layout.setSpacing(14)

        badge = QLabel("Payment terminal")
        badge.setObjectName("HeroBadge")
        badge.setAlignment(Qt.AlignCenter)
        card_layout.addWidget(badge, 0, Qt.AlignLeft)

        title = QLabel("Approve checkout?")
        title.setObjectName("DialogTitle")
        card_layout.addWidget(title)

        subtitle = QLabel(
            "Use this separate terminal window to accept or reject the active payment request."
        )
        subtitle.setObjectName("CardHint")
        subtitle.setWordWrap(True)
        card_layout.addWidget(subtitle)

        self.terminal_status = QLabel("Waiting for checkout")
        self.terminal_status.setObjectName("DialogStatus")
        self.terminal_status.setMinimumHeight(64)
        self.terminal_status.setAlignment(Qt.AlignCenter)
        card_layout.addWidget(self.terminal_status)

        actions = QHBoxLayout()
        actions.setSpacing(12)

        self.accept_btn = QPushButton("Approve")
        self.accept_btn.setObjectName("PrimaryButton")
        self.accept_btn.setEnabled(False)
        self.accept_btn.setMinimumHeight(52)
        self.accept_btn.clicked.connect(self.approve_callback)
        actions.addWidget(self.accept_btn)

        self.decline_btn = QPushButton("Decline")
        self.decline_btn.setObjectName("DangerButton")
        self.decline_btn.setEnabled(False)
        self.decline_btn.setMinimumHeight(52)
        self.decline_btn.clicked.connect(self.decline_callback)
        actions.addWidget(self.decline_btn)

        card_layout.addLayout(actions)
        card.setLayout(card_layout)
        root_layout.addWidget(card)
        central_widget.setLayout(root_layout)

    def set_payment_pending(self):
        self.terminal_status.setText("Pending payment")
        self.accept_btn.setEnabled(True)
        self.decline_btn.setEnabled(True)

    def set_result(self, result_text):
        self.terminal_status.setText(result_text)
        self.accept_btn.setEnabled(False)
        self.decline_btn.setEnabled(False)

    def reset(self):
        self.terminal_status.setText("Waiting for checkout")
        self.accept_btn.setEnabled(False)
        self.decline_btn.setEnabled(False)


class PaymentGUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("DroneBite Delivery")
        self.setGeometry(90, 60, 1240, 820)

        self.backend_worker = BackendWorker()
        self.backend_worker.state_received.connect(self.update_state)
        self.backend_worker.start()
        self.payment_terminal = PaymentTerminalWindow(
            self.on_approve_payment,
            self.on_decline_payment,
        )

        self.selected_restaurant = None
        self.selected_items = []
        self.cart_total = 0
        self.pickup_order_id = DEFAULT_PICKUP_ORDER_ID
        self.payment_requested = False
        self.delivery_stages = [
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
        self.delivery_stage_index_map = {
            stage["key"]: index for index, stage in enumerate(self.delivery_stages)
        }
        self.delivery_stage_index = -1
        self.delivery_tracking_started = False

        self.setup_ui()
        self.show_restaurant_page()

    def add_list_item(self, list_widget, text, height=50, widget=None):
        item = QListWidgetItem(text)
        item.setSizeHint(QSize(0, height))
        list_widget.addItem(item)
        if widget:
            list_widget.setItemWidget(item, widget)
        return item

    def restaurant_description(self, restaurant_name):
        descriptions = {
            "Pizza Palace": "Stone-baked pizza, fast prep, and easy drone pickup.",
            "Burger Queen": "Stacked burgers and comfort food packed for delivery.",
        }
        return descriptions.get(
            restaurant_name,
            "Fresh local food prepared for quick drone pickup.",
        )

    def item_description(self, item_name):
        name = item_name.lower()
        if "pizza" in name or item_name in {"Margherita", "Pepperoni", "Vegetarian"}:
            return "Hot, boxed, and ready for the flight."
        if "burger" in name:
            return "Packed warm with a delivery-friendly wrap."
        if "bbq" in name:
            return "Smoky, filling, and a strong dinner pick."
        return "Freshly prepared for this order."

    def refresh_list_card_selection(self, list_widget):
        current = list_widget.currentItem()
        for index in range(list_widget.count()):
            item = list_widget.item(index)
            widget = list_widget.itemWidget(item)
            if widget:
                widget.setProperty("selected", "true" if item is current else "false")
                widget.style().unpolish(widget)
                widget.style().polish(widget)
                widget.update()

    def create_restaurant_card(self, restaurant_name):
        card = QFrame()
        card.setObjectName("RestaurantCard")
        card.setProperty("selected", "false")
        card.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        layout = QHBoxLayout()
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(16)

        icon = QFrame()
        icon.setObjectName("FoodIcon")
        icon.setFixedSize(64, 64)
        icon_layout = QVBoxLayout()
        icon_layout.setContentsMargins(0, 0, 0, 0)
        icon_label = QLabel(restaurant_name[:1])
        icon_label.setObjectName("MetricValue")
        icon_label.setAlignment(Qt.AlignCenter)
        icon_layout.addWidget(icon_label)
        icon.setLayout(icon_layout)
        layout.addWidget(icon)

        text_layout = QVBoxLayout()
        text_layout.setContentsMargins(0, 0, 0, 0)
        text_layout.setSpacing(5)
        name = QLabel(restaurant_name)
        name.setObjectName("RestaurantName")
        text_layout.addWidget(name)

        description = QLabel(self.restaurant_description(restaurant_name))
        description.setObjectName("RestaurantMeta")
        description.setWordWrap(True)
        text_layout.addWidget(description)

        item_count = len(RESTAURANTS[restaurant_name]["items"])
        meta = QLabel(f"Drone pickup ready • {item_count} menu items")
        meta.setObjectName("RestaurantMeta")
        text_layout.addWidget(meta)
        layout.addLayout(text_layout, 1)

        cta = QLabel("View menu")
        cta.setObjectName("AddPill")
        cta.setAlignment(Qt.AlignCenter)
        layout.addWidget(cta)

        card.setLayout(layout)
        return card

    def create_food_item_card(self, item):
        card = QFrame()
        card.setObjectName("FoodItemCard")
        card.setProperty("selected", "false")
        card.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        layout = QHBoxLayout()
        layout.setContentsMargins(18, 14, 18, 14)
        layout.setSpacing(16)

        icon = QFrame()
        icon.setObjectName("FoodIcon")
        icon.setFixedSize(58, 58)
        icon_layout = QVBoxLayout()
        icon_layout.setContentsMargins(0, 0, 0, 0)
        icon_label = QLabel(item["name"][:1])
        icon_label.setObjectName("MetricValue")
        icon_label.setAlignment(Qt.AlignCenter)
        icon_layout.addWidget(icon_label)
        icon.setLayout(icon_layout)
        layout.addWidget(icon)

        details = QVBoxLayout()
        details.setContentsMargins(0, 0, 0, 0)
        details.setSpacing(5)
        name = QLabel(item["name"])
        name.setObjectName("FoodName")
        details.addWidget(name)

        description = QLabel(self.item_description(item["name"]))
        description.setObjectName("FoodMeta")
        description.setWordWrap(True)
        details.addWidget(description)
        layout.addLayout(details, 1)

        price_layout = QVBoxLayout()
        price_layout.setContentsMargins(0, 0, 0, 0)
        price_layout.setSpacing(7)
        price = QLabel(f"{item['price']} kr")
        price.setObjectName("PriceText")
        price.setAlignment(Qt.AlignRight)
        price_layout.addWidget(price)

        add = QLabel("Add +")
        add.setObjectName("AddPill")
        add.setAlignment(Qt.AlignCenter)
        price_layout.addWidget(add)
        layout.addLayout(price_layout)

        card.setLayout(layout)
        return card

    def create_cart_line(self, name, price):
        line = QFrame()
        line.setObjectName("ReceiptLine")
        line.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        layout = QHBoxLayout()
        layout.setContentsMargins(12, 9, 12, 9)
        layout.setSpacing(8)

        item_name = QLabel(name)
        item_name.setObjectName("SummaryValue")
        layout.addWidget(item_name, 1)

        item_price = QLabel(f"{price} kr")
        item_price.setObjectName("PriceText")
        item_price.setAlignment(Qt.AlignRight)
        layout.addWidget(item_price)

        line.setLayout(layout)
        return line

    def setup_ui(self):
        central_widget = QWidget()
        central_widget.setObjectName("RootWidget")
        self.setCentralWidget(central_widget)

        root_layout = QVBoxLayout()
        root_layout.setContentsMargins(24, 22, 24, 22)
        root_layout.setSpacing(0)

        shell_row = QHBoxLayout()
        shell_row.setContentsMargins(0, 0, 0, 0)
        shell_row.setSpacing(0)
        shell_row.addStretch(1)

        shell = QFrame()
        shell.setObjectName("AppShell")
        shell.setMaximumWidth(1180)
        shell.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        shell_layout = QVBoxLayout()
        shell_layout.setContentsMargins(0, 0, 0, 0)
        shell_layout.setSpacing(0)

        top_bar = QFrame()
        top_bar.setObjectName("TopBar")
        top_layout = QHBoxLayout()
        top_layout.setContentsMargins(24, 16, 24, 16)
        top_layout.setSpacing(12)

        brand = QLabel("DroneBite Express")
        brand.setObjectName("BrandName")
        top_layout.addWidget(brand)
        top_layout.addStretch(1)

        self.top_meta = QLabel("Session ready")
        self.top_meta.setObjectName("TopMeta")
        top_layout.addWidget(self.top_meta)

        self.top_badge = QLabel("Cart: 0 items | 0 kr")
        self.top_badge.setObjectName("TopBadge")
        top_layout.addWidget(self.top_badge)

        top_bar.setLayout(top_layout)
        shell_layout.addWidget(top_bar)

        body = QWidget()
        body_layout = QVBoxLayout()
        body_layout.setContentsMargins(0, 18, 0, 0)
        body_layout.setSpacing(12)

        header_layout = QVBoxLayout()
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(4)
        self.page_title = QLabel()
        self.page_title.setObjectName("PageTitle")
        self.page_subtitle = QLabel()
        self.page_subtitle.setObjectName("PageSubtitle")
        self.page_subtitle.setWordWrap(True)
        header_layout.addWidget(self.page_title)
        header_layout.addWidget(self.page_subtitle)
        self.page_title.hide()
        self.page_subtitle.hide()
        body_layout.addLayout(header_layout)

        step_row = QFrame()
        step_row.setObjectName("StepRow")
        step_layout = QHBoxLayout()
        step_layout.setContentsMargins(12, 10, 12, 10)
        step_layout.setSpacing(10)

        self.step_chips = []
        for text in ("1. Choose restaurant", "2. Build cart", "3. Pay and track"):
            chip = QLabel(text)
            chip.setObjectName("StepChip")
            chip.setProperty("state", "idle")
            chip.setAlignment(Qt.AlignCenter)
            step_layout.addWidget(chip, 1)
            self.step_chips.append(chip)

        step_row.setLayout(step_layout)
        body_layout.addWidget(step_row)

        page_surface = QFrame()
        page_surface.setObjectName("PageSurface")
        page_surface_layout = QVBoxLayout()
        page_surface_layout.setContentsMargins(0, 16, 0, 0)
        page_surface_layout.setSpacing(0)

        self.stacked_widget = QStackedWidget()
        page_surface_layout.addWidget(self.stacked_widget)
        page_surface.setLayout(page_surface_layout)
        body_layout.addWidget(page_surface, 1)

        self.setup_restaurant_page()
        self.setup_food_page()
        self.setup_payment_page()
        self.update_marketplace_stats()

        body.setLayout(body_layout)
        shell_layout.addWidget(body, 1)

        shell.setLayout(shell_layout)
        shell_row.addWidget(shell, 1)
        shell_row.addStretch(1)
        root_layout.addLayout(shell_row, 1)
        central_widget.setLayout(root_layout)

    def setup_restaurant_page(self):
        self.restaurant_page = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(16)

        hero = QFrame()
        hero.setObjectName("HeroCard")
        hero_layout = QHBoxLayout()
        hero_layout.setContentsMargins(28, 24, 28, 24)
        hero_layout.setSpacing(24)

        hero_text = QVBoxLayout()
        hero_text.setContentsMargins(0, 0, 0, 0)
        hero_text.setSpacing(8)
        hero_badge = QLabel("Drone pickup marketplace")
        hero_badge.setObjectName("HeroBadge")
        hero_badge.setAlignment(Qt.AlignCenter)
        hero_text.addWidget(hero_badge, 0, Qt.AlignLeft)

        hero_title = QLabel("Fresh food, cleared for takeoff")
        hero_title.setObjectName("HeroTitle")
        hero_text.addWidget(hero_title)

        hero_subtitle = QLabel(
            "Pick a restaurant, build a small delivery-ready order, and let the drone tracker handle the rest."
        )
        hero_subtitle.setObjectName("HeroSubtitle")
        hero_subtitle.setWordWrap(True)
        hero_text.addWidget(hero_subtitle)
        hero_layout.addLayout(hero_text, 1)

        hero_stats = QHBoxLayout()
        hero_stats.setSpacing(12)

        restaurant_tile = QFrame()
        restaurant_tile.setObjectName("MetricTile")
        restaurant_tile_layout = QVBoxLayout()
        restaurant_tile_layout.setContentsMargins(16, 13, 16, 13)
        restaurant_tile_layout.setSpacing(2)
        restaurant_label = QLabel("RESTAURANTS")
        restaurant_label.setObjectName("MetricLabel")
        restaurant_tile_layout.addWidget(restaurant_label)
        self.market_restaurants_value = QLabel("0")
        self.market_restaurants_value.setObjectName("MetricValue")
        restaurant_tile_layout.addWidget(self.market_restaurants_value)
        restaurant_tile.setLayout(restaurant_tile_layout)
        hero_stats.addWidget(restaurant_tile)

        items_tile = QFrame()
        items_tile.setObjectName("MetricTile")
        items_tile_layout = QVBoxLayout()
        items_tile_layout.setContentsMargins(16, 13, 16, 13)
        items_tile_layout.setSpacing(2)
        items_label = QLabel("MENU ITEMS")
        items_label.setObjectName("MetricLabel")
        items_tile_layout.addWidget(items_label)
        self.market_items_value = QLabel("0")
        self.market_items_value.setObjectName("MetricValue")
        items_tile_layout.addWidget(self.market_items_value)
        items_tile.setLayout(items_tile_layout)
        hero_stats.addWidget(items_tile)
        hero_layout.addLayout(hero_stats)

        hero.setLayout(hero_layout)
        layout.addWidget(hero)

        content_row = QHBoxLayout()
        content_row.setContentsMargins(0, 0, 0, 0)
        content_row.setSpacing(16)

        left_card = QFrame()
        left_card.setObjectName("Card")
        left_layout = QVBoxLayout()
        left_layout.setContentsMargins(20, 18, 20, 18)
        left_layout.setSpacing(12)

        title = QLabel("Choose a restaurant")
        title.setObjectName("CardTitle")
        left_layout.addWidget(title)

        hint = QLabel("Restaurant cards are selectable. Continue when one is highlighted.")
        hint.setObjectName("CardHint")
        hint.setWordWrap(True)
        left_layout.addWidget(hint)

        self.restaurant_list = QListWidget()
        self.restaurant_list.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        for restaurant in RESTAURANTS.keys():
            self.add_list_item(
                self.restaurant_list,
                restaurant,
                118,
                self.create_restaurant_card(restaurant),
            )
        self.restaurant_list.itemSelectionChanged.connect(
            self.update_restaurant_selection_state
        )
        left_layout.addWidget(self.restaurant_list, 1)

        self.select_btn = QPushButton("Continue to menu")
        self.select_btn.setObjectName("PrimaryButton")
        self.select_btn.setEnabled(False)
        self.select_btn.setMinimumHeight(46)
        self.select_btn.clicked.connect(self.on_restaurant_selected)
        left_layout.addWidget(self.select_btn)

        left_card.setLayout(left_layout)
        content_row.addWidget(left_card, 2)

        right_card = QFrame()
        right_card.setObjectName("CardSubtle")
        right_layout = QVBoxLayout()
        right_layout.setContentsMargins(20, 18, 20, 18)
        right_layout.setSpacing(12)

        summary_title = QLabel("Selected pickup")
        summary_title.setObjectName("CardTitle")
        right_layout.addWidget(summary_title)

        self.restaurant_preview = QLabel(
            "Choose a restaurant card to see pickup details and unlock the menu."
        )
        self.restaurant_preview.setWordWrap(True)
        self.restaurant_preview.setObjectName("MessageBox")
        right_layout.addWidget(self.restaurant_preview)

        note = QLabel("Orders are sent to payment only after you add at least one item.")
        note.setWordWrap(True)
        note.setObjectName("CardHint")
        right_layout.addWidget(note)
        right_layout.addStretch()

        right_card.setLayout(right_layout)
        content_row.addWidget(right_card, 1)
        layout.addLayout(content_row, 1)

        self.restaurant_page.setLayout(layout)
        self.stacked_widget.addWidget(self.restaurant_page)

    def setup_food_page(self):
        self.food_page = QWidget()
        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(16)

        left_card = QFrame()
        left_card.setObjectName("Card")
        left_layout = QVBoxLayout()
        left_layout.setContentsMargins(20, 18, 20, 18)
        left_layout.setSpacing(12)

        title = QLabel("Build your flight-ready order")
        title.setObjectName("CardTitle")
        left_layout.addWidget(title)

        self.restaurant_name_label = QLabel("No restaurant selected")
        self.restaurant_name_label.setObjectName("CardHint")
        self.restaurant_name_label.setWordWrap(True)
        left_layout.addWidget(self.restaurant_name_label)

        self.food_list = QListWidget()
        self.food_list.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.food_list.itemSelectionChanged.connect(self.on_food_selected)
        left_layout.addWidget(self.food_list, 1)
        left_card.setLayout(left_layout)
        layout.addWidget(left_card, 3)

        right_card = QFrame()
        right_card.setObjectName("ReceiptCard")
        right_layout = QVBoxLayout()
        right_layout.setContentsMargins(22, 20, 22, 20)
        right_layout.setSpacing(12)

        summary_title = QLabel("Your cart")
        summary_title.setObjectName("CardTitle")
        right_layout.addWidget(summary_title)

        self.summary_restaurant = QLabel("No restaurant selected")
        self.summary_restaurant.setObjectName("SummaryRestaurant")
        right_layout.addWidget(self.summary_restaurant)

        self.total_big = QLabel("0 kr")
        self.total_big.setObjectName("SummaryBig")
        right_layout.addWidget(self.total_big)

        summary_row = QHBoxLayout()
        summary_row.setContentsMargins(0, 0, 0, 0)
        summary_row.setSpacing(8)
        item_count_label = QLabel("ITEMS")
        item_count_label.setObjectName("SummaryLabel")
        summary_row.addWidget(item_count_label)

        self.item_count_value = QLabel("0 items")
        self.item_count_value.setObjectName("SummaryValue")
        self.item_count_value.setAlignment(Qt.AlignRight)
        summary_row.addWidget(self.item_count_value, 1)
        right_layout.addLayout(summary_row)

        selected_label = QLabel("SELECTED ITEMS")
        selected_label.setObjectName("SummaryLabel")
        right_layout.addWidget(selected_label)

        self.selected_items_list = QListWidget()
        self.selected_items_list.setMinimumHeight(220)
        right_layout.addWidget(self.selected_items_list, 1)

        self.checkout_btn = QPushButton("Proceed to checkout")
        self.checkout_btn.setObjectName("PrimaryButton")
        self.checkout_btn.setEnabled(False)
        self.checkout_btn.setMinimumHeight(50)
        self.checkout_btn.clicked.connect(self.on_proceed_checkout)
        right_layout.addWidget(self.checkout_btn)

        back_btn = QPushButton("Back to restaurants")
        back_btn.setObjectName("SecondaryButton")
        back_btn.setMinimumHeight(46)
        back_btn.clicked.connect(self.reset_and_show_restaurant)
        right_layout.addWidget(back_btn)

        right_card.setLayout(right_layout)
        layout.addWidget(right_card, 1)

        self.food_page.setLayout(layout)
        self.stacked_widget.addWidget(self.food_page)

    def setup_payment_page(self):
        self.payment_page = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(16)

        status_hero = QFrame()
        status_hero.setObjectName("OrderStatusHero")
        status_layout = QHBoxLayout()
        status_layout.setContentsMargins(24, 22, 24, 22)
        status_layout.setSpacing(18)

        status_text = QVBoxLayout()
        status_text.setContentsMargins(0, 0, 0, 0)
        status_text.setSpacing(8)
        hero_badge = QLabel("Live order tracking")
        hero_badge.setObjectName("HeroBadge")
        hero_badge.setAlignment(Qt.AlignCenter)
        status_text.addWidget(hero_badge, 0, Qt.AlignLeft)

        status_title = QLabel("Payment and drone dispatch")
        status_title.setObjectName("HeroTitle")
        status_text.addWidget(status_title)

        self.delivery_status_message = QLabel(
            "Waiting for payment approval before drone dispatch."
        )
        self.delivery_status_message.setObjectName("HeroSubtitle")
        self.delivery_status_message.setWordWrap(True)
        status_text.addWidget(self.delivery_status_message)
        status_layout.addLayout(status_text, 1)

        status_cards = QHBoxLayout()
        status_cards.setSpacing(12)

        payment_card = QFrame()
        payment_card.setObjectName("StatusPill")
        payment_card_layout = QVBoxLayout()
        payment_card_layout.setContentsMargins(16, 13, 16, 13)
        payment_card_layout.setSpacing(4)
        payment_label = QLabel("PAYMENT")
        payment_label.setObjectName("StatusLabel")
        payment_card_layout.addWidget(payment_label)

        self.payment_status = QLabel("Waiting")
        self.payment_status.setObjectName("StatusValue")
        payment_card_layout.addWidget(self.payment_status)
        payment_card.setLayout(payment_card_layout)
        status_cards.addWidget(payment_card)

        drone_card = QFrame()
        drone_card.setObjectName("StatusPill")
        drone_card_layout = QVBoxLayout()
        drone_card_layout.setContentsMargins(16, 13, 16, 13)
        drone_card_layout.setSpacing(4)
        drone_label = QLabel("DRONE")
        drone_label.setObjectName("StatusLabel")
        drone_card_layout.addWidget(drone_label)

        self.drone_status = QLabel("Waiting for order")
        self.drone_status.setObjectName("StatusValue")
        drone_card_layout.addWidget(self.drone_status)
        drone_card.setLayout(drone_card_layout)
        status_cards.addWidget(drone_card)
        status_layout.addLayout(status_cards)

        status_hero.setLayout(status_layout)
        layout.addWidget(status_hero)

        content_row = QHBoxLayout()
        content_row.setContentsMargins(0, 0, 0, 0)
        content_row.setSpacing(16)

        timeline_card = QFrame()
        timeline_card.setObjectName("Card")
        timeline_layout = QVBoxLayout()
        timeline_layout.setContentsMargins(22, 20, 22, 20)
        timeline_layout.setSpacing(12)

        delivery_label = QLabel("Delivery timeline")
        delivery_label.setObjectName("CardTitle")
        timeline_layout.addWidget(delivery_label)

        delivery_hint = QLabel("The current drone state updates this stepper automatically.")
        delivery_hint.setObjectName("CardHint")
        delivery_hint.setWordWrap(True)
        timeline_layout.addWidget(delivery_hint)

        self.delivery_step_labels = []
        for stage in self.delivery_stages:
            step_label = QLabel(stage["label"])
            step_label.setObjectName("DeliveryStep")
            step_label.setProperty("state", "idle")
            step_label.setWordWrap(True)
            step_label.setMinimumHeight(54)
            timeline_layout.addWidget(step_label)
            self.delivery_step_labels.append(step_label)
        timeline_layout.addStretch()
        timeline_card.setLayout(timeline_layout)
        content_row.addWidget(timeline_card, 2)

        side_column = QVBoxLayout()
        side_column.setContentsMargins(0, 0, 0, 0)
        side_column.setSpacing(16)

        receipt_card = QFrame()
        receipt_card.setObjectName("ReceiptCard")
        receipt_layout = QVBoxLayout()
        receipt_layout.setContentsMargins(22, 20, 22, 20)
        receipt_layout.setSpacing(12)

        details_label = QLabel("Receipt")
        details_label.setObjectName("CardTitle")
        receipt_layout.addWidget(details_label)

        self.payment_order_details = QLabel("No order submitted.")
        self.payment_order_details.setObjectName("MessageBox")
        self.payment_order_details.setWordWrap(True)
        receipt_layout.addWidget(self.payment_order_details)

        self.payment_message = QLabel("No payment request.")
        self.payment_message.setObjectName("MessageBox")
        self.payment_message.setWordWrap(True)
        receipt_layout.addWidget(self.payment_message)
        receipt_card.setLayout(receipt_layout)
        side_column.addWidget(receipt_card)

        actions_card = QFrame()
        actions_card.setObjectName("CardSubtle")
        actions_layout = QVBoxLayout()
        actions_layout.setContentsMargins(22, 20, 22, 20)
        actions_layout.setSpacing(12)

        actions_title = QLabel("Actions")
        actions_title.setObjectName("CardTitle")
        actions_layout.addWidget(actions_title)

        actions_hint = QLabel(
            "Use the terminal window for the payment decision, or reset to start over."
        )
        actions_hint.setObjectName("CardHint")
        actions_hint.setWordWrap(True)
        actions_layout.addWidget(actions_hint)

        reopen_btn = QPushButton("Open payment terminal")
        reopen_btn.setObjectName("GhostButton")
        reopen_btn.setMinimumHeight(48)
        reopen_btn.clicked.connect(self.show_payment_terminal)
        actions_layout.addWidget(reopen_btn)

        back_btn = QPushButton("Back to restaurants")
        back_btn.setObjectName("SecondaryButton")
        back_btn.setMinimumHeight(46)
        back_btn.clicked.connect(self.reset_and_show_restaurant)
        actions_layout.addWidget(back_btn)

        actions_card.setLayout(actions_layout)
        side_column.addWidget(actions_card)
        side_column.addStretch()
        content_row.addLayout(side_column, 1)
        layout.addLayout(content_row, 1)

        self.payment_page.setLayout(layout)
        self.stacked_widget.addWidget(self.payment_page)

    def update_marketplace_stats(self):
        restaurant_count = len(RESTAURANTS)
        menu_count = sum(len(data["items"]) for data in RESTAURANTS.values())
        self.market_restaurants_value.setText(str(restaurant_count))
        self.market_items_value.setText(str(menu_count))

    def set_page_header(self, title, subtitle):
        self.page_title.setText(title)
        self.page_subtitle.setText(subtitle)

    def set_active_step(self, active_index):
        for index, chip in enumerate(self.step_chips):
            if index < active_index:
                state = "done"
            elif index == active_index:
                state = "active"
            else:
                state = "idle"
            chip.setProperty("state", state)
            chip.style().unpolish(chip)
            chip.style().polish(chip)
            chip.update()

    def set_delivery_stage(self, stage_key, force=False, message_override=None):
        if not hasattr(self, "delivery_step_labels"):
            return
        if stage_key not in self.delivery_stage_index_map:
            return

        target_index = self.delivery_stage_index_map[stage_key]
        if not force and target_index < self.delivery_stage_index:
            return

        self.delivery_stage_index = target_index
        if message_override:
            self.delivery_status_message.setText(message_override)
        else:
            self.delivery_status_message.setText(
                self.delivery_stages[target_index]["message"]
            )

        for index, step_label in enumerate(self.delivery_step_labels):
            if index < target_index:
                state = "done"
            elif index == target_index:
                state = "active"
            else:
                state = "idle"
            step_label.setProperty("state", state)
            step_label.style().unpolish(step_label)
            step_label.style().polish(step_label)
            step_label.update()

    def reset_delivery_tracking(self, message=None):
        if not hasattr(self, "delivery_step_labels"):
            return
        self.delivery_tracking_started = False
        self.delivery_stage_index = -1

        fallback_message = "Waiting for payment approval before drone dispatch."
        self.delivery_status_message.setText(message or fallback_message)

        for step_label in self.delivery_step_labels:
            step_label.setProperty("state", "idle")
            step_label.style().unpolish(step_label)
            step_label.style().polish(step_label)
            step_label.update()

    def start_delivery_tracking(self):
        if not hasattr(self, "delivery_step_labels"):
            return
        if self.delivery_tracking_started:
            return

        self.delivery_tracking_started = True
        self.delivery_status_message.setText(
            "Payment approved. Waiting for drone state updates from MQTT."
        )

    def update_delivery_from_drone_state(self, drone_state_text):
        if not hasattr(self, "delivery_step_labels"):
            return
        state_text = (drone_state_text or "").strip().lower()
        base_state = state_text.split(" (")[0]
        reason = ""
        if "(" in state_text and ")" in state_text:
            reason = state_text[state_text.find("(") + 1 : state_text.rfind(")")].strip()

        if base_state in {
            "waiting_for_drone",
            "dispatch_requested",
            "dispatched_to_pickup",
            "in_flight_to_pickup",
            "to_restaurant",
        }:
            self.set_delivery_stage("to_restaurant")
        elif base_state == "at_pickup":
            self.set_delivery_stage("at_restaurant")
        elif base_state == "pickup_delayed":
            message = "Restaurant is not ready. Drone is waiting at pickup."
            if reason:
                message = f"Restaurant is not ready ({reason}). Drone is waiting at pickup."
            self.set_delivery_stage("at_restaurant", force=True, message_override=message)
        elif base_state == "package_loaded":
            self.set_delivery_stage("food_loaded")
        elif base_state == "in_flight":
            self.set_delivery_stage("to_customer")

    def sync_top_badge(self):
        item_count = len(self.selected_items)
        self.top_badge.setText(f"Cart: {item_count} items | {self.cart_total} kr")

    def get_payment_phase(self):
        payment_state = self.payment_status.text().lower()

        if any(token in payment_state for token in ("approved", "accepted", "success")):
            return "approved"
        if any(
            token in payment_state
            for token in ("cancelled", "canceled", "expired", "timeout")
        ):
            return "cancelled"
        if any(token in payment_state for token in ("declined", "denied", "rejected", "failed")):
            return "declined"
        if any(token in payment_state for token in ("pending", "waiting", "started")):
            return "pending"
        return "unknown"

    def refresh_payment_feedback(self):
        if not self.payment_requested:
            self.payment_message.setText("No payment request.")
            return

        phase = self.get_payment_phase()
        if phase == "approved":
            self.set_page_header(
                "Payment approved",
                "Order is confirmed and waiting for drone delivery updates.",
            )
            self.top_meta.setText("Payment approved")
            self.payment_message.setText("Payment approved. Drone delivery should continue.")
        elif phase == "declined":
            self.set_page_header(
                "Payment declined",
                "Go back to restaurants to start a new order.",
            )
            self.top_meta.setText("Payment declined")
            self.payment_message.setText("Payment declined. Start a new order to retry.")
        elif phase == "cancelled":
            self.set_page_header(
                "Payment expired",
                "Start a new order to create a new payment request.",
            )
            self.top_meta.setText("Payment expired")
            self.payment_message.setText(
                "Payment request is no longer active. Start a new order to retry."
            )
        else:
            self.set_page_header(
                "Awaiting payment",
                "Approve or decline the request in the payment terminal.",
            )
            self.top_meta.setText("Awaiting payment")
            self.payment_message.setText("Payment request is still pending.")

    def show_restaurant_page(self):
        self.set_page_header(
            "Order drone-delivered food",
            "Choose a restaurant, build your cart, then approve the payment in the terminal.",
        )
        self.top_meta.setText("Session ready")
        self.set_active_step(0)
        self.update_restaurant_selection_state()
        self.sync_top_badge()
        self.stacked_widget.setCurrentIndex(0)

    def update_restaurant_selection_state(self):
        selected = self.restaurant_list.currentItem()
        self.select_btn.setEnabled(selected is not None)
        self.refresh_list_card_selection(self.restaurant_list)
        if hasattr(self, "restaurant_preview"):
            if selected:
                restaurant_name = selected.text()
                item_count = len(RESTAURANTS[restaurant_name]["items"])
                self.restaurant_preview.setText(
                    f"{restaurant_name}\n{self.restaurant_description(restaurant_name)}\n"
                    f"{item_count} menu items available for drone pickup."
                )
            else:
                self.restaurant_preview.setText(
                    "Choose a restaurant card to see pickup details and unlock the menu."
                )

    def on_restaurant_selected(self):
        selected = self.restaurant_list.currentItem()
        if not selected:
            return

        self.selected_restaurant = selected.text()
        self.restaurant_name_label.setText(self.selected_restaurant)
        self.summary_restaurant.setText(self.selected_restaurant)
        self.set_page_header(
            "Build your order",
            "Select menu items to add them to the cart. Each item can be added once.",
        )
        self.top_meta.setText(f"Ordering from {self.selected_restaurant}")
        self.set_active_step(1)
        self.load_food_items()
        self.stacked_widget.setCurrentIndex(1)

    def load_food_items(self):
        self.food_list.clear()
        self.selected_items = []
        self.cart_total = 0

        items = RESTAURANTS[self.selected_restaurant]["items"]
        for item in items:
            self.add_list_item(
                self.food_list,
                f"{item['name']} - {item['price']} kr",
                106,
                self.create_food_item_card(item),
            )

        self.update_cart_label()

    def on_food_selected(self):
        selected = self.food_list.currentItem()
        if not selected:
            return

        item_text = selected.text()
        item_name = item_text.split(" - ")[0]
        restaurant_items = RESTAURANTS[self.selected_restaurant]["items"]
        selected_names = [name for name, _ in self.selected_items]

        for item in restaurant_items:
            if item["name"] == item_name and item_name not in selected_names:
                self.selected_items.append((item_name, item["price"]))
                self.cart_total += item["price"]
                self.update_cart_label()
                self.food_list.clearSelection()
                break

    def update_cart_label(self):
        item_count = len(self.selected_items)
        item_word = "item" if item_count == 1 else "items"
        self.total_big.setText(f"{self.cart_total} kr")
        self.item_count_value.setText(f"{item_count} {item_word}")
        self.checkout_btn.setEnabled(item_count > 0)

        self.selected_items_list.clear()
        if not self.selected_items:
            self.add_list_item(self.selected_items_list, "No items selected.", 44)
        else:
            for name, price in self.selected_items:
                self.add_list_item(
                    self.selected_items_list,
                    f"{name} - {price} kr",
                    54,
                    self.create_cart_line(name, price),
                )

        self.sync_top_badge()

    def build_order_details_text(self):
        if not self.selected_restaurant:
            return "No order submitted."

        item_count = len(self.selected_items)
        item_word = "item" if item_count == 1 else "items"
        return (
            f"Restaurant: {self.selected_restaurant}\n"
            f"Items: {item_count} {item_word}\n"
            f"Total: {self.cart_total} kr"
        )

    def on_proceed_checkout(self):
        if not self.selected_items:
            return

        self.backend_worker.send_order_trigger("proceedToCart")
        self.backend_worker.send_order_trigger("confirmOrder")
        self.backend_worker.set_pickup_order_id(self.pickup_order_id)

        self.backend_worker.send_payment_trigger("checkoutStarted")
        self.payment_requested = True
        self.payment_status.setText("Pending payment")
        self.reset_delivery_tracking(
            "Waiting for payment approval before drone dispatch."
        )
        self.payment_order_details.setText(self.build_order_details_text())
        self.refresh_payment_feedback()
        self.set_active_step(2)
        self.payment_terminal.set_payment_pending()
        self.show_payment_terminal()
        self.stacked_widget.setCurrentIndex(2)

    def on_approve_payment(self):
        if self.get_payment_phase() != "pending":
            self.payment_terminal.set_result("Payment request expired")
            self.payment_status.setText("Payment cancelled")
            self.reset_delivery_tracking("Payment request expired. Drone dispatch cancelled.")
            self.refresh_payment_feedback()
            return

        sent = self.backend_worker.send_payment_trigger("paymentApproved")
        if not sent:
            self.payment_terminal.set_result("Payment request expired")
            self.payment_status.setText("Payment cancelled")
            self.reset_delivery_tracking("Payment request expired. Drone dispatch cancelled.")
            self.refresh_payment_feedback()
            return

        self.payment_terminal.set_result("Approval sent")
        self.payment_message.setText("Approval sent. Waiting for backend confirmation.")
        self.payment_terminal.close()

    def on_decline_payment(self):
        sent = self.backend_worker.send_payment_trigger("paymentDeclined")
        if not sent:
            self.payment_terminal.set_result("Payment request expired")
            self.payment_status.setText("Payment cancelled")
            self.reset_delivery_tracking("Payment request expired. Drone dispatch cancelled.")
            self.refresh_payment_feedback()
            return

        self.payment_terminal.set_result("Payment declined")
        self.payment_status.setText("Payment declined")
        self.reset_delivery_tracking("Payment declined. Drone dispatch cancelled.")
        self.refresh_payment_feedback()
        self.payment_terminal.close()

    def show_payment_terminal(self):
        self.payment_terminal.show()
        self.payment_terminal.raise_()
        self.payment_terminal.activateWindow()

    def reset_and_show_restaurant(self):
        self.backend_worker.send_order_trigger("resetOrder")
        self.backend_worker.send_payment_trigger("resetPayment")

        self.selected_restaurant = None
        self.selected_items = []
        self.cart_total = 0
        self.payment_requested = False

        self.restaurant_list.clearSelection()
        self.food_list.clear()
        self.selected_items_list.clear()
        self.add_list_item(self.selected_items_list, "No items selected.", 44)
        self.restaurant_name_label.setText("No restaurant selected")
        self.summary_restaurant.setText("No restaurant selected")
        self.total_big.setText("0 kr")
        self.item_count_value.setText("0 items")
        self.checkout_btn.setEnabled(False)

        self.payment_status.setText("Waiting")
        self.drone_status.setText("Waiting for order")
        self.payment_order_details.setText("No order submitted.")
        self.payment_message.setText("No payment request.")
        self.reset_delivery_tracking("Waiting for payment approval before drone dispatch.")

        self.top_meta.setText("Session ready")
        self.sync_top_badge()

        self.payment_terminal.reset()
        self.payment_terminal.close()
        self.show_restaurant_page()

    def update_state(self, state_type, state_name):
        readable_state = (state_name or "").replace("_", " ")

        if state_type == "payment_state":
            self.payment_status.setText(readable_state)
            self.refresh_payment_feedback()
            payment_phase = self.get_payment_phase()
            if payment_phase == "approved":
                self.start_delivery_tracking()
            elif payment_phase == "declined":
                self.reset_delivery_tracking("Payment declined. Drone dispatch cancelled.")
                self.payment_terminal.set_result(readable_state)
            elif payment_phase == "cancelled":
                self.reset_delivery_tracking("Payment request expired. Drone dispatch cancelled.")
                self.payment_terminal.set_result(readable_state)
            elif payment_phase == "pending" and not self.delivery_tracking_started:
                self.reset_delivery_tracking(
                    "Waiting for payment approval before drone dispatch."
                )
        elif state_type == "drone_state":
            raw_drone_state = (state_name or "").strip()
            self.drone_status.setText(raw_drone_state.replace("_", " "))
            self.update_delivery_from_drone_state(raw_drone_state)

    def closeEvent(self, event):
        self.payment_terminal.close()
        self.backend_worker.stop()
        self.backend_worker.wait()
        event.accept()


def main():
    app = QApplication(sys.argv)
    app.setStyleSheet(APP_STYLESHEET)
    gui = PaymentGUI()
    gui.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
