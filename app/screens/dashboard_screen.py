import re
from threading import Thread

from kivy.animation import Animation
from kivy.clock import Clock
from kivy.metrics import dp, sp
from kivy.properties import BooleanProperty
from kivy.uix.anchorlayout import AnchorLayout
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.card import MDCard
from kivymd.uix.gridlayout import MDGridLayout
from kivymd.uix.label import MDIcon, MDLabel
from kivymd.uix.spinner import MDSpinner

from app.core.elm_pid_registry import ELM_EMULATOR_PIDS
from app.core.measurement_mapper import measurement_from_readings
from app.core.theme import AMBER, BLUE, GREEN, MUTED, RED, TEXT, status_color, with_alpha
from app.screens.base_screen import BaseScreen
from app.widgets.ui_components import Badge, GlowCard, MetricCard, SectionLabel


PRIMARY_METRIC_KEYS = ("rpm", "speed", "coolant_temp", "hybrid_soc")

COMPACT_SECTIONS = (
    ("MOTEUR", ("engine_load", "intake_pressure", "intake_temp", "maf", "throttle_pos", "module_voltage")),
    ("HYBRIDE", ("hybrid_current", "mg1_temp", "mg2_temp", "mg1_torque", "mg2_torque")),
    ("VEHICULE", ("odometer", "fuel_level", "vin")),
    ("CONFORT / ENVIRONNEMENT", ("ambient_temp",)),
)


class DashboardIconButton(MDCard):
    disabled = BooleanProperty(False)

    def __init__(self, text: str, icon: str = "", fill_color=None, line_color=None, on_release=None, **kwargs):
        super().__init__(**kwargs)
        self.on_release_callback = on_release
        self.loading = False
        self.orientation = "vertical"
        self.padding = (dp(14), 0, dp(14), 0)
        self.radius = [dp(14)]
        self.elevation = 0
        self.size_hint = (None, None)
        self.width = dp(160)
        self.height = dp(44)
        self.md_bg_color = fill_color or (0.247, 0.494, 0.91, 1)
        self.line_color = line_color or with_alpha(BLUE, 0)

        self.content_anchor = AnchorLayout(anchor_x="center", anchor_y="center")
        self.content = MDBoxLayout(
            orientation="horizontal",
            size_hint=(None, None),
            adaptive_height=True,
            spacing=dp(8),
        )
        self.content.bind(minimum_width=lambda widget, value: setattr(widget, "width", value))

        self.icon_widget = MDIcon(
            icon=icon,
            theme_text_color="Custom",
            text_color=TEXT,
            font_size=dp(22),
            size_hint=(None, None),
            size=(dp(22), dp(22)),
            halign="center",
            valign="middle",
        )
        self.icon_widget.bind(size=self._sync_text_size)
        self.spinner = MDSpinner(
            size_hint=(None, None),
            size=(dp(16), dp(16)),
            line_width=dp(2),
            active=False,
            palette=[TEXT],
        )

        self.label = MDLabel(
            text=text,
            theme_text_color="Custom",
            text_color=TEXT,
            font_style="Button",
            font_size=sp(14),
            bold=True,
            size_hint=(None, None),
            halign="center",
            valign="middle",
        )
        self.label.bind(texture_size=self._sync_label_size)

        if icon:
            self.content.add_widget(self.icon_widget)
        self.content.add_widget(self.label)
        self.content_anchor.add_widget(self.content)
        self.add_widget(self.content_anchor)

    def set_button(self, text: str, icon: str = "", fill_color=None, line_color=None, font_size=None):
        self.label.text = text
        self.loading = False
        self.spinner.active = False
        self.icon_widget.icon = icon
        self.label.font_size = font_size or sp(14)
        self.content.clear_widgets()
        if self.loading:
            self.content.add_widget(self.spinner)
        elif icon:
            self.content.add_widget(self.icon_widget)
        self.content.add_widget(self.label)
        if fill_color is not None:
            self.md_bg_color = fill_color
        if line_color is not None:
            self.line_color = line_color

    def set_loading(self, text: str, fill_color=None, line_color=None, font_size=None):
        self.label.text = text
        self.loading = True
        self.spinner.active = True
        self.label.font_size = font_size or sp(13)
        self.content.clear_widgets()
        self.content.add_widget(self.spinner)
        self.content.add_widget(self.label)
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

    @staticmethod
    def _sync_text_size(widget, size):
        widget.text_size = size

    @staticmethod
    def _sync_label_size(label, _texture_size):
        label.text_size = (None, None)
        label.width = max(dp(1), label.texture_size[0])
        label.height = max(dp(1), label.texture_size[1])


