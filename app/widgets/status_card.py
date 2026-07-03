from kivy.animation import Animation
from kivy.metrics import dp
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.label import MDIcon, MDLabel

from app.core.theme import BLUE, GREEN, RED, TEXT, with_alpha
from app.widgets.ui_components import Badge, GlowCard

CONNECTED_ICON = (0, 200 / 255, 83 / 255, 1)
DISCONNECTED_ICON = (77 / 255, 140 / 255, 1, 1)
SUBTITLE = (154 / 255, 168 / 255, 199 / 255, 1)


class StatusCard(GlowCard):
    def __init__(self, title: str, value: str = "-", helper: str = "", **kwargs):
        super().__init__(accent=GREEN, **kwargs)
        self.size_hint_y = None
        self.height = dp(124)
        self.padding = (dp(24), dp(16), dp(24), dp(16))
        self.spacing = dp(0)
        self.radius = [dp(18)]
        self._live_pulse = None

        row = MDBoxLayout(adaptive_height=True, spacing=dp(16), pos_hint={"center_y": 0.5})

        self.icon = MDIcon(
            icon="wifi",
            theme_text_color="Custom",
            text_color=DISCONNECTED_ICON,
            size_hint=(None, None),
            size=(dp(30), dp(30)),
            font_size=dp(30),
        )
        self.icon.pos_hint = {"center_y": 0.5}
        row.add_widget(self.icon)

        copy = MDBoxLayout(
            orientation="vertical",
            adaptive_height=True,
            spacing=dp(8),
            pos_hint={"center_y": 0.5},
        )
        self.title_label = MDLabel(
            text=title,
            theme_text_color="Custom",
            text_color=TEXT,
            font_style="H6",
            bold=True,
            adaptive_height=True,
        )
        self.protocol_label = MDLabel(
            text="ELM327 TCP/IP",
            theme_text_color="Custom",
            text_color=with_alpha(TEXT, 0.82),
            font_style="Body2",
            adaptive_height=True,
        )
        self.helper_label = MDLabel(
            text=helper,
            theme_text_color="Custom",
            text_color=SUBTITLE,
            font_style="Caption",
            adaptive_height=True,
            size_hint_x=1,
        )
        self.helper_label.bind(size=self._sync_text_size)
        copy.add_widget(self.title_label)
        copy.add_widget(self.protocol_label)
        copy.add_widget(self.helper_label)
        row.add_widget(copy)

        badge_box = MDBoxLayout(
            adaptive_height=True,
            size_hint_x=1,
            spacing=dp(8),
            pos_hint={"center_y": 0.5},
        )
        badge_box.add_widget(MDBoxLayout())
        self.live_dot = MDLabel(
            text="*",
            theme_text_color="Custom",
            text_color=GREEN,
            font_style="H6",
            bold=True,
            size_hint=(None, None),
            size=(dp(14), dp(20)),
            opacity=0,
        )
        badge_box.add_widget(self.live_dot)
        self.badge = Badge("LIVE" if value.lower().startswith("connect") else "OFF", GREEN)
        badge_box.add_widget(self.badge)
        row.add_widget(badge_box)

        self.add_widget(row)
        self.set_value(value, helper)

    def set_value(self, value: str, helper: str = ""):
        connected = value.lower().startswith("connect")
        color = GREEN if connected else RED
        self.title_label.text = "Connecte" if connected else "Hors ligne"
        self.helper_label.text = helper
        self.icon.text_color = CONNECTED_ICON if connected else DISCONNECTED_ICON
        self.badge.set_badge("LIVE" if connected else "OFF", color if connected else BLUE)
        self.line_color = with_alpha(color if connected else BLUE, 0.65)
        self._sync_live_pulse(connected)

    def _sync_live_pulse(self, connected: bool):
        Animation.cancel_all(self.live_dot, "opacity")
        self.live_dot.opacity = 1 if connected else 0
        if not connected:
            return
        pulse = Animation(opacity=0.32, d=0.7, t="in_out_sine") + Animation(opacity=1, d=0.7, t="in_out_sine")
        pulse.repeat = True
        pulse.start(self.live_dot)

    @staticmethod
    def _sync_text_size(label, size):
        label.text_size = (size[0], None)
