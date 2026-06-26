from kivy.metrics import dp
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.label import MDIcon, MDLabel

from app.core.theme import BLUE, GREEN, MUTED, RED, TEXT, with_alpha
from app.widgets.ui_components import Badge, GlowCard


class StatusCard(GlowCard):
    def __init__(self, title: str, value: str = "-", helper: str = "", **kwargs):
        super().__init__(accent=GREEN, **kwargs)
        self.size_hint_y = None
        self.height = dp(92)
        self.orientation = "horizontal"
        self.spacing = dp(12)
        self.padding = dp(14)

        icon_box = MDBoxLayout(
            size_hint=(None, None),
            size=(dp(48), dp(48)),
            md_bg_color=with_alpha(GREEN, 0.12),
            pos_hint={"center_y": 0.5},
        )
        icon_box.add_widget(
            MDIcon(
                icon="wifi",
                theme_text_color="Custom",
                text_color=GREEN,
                halign="center",
                valign="center",
                font_size=dp(26),
            )
        )
        self.add_widget(icon_box)

        copy = MDBoxLayout(orientation="vertical", spacing=dp(2))
        self.title_label = MDLabel(
            text=title,
            theme_text_color="Custom",
            text_color=TEXT,
            font_style="Subtitle1",
            bold=True,
        )
        self.value_label = MDLabel(
            text=value,
            theme_text_color="Custom",
            text_color=MUTED,
            font_style="Caption",
        )
        self.helper_label = MDLabel(
            text=helper,
            theme_text_color="Custom",
            text_color=MUTED,
            font_style="Caption",
        )
        copy.add_widget(self.title_label)
        copy.add_widget(self.value_label)
        copy.add_widget(self.helper_label)
        self.add_widget(copy)

        self.badge = Badge("LIVE" if value.lower().startswith("connect") else "OFF", GREEN)
        self.badge.pos_hint = {"center_y": 0.5}
        self.add_widget(self.badge)

    def set_value(self, value: str, helper: str = ""):
        connected = value.lower().startswith("connect")
        color = GREEN if connected else RED
        self.title_label.text = "Connecte" if connected else "Hors ligne"
        self.value_label.text = value
        self.helper_label.text = helper
        self.badge.set_badge("LIVE" if connected else "OFF", color)
        self.line_color = with_alpha(color, 0.65)
