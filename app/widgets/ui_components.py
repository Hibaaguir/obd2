from kivy.animation import Animation
from kivy.clock import Clock
from kivy.graphics import Color, Line, RoundedRectangle
from kivy.metrics import dp, sp
from kivy.properties import ListProperty, ObjectProperty, StringProperty
from kivy.uix.behaviors import ButtonBehavior
from kivy.uix.widget import Widget
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.card import MDCard
from kivymd.uix.label import MDIcon, MDLabel

from app.core.theme import (
    AMBER,
    APP_BG,
    BLUE,
    BORDER,
    BORDER_ACTIVE,
    DIM,
    GREEN,
    MUTED,
    PANEL_ALT,
    PANEL_BG,
    PANEL_DARK,
    RED,
    TEXT,
    with_alpha,
)


class GlowCard(MDCard):
    def __init__(self, accent=None, **kwargs):
        super().__init__(**kwargs)
        self.orientation = "vertical"
        self.padding = dp(14)
        self.spacing = dp(8)
        self.radius = [dp(10)]
        self.elevation = 0
        self.md_bg_color = PANEL_BG
        self.line_color = with_alpha(accent or BORDER, 0.85)


class LinearIndicator(Widget):
    def __init__(self, accent=GREEN, ratio=0, **kwargs):
        super().__init__(**kwargs)
        self.accent = accent
        self.ratio = 0
        self.set_ratio(ratio)
        self.bind(pos=self._redraw, size=self._redraw)

    def set_ratio(self, ratio):
        self.ratio = max(0, min(1, ratio))
        self._redraw()

    def set_accent(self, accent):
        self.accent = accent
        self._redraw()

    def _redraw(self, *_):
        self.canvas.clear()
        track_height = min(self.height, dp(5))
        radius = [track_height / 2]
        track_y = self.center_y - track_height / 2
        fill_width = max(track_height, self.width * self.ratio) if self.ratio > 0 else 0

        with self.canvas:
            Color(*with_alpha(BORDER, 0.9))
            RoundedRectangle(pos=(self.x, track_y), size=(self.width, track_height), radius=radius)
            if fill_width > 0:
                Color(*self.accent)
                RoundedRectangle(pos=(self.x, track_y), size=(fill_width, track_height), radius=radius)


class AccentMetricCard(GlowCard):
    def __init__(
        self,
        title: str,
        icon: str = "chart-line",
        value: str = "-",
        unit: str = "",
        status: str = "En attente",
        accent=GREEN,
        **kwargs,
    ):
        super().__init__(accent=accent, **kwargs)
        self.accent = accent
        self.size_hint_y = None
        self.height = dp(132)
        self.padding = 0

        row = MDBoxLayout(spacing=0)
        marker = MDBoxLayout(size_hint_x=None, width=dp(4), md_bg_color=accent)
        content = MDBoxLayout(
            orientation="vertical",
            padding=(dp(10), dp(9), dp(10), dp(9)),
            spacing=dp(6),
        )

        header = MDBoxLayout(size_hint_y=None, height=dp(40), spacing=dp(8))
        self.icon_label = MDIcon(
            icon=icon,
            theme_text_color="Custom",
            text_color=accent,
            font_size=dp(22),
            size_hint_x=None,
            width=dp(28),
            halign="center",
            valign="center",
        )
        self.title_label = MDLabel(
            text=title,
            theme_text_color="Custom",
            text_color=TEXT,
            font_style="Subtitle2",
            bold=True,
            halign="left",
            valign="center",
        )
        self.icon_label.bind(size=self._sync_text_size)
        self.title_label.bind(size=self._sync_text_size)
        header.add_widget(self.icon_label)
        header.add_widget(self.title_label)

        value_row = MDBoxLayout(size_hint_y=None, height=dp(42), spacing=dp(6))
        self.value_label = MDLabel(
            text=value,
            theme_text_color="Custom",
            text_color=TEXT,
            font_style="H5",
            bold=True,
            halign="left",
            valign="center",
        )
        self.unit_label = MDLabel(
            text=unit,
            theme_text_color="Custom",
            text_color=MUTED,
            font_style="Caption",
            size_hint_x=None,
            width=dp(44),
            halign="left",
            valign="center",
        )
        self.value_label.bind(size=self._sync_text_size)
        self.unit_label.bind(size=self._sync_text_size)
        value_row.add_widget(self.value_label)
        value_row.add_widget(self.unit_label)

        self.status_label = MDLabel(
            text=status,
            theme_text_color="Custom",
            text_color=MUTED,
            font_style="Caption",
            size_hint_y=None,
            height=dp(22),
            halign="left",
            valign="center",
        )
        self.status_label.bind(size=self._sync_text_size)

        content.add_widget(header)
        content.add_widget(value_row)
        content.add_widget(self.status_label)
        row.add_widget(marker)
        row.add_widget(content)
        self.add_widget(row)

    def set_data(self, value: str, unit: str = "", status: str = "Lecture ECU"):
        self.value_label.text = value
        self.value_label.font_style = "Subtitle1" if len(value) > 8 else "H5"
        self.unit_label.text = unit
        self.status_label.text = status

    @staticmethod
    def _sync_text_size(label, size):
        label.text_size = size


class GaugeArc(Widget):
    def __init__(self, accent=GREEN, ratio=0, **kwargs):
        super().__init__(**kwargs)
        self.accent = accent
        self.ratio = ratio
        self.bind(pos=self._redraw, size=self._redraw)

    def set_ratio(self, ratio):
        self.ratio = max(0, min(1, ratio))
        self._redraw()

    def _redraw(self, *_):
        self.canvas.clear()
        radius = max(1, min(self.width, self.height * 2) / 2 - dp(5))
        center_x = self.center_x
        center_y = self.y + dp(8)
        start = 205
        end = 335
        active_end = start + (end - start) * self.ratio
        with self.canvas:
            Color(*with_alpha(BORDER, 0.8))
            Line(circle=(center_x, center_y, radius, start, end), width=dp(4))
            Color(*self.accent)
            Line(circle=(center_x, center_y, radius, start, active_end), width=dp(4))


