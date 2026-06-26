from threading import Thread

from kivy.clock import Clock
from kivy.metrics import dp
from kivymd.uix.button import MDRaisedButton
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.label import MDLabel
from kivymd.uix.textfield import MDTextField

from app.core.obd_config import OBD_HOST, OBD_PORT
from app.core.theme import BLUE, GREEN, MUTED, PANEL_DARK, RED, TEXT, with_alpha
from app.screens.base_screen import BaseScreen
from app.widgets.status_card import StatusCard
from app.widgets.ui_components import GlowCard, HeaderBlock


class HomeScreen(BaseScreen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        layout = self.build_page()

        layout.add_widget(
            HeaderBlock(
                "OBD2 Diagnostic",
                "Adaptateur ELM327 - TCP/IP",
                icon="shield-check-outline",
            )
        )

        self.status_card = StatusCard("Etat adaptateur", "Non connecte", "Aucune donnee lue")
        layout.add_widget(self.status_card)

        config_card = GlowCard()
        config_card.size_hint_y = None
        config_card.height = dp(206)
        config_card.add_widget(
            MDLabel(
                text="CONFIGURATION ADAPTATEUR",
                theme_text_color="Custom",
                text_color=MUTED,
                font_style="Caption",
                bold=True,
                size_hint_y=None,
                height=dp(22),
            )
        )

        self.host_input = self._build_text_field(
            text=OBD_HOST,
            hint_text="ADRESSE IP",
        )
        self.port_input = self._build_text_field(
            text=str(OBD_PORT),
            hint_text="PORT TCP",
        )
        config_card.add_widget(self.host_input)
        config_card.add_widget(self.port_input)

        self.cable_label = MDLabel(
            text=f"Cable    {OBD_HOST}:{OBD_PORT}",
            theme_text_color="Custom",
            text_color=BLUE,
            font_style="Caption",
            size_hint_y=None,
            height=dp(36),
            padding=(dp(12), 0),
        )
        cable_box = MDBoxLayout(
            size_hint_y=None,
            height=dp(38),
            padding=(dp(8), 0, dp(8), 0),
            md_bg_color=PANEL_DARK,
        )
        cable_box.add_widget(self.cable_label)
        config_card.add_widget(cable_box)
        layout.add_widget(config_card)

        self.connect_button = MDRaisedButton(
            text="  Connecter OBD2",
            icon="connection",
            md_bg_color=with_alpha(BLUE, 0.85),
            text_color=TEXT,
            size_hint=(1, None),
            height=dp(50),
            on_release=self.connect,
        )
        self.disconnect_button = MDRaisedButton(
            text="  Deconnecter",
            icon="connection",
            md_bg_color=with_alpha(RED, 0.14),
            text_color=RED,
            size_hint=(1, None),
            height=dp(50),
            on_release=self.disconnect,
        )
        layout.add_widget(self.connect_button)
        layout.add_widget(self.disconnect_button)

        helper = GlowCard()
        helper.size_hint_y = None
        helper.height = dp(76)
        helper.md_bg_color = with_alpha(PANEL_DARK, 0.76)
        helper.add_widget(
            MDLabel(
                text=(
                    "Compatible ELM327 v1.5+. Connectez l'adaptateur OBD2 au port "
                    "diagnostic du vehicule avant de lancer la connexion TCP/IP."
                ),
                theme_text_color="Custom",
                text_color=MUTED,
                font_style="Caption",
                adaptive_height=True,
            )
        )
        layout.add_widget(helper)
        layout.add_widget(MDLabel(size_hint_y=None, height=dp(20)))

        self.host_input.bind(text=lambda *_: self._sync_cable_label())
        self.port_input.bind(text=lambda *_: self._sync_cable_label())

    def _build_text_field(self, text: str, hint_text: str):
        field = MDTextField(
            text=text,
            hint_text=hint_text,
            mode="fill",
            fill_color_normal=PANEL_DARK,
            fill_color_focus=PANEL_DARK,
            text_color_normal=TEXT,
            text_color_focus=TEXT,
            hint_text_color_normal=MUTED,
            hint_text_color_focus=BLUE,
            line_color_focus=BLUE,
            size_hint_y=None,
            height=dp(64),
        )
        return field

    def _sync_cable_label(self):
        host = self.host_input.text or OBD_HOST
        port = self.port_input.text or OBD_PORT
        self.cable_label.text = f"Cable    {host}:{port}"

    def connect(self, *_):
        self.connect_button.disabled = True
        self.connect_button.text = "  Connexion..."
        self.status_card.set_value("Connexion...", "Initialisation ELM327 en cours")
        host = self.host_input.text
        port = self.port_input.text
        Thread(target=self._connect_worker, args=(host, port), daemon=True).start()

    def _connect_worker(self, host, port):
        connected = self.app.obd_service.connect(host, port)
        Clock.schedule_once(lambda *_: self._finish_connect(connected), 0)

    def _finish_connect(self, connected):
        self.connect_button.disabled = False
        self.connect_button.text = "  Connecter OBD2"
        if connected:
            service = self.app.obd_service
            self.status_card.set_value(
                "Connecte",
                f"{service.current_host}:{service.current_port}",
            )
            self.connect_button.md_bg_color = with_alpha(GREEN, 0.75)
        else:
            self.status_card.set_value("Non connecte", self.app.obd_service.last_error)
            self.connect_button.md_bg_color = with_alpha(BLUE, 0.85)

    def disconnect(self, *_):
        self.app.obd_service.disconnect()
        self.refresh()

    def refresh(self):
        service = self.app.obd_service
        helper = f"{service.current_host}:{service.current_port}" if service.is_connected() else service.last_error or "Aucun adaptateur actif"
        self.status_card.set_value(service.status_label, helper)
        self.connect_button.md_bg_color = with_alpha(GREEN if service.is_connected() else BLUE, 0.85)
