import hashlib
import tempfile
from pathlib import Path

from kivy.graphics import Color, Line, PopMatrix, PushMatrix, RoundedRectangle, Scale, Translate
from kivy.graphics.svg import Svg
from kivy.metrics import dp, sp
from kivy.properties import BooleanProperty, ListProperty, ObjectProperty, StringProperty
from kivy.uix.anchorlayout import AnchorLayout
from kivy.uix.behaviors import ButtonBehavior
from kivy.uix.widget import Widget
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.card import MDCard
from kivymd.uix.label import MDIcon, MDLabel

from app.core.icons import icon_path
from app.core.theme import BLUE, BORDER, DIM, MUTED, PANEL_BG, TEXT, with_alpha


class SvgIcon(Widget):
    icon_name = StringProperty("")
    icon_color = ListProperty(TEXT)
    _svg_cache: dict[tuple[str, str], str] = {}

    def __init__(self, icon_name: str = "", icon_color=TEXT, **kwargs):
        super().__init__(**kwargs)
        self.icon_name = icon_name
        self.icon_color = icon_color
        self.size_hint = kwargs.get("size_hint", (None, None))
        if "size" not in kwargs:
            self.size = (dp(20), dp(20))
        self.bind(pos=self._redraw, size=self._redraw, icon_name=self._redraw, icon_color=self._redraw)

    def _redraw(self, *_):
        self.canvas.clear()
        source = icon_path(self.icon_name)
        if not source or not source.exists():
            return

        svg = Svg(source=self._resolved_svg_source(source))
        intrinsic_width = svg.width or 256
        intrinsic_height = svg.height or 256
        scale = min(self.width / intrinsic_width, self.height / intrinsic_height)
        draw_width = intrinsic_width * scale
        draw_height = intrinsic_height * scale
        offset_x = self.x + (self.width - draw_width) / 2
        offset_y = self.y + (self.height - draw_height) / 2

        with self.canvas:
            PushMatrix()
            Translate(offset_x, offset_y, 0)
            Scale(scale, scale, 1)
            self.canvas.add(svg)
            PopMatrix()

    def _resolved_svg_source(self, source: Path) -> str:
        color_hex = self._color_to_hex(self.icon_color)
        cache_key = (str(source.resolve()), color_hex)
        cached = self._svg_cache.get(cache_key)
        if cached and Path(cached).exists():
            return cached

        svg_markup = source.read_text(encoding="utf-8")
        themed_markup = self._theme_svg_markup(svg_markup, color_hex)
        cache_dir = Path(tempfile.gettempdir()) / "obd2_svg_cache"
        cache_dir.mkdir(parents=True, exist_ok=True)
        cache_name = hashlib.sha1(f"{source.resolve()}:{color_hex}".encode("utf-8")).hexdigest()
        themed_path = cache_dir / f"{source.stem}_{cache_name}.svg"
        if not themed_path.exists():
            themed_path.write_text(themed_markup, encoding="utf-8")
        themed_source = str(themed_path)
        self._svg_cache[cache_key] = themed_source
        return themed_source

    @staticmethod
    def _color_to_hex(color) -> str:
        red, green, blue = (max(0, min(255, round(float(channel) * 255))) for channel in color[:3])
        return f"#{red:02X}{green:02X}{blue:02X}"

    @staticmethod
    def _theme_svg_markup(svg_markup: str, color_hex: str) -> str:
        themed_markup = svg_markup.replace("currentColor", color_hex).replace("currentcolor", color_hex)
        black_tokens = (
            '"#000"',
            '"#000000"',
            "'#000'",
            "'#000000'",
            '"black"',
            "'black'",
            '"rgb(0,0,0)"',
            "'rgb(0,0,0)'",
        )
        for token in black_tokens:
            themed_markup = themed_markup.replace(f"fill={token}", f'fill="{color_hex}"')
            themed_markup = themed_markup.replace(f"stroke={token}", f'stroke="{color_hex}"')
        return themed_markup