class GaugeMetricCard(GlowCard):
    def __init__(
        self,
        title: str,
        icon: str,
        max_value: float,
        value: str = "-",
        unit: str = "",
        status: str = "En attente",
        accent=GREEN,
        min_value: float = 0,
        **kwargs,
    ):
        super().__init__(accent=accent, **kwargs)
        self.accent = accent
        self.min_value = min_value
        self.max_value = max_value
        self.size_hint_y = None
        self.height = dp(158)
        self.padding = dp(12)
        self.spacing = dp(6)

        header = MDBoxLayout(size_hint_y=None, height=dp(32), spacing=dp(8))
        header.add_widget(
            MDIcon(
                icon=icon,
                theme_text_color="Custom",
                text_color=accent,
                size_hint_x=None,
                width=dp(28),
                font_size=dp(22),
            )
        )
        self.title_label = MDLabel(
            text=title,
            theme_text_color="Custom",
            text_color=TEXT,
            font_style="Subtitle1",
            bold=True,
            halign="left",
            valign="center",
        )
        self.title_label.bind(size=self._sync_text_size)
        header.add_widget(self.title_label)

        value_row = MDBoxLayout(size_hint_y=None, height=dp(42), spacing=dp(8))
        self.value_label = MDLabel(
            text=value,
            theme_text_color="Custom",
            text_color=TEXT,
            font_style="H3",
            bold=True,
            halign="left",
            valign="center",
        )
        self.value_label.bind(size=self._sync_text_size)
        self.unit_label = MDLabel(
            text=unit,
            theme_text_color="Custom",
            text_color=MUTED,
            font_style="Caption",
            size_hint_x=None,
            width=dp(58),
            halign="left",
            valign="center",
        )
        self.unit_label.bind(size=self._sync_text_size)
        value_row.add_widget(self.value_label)
        value_row.add_widget(self.unit_label)

        self.gauge = GaugeArc(accent=accent, size_hint_y=None, height=dp(42))
        self.status_label = MDLabel(
            text=status,
            theme_text_color="Custom",
            text_color=MUTED,
            font_style="Caption",
            size_hint_y=None,
            height=dp(22),
            halign="left",
            valign="center",
        )
        self.status_label.bind(size=self._sync_text_size)

        self.add_widget(header)
        self.add_widget(value_row)
        self.add_widget(self.gauge)
        self.add_widget(self.status_label)
        self.set_data(value, unit, status)

    def set_data(self, value: str, unit: str = "", status: str = "Lecture ECU"):
        self.value_label.text = value
        self.value_label.font_style = "H5" if len(value) > 7 else "H4"
        self.unit_label.text = unit
        self.status_label.text = status
        numeric = self._to_float(value)
        if numeric is None:
            self.gauge.set_ratio(0)
            return
        span = self.max_value - self.min_value or 1
        self.gauge.set_ratio((numeric - self.min_value) / span)

    @staticmethod
    def _to_float(value):
        try:
            return float(str(value).replace(",", "."))
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _sync_text_size(label, size):
        label.text_size = size


