from threading import Thread

from kivy.clock import Clock
from kivy.graphics import Color, Line, RoundedRectangle
from kivy.metrics import dp, sp
from kivy.properties import BooleanProperty, ListProperty
from kivy.uix.anchorlayout import AnchorLayout
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.label import MDIcon, MDLabel
from kivymd.uix.textfield import MDTextField

from app.core.obd_config import OBD_HOST, OBD_PORT
from app.core.theme import BLUE, PANEL_ALT, PANEL_DARK, TEXT, with_alpha
from app.screens.base_screen import BaseScreen
from app.widgets.status_card import StatusCard
from app.widgets.ui_components import GlowCard


CARD_RADIUS = [dp(18)]
SECTION_SPACING = dp(18)
PAGE_ICON = (77 / 255, 140 / 255, 1, 1)
TITLE_WHITE = (1, 1, 1, 1)
SUBTITLE = (154 / 255, 168 / 255, 199 / 255, 1)
SECTION_TITLE = (175 / 255, 192 / 255, 232 / 255, 1)


class ConnectionActionButton(MDBoxLayout):
    disabled = BooleanProperty(False)
    button_color = ListProperty(with_alpha(BLUE, 0.85))
    border_color = ListProperty((0, 0, 0, 0))

    def __init__(self, text: str, on_release=None, **kwargs):
        self._on_release_callback = on_release
        super().__init__(**kwargs)
        self.orientation = "vertical"
        self.size_hint = (1, None)
        self.height = dp(52)
        self.padding = 0
        self.corner_radius = dp(14)
        self.md_bg_color = (0, 0, 0, 0)
        self.bind(pos=self._redraw, size=self._redraw, button_color=self._redraw, border_color=self._redraw)

        self.label = MDLabel(
            text=text,
            theme_text_color="Custom",
            text_color=TEXT,
            bold=True,
            font_style="Button",
            font_size=sp(15),
            halign="center",
            valign="middle",
        )
        self.label.bind(size=self._sync_text_size)
        self.add_widget(self.label)

    def set_text(self, text: str):
        self.label.text = text

    def _redraw(self, *_):
        self.canvas.before.clear()
        with self.canvas.before:
            Color(*self.button_color)
            radius = [(self.corner_radius, self.corner_radius)] * 4
            RoundedRectangle(
                pos=self.pos,
                size=self.size,
                radius=radius,
            )
            if self.border_color[3] > 0:
                Color(*self.border_color)
                Line(
                    rounded_rectangle=(
                        self.x + dp(1),
                        self.y + dp(1),
                        max(0, self.width - dp(2)),
                        max(0, self.height - dp(2)),
                        self.corner_radius,
                    ),
                    width=1.2,
                )

    def on_release(self):
        if not self.disabled and self._on_release_callback:
            self._on_release_callback(self)

    def on_touch_down(self, touch):
        if self.disabled:
            return False
        if self.collide_point(*touch.pos):
            touch.grab(self)
            return True
        return super().on_touch_down(touch)

    def on_touch_up(self, touch):
        if touch.grab_current is self:
            touch.ungrab(self)
            if not self.disabled and self.collide_point(*touch.pos):
                self.on_release()
            return True
        return super().on_touch_up(touch)

    @staticmethod
    def _sync_text_size(label, size):
        label.text_size = size