class IconButton(MDCard):
    disabled = BooleanProperty(False)

    def __init__(
        self,
        text: str,
        icon_name: str = "",
        text_color=TEXT,
        icon_color=TEXT,
        fill_color=None,
        line_color=None,
        **kwargs,
    ):
        self.on_release_callback = kwargs.pop("on_release", None)
        super().__init__(**kwargs)
        self.orientation = "vertical"
        self.padding = 0
        self.radius = [dp(18)]
        self.elevation = 0
        self.size_hint = (1, None)
        self.height = dp(48)
        self.md_bg_color = fill_color or with_alpha(BLUE, 0.85)
        self.line_color = line_color or with_alpha(BLUE, 0)

        self.content = MDBoxLayout(
            orientation="horizontal",
            size_hint=(None, None),
            adaptive_height=True,
            spacing=dp(10),
            pos_hint={"center_x": 0.5, "center_y": 0.5},
        )
        self.content.bind(minimum_width=self._sync_content_width)

        self.icon_widget = SvgIcon(
            icon_name=icon_name,
            icon_color=icon_color,
            size_hint=(None, None),
            size=(dp(22), dp(22)),
        )
        self.label = MDLabel(
            text=text.strip(),
            theme_text_color="Custom",
            text_color=text_color,
            font_style="Button",
            bold=True,
            size_hint=(None, None),
            halign="center",
            valign="middle",
            shorten=True,
            shorten_from="right",
        )
        self.label.bind(texture_size=self._sync_label_size)
        self._rebuild_content(icon_name)
        self.add_widget(self.content)

    def set_button(self, text: str, icon_name: str = "", text_color=TEXT, icon_color=TEXT, fill_color=None, line_color=None):
        self.label.text = text.strip()
        self.label.text_color = text_color
        self.icon_widget.icon_name = icon_name
        self.icon_widget.icon_color = icon_color
        self._rebuild_content(icon_name)
        if fill_color is not None:
            self.md_bg_color = fill_color
        if line_color is not None:
            self.line_color = line_color

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
            if not self.disabled and self.collide_point(*touch.pos) and self.on_release_callback:
                self.on_release_callback(self)
            return True
        return super().on_touch_up(touch)

    def _rebuild_content(self, icon_name: str):
        self.content.clear_widgets()
        if icon_name:
            self.content.add_widget(self.icon_widget)
        self.content.add_widget(self.label)

    @staticmethod
    def _sync_content_width(widget, width):
        widget.width = width

    @staticmethod
    def _sync_label_size(label, _texture_size):
        label.text_size = (None, None)
        label.width = max(dp(1), label.texture_size[0])
        label.height = max(dp(1), label.texture_size[1])


