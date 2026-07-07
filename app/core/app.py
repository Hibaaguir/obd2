import logging
import traceback
from pathlib import Path

from kivy.clock import Clock
from kivy.core.window import Window
from kivy.metrics import dp
from kivy.utils import platform
from kivy.uix.screenmanager import ScreenManager
from kivymd.app import MDApp
from kivymd.uix.boxlayout import MDBoxLayout

from app.core.config import ACCENT_PALETTE, APP_TITLE, PRIMARY_PALETTE
from app.core.mobile import PHONE_CONTENT_MAX_WIDTH, PHONE_MIN_SIZE, PHONE_PREVIEW_SIZE
from app.core.theme import APP_BG, BORDER, PANEL_DARK
from app.database.database import Database
from app.screens.dashboard_screen import DashboardScreen
from app.screens.diagnostic_screen import DiagnosticScreen
from app.screens.history_screen import HistoryScreen
from app.screens.home_screen import HomeScreen
from app.services.diagnostic_service import DiagnosticService
from app.services.obd_service import OBDService
from app.services.vehicle_state_service import VehicleStateService
from app.widgets.ui_components import NavItem


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)


class OBD2App(MDApp):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.obd_service = OBDService()
        self.diagnostic_service = DiagnosticService()
        self.database = Database()
        self.vehicle_state_service = VehicleStateService(
            self.obd_service,
            self.diagnostic_service,
            self.database,
        )
        self.screen_manager = ScreenManager()
        self.nav_items = {}

    def build(self):
        self.title = APP_TITLE
        self._apply_phone_window()
        self.theme_cls.primary_palette = PRIMARY_PALETTE
        self.theme_cls.accent_palette = ACCENT_PALETTE
        self.theme_cls.theme_style = "Dark"

        self.database.initialize()

        root = MDBoxLayout(orientation="horizontal", md_bg_color=APP_BG)
        root.add_widget(MDBoxLayout(md_bg_color=APP_BG))

        self.phone_frame = MDBoxLayout(
            orientation="vertical",
            size_hint_x=None,
            width=dp(PHONE_CONTENT_MAX_WIDTH),
            md_bg_color=APP_BG,
        )

        self.screen_manager.add_widget(HomeScreen(name="home"))
        self.screen_manager.add_widget(DashboardScreen(name="dashboard"))
        self.screen_manager.add_widget(DiagnosticScreen(name="diagnostic"))
        self.screen_manager.add_widget(HistoryScreen(name="history"))
        self.phone_frame.add_widget(self.screen_manager)

        self.phone_frame.add_widget(self._build_navigation())
        root.add_widget(self.phone_frame)
        root.add_widget(MDBoxLayout(md_bg_color=APP_BG))
        root.bind(width=self._sync_phone_frame_width)
        Clock.schedule_once(lambda *_: self.screen_manager.get_screen("home").refresh(), 0)
        Clock.schedule_once(lambda *_: self._sync_navigation("home"), 0)
        return root

    @property
    def crash_log_path(self) -> Path:
        return Path(__file__).resolve().parents[2] / "data" / "crash.log"

    def _build_navigation(self):
        dock = MDBoxLayout(
            orientation="vertical",
            size_hint_y=None,
            height=dp(64),
            md_bg_color=PANEL_DARK,
        )
        dock.add_widget(
            MDBoxLayout(
                size_hint_y=None,
                height=dp(1),
                md_bg_color=BORDER,
            )
        )

        navigation = MDBoxLayout(
            size_hint_y=None,
            height=dp(63),
            padding=(dp(6), dp(8), dp(6), dp(8)),
            spacing=dp(4),
            md_bg_color=PANEL_DARK,
        )
        items = (
            ("home", "Connexion", "wifi"),
            ("dashboard", "Dashboard", "gauge"),
            ("diagnostic", "Diagnostic", "clipboard-pulse-outline"),
            ("history", "Historique", "history"),
        )
        for screen_name, label, icon in items:
            item = NavItem(screen_name, label, icon, self.change_screen)
            self.nav_items[screen_name] = item
            navigation.add_widget(item)
        dock.add_widget(navigation)
        return dock

    def change_screen(self, screen_name, title):
        previous_screen = self.screen_manager.current
        try:
            self.screen_manager.current = screen_name
            self._sync_navigation(screen_name)
            screen = self.screen_manager.get_screen(screen_name)
            if hasattr(screen, "refresh"):
                screen.refresh()
        except Exception as exc:
            self._log_screen_error(screen_name, exc)
            logging.exception("Erreur pendant l'ouverture de l'ecran %s", screen_name)
            self.screen_manager.current = previous_screen
            self._sync_navigation(previous_screen)
            home_screen = self.screen_manager.get_screen("home")
            if hasattr(home_screen, "status_card"):
                home_screen.status_card.set_value(
                    "Erreur navigation",
                    f"Ouverture {title}: {exc}",
                )

    def _log_screen_error(self, screen_name, exc):
        log_path = self.crash_log_path
        log_path.parent.mkdir(parents=True, exist_ok=True)
        with log_path.open("a", encoding="utf-8") as handle:
            handle.write(f"\n=== Screen open failure: {screen_name} ===\n")
            traceback.print_exc(file=handle)

    def _sync_navigation(self, screen_name):
        for name, item in self.nav_items.items():
            item.set_active(name == screen_name)

    def _sync_phone_frame_width(self, _, width):
        self.phone_frame.width = min(width, dp(PHONE_CONTENT_MAX_WIDTH))

    def _apply_phone_window(self):
        if platform in {"android", "ios"}:
            return
        Window.minimum_width = PHONE_MIN_SIZE[0]
        Window.minimum_height = PHONE_MIN_SIZE[1]
        Window.size = PHONE_PREVIEW_SIZE

    def on_stop(self):
        self.obd_service.disconnect()
        self.database.close()