class HomeScreen(BaseScreen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        layout = self.build_page()
        layout.spacing = SECTION_SPACING

        layout.add_widget(self._build_header())

        self.status_card = StatusCard("Etat adaptateur", "Non connecte", "Aucune donnee lue")
        layout.add_widget(self.status_card)

        config_card = GlowCard()
        config_card.size_hint_y = None
        config_card.height = dp(188)
        config_card.radius = CARD_RADIUS
        config_card.padding = (dp(18), dp(18), dp(18), dp(18))
        config_card.spacing = dp(14)
        config_card.add_widget(
            MDLabel(
                text="CONFIGURATION ADAPTATEUR",
                theme_text_color="Custom",
                text_color=SECTION_TITLE,
                font_style="Caption",
                bold=True,
                size_hint_y=None,
                height=dp(20),
            )
        )

        self.host_input = self._build_text_field(
            text=OBD_HOST,
            hint_text="Adresse IP",
        )
        self.port_input = self._build_text_field(
            text=str(OBD_PORT),
            hint_text="Port TCP",
        )
        config_card.add_widget(self.host_input)
        config_card.add_widget(self.port_input)
        layout.add_widget(config_card)

        self.action_button = ConnectionActionButton(
            text="CONNECTER OBD2",
            on_release=self._handle_action,
        )
        layout.add_widget(self.action_button)

        helper = GlowCard()
        helper.size_hint_y = None
        helper.height = dp(92)
        helper.radius = CARD_RADIUS
        helper.padding = (dp(18), dp(18), dp(18), dp(18))
        helper.spacing = dp(10)
        helper.md_bg_color = with_alpha(PANEL_DARK, 0.76)
        info_row = MDBoxLayout(
            adaptive_height=True,
            spacing=dp(16),
            padding=(0, 0, 0, 0),
            pos_hint={"center_y": 0.5},
        )
        info_icon_wrap = MDBoxLayout(
            orientation="vertical",
            size_hint=(None, None),
            size=(dp(24), dp(24)),
            pos_hint={"center_y": 0.5},
        )
        info_icon_wrap.add_widget(
            MDIcon(
                icon="information-outline",
                theme_text_color="Custom",
                text_color=PAGE_ICON,
                size_hint=(None, None),
                size=(dp(24), dp(24)),
                font_size=dp(24),
                pos_hint={"center_x": 0.5, "center_y": 0.5},
            )
        )
        info_row.add_widget(info_icon_wrap)
        info_copy = MDBoxLayout(
            orientation="vertical",
            adaptive_height=True,
            spacing=dp(2),
            pos_hint={"center_y": 0.5},
        )
        info_copy.add_widget(
            MDLabel(
                text="Compatible avec les adaptateurs ELM327 TCP/IP.",
                theme_text_color="Custom",
                text_color=TEXT,
                font_style="Subtitle2",
                bold=True,
                adaptive_height=True,
            )
        )
        info_copy.add_widget(
            MDLabel(
                text="Connectez un adaptateur avant de demarrer la connexion.",
                theme_text_color="Custom",
                text_color=SUBTITLE,
                font_style="Caption",
                adaptive_height=True,
            )
        )
        info_row.add_widget(info_copy)
        helper.add_widget(info_row)
        layout.add_widget(helper)
        layout.add_widget(MDLabel(size_hint_y=None, height=dp(12)))
        self._sync_action_button()

    def _build_header(self):
        header = MDBoxLayout(
            orientation="horizontal",
            size_hint_y=None,
            height=dp(52),
            spacing=dp(14),
            padding=(0, dp(2), 0, dp(6)),
        )

        icon_wrap = AnchorLayout(
            anchor_x="center",
            anchor_y="center",
            size_hint=(None, 1),
            width=dp(26),
        )
        icon_wrap.add_widget(
            MDIcon(
                icon="shield-check",
                theme_text_color="Custom",
                text_color=PAGE_ICON,
                size_hint=(None, None),
                size=(dp(26), dp(26)),
                font_size=dp(26),
                halign="center",
                valign="middle",
            )
        )
        header.add_widget(icon_wrap)

        copy = MDBoxLayout(
            orientation="vertical",
            adaptive_height=True,
            spacing=0,
            pos_hint={"center_y": 0.5},
        )
        copy.add_widget(
            MDLabel(
                text="Connexion OBD2",
                theme_text_color="Custom",
                text_color=TITLE_WHITE,
                bold=True,
                size_hint_y=None,
                height=dp(28),
                font_size=sp(22),
            )
        )
        copy.add_widget(
            MDLabel(
                text="Adaptateur ELM327 - TCP/IP",
                theme_text_color="Custom",
                text_color=SUBTITLE,
                size_hint_y=None,
                height=dp(18),
                font_size=sp(14),
            )
        )
        header.add_widget(copy)
        return header

    def _build_text_field(self, text: str, hint_text: str):
        field = MDTextField(
            text=text,
            hint_text=hint_text,
            mode="fill",
            fill_color_normal=PANEL_ALT,
            fill_color_focus=PANEL_ALT,
            text_color_normal=TEXT,
            text_color_focus=TEXT,
            hint_text_color_normal=SUBTITLE,
            hint_text_color_focus=SUBTITLE,
            line_color_focus=BLUE,
            size_hint_y=None,
            height=dp(58),
            font_size=sp(16),
        )
        return field

    def connect(self, *_):
        self.action_button.disabled = True
        self.action_button.set_text("CONNEXION...")
        self.status_card.set_value(
            "Connexion...",
            "Tentative de connexion a l'adaptateur ELM327 en cours",
        )
        host = self.host_input.text
        port = self.port_input.text
        Thread(target=self._connect_worker, args=(host, port), daemon=True).start()

    def _connect_worker(self, host, port):
        connected = self.app.obd_service.connect(host, port)
        Clock.schedule_once(lambda *_: self._finish_connect(connected), 0)

    def _finish_connect(self, connected):
        self.action_button.disabled = False
        if connected:
            service = self.app.obd_service
            self.status_card.set_value(
                "Connecte",
                f"{service.current_host}:{service.current_port}",
            )
        else:
            self.status_card.set_value("Non connecte", self.app.obd_service.last_error)
        self._sync_action_button()

    def disconnect(self, *_):
        self.app.obd_service.disconnect()
        self.refresh()

    def refresh(self):
        service = self.app.obd_service
        helper = (
            f"{service.current_host}:{service.current_port}"
            if service.is_connected()
            else service.last_error or "Aucun adaptateur actif"
        )
        self.status_card.set_value(service.status_label, helper)
        self._sync_action_button()

    def _handle_action(self, *_):
        if self.app.obd_service.is_connected():
            self.disconnect()
            return
        self.connect()

    def _sync_action_button(self):
        service = self.app.obd_service
        if service.is_connected():
            self.action_button.set_text("DECONNECTER")
            self.action_button.button_color = with_alpha(BLUE, 0.18)
            self.action_button.border_color = with_alpha(BLUE, 0.75)
            self.action_button.label.text_color = TEXT
        else:
            self.action_button.set_text("CONNECTER OBD2")
            self.action_button.button_color = with_alpha(BLUE, 0.85)
            self.action_button.border_color = (0, 0, 0, 0)
            self.action_button.label.text_color = TEXT