class IconBadge(MDCard):
    def __init__(
        self,
        icon_name: str,
        icon_color=BLUE,
        icon_size=None,
        outline_color=None,
        background_color=None,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self._outline_color = outline_color
        self.size_hint = (None, None)
        self.size = (dp(48), dp(48))
        self.radius = [dp(24)]
        self.elevation = 0
        self.md_bg_color = background_color or (0, 0, 0, 0)
        self.line_color = outline_color or with_alpha(icon_color, 0.28)
        anchor = AnchorLayout(anchor_x="center", anchor_y="center")
        self.icon = SvgIcon(
            icon_name=icon_name,
            icon_color=icon_color,
            size_hint=(None, None),
            size=icon_size or (dp(26), dp(26)),
        )
        anchor.add_widget(self.icon)
        self.add_widget(anchor)

    def set_icon(self, icon_name: str, icon_color):
        self.icon.icon_name = icon_name
        self.icon.icon_color = icon_color
        self.line_color = self._outline_color if self._outline_color is not None else with_alpha(icon_color, 0.28)


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
        self.height = dp(146)
        self.padding = (dp(16), dp(16), dp(16), dp(16))
        self.spacing = dp(12)
        self.radius = [dp(18)]
        self.elevation = 0
        self.md_bg_color = PANEL_BG
        self.line_color = with_alpha(BLUE, 0)

        header = MDBoxLayout(size_hint_y=None, height=dp(26), spacing=dp(8))
        self.icon_label = MDIcon(
            icon=icon,
            theme_text_color="Custom",
            text_color=accent,
            font_size=dp(22),
            size_hint=(None, None),
            size=(dp(22), dp(22)),
            halign="center",
            valign="middle",
        )
        self.icon_label.bind(size=self._sync_icon_size)
        self.title_label = MDLabel(
            text=title,
            theme_text_color="Custom",
            text_color=with_alpha(TEXT, 0.9),
            font_style="Subtitle2",
            font_size=sp(14),
            bold=True,
            halign="left",
            valign="middle",
        )
        self.title_label.bind(width=self._sync_wrapped_text)
        header.add_widget(self.icon_label)
        header.add_widget(self.title_label)

        value_block = MDBoxLayout(size_hint_y=None, height=dp(34), spacing=dp(6))
        self.value_label = MDLabel(
            text=value,
            theme_text_color="Custom",
            text_color=TEXT,
            font_style="H4",
            font_size=sp(27),
            bold=True,
            halign="left",
            valign="middle",
        )
        self.value_label.bind(size=lambda label, size: setattr(label, "text_size", size))
        self.unit_label = MDLabel(
            text=unit,
            theme_text_color="Custom",
            text_color=with_alpha(TEXT, 0.62),
            font_style="Subtitle2",
            font_size=sp(13),
            bold=True,
            halign="left",
            valign="middle",
            size_hint_x=None,
            width=dp(52),
        )
        self.unit_label.bind(size=lambda label, size: setattr(label, "text_size", size))
        value_block.add_widget(self.value_label)
        value_block.add_widget(self.unit_label)

        footer = MDBoxLayout(size_hint_y=None, height=dp(18), spacing=dp(8))
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
        )
        self.status_label.bind(width=self._sync_wrapped_text)
        footer.add_widget(self.status_dot)
        footer.add_widget(self.status_label)

        self.add_widget(header)
        self.add_widget(value_block)
        self.add_widget(footer)
        self.set_data(value, unit, status)

    def set_data(self, value: str, unit: str = "", status: str = "En attente", accent=None):
        value_text = str(value)
        self.value_label.text = value_text
        self.value_label.font_style = "H5" if len(value_text) > 7 else "H4"
        self.value_label.font_size = sp(24) if len(value_text) > 7 else sp(27)
        self.unit_label.text = unit
        self.status_label.text = status
        self._apply_accent(accent or self.accent, status)

    def _apply_accent(self, accent, status=""):
        self.accent = accent
        self.icon_label.text_color = accent
        self.status_dot.text_color = accent
        normalized_status = str(status or "").strip().lower()
        if normalized_status in {"attention", "critique"}:
            self.line_color = with_alpha(accent, 0.22)
        else:
            self.line_color = with_alpha(BLUE, 0)

    @staticmethod
    def _sync_wrapped_text(label, width):
        label.text_size = (width, None)

    @staticmethod
    def _sync_icon_size(icon, size):
        icon.text_size = size


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
        self.anchor = AnchorLayout(anchor_x="center", anchor_y="center")
        self.label = MDLabel(
            text=text.upper(),
            theme_text_color="Custom",
            text_color=color,
            font_style="Caption",
            bold=True,
            halign="center",
            valign="middle",
            size_hint=(None, None),
            shorten=True,
            shorten_from="right",
        )
        self.label.bind(texture_size=self._sync_size)
        self.anchor.add_widget(self.label)
        self.add_widget(self.anchor)
        self._sync_size(self.label, self.label.texture_size)

    def set_badge(self, text: str, color=BLUE):
        self.label.text = text.upper()
        self.label.text_color = color
        self.md_bg_color = with_alpha(color, 0.16)
        self.line_color = with_alpha(color, 0.55)
        self._sync_size(self.label, self.label.texture_size)

    def _sync_size(self, _label, texture_size):
        self.label.text_size = (None, None)
        text_width = max(dp(42), texture_size[0])
        text_height = max(dp(14), texture_size[1])
        self.label.width = text_width
        self.label.height = text_height
        self.width = text_width + dp(22)


class SectionLabel(MDBoxLayout):
    def __init__(self, text: str, **kwargs):
        super().__init__(**kwargs)
        self.orientation = "horizontal"
        self.adaptive_height = True
        self.padding = (0, dp(8), 0, dp(2))
        self.spacing = dp(8)
        self.add_widget(_ThinLine())
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
        self.add_widget(_ThinLine())


class _ThinLine(Widget):
    def __init__(self, color=DIM, **kwargs):
        super().__init__(**kwargs)
        self.size_hint_y = None
        self.height = dp(1)
        self._color = color
        self.bind(pos=self._redraw, size=self._redraw)

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
                SvgIcon(
                    icon_name=icon,
                    icon_color=BLUE,
                    size=(dp(24), dp(24)),
                    pos_hint={"center_x": 0.5, "center_y": 0.5},
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
        self.height = dp(46) if active else dp(42)
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
        self.add_widget(_SparkLine(points=points, color=color))


class _SparkLine(Widget):
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