class MetricCard(MDCard):
    def __init__(
        self,
        title: str,
        icon: str = "chart-line",
        value: str = "-",
        unit: str = "",
        status: str = "En attente",
        accent=BLUE,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.accent = accent
        self.orientation = "vertical"
        self.size_hint_y = None
        self.height = dp(158)
        self.padding = dp(20)
        self.spacing = dp(8)
        self.radius = [dp(20)]
        self.elevation = 0
        self.md_bg_color = PANEL_BG
        self.line_color = with_alpha(accent, 0.22)

        header = MDBoxLayout(size_hint_y=None, height=dp(24), spacing=dp(8))
        self.icon_label = MDIcon(
            icon=icon,
            theme_text_color="Custom",
            text_color=accent,
            size_hint_x=None,
            width=dp(18),
            font_size=dp(16),
        )
        self.title_label = MDLabel(
            text=title,
            theme_text_color="Custom",
            text_color=with_alpha(TEXT, 0.9),
            font_style="Subtitle2",
            bold=True,
            halign="left",
            valign="center",
            shorten=True,
            shorten_from="right",
        )
        self.title_label.bind(size=self._sync_text_size)
        header.add_widget(self.icon_label)
        header.add_widget(self.title_label)

        value_block = MDBoxLayout(
            orientation="vertical",
            size_hint_y=None,
            height=dp(68),
            spacing=dp(2),
        )
        self.value_label = MDLabel(
            text=value,
            theme_text_color="Custom",
            text_color=TEXT,
            font_style="H3",
            bold=True,
            halign="left",
            valign="middle",
            size_hint_y=None,
            height=dp(42),
        )
        self.value_label.bind(size=self._sync_text_size)
        self.unit_label = MDLabel(
            text=unit,
            theme_text_color="Custom",
            text_color=with_alpha(TEXT, 0.62),
            font_style="Caption",
            bold=True,
            halign="left",
            valign="top",
            size_hint_y=None,
            height=dp(18),
        )
        self.unit_label.bind(size=self._sync_text_size)
        value_block.add_widget(self.value_label)
        value_block.add_widget(self.unit_label)

        spacer = MDBoxLayout()

        footer = MDBoxLayout(
            size_hint_y=None,
            height=dp(22),
            spacing=dp(8),
        )
        self.status_dot = MDLabel(
            text="•",
            theme_text_color="Custom",
            text_color=accent,
            size_hint_x=None,
            width=dp(12),
            font_style="Caption",
            bold=True,
            halign="center",
            valign="center",
        )
        self.status_dot.bind(size=self._sync_text_size)
        self.status_label = MDLabel(
            text=status,
            theme_text_color="Custom",
            text_color=with_alpha(TEXT, 0.72),
            font_style="Caption",
            bold=True,
            halign="left",
            valign="center",
        )
        self.status_label.bind(size=self._sync_text_size)
        footer.add_widget(self.status_dot)
        footer.add_widget(self.status_label)

        self.add_widget(header)
        self.add_widget(value_block)
        self.add_widget(spacer)
        self.add_widget(footer)
        self.set_data(value, unit, status)

    def set_data(self, value: str, unit: str = "", status: str = "En attente", accent=None):
        value_text = str(value)
        self.value_label.text = value_text
        self.value_label.font_style = "H4" if len(value_text) > 7 else "H3"
        self.unit_label.text = unit
        self.status_label.text = status
        self._apply_accent(accent or self.accent)

    def _apply_accent(self, accent):
        self.accent = accent
        self.icon_label.text_color = accent
        self.status_dot.text_color = accent
        self.line_color = with_alpha(accent, 0.22)

    @staticmethod
    def _sync_text_size(label, size):
        label.text_size = size


class CleanMetricCard(MDCard):
    def __init__(
        self,
        title: str,
        icon: str = "chart-line",
        value: str = "-",
        unit: str = "",
        status: str = "En attente",
        accent=BLUE,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.accent = accent
        self.orientation = "vertical"
        self.size_hint_y = None
        self.adaptive_height = True
        self.padding = (dp(16), dp(14), dp(16), dp(14))
        self.spacing = dp(10)
        self.radius = [dp(20)]
        self.elevation = 0
        self.md_bg_color = PANEL_BG
        self.line_color = with_alpha(accent, 0.22)
        self.bind(minimum_height=self.setter("height"))

        header = MDBoxLayout(adaptive_height=True, spacing=dp(8))
        self.icon_label = MDIcon(
            icon=icon,
            theme_text_color="Custom",
            text_color=accent,
            size_hint=(None, None),
            size=(dp(18), dp(20)),
            font_size=dp(16),
        )
        self.title_label = MDLabel(
            text=title,
            theme_text_color="Custom",
            text_color=with_alpha(TEXT, 0.9),
            font_style="Subtitle2",
            bold=True,
            halign="left",
            valign="middle",
            adaptive_height=True,
        )
        self.title_label.bind(width=self._sync_wrapped_text)
        header.add_widget(self.icon_label)
        header.add_widget(self.title_label)

        value_block = MDBoxLayout(
            orientation="vertical",
            adaptive_height=True,
            spacing=dp(4),
        )
        self.value_label = MDLabel(
            text=value,
            theme_text_color="Custom",
            text_color=TEXT,
            font_style="H4",
            bold=True,
            halign="left",
            valign="middle",
            adaptive_height=True,
        )
        self.value_label.bind(width=self._sync_wrapped_text)
        self.unit_label = MDLabel(
            text=unit,
            theme_text_color="Custom",
            text_color=with_alpha(TEXT, 0.62),
            font_style="Subtitle2",
            bold=True,
            halign="left",
            valign="middle",
            adaptive_height=True,
        )
        self.unit_label.bind(width=self._sync_wrapped_text)
        value_block.add_widget(self.value_label)
        value_block.add_widget(self.unit_label)

        spacer = MDBoxLayout()

        footer = MDBoxLayout(adaptive_height=True, spacing=dp(8))
        self.status_dot = MDLabel(
            text="•",
            theme_text_color="Custom",
            text_color=accent,
            size_hint=(None, None),
            size=(dp(12), dp(18)),
            font_style="Caption",
            bold=True,
            halign="center",
            valign="center",
        )
        self.status_dot.bind(width=self._sync_wrapped_text)
        self.status_label = MDLabel(
            text=status,
            theme_text_color="Custom",
            text_color=with_alpha(TEXT, 0.72),
            font_style="Caption",
            bold=True,
            halign="left",
            valign="middle",
            adaptive_height=True,
        )
        self.status_label.bind(width=self._sync_wrapped_text)
        footer.add_widget(self.status_dot)
        footer.add_widget(self.status_label)

        self.add_widget(header)
        self.add_widget(value_block)
        self.add_widget(spacer)
        self.add_widget(footer)
        self.set_data(value, unit, status)

    def set_data(self, value: str, unit: str = "", status: str = "En attente", accent=None):
        value_text = str(value)
        self.value_label.text = value_text
        self.value_label.font_style = "H4" if len(value_text) > 7 else "H3"
        self.unit_label.text = unit
        self.status_label.text = status
        self._apply_accent(accent or self.accent)

    def _apply_accent(self, accent):
        self.accent = accent
        self.icon_label.text_color = accent
        self.status_dot.text_color = accent
        self.line_color = with_alpha(accent, 0.22)

    @staticmethod
    def _sync_wrapped_text(label, width):
        label.text_size = (width, None)


class PremiumMetricCard(MDCard):
    def __init__(
        self,
        title: str,
        icon: str = "chart-line",
        value: str = "-",
        unit: str = "",
        status: str = "En attente",
        accent=BLUE,
        priority: str = "standard",
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.accent = accent
        self.priority = priority
        self._value_event = None
        self._display_numeric = None
        self._target_numeric = None
        self._precision = 0
        self.orientation = "vertical"
        self.size_hint_y = None
        self.height = dp(184) if priority == "primary" else (dp(166) if priority == "secondary" else dp(152))
        self.padding = dp(22) if priority == "primary" else dp(20)
        self.spacing = dp(10)
        self.radius = [dp(20)]
        self.elevation = 2 if priority == "primary" else 1
        self.md_bg_color = self._background_for_priority(accent, priority)
        self.line_color = with_alpha(accent, 0.26 if priority != "compact" else 0.2)
        self.opacity = 0

        header = MDBoxLayout(size_hint_y=None, height=dp(24), spacing=dp(8))
        self.icon_label = MDIcon(
            icon=icon,
            theme_text_color="Custom",
            text_color=accent,
            size_hint_x=None,
            width=dp(18),
            font_size=sp(15),
        )
        self.title_label = MDLabel(
            text=title,
            theme_text_color="Custom",
            text_color=with_alpha(TEXT, 0.9),
            font_style="Body1",
            bold=False,
            font_size=self._title_font_size(title),
            halign="left",
            valign="center",
        )
        self.title_label.bind(size=self._sync_single_line_text)
        header.add_widget(self.icon_label)
        header.add_widget(self.title_label)

        value_block = MDBoxLayout(
            orientation="vertical",
            size_hint_y=None,
            height=dp(88) if priority == "primary" else dp(78),
            spacing=dp(4),
        )
        value_row = MDBoxLayout(
            size_hint_y=None,
            height=dp(58) if priority == "primary" else dp(50),
            spacing=dp(6),
            adaptive_width=True,
        )
        self.value_label = MDLabel(
            text=value,
            theme_text_color="Custom",
            text_color=TEXT,
            font_style="H2" if priority == "primary" else "H3",
            bold=True,
            halign="left",
            valign="middle",
            size_hint_y=None,
            size_hint_x=None,
            height=dp(58) if priority == "primary" else dp(50),
        )
        self.value_label.bind(size=self._sync_single_line_text)
        self.value_label.bind(texture_size=self._fit_to_texture)
        self.unit_label = MDLabel(
            text=unit,
            theme_text_color="Custom",
            text_color=with_alpha(TEXT, 0.72),
            font_style="Body2",
            font_size=sp(16),
            bold=True,
            halign="left",
            valign="bottom",
            size_hint_y=None,
            size_hint_x=None,
            height=dp(32),
        )
        self.unit_label.bind(size=self._sync_single_line_text)
        self.unit_label.bind(texture_size=self._fit_to_texture)
        value_row.add_widget(self.value_label)
        value_row.add_widget(self.unit_label)

        self.status_hint = MDLabel(
            text="Mise a jour en direct",
            theme_text_color="Custom",
            text_color=with_alpha(MUTED, 0.88),
            font_style="Caption",
            font_size=sp(14),
            halign="left",
            valign="middle",
            size_hint_y=None,
            height=dp(20),
        )
        self.status_hint.bind(size=self._sync_single_line_text)
        value_block.add_widget(value_row)
        value_block.add_widget(self.status_hint)

        spacer = MDBoxLayout()

        footer = MDBoxLayout(
            size_hint_y=None,
            height=dp(30),
            spacing=dp(10),
        )
        self.status_badge = MDCard(
            orientation="horizontal",
            padding=(dp(12), dp(5), dp(12), dp(5)),
            spacing=dp(5),
            radius=[dp(13)],
            elevation=0,
            size_hint=(None, None),
            height=dp(28),
            md_bg_color=with_alpha(accent, 0.14),
            line_color=with_alpha(accent, 0.22),
        )
        self.status_dot = MDLabel(
            text="*",
            theme_text_color="Custom",
            text_color=accent,
            size_hint_x=None,
            width=dp(8),
            font_style="Body2",
            font_size=sp(14),
            bold=True,
            halign="center",
            valign="center",
        )
        self.status_dot.bind(size=self._sync_single_line_text)
        self.status_label = MDLabel(
            text=(status or "").upper(),
            theme_text_color="Custom",
            text_color=accent,
            font_style="Caption",
            font_size=sp(14),
            bold=True,
            halign="left",
            valign="center",
            size_hint_x=None,
        )
        self.status_label.bind(size=self._sync_single_line_text)
        self.status_label.bind(texture_size=self._fit_to_texture)
        self.status_badge.add_widget(self.status_dot)
        self.status_badge.add_widget(self.status_label)
        footer.add_widget(self.status_badge)

        self.add_widget(header)
        self.add_widget(value_block)
        self.add_widget(spacer)
        self.add_widget(footer)
        self.set_data(value, unit, status)
        Clock.schedule_once(lambda *_: Animation(opacity=1, d=0.22, t="out_quad").start(self), 0)

    def set_data(self, value: str, unit: str = "", status: str = "En attente", accent=None):
        value_text = str(value)
        self._update_value(value_text)
        self.unit_label.text = unit
        self.status_hint.text = "Lecture indisponible" if value_text == "-" else "Mise a jour en direct"
        self._apply_status(status, accent or self.accent)

    def _apply_status(self, status, accent):
        status_text = status or "En attente"
        status_accent = self._status_accent(status_text, accent)
        self._apply_accent(accent)
        self.status_label.text = status_text.upper()
        self.status_label.text_color = status_accent
        self.status_dot.text_color = status_accent
        self.status_badge.md_bg_color = with_alpha(status_accent, 0.16)
        self.status_badge.line_color = with_alpha(status_accent, 0.22)
        self.status_badge.width = max(dp(92), self.status_label.texture_size[0] + dp(34))
        Animation.cancel_all(self.status_badge, "opacity")
        self.status_badge.opacity = 1
        if status_text.lower() in {"attention", "critique"}:
            pulse = Animation(opacity=0.82, d=0.45, t="in_out_sine") + Animation(opacity=1, d=0.45, t="in_out_sine")
            pulse.repeat = status_text.lower() == "critique"
            pulse.start(self.status_badge)

    def _apply_accent(self, accent):
        self.accent = accent
        self.icon_label.text_color = accent
        self.line_color = with_alpha(accent, 0.26 if self.priority != "compact" else 0.2)
        self.md_bg_color = self._background_for_priority(accent, self.priority)

    def _update_value(self, value_text: str):
        target = self._to_float(value_text)
        if target is None:
            if self._value_event is not None:
                self._value_event.cancel()
                self._value_event = None
            self._display_numeric = None
            self.value_label.text = value_text
            self.value_label.font_style = "H4" if len(value_text) > 7 else ("H2" if self.priority == "primary" else "H3")
            return

        self._precision = self._precision_for_value(value_text)
        if self._display_numeric is None:
            self._display_numeric = target
            self._target_numeric = target
            self.value_label.text = self._format_numeric(target)
            return

        self._target_numeric = target
        if self._value_event is not None:
            self._value_event.cancel()
        self._value_event = Clock.schedule_interval(self._step_value_animation, 1 / 30)

    def _step_value_animation(self, _dt):
        if self._display_numeric is None or self._target_numeric is None:
            return False
        delta = self._target_numeric - self._display_numeric
        if abs(delta) < 0.05:
            self._display_numeric = self._target_numeric
            self.value_label.text = self._format_numeric(self._display_numeric)
            self._value_event = None
            return False
        self._display_numeric += delta * 0.24
        self.value_label.text = self._format_numeric(self._display_numeric)
        return True

    def _format_numeric(self, numeric):
        if self._precision <= 0:
            return str(int(round(numeric)))
        return f"{numeric:.{self._precision}f}"

    @staticmethod
    def _title_font_size(title: str):
        length = len(title or "")
        if length <= 12:
            return sp(16)
        if length <= 18:
            return sp(15)
        if length <= 22:
            return sp(14)
        return sp(13)

    @staticmethod
    def _background_for_priority(accent, priority):
        alpha = 0.12 if priority == "primary" else (0.085 if priority == "secondary" else 0.06)
        return with_alpha(accent, alpha)

    @staticmethod
    def _status_accent(status: str, fallback):
        normalized = (status or "").lower()
        if normalized in {"critique", "critical"}:
            return RED
        if normalized in {"attention", "alerte"}:
            return AMBER
        if normalized in {"normal", "optimal"}:
            return GREEN
        if normalized in {"stable", "en attente", "hors ligne", "non supporte"}:
            return BLUE
        return fallback

    @staticmethod
    def _precision_for_value(value: str):
        text = str(value)
        if "." in text:
            return len(text.split(".", 1)[1])
        return 0

    @staticmethod
    def _to_float(value):
        try:
            return float(str(value).replace(",", "."))
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _sync_single_line_text(label, size):
        label.text_size = (size[0], None)

    @staticmethod
    def _fit_to_texture(label, _texture_size):
        label.width = max(dp(18), label.texture_size[0])


class HeroMetricCard(MDCard):
    def __init__(
        self,
        title: str,
        icon: str = "chart-line",
        max_value: float = 100,
        value: str = "-",
        unit: str = "",
        status: str = "En attente",
        accent=GREEN,
        min_value: float = 0,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.accent = accent
        self.min_value = min_value
        self.max_value = max_value
        self.orientation = "vertical"
        self.size_hint_y = None
        self.height = dp(144)
        self.padding = (dp(16), dp(14), dp(16), dp(14))
        self.spacing = dp(10)
        self.radius = [dp(20)]
        self.elevation = 0
        self.md_bg_color = PANEL_ALT
        self.line_color = with_alpha(accent, 0.34)
        self.bind(pos=self._redraw_surface, size=self._redraw_surface)

        header = MDBoxLayout(size_hint_y=None, height=dp(26), spacing=dp(8))
        self.icon_label = MDIcon(
            icon=icon,
            theme_text_color="Custom",
            text_color=accent,
            size_hint_x=None,
            width=dp(22),
            font_size=dp(18),
        )
        self.title_label = MDLabel(
            text=title,
            theme_text_color="Custom",
            text_color=with_alpha(TEXT, 0.92),
            font_style="Subtitle1",
            bold=True,
            halign="left",
            valign="center",
        )
        self.title_label.bind(size=self._sync_text_size)
        self.icon_label.bind(size=self._sync_text_size)
        header.add_widget(self.icon_label)
        header.add_widget(self.title_label)

        value_row = MDBoxLayout(
            size_hint_y=None,
            height=dp(48),
            spacing=dp(4),
            adaptive_width=True,
        )
        self.value_label = MDLabel(
            text=value,
            theme_text_color="Custom",
            text_color=TEXT,
            font_style="H4",
            bold=True,
            halign="left",
            valign="center",
            size_hint_x=None,
        )
        self.value_label.bind(size=self._sync_text_size)
        self.value_label.bind(texture_size=self._fit_to_texture)
        self.unit_label = MDLabel(
            text=unit,
            theme_text_color="Custom",
            text_color=with_alpha(TEXT, 0.76),
            font_style="Subtitle2",
            bold=True,
            size_hint_x=None,
            width=dp(40),
            halign="left",
            valign="bottom",
        )
        self.unit_label.bind(size=self._sync_text_size)
        self.unit_label.bind(texture_size=self._fit_to_texture)
        value_row.add_widget(self.value_label)
        value_row.add_widget(self.unit_label)

        footer = MDBoxLayout(orientation="vertical", spacing=dp(8))
        self.indicator = LinearIndicator(accent=accent, size_hint_y=None, height=dp(6))
        status_row = MDBoxLayout(size_hint_y=None, height=dp(22), spacing=dp(6))
        self.status_dot = MDIcon(
            icon="circle-medium",
            theme_text_color="Custom",
            text_color=accent,
            size_hint_x=None,
            width=dp(14),
            font_size=dp(12),
        )
        self.status_label = MDLabel(
            text=status,
            theme_text_color="Custom",
            text_color=with_alpha(TEXT, 0.78),
            font_style="Caption",
            bold=True,
            size_hint_y=None,
            height=dp(22),
            halign="left",
            valign="center",
        )
        self.status_label.bind(size=self._sync_text_size)
        self.status_dot.bind(size=self._sync_text_size)
        status_row.add_widget(self.status_dot)
        status_row.add_widget(self.status_label)
        footer.add_widget(self.indicator)
        footer.add_widget(status_row)

        self.add_widget(header)
        self.add_widget(value_row)
        self.add_widget(footer)
        self.set_data(value, unit, status)

    def set_data(self, value: str, unit: str = "", status: str = "Lecture ECU"):
        value_text = str(value)
        self.value_label.text = value_text
        self.value_label.font_style = "H5" if len(value_text) > 7 else "H4"
        self.unit_label.text = unit
        self.status_label.text = status
        accent = self._accent_for_status(status, value_text)
        self._apply_accent(accent)
        numeric = self._to_float(value)
        if numeric is None:
            self.indicator.set_ratio(0)
            return
        span = self.max_value - self.min_value or 1
        self.indicator.set_ratio((numeric - self.min_value) / span)

    def _redraw_surface(self, *_):
        self.canvas.before.clear()
        self.canvas.after.clear()
        with self.canvas.before:
            Color(0, 0, 0, 0.2)
            RoundedRectangle(
                pos=(self.x, self.y - dp(4)),
                size=self.size,
                radius=[dp(20)],
            )
            Color(*with_alpha(self.accent, 0.08))
            RoundedRectangle(
                pos=(self.x + dp(1), self.y + dp(1)),
                size=(self.width - dp(2), self.height - dp(2)),
                radius=[dp(19)],
            )
        with self.canvas.after:
            Color(*with_alpha(self.accent, 0.16))
            RoundedRectangle(
                pos=(self.x + dp(1), self.top - dp(4)),
                size=(self.width - dp(2), dp(3)),
                radius=[dp(2)],
            )

    def _apply_accent(self, accent):
        self.accent = accent
        self.icon_label.text_color = accent
        self.unit_label.text_color = with_alpha(accent, 0.9)
        self.status_dot.text_color = accent
        self.status_label.text_color = with_alpha(TEXT, 0.8)
        self.indicator.set_accent(accent)
        self.line_color = with_alpha(accent, 0.34)
        self._redraw_surface()

    @staticmethod
    def _accent_for_status(status: str, value: str):
        normalized = (status or "").strip().lower()
        if normalized in {"attention", "alerte"}:
            return AMBER
        if normalized in {"critique", "critical"}:
            return RED
        if normalized == "optimal":
            return GREEN
        if normalized in {"hors ligne", "en attente", "non supporte"} or value == "-":
            return BLUE
        if normalized in {"normal", "stable"}:
            return BLUE
        return BLUE

    @staticmethod
    def _to_float(value):
        try:
            return float(str(value).replace(",", "."))
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _sync_text_size(label, size):
        label.text_size = size

    @staticmethod
    def _fit_to_texture(label, _texture_size):
        label.width = max(dp(20), label.texture_size[0])


class CompactMetricCard(GlowCard):
    def __init__(
        self,
        title: str,
        icon: str = "chart-line",
        value: str = "-",
        unit: str = "",
        status: str = "En attente",
        accent=GREEN,
        **kwargs,
    ):
        super().__init__(accent=accent, **kwargs)
        self.size_hint_y = None
        self.height = dp(104)
        self.padding = dp(10)
        self.spacing = dp(4)

        header = MDBoxLayout(size_hint_y=None, height=dp(32), spacing=dp(8))
        header.add_widget(
            MDIcon(
                icon=icon,
                theme_text_color="Custom",
                text_color=accent,
                size_hint_x=None,
                width=dp(24),
                font_size=dp(20),
            )
        )
        self.title_label = MDLabel(
            text=title,
            theme_text_color="Custom",
            text_color=TEXT,
            font_style="Subtitle2",
            bold=True,
            halign="left",
            valign="center",
        )
        self.title_label.bind(size=self._sync_text_size)
        header.add_widget(self.title_label)

        value_row = MDBoxLayout(size_hint_y=None, height=dp(34), spacing=dp(5))
        self.value_label = MDLabel(
            text=value,
            theme_text_color="Custom",
            text_color=TEXT,
            font_style="H6",
            bold=True,
            halign="left",
            valign="center",
        )
        self.value_label.bind(size=self._sync_text_size)
        self.unit_label = MDLabel(
            text=unit,
            theme_text_color="Custom",
            text_color=MUTED,
            font_style="Caption",
            size_hint_x=None,
            width=dp(42),
            halign="left",
            valign="center",
        )
        self.unit_label.bind(size=self._sync_text_size)
        value_row.add_widget(self.value_label)
        value_row.add_widget(self.unit_label)

        self.status_label = MDLabel(
            text=status,
            theme_text_color="Custom",
            text_color=MUTED,
            font_style="Caption",
            size_hint_y=None,
            height=dp(22),
            halign="left",
            valign="center",
        )
        self.status_label.bind(size=self._sync_text_size)

        self.add_widget(header)
        self.add_widget(value_row)
        self.add_widget(self.status_label)

    def set_data(self, value: str, unit: str = "", status: str = "Lecture ECU"):
        self.value_label.text = value
        self.value_label.font_style = "Subtitle2" if len(value) > 9 else "H6"
        self.unit_label.text = unit
        self.status_label.text = status

    @staticmethod
    def _sync_text_size(label, size):
        label.text_size = size


class Badge(MDCard):
    def __init__(self, text: str, color=BLUE, **kwargs):
        super().__init__(**kwargs)
        self.orientation = "horizontal"
        self.padding = (dp(8), dp(2), dp(8), dp(2))
        self.spacing = dp(4)
        self.radius = [dp(6)]
        self.elevation = 0
        self.md_bg_color = with_alpha(color, 0.16)
        self.line_color = with_alpha(color, 0.55)
        self.size_hint = (None, None)
        self.height = dp(28)
        self.width = max(dp(86), dp(12) * len(text))
        self.label = MDLabel(
            text=text.upper(),
            theme_text_color="Custom",
            text_color=color,
            font_style="Caption",
            bold=True,
            halign="center",
        )
        self.add_widget(self.label)

    def set_badge(self, text: str, color=BLUE):
        self.label.text = text.upper()
        self.label.text_color = color
        self.md_bg_color = with_alpha(color, 0.16)
        self.line_color = with_alpha(color, 0.55)
        self.width = max(dp(86), dp(12) * len(text))


class SectionToggle(ButtonBehavior, MDBoxLayout):
    def __init__(self, text: str, icon: str, on_release_callback, **kwargs):
        super().__init__(**kwargs)
        self.orientation = "horizontal"
        self.adaptive_height = True
        self.spacing = dp(10)
        self.on_release_callback = on_release_callback
        icon_box = MDCard(
            size_hint=(None, None),
            size=(dp(34), dp(34)),
            radius=[dp(12)],
            elevation=0,
            md_bg_color=with_alpha(BLUE, 0.12),
            line_color=with_alpha(BLUE, 0.2),
        )
        icon_box.add_widget(
            MDIcon(
                icon=icon,
                theme_text_color="Custom",
                text_color=BLUE,
                halign="center",
                valign="center",
                font_size=dp(18),
            )
        )
        self.add_widget(icon_box)
        copy = MDBoxLayout(orientation="vertical", adaptive_height=True, spacing=dp(2))
        self.title_label = MDLabel(
            text=text,
            theme_text_color="Custom",
            text_color=TEXT,
            font_style="Subtitle2",
            bold=True,
            adaptive_height=True,
        )
        self.helper_label = MDLabel(
            text="Afficher les détails",
            theme_text_color="Custom",
            text_color=MUTED,
            font_style="Caption",
            adaptive_height=True,
        )
        copy.add_widget(self.title_label)
        copy.add_widget(self.helper_label)
        self.add_widget(copy)
        self.chevron = MDIcon(
            icon="chevron-down",
            theme_text_color="Custom",
            text_color=MUTED,
            size_hint=(None, None),
            size=(dp(22), dp(22)),
            font_size=dp(20),
        )
        self.add_widget(self.chevron)

    def on_release(self):
        if self.on_release_callback:
            self.on_release_callback()

    def set_expanded(self, expanded: bool):
        self.helper_label.text = "Masquer les détails" if expanded else "Afficher les détails"
        self.chevron.icon = "chevron-up" if expanded else "chevron-down"


class CollapsibleSection(GlowCard):
    def __init__(self, title: str, icon: str = "chevron-down", expanded: bool = False, **kwargs):
        super().__init__(**kwargs)
        self.expanded = expanded
        self.header = SectionToggle(title, icon, self.toggle)
        self.add_widget(self.header)
        self.body = MDBoxLayout(
            orientation="vertical",
            adaptive_height=True,
            spacing=dp(8),
            padding=(0, dp(6), 0, 0),
        )
        self.body.bind(minimum_height=lambda *_: self._sync_body_height())
        self.body_wrapper = MDBoxLayout(orientation="vertical", size_hint_y=None, height=0, opacity=0)
        self.body_wrapper.add_widget(self.body)
        self.add_widget(self.body_wrapper)
        self.set_expanded(expanded)

    def add_body_widget(self, widget):
        self.body.add_widget(widget)
        self._sync_body_height()

    def clear_body(self):
        self.body.clear_widgets()
        self._sync_body_height()

    def toggle(self):
        self.set_expanded(not self.expanded)

    def set_expanded(self, expanded: bool):
        self.expanded = expanded
        self.header.set_expanded(expanded)
        self.body_wrapper.opacity = 1 if expanded else 0
        self._sync_body_height()

    def _sync_body_height(self):
        self.body_wrapper.height = self.body.minimum_height if self.expanded else 0


class SectionLabel(MDBoxLayout):
    def __init__(self, text: str, **kwargs):
        super().__init__(**kwargs)
        self.orientation = "horizontal"
        self.adaptive_height = True
        self.padding = (0, dp(8), 0, dp(2))
        self.spacing = dp(8)
        self.add_widget(ThinLine())
        self.add_widget(
            MDLabel(
                text=text.upper(),
                theme_text_color="Custom",
                text_color=MUTED,
                font_style="Caption",
                bold=True,
                halign="center",
                size_hint_x=None,
                width=dp(160),
            )
        )
        self.add_widget(ThinLine())


class ThinLine(Widget):
    def __init__(self, color=DIM, **kwargs):
        super().__init__(**kwargs)
        self.size_hint_y = None
        self.height = dp(1)
        self.bind(pos=self._redraw, size=self._redraw)
        self._color = color

    def _redraw(self, *_):
        self.canvas.clear()
        with self.canvas:
            Color(*with_alpha(self._color, 0.55))
            Line(points=[self.x, self.center_y, self.right, self.center_y], width=1)


class HeaderBlock(MDBoxLayout):
    def __init__(self, title: str, subtitle: str, icon: str | None = None, **kwargs):
        super().__init__(**kwargs)
        self.orientation = "horizontal"
        self.adaptive_height = True
        self.spacing = dp(12)
        self.padding = (0, dp(2), 0, dp(10))
        if icon:
            icon_box = MDCard(
                size_hint=(None, None),
                size=(dp(48), dp(48)),
                radius=[dp(10)],
                elevation=0,
                md_bg_color=with_alpha(BLUE, 0.12),
                line_color=with_alpha(BLUE, 0.35),
            )
            icon_box.add_widget(
                MDIcon(
                    icon=icon,
                    theme_text_color="Custom",
                    text_color=BLUE,
                    halign="center",
                    valign="center",
                    font_size=dp(26),
                )
            )
            self.add_widget(icon_box)

        copy = MDBoxLayout(orientation="vertical", adaptive_height=True, spacing=dp(2))
        copy.add_widget(
            MDLabel(
                text=title,
                theme_text_color="Custom",
                text_color=TEXT,
                font_style="H5",
                bold=True,
                size_hint_y=None,
                height=dp(30),
            )
        )
        copy.add_widget(
            MDLabel(
                text=subtitle,
                theme_text_color="Custom",
                text_color=MUTED,
                font_style="Caption",
                size_hint_y=None,
                height=dp(20),
            )
        )
        self.add_widget(copy)


class NavItem(ButtonBehavior, MDBoxLayout):
    icon = StringProperty("")
    label = StringProperty("")
    screen_name = StringProperty("")
    on_select = ObjectProperty(None, allownone=True)
    active_color = ListProperty(BLUE)

    def __init__(self, screen_name: str, label: str, icon: str, on_select, **kwargs):
        super().__init__(**kwargs)
        self.screen_name = screen_name
        self.on_select = on_select
        self.orientation = "vertical"
        self.padding = (0, 0, 0, 0)
        self.size_hint = (1, None)
        self.height = dp(42)
        self.pos_hint = {"center_y": 0.5}
        self.active = False

        self.surface = MDCard(
            orientation="vertical",
            padding=(dp(4), 0, dp(4), 0),
            radius=[dp(14)],
            elevation=0,
            line_color=with_alpha(BLUE, 0),
            md_bg_color=with_alpha(BLUE, 0),
        )
        self.text_label = MDLabel(
            text=label,
            theme_text_color="Custom",
            text_color=MUTED,
            font_style="Caption",
            bold=False,
            halign="center",
            valign="center",
        )
        self.text_label.bind(size=self._sync_text_size)
        self.surface.add_widget(self.text_label)
        self.add_widget(self.surface)

    def on_release(self):
        if self.on_select:
            self.on_select(self.screen_name, self.text_label.text)

    def on_touch_down(self, touch):
        if self.collide_point(*touch.pos):
            touch.grab(self)
            return True
        return super().on_touch_down(touch)

    def on_touch_up(self, touch):
        if touch.grab_current is self:
            touch.ungrab(self)
            if self.collide_point(*touch.pos):
                self.on_release()
            return True
        return super().on_touch_up(touch)

    def set_active(self, active: bool):
        self.active = active
        self.text_label.text_color = TEXT if active else MUTED
        self.text_label.bold = active
        self.surface.md_bg_color = with_alpha(BLUE, 0.9 if active else 0)
        self.surface.line_color = with_alpha(BLUE, 0.95 if active else 0.18)

    @staticmethod
    def _sync_text_size(label, size):
        label.text_size = size


class MiniTrend(GlowCard):
    def __init__(self, title: str, value: str, unit: str, points, color=BLUE, **kwargs):
        super().__init__(accent=color, **kwargs)
        self.size_hint_y = None
        self.height = dp(112)
        header = MDBoxLayout(adaptive_height=True)
        header.add_widget(
            MDLabel(
                text=title,
                theme_text_color="Custom",
                text_color=TEXT,
                font_style="Subtitle2",
                bold=True,
            )
        )
        header.add_widget(
            MDLabel(
                text=f"{value} {unit}",
                theme_text_color="Custom",
                text_color=TEXT,
                font_style="Subtitle2",
                bold=True,
                halign="right",
            )
        )
        self.add_widget(header)
        self.add_widget(SparkLine(points=points, color=color))


class SparkLine(Widget):
    def __init__(self, points, color=BLUE, **kwargs):
        super().__init__(**kwargs)
        self.points = points or [0, 0, 0]
        self.color = color
        self.bind(pos=self._redraw, size=self._redraw)

    def _redraw(self, *_):
        self.canvas.clear()
        values = [float(point or 0) for point in self.points]
        low = min(values)
        high = max(values)
        span = high - low or 1
        step = self.width / max(1, len(values) - 1)
        coords = []
        for index, value in enumerate(values):
            x = self.x + index * step
            y = self.y + dp(10) + ((value - low) / span) * max(1, self.height - dp(20))
            coords.extend([x, y])
        with self.canvas:
            Color(*with_alpha(self.color, 0.18))
            RoundedRectangle(pos=self.pos, size=self.size, radius=[dp(8)])
            Color(*self.color)
            Line(points=coords, width=1.4)
            for index in range(0, len(coords), 2):
                Line(circle=(coords[index], coords[index + 1], dp(2.2)), width=1)