class DashboardCollapsibleSection(MDCard):
    def __init__(self, title: str, on_toggle=None, **kwargs):
        super().__init__(**kwargs)
        self.on_toggle = on_toggle
        self.expanded = False
        self._animation = None
        self.orientation = "vertical"
        self.size_hint_y = None
        self.adaptive_height = True
        self.padding = (dp(14), dp(12), dp(14), dp(12))
        self.spacing = 0
        self.radius = [dp(18)]
        self.elevation = 0
        self.md_bg_color = with_alpha(BLUE, 0.03)
        self.line_color = with_alpha(BLUE, 0.18)

        self.header = MDCard(
            orientation="horizontal",
            size_hint_y=None,
            height=dp(32),
            padding=(0, 0, 0, 0),
            radius=[0],
            elevation=0,
            md_bg_color=(0, 0, 0, 0),
            line_color=(0, 0, 0, 0),
        )
        self.title_label = MDLabel(
            text=title,
            theme_text_color="Custom",
            text_color=TEXT,
            font_style="Subtitle2",
            bold=True,
            halign="left",
            valign="middle",
        )
        self.title_label.bind(size=lambda label, size: setattr(label, "text_size", size))
        self.chevron = MDIcon(
            icon="chevron-down",
            theme_text_color="Custom",
            text_color=BLUE,
            font_size=dp(22),
            size_hint=(None, None),
            size=(dp(22), dp(22)),
            halign="center",
            valign="middle",
        )
        self.chevron.bind(size=lambda widget, size: setattr(widget, "text_size", size))
        self.header.add_widget(self.title_label)
        self.header.add_widget(self.chevron)

        self.body = MDBoxLayout(
            orientation="vertical",
            adaptive_height=True,
            spacing=dp(12),
            opacity=0,
        )
        self.body.bind(minimum_height=self._sync_body_height)
        self.body_wrapper = MDBoxLayout(
            orientation="vertical",
            size_hint_y=None,
            height=0,
            padding=(0, dp(12), 0, 0),
        )
        self.body_wrapper.add_widget(self.body)

        self.add_widget(self.header)
        self.add_widget(self.body_wrapper)
        self.bind(minimum_height=self.setter("height"))
        self._apply_state(animated=False)

    def add_body_widget(self, widget):
        self.body.add_widget(widget)
        self._sync_body_height()

    def on_touch_down(self, touch):
        if self.header.collide_point(*touch.pos):
            touch.grab(self)
            return True
        return super().on_touch_down(touch)

    def on_touch_up(self, touch):
        if touch.grab_current is self:
            touch.ungrab(self)
            if self.header.collide_point(*touch.pos):
                if self.on_toggle:
                    self.on_toggle(self)
                else:
                    self.set_expanded(not self.expanded)
            return True
        return super().on_touch_up(touch)

    def set_expanded(self, expanded: bool, animated=True):
        self.expanded = expanded
        self._apply_state(animated=animated)

    def _apply_state(self, animated=True):
        self.chevron.icon = "chevron-up" if self.expanded else "chevron-down"
        target_height = self.body.minimum_height + dp(12) if self.expanded and self.body.children else 0
        target_opacity = 1 if self.expanded else 0
        Animation.cancel_all(self.body_wrapper)
        Animation.cancel_all(self.body)
        self._animation = None
        if animated:
            self._animation = Animation(height=target_height, d=0.18, t="out_quad")
            self._animation.bind(on_complete=lambda *_: setattr(self, "_animation", None))
            self._animation.start(self.body_wrapper)
            Animation(opacity=target_opacity, d=0.16, t="out_quad").start(self.body)
        else:
            self.body_wrapper.height = target_height
            self.body.opacity = target_opacity

    def _sync_body_height(self, *_):
        if self.expanded and self._animation is None:
            self.body_wrapper.height = self.body.minimum_height + dp(12)


