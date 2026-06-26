from kivy.metrics import dp
from kivymd.app import MDApp
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.screen import MDScreen
from kivymd.uix.scrollview import MDScrollView

from app.core.mobile import PHONE_CONTENT_MAX_WIDTH
from app.core.theme import APP_BG


class BaseScreen(MDScreen):
    @property
    def app(self):
        return MDApp.get_running_app()

    def build_page(self) -> MDBoxLayout:
        self.md_bg_color = APP_BG
        scroll = MDScrollView(
            bar_color=(0.12, 0.3, 0.72, 0.65),
            bar_inactive_color=(0.05, 0.07, 0.12, 0.25),
        )
        layout = MDBoxLayout(
            orientation="vertical",
            padding=(dp(14), dp(18), dp(14), dp(20)),
            spacing=dp(12),
            adaptive_height=True,
            size_hint=(None, None),
            width=dp(PHONE_CONTENT_MAX_WIDTH),
            pos_hint={"center_x": 0.5},
            md_bg_color=APP_BG,
        )
        layout.bind(minimum_height=layout.setter("height"))
        self.bind(
            width=lambda _, value: setattr(
                layout,
                "width",
                min(value, dp(PHONE_CONTENT_MAX_WIDTH)),
            )
        )
        scroll.add_widget(layout)
        self.add_widget(scroll)
        return layout

    def refresh(self):
        pass