class DashboardSecondaryMetricCard(MDCard):
    def __init__(self, title: str, value: str = "-", unit: str = "", status: str = "En attente", accent=BLUE, **kwargs):
        super().__init__(**kwargs)
        self.accent = accent
        self.orientation = "vertical"
        self.size_hint_y = None
        self.height = dp(105)
        self.padding = (dp(16), dp(16), dp(16), dp(16))
        self.spacing = dp(8)
        self.radius = [dp(18)]
        self.elevation = 0
        self.md_bg_color = with_alpha(BLUE, 0.03)
        self.line_color = with_alpha(BLUE, 0)

        self.title_label = MDLabel(
            text=title,
            theme_text_color="Custom",
            text_color=with_alpha(TEXT, 0.9),
            font_style="Caption",
            font_size=sp(11),
            bold=True,
            halign="left",
            valign="middle",
            size_hint_y=None,
            height=dp(18),
        )
        self.title_label.bind(size=lambda label, size: setattr(label, "text_size", size))

        value_row = MDBoxLayout(size_hint_y=None, height=dp(34), spacing=dp(4))
        self.value_label = MDLabel(
            text=value,
            theme_text_color="Custom",
            text_color=TEXT,
            font_style="H5",
            font_size=sp(22),
            bold=True,
            halign="left",
            valign="middle",
        )
        self.value_label.bind(size=lambda label, size: setattr(label, "text_size", size))
        self.unit_label = MDLabel(
            text=unit,
            theme_text_color="Custom",
            text_color=with_alpha(TEXT, 0.62),
            font_style="Caption",
            bold=True,
            halign="left",
            valign="middle",
            size_hint_x=None,
            width=dp(44),
        )
        self.unit_label.bind(size=lambda label, size: setattr(label, "text_size", size))
        value_row.add_widget(self.value_label)
        value_row.add_widget(self.unit_label)

        footer = MDBoxLayout(size_hint_y=None, height=dp(16), spacing=dp(6))
        self.status_dot = MDLabel(
            text="•",
            theme_text_color="Custom",
            text_color=accent,
            size_hint=(None, None),
            size=(dp(10), dp(16)),
            font_style="Caption",
            bold=True,
            halign="center",
            valign="middle",
        )
        self.status_dot.bind(size=lambda label, size: setattr(label, "text_size", size))
        self.status_label = MDLabel(
            text=status,
            theme_text_color="Custom",
            text_color=with_alpha(TEXT, 0.7),
            font_style="Caption",
            halign="left",
            valign="middle",
        )
        self.status_label.bind(size=lambda label, size: setattr(label, "text_size", size))
        footer.add_widget(self.status_dot)
        footer.add_widget(self.status_label)

        content = MDBoxLayout(orientation="vertical", spacing=dp(8))
        content.add_widget(self.title_label)
        content.add_widget(value_row)
        content.add_widget(footer)
        self.add_widget(content)
        self.set_data(value, unit, status)

    def set_data(self, value: str, unit: str = "", status: str = "En attente", accent=None):
        value_text = str(value)
        self.value_label.text = value_text
        self.value_label.font_style = "Subtitle1" if len(value_text) > 7 else "H5"
        self.value_label.font_size = sp(15) if len(value_text) > 7 else sp(22)
        self.unit_label.text = unit
        self.status_label.text = status
        self._apply_accent(accent or self.accent, status)

    def _apply_accent(self, accent, status=""):
        self.accent = accent
        self.status_dot.text_color = accent
        normalized_status = str(status or "").strip().lower()
        if normalized_status in {"attention", "critique"}:
            self.line_color = with_alpha(accent, 0.18)
        else:
            self.line_color = with_alpha(BLUE, 0)


class DashboardScreen(BaseScreen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.loading = False
        self.cards = {}
        self.secondary_sections = []
        self._scroll_preserve_event = None

        layout = self.build_page()
        self.page_layout = layout
        self.page_scroll = self.children[0]
        layout.add_widget(self._build_header())

        self.status_card = self._build_status_card()
        layout.add_widget(self.status_card)

        layout.add_widget(SectionLabel("Valeurs principales"))
        primary_grid = self._build_metric_grid(spacing=dp(12), responsive=False)
        for key in PRIMARY_METRIC_KEYS:
            pid = self._pid(key)
            if not pid:
                continue
            card = self._build_metric_card(pid)
            self.cards[key] = card
            primary_grid.add_widget(card)
        layout.add_widget(primary_grid)

        layout.add_widget(SectionLabel("Assistant entretien"))
        self.recommendations = GlowCard()
        self.recommendations.size_hint_y = None
        self.recommendations.height = dp(156)
        self.recommendations.radius = [dp(18)]
        self.recommendations.spacing = dp(10)
        self.recommendations.padding = dp(20)
        layout.add_widget(self.recommendations)
        self._render_recommendations([])

        for title, keys in COMPACT_SECTIONS:
            layout.add_widget(self._build_secondary_section(title, keys))

        layout.add_widget(MDLabel(size_hint_y=None, height=dp(88)))

    @staticmethod
    def _build_metric_grid(spacing, responsive=True):
        grid = MDGridLayout(cols=2, spacing=spacing, adaptive_height=True)
        if responsive:
            grid.bind(width=lambda instance, value: setattr(instance, "cols", 1 if value < dp(320) else 2))
        return grid

    def _build_status_card(self):
        card = GlowCard(accent=BLUE)
        card.size_hint_y = None
        card.height = dp(108)
        card.radius = [dp(18)]
        card.padding = (dp(16), dp(12), dp(16), dp(12))
        card.spacing = dp(12)

        self.connection_label = MDLabel(
            text="Hors ligne",
            theme_text_color="Custom",
            text_color=TEXT,
            font_style="Subtitle1",
            bold=True,
            size_hint_y=None,
            height=dp(22),
            halign="left",
            valign="middle",
        )
        self.connection_label.bind(size=lambda label, size: setattr(label, "text_size", size))

        self.address_label = MDLabel(
            text="ELM327 TCP/IP",
            theme_text_color="Custom",
            text_color=with_alpha(TEXT, 0.82),
            font_style="Caption",
            bold=True,
            size_hint_y=None,
            height=dp(18),
            halign="left",
            valign="middle",
        )
        self.address_label.bind(size=lambda label, size: setattr(label, "text_size", size))

        self.message = MDLabel(
            text="Aucune donnee ECU disponible",
            theme_text_color="Custom",
            text_color=MUTED,
            font_style="Caption",
            size_hint_y=None,
            height=dp(34),
            halign="left",
            valign="top",
        )
        self.message.bind(size=lambda label, size: setattr(label, "text_size", size))

        self.status_content = MDBoxLayout(
            orientation="horizontal",
            spacing=dp(12),
            adaptive_height=True,
        )
        copy = MDBoxLayout(orientation="vertical", spacing=0)
        copy.add_widget(self.connection_label)
        copy.add_widget(self.address_label)
        copy.add_widget(self.message)

        self.refresh_button = DashboardIconButton(
            text="Actualiser",
            icon="",
            fill_color=(0.247, 0.494, 0.91, 1),
            on_release=lambda *_: self.refresh(),
            line_color=with_alpha(BLUE, 0),
        )
        self.refresh_button.width = dp(160)
        self.refresh_button.height = dp(44)
        self.refresh_button.radius = [dp(14)]

        self.status_actions = AnchorLayout(
            anchor_x="right",
            anchor_y="center",
            size_hint_x=None,
            width=dp(160),
            size_hint_y=None,
            height=dp(44),
        )
        self.status_actions.add_widget(self.refresh_button)

        self.status_content.add_widget(copy)
        self.status_content.add_widget(self.status_actions)

        card.add_widget(self.status_content)
        card.bind(width=self._update_status_card_layout)
        Clock.schedule_once(lambda *_: self._update_status_card_layout(card, card.width), 0)
        return card

    def _build_secondary_section(self, title, keys):
        section = DashboardCollapsibleSection(
            self._section_title(title),
            on_toggle=self._toggle_secondary_section,
        )
        self.secondary_sections.append(section)
        if title == "VEHICULE":
            vehicle_grid = self._build_metric_grid(spacing=dp(12), responsive=False)
            for key in ("odometer", "fuel_level", "vin"):
                pid = self._pid(key)
                if not pid:
                    continue
                card = self._build_secondary_metric_card(pid)
                self.cards[key] = card
                vehicle_grid.add_widget(card)
            section.add_body_widget(vehicle_grid)
            return section

        grid = self._build_metric_grid(spacing=dp(12), responsive=False)
        for key in keys:
            pid = self._pid(key)
            if not pid:
                continue
            card = self._build_secondary_metric_card(pid)
            self.cards[key] = card
            grid.add_widget(card)
        section.add_body_widget(grid)
        return section

    def _toggle_secondary_section(self, target_section):
        scroll_offset = self._current_scroll_offset()
        target_expanded = not target_section.expanded

        for section in self.secondary_sections:
            section.set_expanded(section is target_section and target_expanded, animated=True)

        if self._scroll_preserve_event is not None:
            self._scroll_preserve_event.cancel()
        self._scroll_preserve_event = Clock.schedule_interval(
            lambda _dt: self._restore_scroll_offset(scroll_offset),
            1 / 60,
        )
        Clock.schedule_once(lambda *_: self._stop_scroll_preserve(scroll_offset), 0.2)

    def _current_scroll_offset(self):
        if not self.page_scroll or not self.page_layout:
            return 0
        scrollable_height = max(0, self.page_layout.height - self.page_scroll.height)
        if scrollable_height <= 0:
            return 0
        return (1 - self.page_scroll.scroll_y) * scrollable_height

    def _restore_scroll_offset(self, scroll_offset):
        if not self.page_scroll or not self.page_layout:
            return False
        scrollable_height = max(0, self.page_layout.height - self.page_scroll.height)
        if scrollable_height <= 0:
            self.page_scroll.scroll_y = 1
            return False

        self.page_scroll.scroll_y = max(0, min(1, 1 - (scroll_offset / scrollable_height)))
        return True

    def _stop_scroll_preserve(self, scroll_offset):
        if self._scroll_preserve_event is not None:
            self._scroll_preserve_event.cancel()
            self._scroll_preserve_event = None
        self._restore_scroll_offset(scroll_offset)

    def refresh(self):
        if self.loading:
            return

        service = self.app.obd_service
        self._update_connection_status()
        if not service.is_connected():
            self.message.text = "Aucune donnee ECU disponible"
            self.address_label.text = "ELM327 TCP/IP"
            for card in self.cards.values():
                card.set_data("-", "", "Hors ligne")
            self._render_recommendations([])
            return

        self.loading = True
        self.refresh_button.disabled = True
        self.refresh_button.set_loading(
            text="Actualisation...",
            fill_color=(0.247, 0.494, 0.91, 1),
            line_color=with_alpha(BLUE, 0),
            font_size=sp(13),
        )
        self.message.text = "Lecture ECU en cours..."
        Thread(target=self._read_worker, daemon=True).start()

    def _read_worker(self):
        try:
            readings = self.app.obd_service.read_live_data()
        except Exception as exc:
            Clock.schedule_once(lambda *_, error=exc: self._finish_read([], [], error), 0)
            return

        try:
            codes = self.app.obd_service.read_error_codes()
        except Exception as exc:
            Clock.schedule_once(lambda *_, error=exc: self._finish_read(readings, [], error), 0)
            return

        Clock.schedule_once(lambda *_: self._finish_read(readings, codes, None), 0)

    def _finish_read(self, readings, codes, error):
        self.loading = False
        self.refresh_button.disabled = False
        self.refresh_button.set_button(
            text="Actualiser",
            icon="",
            fill_color=(0.247, 0.494, 0.91, 1),
            line_color=with_alpha(BLUE, 0),
            font_size=sp(14),
        )
        self._update_connection_status()
        if error is not None and not readings:
            self.message.text = "Lecture ECU impossible"
            return

        self.app.database.save_measurement(measurement_from_readings(readings))
        available = sum(1 for reading in readings if reading.available)
        service = self.app.obd_service
        self.message.text = (
            f"{service.current_host}:{service.current_port}\n"
            f"{available}/{len(readings)} donnees ECU disponibles"
        )

        for reading in readings:
            card = self.cards.get(reading.key)
            if not card:
                continue
            status = self._status_for_reading(reading)
            card.set_data(reading.value, reading.unit, status)

        diagnostics = self.app.diagnostic_service.analyze(readings, codes)
        self._render_recommendations(diagnostics)

    def _update_connection_status(self):
        service = self.app.obd_service
        if service.is_connected():
            self.connection_label.text = "Connecte"
            self.address_label.text = "ELM327 TCP/IP"
            self.connection_label.text_color = TEXT
        else:
            self.connection_label.text = "Hors ligne"
            self.address_label.text = "ELM327 TCP/IP"
            self.connection_label.text_color = TEXT

    def _update_status_card_layout(self, card, width):
        compact = width < dp(320)
        self.status_content.orientation = "vertical" if compact else "horizontal"
        self.status_actions.anchor_x = "center" if compact else "right"
        self.status_actions.size_hint_x = 1 if compact else None
        self.status_actions.width = 0 if compact else dp(160)
        self.refresh_button.size_hint_x = 1 if compact else None
        self.refresh_button.width = 0 if compact else dp(160)
        card.height = dp(136) if compact else dp(108)

    def _render_recommendations(self, diagnostics):
        self.recommendations.clear_widgets()
        dtc_result = next((item for item in diagnostics if self._is_dtc_recommendation(item.title)), None)
        visible_diagnostics = [item for item in diagnostics if not self._is_dtc_recommendation(item.title)]
        primary_result = visible_diagnostics[0] if visible_diagnostics else None

        if dtc_result is not None and primary_result is not None:
            self.recommendations.height = dp(238)
            self.recommendations.add_widget(self._recommendation_compact_card(dtc_result, primary_result))
            return

        if dtc_result is not None:
            self.recommendations.height = dp(152)
            self.recommendations.add_widget(self._recommendation_compact_card(dtc_result, None))
            return

        if primary_result is not None:
            self.recommendations.height = dp(160)
            self.recommendations.add_widget(self._recommendation_compact_card(None, primary_result))
            return

        self.recommendations.height = dp(160)
        self.recommendations.add_widget(
            self._recommendation_compact_card(
                None,
                None,
                title="Systeme en attente",
                detail="Lance une lecture pour afficher les recommandations.",
                severity="warning",
            )
        )

    @staticmethod
    def _is_dtc_recommendation(title):
        normalized = str(title or "").strip().lower()
        return normalized.startswith("code dtc")

    def _recommendation_compact_card(self, dtc_result=None, primary_result=None, title="", detail="", severity="warning"):
        active_severity = (
            dtc_result.severity if dtc_result is not None else
            primary_result.severity if primary_result is not None else
            severity
        )
        color = status_color(active_severity)
        wrapper = MDBoxLayout(
            orientation="vertical",
            adaptive_height=True,
            spacing=dp(16),
        )

        badge = self._recommendation_status_badge(self._severity_badge_label(active_severity), color)
        badge_row = MDBoxLayout(size_hint_y=None, height=dp(28))
        badge_row.add_widget(badge)
        badge_row.add_widget(MDBoxLayout())
        wrapper.add_widget(badge_row)

        if dtc_result is not None:
            dtc_headline_row = MDBoxLayout(size_hint_y=None, height=dp(28), spacing=dp(12))
            dtc_icon = MDIcon(
                icon="alert-outline",
                theme_text_color="Custom",
                text_color=color,
                font_size=dp(22),
                size_hint=(None, None),
                size=(dp(22), dp(22)),
                halign="center",
                valign="middle",
            )
            dtc_icon.bind(size=lambda widget, size: setattr(widget, "text_size", size))
            dtc_headline_row.add_widget(dtc_icon)

            dtc_label = MDLabel(
                text=self._dtc_count_headline(dtc_result.message),
                theme_text_color="Custom",
                text_color=TEXT,
                font_style="Subtitle1",
                font_size=sp(18),
                bold=True,
                halign="left",
                valign="middle",
                size_hint_y=None,
                height=dp(28),
            )
            dtc_label.bind(size=lambda label, size: setattr(label, "text_size", size))
            dtc_headline_row.add_widget(dtc_label)
            wrapper.add_widget(dtc_headline_row)

            dtc_detail_row = MDBoxLayout(size_hint_y=None, height=dp(16), spacing=dp(8))
            dtc_detail_row.add_widget(MDBoxLayout(size_hint=(None, 1), width=dp(22)))
            dtc_detail = MDLabel(
                text="Consultez l'onglet Diagnostic pour plus de détails.",
                theme_text_color="Custom",
                text_color=with_alpha(MUTED, 0.92),
                font_style="Body2",
                font_size=sp(13),
                size_hint_y=None,
                height=dp(16),
                halign="left",
                valign="middle",
                shorten=True,
                shorten_from="right",
            )
            dtc_detail.bind(size=lambda label, size: setattr(label, "text_size", size))
            dtc_detail_row.add_widget(dtc_detail)
            wrapper.add_widget(dtc_detail_row)
            wrapper.add_widget(self._recommendation_separator())

        if primary_result is not None:
            recommendation_row = MDBoxLayout(size_hint_y=None, height=dp(24), spacing=dp(10))
            recommendation_icon = MDIcon(
                icon="wrench-outline",
                theme_text_color="Custom",
                text_color=AMBER,
                font_size=dp(18),
                size_hint=(None, None),
                size=(dp(18), dp(18)),
                halign="center",
                valign="middle",
            )
            recommendation_icon.bind(size=lambda widget, size: setattr(widget, "text_size", size))
            recommendation_row.add_widget(recommendation_icon)
            recommendation_title = MDLabel(
                text=f"Recommandation : {primary_result.title}",
                theme_text_color="Custom",
                text_color=AMBER,
                font_style="Subtitle2",
                font_size=sp(16),
                bold=True,
                size_hint_y=None,
                height=dp(24),
                halign="left",
                valign="middle",
                shorten=True,
                shorten_from="right",
            )
            recommendation_title.bind(size=lambda label, size: setattr(label, "text_size", size))
            recommendation_row.add_widget(recommendation_title)
            wrapper.add_widget(recommendation_row)
            detail_text = self._recommendation_message(primary_result.title, primary_result.message)
        else:
            detail_text = detail

        if detail_text:
            wrapper.add_widget(self._recommendation_metrics_row(detail_text))

        return wrapper

    @staticmethod
    def _severity_badge_label(severity):
        return {"normal": "normal", "warning": "alerte", "critical": "critique"}.get(severity, severity)

    @staticmethod
    def _dtc_count_headline(message):
        match = re.search(r"(\d+)", str(message or ""))
        count = match.group(1) if match else "0"
        return f"{count} codes DTC actifs"

    @staticmethod
    def _recommendation_message(title, message):
        normalized_title = str(title or "").strip().lower()
        normalized_message = str(message or "").strip()
        if normalized_title == "ralenti moteur irregulier":
            rpm_match = re.search(r"(\d+)\s*tr/min", normalized_message)
            load_match = re.search(r"(\d+)\s*%", normalized_message)
            rpm_value = rpm_match.group(1) if rpm_match else "-"
            load_value = load_match.group(1) if load_match else "-"
            return f"{rpm_value}|{load_value}"
        return normalized_message

    @staticmethod
    def _recommendation_badge(text, color):
        badge = MDCard(
            orientation="horizontal",
            size_hint=(None, None),
            height=dp(28),
            radius=[dp(14)],
            elevation=0,
            md_bg_color=with_alpha(color, 0.12),
            line_color=with_alpha(color, 0.65),
            padding=(dp(12), 0, dp(14), 0),
            spacing=dp(8),
        )
        dot = MDLabel(
            text="●",
            theme_text_color="Custom",
            text_color=color,
            font_size=sp(10),
            size_hint=(None, None),
            size=(dp(12), dp(12)),
            halign="center",
            valign="middle",
        )
        dot.bind(size=lambda label, size: setattr(label, "text_size", size))
        label = MDLabel(
            text=text.upper(),
            theme_text_color="Custom",
            text_color=color,
            font_style="Caption",
            bold=True,
            size_hint=(None, None),
            halign="left",
            valign="middle",
        )
        label.bind(texture_size=lambda widget, texture_size: setattr(widget, "size", texture_size))
        label.bind(texture_size=lambda widget, texture_size: setattr(badge, "width", texture_size[0] + dp(42)))
        badge.add_widget(dot)
        badge.add_widget(label)
        badge.width = dp(112)
        return badge

    @staticmethod
    def _recommendation_status_badge(text, color):
        badge = MDCard(
            orientation="horizontal",
            size_hint=(None, None),
            height=dp(28),
            radius=[dp(14)],
            elevation=0,
            md_bg_color=with_alpha(color, 0.12),
            line_color=with_alpha(color, 0.65),
            padding=(dp(14), 0, dp(14), 0),
            spacing=dp(8),
        )
        dot = MDCard(
            size_hint=(None, None),
            size=(dp(9), dp(9)),
            radius=[dp(5)],
            elevation=0,
            md_bg_color=color,
            line_color=with_alpha(color, 0),
            pos_hint={"center_y": 0.5},
        )
        label = MDLabel(
            text=text.upper(),
            theme_text_color="Custom",
            text_color=color,
            font_style="Caption",
            font_size=sp(12.5),
            bold=True,
            size_hint=(None, None),
            halign="left",
            valign="middle",
            height=dp(28),
        )
        label.bind(
            texture_size=lambda widget, texture_size: setattr(widget, "size", (texture_size[0], dp(28)))
        )
        label.bind(size=lambda widget, size: setattr(widget, "text_size", size))
        label.bind(texture_size=lambda widget, texture_size: setattr(badge, "width", texture_size[0] + dp(52)))
        badge.add_widget(dot)
        badge.add_widget(label)
        badge.width = dp(126)
        return badge

    @staticmethod
    def _recommendation_separator():
        return MDCard(
            orientation="vertical",
            size_hint_y=None,
            height=dp(1),
            md_bg_color=with_alpha(BLUE, 0.14),
            line_color=with_alpha(BLUE, 0),
            elevation=0,
        )

    def _recommendation_metrics_row(self, detail_text):
        rpm_value, load_value = (detail_text.split("|", 1) + ["-"])[:2]
        row = MDBoxLayout(size_hint_y=None, height=dp(32), spacing=dp(12))

        rpm_group = MDBoxLayout(size_hint=(0.5, 1), spacing=dp(8))
        rpm_icon = MDIcon(
            icon="flag-checkered",
            theme_text_color="Custom",
            text_color=BLUE,
            font_size=dp(18),
            size_hint=(None, None),
            size=(dp(18), dp(18)),
            halign="center",
            valign="middle",
        )
        rpm_icon.bind(size=lambda widget, size: setattr(widget, "text_size", size))
        rpm_group.add_widget(rpm_icon)
        rpm_label = MDLabel(
            text=f"[color=#7F90B7]Ralenti :[/color] [color=#F4F7FF][b]{rpm_value} tr/min[/b][/color]",
            markup=True,
            theme_text_color="Custom",
            text_color=with_alpha(TEXT, 0.94),
            font_style="Body2",
            font_size=sp(13),
            size_hint=(1, 1),
            halign="left",
            valign="middle",
            max_lines=1,
        )
        rpm_label.bind(size=lambda label, size: setattr(label, "text_size", size))
        rpm_group.add_widget(rpm_label)
        row.add_widget(rpm_group)

        divider = MDCard(
            orientation="vertical",
            size_hint=(None, None),
            width=dp(1),
            height=dp(20),
            md_bg_color=with_alpha(BLUE, 0.22),
            line_color=with_alpha(BLUE, 0),
            elevation=0,
        )
        row.add_widget(divider)

        load_group = MDBoxLayout(size_hint=(0.5, 1), spacing=dp(8))
        load_icon = MDIcon(
            icon="battery-outline",
            theme_text_color="Custom",
            text_color=BLUE,
            font_size=dp(18),
            size_hint=(None, None),
            size=(dp(18), dp(18)),
            halign="center",
            valign="middle",
        )
        load_icon.bind(size=lambda widget, size: setattr(widget, "text_size", size))
        load_group.add_widget(load_icon)
        load_label = MDLabel(
            text=f"[color=#7F90B7]Charge :[/color] [color=#F4F7FF][b]{load_value} %[/b][/color]",
            markup=True,
            theme_text_color="Custom",
            text_color=with_alpha(TEXT, 0.94),
            font_style="Body2",
            font_size=sp(13),
            size_hint=(1, 1),
            halign="left",
            valign="middle",
            max_lines=1,
        )
        load_label.bind(size=lambda label, size: setattr(label, "text_size", size))
        load_group.add_widget(load_label)
        row.add_widget(load_group)
        return row

    def _status_for_reading(self, reading):
        if not reading.available:
            return "Non supporte"

        if reading.key == "speed":
            return self._speed_status(reading.value)
        if reading.key == "rpm":
            return self._rpm_status(reading.value)
        if reading.key == "coolant_temp":
            return self._coolant_status(reading.value)
        if reading.key == "hybrid_soc":
            return self._soc_status(reading.value)
        return "Disponible"

    @staticmethod
    def _to_float(value):
        try:
            return float(str(value).replace(",", "."))
        except (TypeError, ValueError):
            return None

    def _speed_status(self, value):
        numeric = self._to_float(value)
        if numeric is None:
            return "En attente"
        if numeric <= 5:
            return "Stable"
        if numeric < 110:
            return "Normal"
        return "Attention"

    def _rpm_status(self, value):
        numeric = self._to_float(value)
        if numeric is None:
            return "En attente"
        if numeric < 900:
            return "Stable"
        if numeric < 3000:
            return "Optimal"
        if numeric < 5000:
            return "Normal"
        return "Attention"

    def _coolant_status(self, value):
        numeric = self._to_float(value)
        if numeric is None:
            return "En attente"
        if numeric < 70:
            return "Stable"
        if numeric <= 98:
            return "Optimal"
        if numeric <= 108:
            return "Attention"
        return "Critique"

    def _soc_status(self, value):
        numeric = self._to_float(value)
        if numeric is None:
            return "En attente"
        if numeric < 30:
            return "Attention"
        if numeric < 55:
            return "Stable"
        if numeric <= 80:
            return "Optimal"
        return "Normal"

    def _build_metric_card(self, pid):
        return MetricCard(
            title=self._primary_card_label(pid.key, pid.label),
            icon=pid.icon,
            unit=pid.unit,
            accent=self._accent_for_key(pid.key),
        )

    def _build_secondary_metric_card(self, pid):
        return DashboardSecondaryMetricCard(
            title=self._card_label(pid.label),
            unit=pid.unit,
            accent=self._accent_for_key(pid.key),
        )

    def _build_header(self):
        header = MDBoxLayout(
            orientation="horizontal",
            size_hint_y=None,
            height=dp(52),
            spacing=dp(12),
            padding=(0, dp(2), 0, dp(6)),
        )
        icon_wrap = AnchorLayout(
            anchor_x="center",
            anchor_y="center",
            size_hint=(None, 1),
            width=dp(24),
        )
        icon = MDIcon(
            icon="gauge",
            theme_text_color="Custom",
            text_color=BLUE,
            font_size=dp(22),
            size_hint=(None, None),
            size=(dp(22), dp(22)),
            halign="center",
            valign="middle",
        )
        icon.bind(size=lambda widget, size: setattr(widget, "text_size", size))
        icon_wrap.add_widget(icon)
        copy = MDBoxLayout(
            orientation="vertical",
            adaptive_height=True,
            spacing=0,
            pos_hint={"center_y": 0.5},
        )
        copy.add_widget(
            MDLabel(
                text="Dashboard",
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
                text="Donnees ECU temps reel",
                theme_text_color="Custom",
                text_color=MUTED,
                font_style="Caption",
                size_hint_y=None,
                height=dp(20),
            )
        )
        header.add_widget(icon_wrap)
        header.add_widget(copy)
        return header

    @staticmethod
    def _card_label(label):
        replacements = {
            "Temperature moteur": "Temp\u00e9rature moteur",
            "Temperature admission": "Temp. admission",
            "Pression admission": "Pression adm.",
            "Charge moteur": "Charge mot.",
            "Position papillon": "Papillon",
            "Courant batterie HV": "Courant HV",
            "Temperature MG1": "Temp. MG1",
            "Temperature MG2": "Temp. MG2",
            "Odometre": "Odom\u00e8tre",
        }
        return replacements.get(label, label)

    @staticmethod
    def _primary_card_label(key, label):
        replacements = {
            "rpm": "RPM",
            "speed": "Vitesse",
            "coolant_temp": "Temp. moteur",
            "hybrid_soc": "Batterie SOC",
        }
        return replacements.get(key, DashboardScreen._card_label(label))

    @staticmethod
    def _section_title(title):
        replacements = {
            "MOTEUR": "Moteur",
            "HYBRIDE": "Hybride",
            "VEHICULE": "V\u00e9hicule",
            "CONFORT / ENVIRONNEMENT": "Confort / Environnement",
        }
        return replacements.get(title, title.title())

    @staticmethod
    def _pid(key):
        return next((pid for pid in ELM_EMULATOR_PIDS if pid.key == key), None)

    @staticmethod
    def _accent_for_key(key):
        if key in {"module_voltage", "vin"}:
            return BLUE
        if key in {"coolant_temp", "intake_temp"}:
            return AMBER
        if key.startswith("mg") or key in {"hybrid_current", "hybrid_soc"}:
            return GREEN
        return GREEN
