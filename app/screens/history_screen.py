from datetime import datetime

from kivy.metrics import dp
from kivy.core.window import Window
from kivy.uix.anchorlayout import AnchorLayout
from kivymd.uix.button import MDRaisedButton
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.card import MDCard
from kivymd.uix.dialog import MDDialog
from kivymd.uix.gridlayout import MDGridLayout
from kivymd.uix.label import MDIcon, MDLabel
from kivymd.uix.scrollview import MDScrollView

from app.core.theme import AMBER, BLUE, BORDER, GREEN, MUTED, PANEL_BG, RED, TEXT, with_alpha
from app.screens.base_screen import BaseScreen
from app.widgets.ui_components import GlowCard


class HistoryScreen(BaseScreen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.history_dialog = None
        self.current_filter = "Tous"
        self.filter_options = ["Tous", "Normal", "Alerte", "Critique"]
        self.filter_buttons = {}

        layout = self.build_page()
        layout.add_widget(self._build_header())

        self.stats_card = GlowCard(accent=BLUE)
        self.stats_card.size_hint_y = None
        self.stats_card.height = dp(78)
        self.stats_card.radius = [dp(18)]
        self.stats_card.padding = (dp(14), dp(10), dp(14), dp(10))
        layout.add_widget(self.stats_card)

        filters = MDGridLayout(cols=4, spacing=dp(8), size_hint_y=None, height=dp(40))
        for label in self.filter_options:
            button = MDRaisedButton(
                text=label,
                md_bg_color=self._filter_button_bg(label, label == self.current_filter),
                text_color=TEXT if label == self.current_filter else MUTED,
                size_hint=(1, None),
                height=dp(40),
                on_release=lambda *_ignored, value=label: self._set_filter(value),
            )
            self.filter_buttons[label] = button
            filters.add_widget(button)
        layout.add_widget(filters)

        self.history_list = MDBoxLayout(orientation="vertical", adaptive_height=True, spacing=dp(10))
        layout.add_widget(self.history_list)
        layout.add_widget(MDLabel(size_hint_y=None, height=dp(96)))

    def refresh(self, mode="measurements"):
        self.stats_card.clear_widgets()
        self.history_list.clear_widgets()

        measurements = self.app.database.get_measurements()
        dtc_codes = self.app.database.get_dtc_history()
        self._render_stats_summary(measurements, dtc_codes)

        rows = self._filtered_measurements(measurements)
        if not rows:
            self.history_list.add_widget(self._empty_card("Aucun historique", "Les lectures reelles apparaitront ici."))
            return

        self._render_grouped_history(rows[:10])

    def _render_stats_summary(self, measurements, dtc_codes):
        summary_row = MDGridLayout(cols=3, spacing=dp(12), adaptive_height=True)
        summary_row.add_widget(self._summary_item("Total analyses", str(len(measurements))))
        summary_row.add_widget(self._summary_item("Dernier scan", self._compact_last_scan_text(measurements, dtc_codes)))
        summary_row.add_widget(self._summary_item("Alertes", str(self._alert_count(measurements))))
        self.stats_card.add_widget(summary_row)

    def _render_grouped_history(self, rows):
        current_group = None
        for row in rows:
            group = self._date_group_key(row["timestamp"])
            if group != current_group:
                current_group = group
                self.history_list.add_widget(self._date_header(group))
            self.history_list.add_widget(self._measurement_card(row))

    def _measurement_card(self, row):
        status = self._status_from_severity(row["diagnostic_status"])
        main_issue = (row["main_issue"] or row["diagnostic_summary"] or "Etat normal").strip()
        summary = self._stored_summary(row)
        detail_payload = {
            "date": self._split_timestamp(row["timestamp"])[0],
            "time": self._split_timestamp(row["timestamp"])[1],
            "status": status,
            "dtc_count": self._row_dtc_count(row),
            "rpm_max": self._display_number(row["rpm"]),
            "speed_max": self._display_number(row["speed"]),
            "coolant_temp_max": self._display_number(row["coolant_temp"]),
            "hybrid_soc": self._display_number(row["hybrid_soc"]),
            "summary": summary,
        }
        return self._history_item_card(
            timestamp=row["timestamp"],
            status=status,
            accent=self._accent_for_status(status),
            title=self._card_title(main_issue, status),
            details=self._measurement_details_text(row),
            detail_payload=detail_payload,
        )

    def _history_item_card(self, timestamp, status, accent, title, details, detail_payload):
        card = GlowCard(accent=accent)
        card.size_hint_y = None
        card.height = dp(105)
        card.radius = [dp(18)]
        card.padding = (dp(16), dp(14), dp(16), dp(14))
        card.on_touch_down = lambda touch, widget=card: self._history_card_touch_down(widget, touch)
        card.on_touch_up = lambda touch, widget=card: self._history_card_touch_up(widget, touch, detail_payload)

        content = MDBoxLayout(orientation="vertical", spacing=dp(6))

        top_row = MDBoxLayout(size_hint_y=None, height=dp(28), spacing=dp(8))
        time_label = MDLabel(
            text=self._format_history_time(timestamp),
            theme_text_color="Custom",
            text_color=MUTED,
            font_style="Caption",
            bold=True,
            halign="left",
            valign="middle",
        )
        time_label.bind(size=lambda label, size: setattr(label, "text_size", size))
        top_row.add_widget(time_label)
        top_row.add_widget(MDBoxLayout())
        top_row.add_widget(self._status_badge(status))

        title_label = MDLabel(
            text=title,
            theme_text_color="Custom",
            text_color=TEXT,
            font_style="Subtitle2",
            bold=True,
            size_hint_y=None,
            height=dp(24),
            halign="left",
            valign="middle",
            shorten=True,
            shorten_from="right",
        )
        title_label.bind(size=lambda label, size: setattr(label, "text_size", size))

        details_label = MDLabel(
            text=details,
            theme_text_color="Custom",
            text_color=MUTED,
            font_style="Caption",
            size_hint_y=None,
            height=dp(20),
            halign="left",
            valign="middle",
            shorten=True,
            shorten_from="right",
        )
        details_label.bind(size=lambda label, size: setattr(label, "text_size", size))

        content.add_widget(top_row)
        content.add_widget(title_label)
        content.add_widget(details_label)
        card.add_widget(content)
        return card

    def _status_badge(self, status):
        color = self._accent_for_status(status)
        badge = MDCard(
            orientation="vertical",
            size_hint=(None, None),
            height=dp(28),
            width=max(dp(88), dp(24) + dp(7) * len(status)),
            padding=(dp(12), 0, dp(12), 0),
            radius=[dp(14)],
            elevation=0,
            md_bg_color=with_alpha(color, 0.16),
            line_color=with_alpha(color, 0.55),
        )
        badge.add_widget(
            MDLabel(
                text=status,
                theme_text_color="Custom",
                text_color=color,
                font_style="Caption",
                bold=True,
                halign="center",
                valign="middle",
            )
        )
        return badge

    def _history_card_touch_down(self, widget, touch):
        if widget.collide_point(*touch.pos):
            touch.grab(widget)
            return True
        return False

    def _history_card_touch_up(self, widget, touch, detail_payload):
        if touch.grab_current is widget:
            touch.ungrab(widget)
            if widget.collide_point(*touch.pos):
                self._open_history_details(detail_payload)
            return True
        return False

    def _open_history_details(self, detail_payload):
        if self.history_dialog:
            self.history_dialog.dismiss()

        max_width = min(self.width * 0.9, Window.width * 0.9, dp(360))
        max_height = min(self.height * 0.75, Window.height * 0.75, dp(520))
        inner_width = max(dp(260), max_width - dp(40))
        inner_height = max(dp(280), max_height - dp(28))
        button_height = dp(44)
        content_padding = dp(14)
        header_height = dp(32)
        date_time_text = f"{detail_payload['date']} • {detail_payload['time']}"

        details = MDBoxLayout(
            orientation="vertical",
            size_hint_y=None,
            spacing=dp(12),
            padding=(0, 0, 0, dp(2)),
        )
        details.bind(minimum_height=details.setter("height"))

        date_time_label = MDLabel(
            text=date_time_text,
            theme_text_color="Custom",
            text_color=MUTED,
            font_style="Caption",
            bold=True,
            size_hint_y=None,
            height=dp(20),
            halign="left",
            valign="middle",
        )
        date_time_label.bind(size=lambda label, size: setattr(label, "text_size", size))
        details.add_widget(date_time_label)
        details.add_widget(self._dialog_section("Resume", detail_payload["summary"]))
        details.add_widget(self._dialog_section("Codes DTC", str(detail_payload["dtc_count"])))

        measures = MDCard(
            orientation="vertical",
            size_hint_y=None,
            adaptive_height=True,
            padding=(dp(14), dp(12), dp(14), dp(12)),
            spacing=dp(10),
            radius=[dp(14)],
            elevation=0,
            md_bg_color=with_alpha(BLUE, 0.05),
            line_color=with_alpha(BORDER, 0.55),
        )
        measures.add_widget(self._section_title("Mesures principales"))
        measures.add_widget(self._measure_row("RPM max", detail_payload["rpm_max"]))
        measures.add_widget(self._measure_row("Vitesse max", detail_payload["speed_max"]))
        measures.add_widget(self._measure_row("Temperature moteur", f"{detail_payload['coolant_temp_max']} C"))
        measures.add_widget(self._measure_row("Batterie SOC", f"{detail_payload['hybrid_soc']}%"))
        details.add_widget(measures)

        scroll = MDScrollView(size_hint=(1, 1), bar_width=dp(3))
        scroll.add_widget(details)

        header_row = MDBoxLayout(
            size_hint_y=None,
            height=header_height,
            spacing=dp(12),
        )
        title_label = MDLabel(
            text="Detail du diagnostic",
            theme_text_color="Custom",
            text_color=TEXT,
            font_style="H6",
            bold=True,
            halign="left",
            valign="middle",
        )
        title_label.bind(size=lambda label, size: setattr(label, "text_size", size))
        header_row.add_widget(title_label)
        header_row.add_widget(self._status_badge(detail_payload["status"]))

        content = MDBoxLayout(
            orientation="vertical",
            size_hint=(None, None),
            width=inner_width,
            height=inner_height,
            spacing=dp(12),
            padding=(content_padding, content_padding, content_padding, content_padding),
        )
        content.add_widget(header_row)
        content.add_widget(scroll)

        button_row = MDBoxLayout(
            size_hint_y=None,
            height=button_height,
        )
        close_button = MDRaisedButton(
            text="Fermer",
            md_bg_color=with_alpha(BLUE, 0.9),
            text_color=TEXT,
            size_hint=(1, None),
            height=button_height,
            on_release=lambda *_: self.history_dialog.dismiss(),
        )
        button_row.add_widget(close_button)
        content.add_widget(button_row)

        self.history_dialog = MDDialog(
            type="custom",
            content_cls=content,
        )
        self.history_dialog.width = max_width
        self.history_dialog.md_bg_color = PANEL_BG
        self.history_dialog.radius = [dp(18), dp(18), dp(18), dp(18)]
        self.history_dialog.line_color = with_alpha(BORDER, 0.9)
        self.history_dialog.open()
        available_height = max(dp(120), inner_height - header_height - button_height - dp(24))
        scroll.height = min(details.height, available_height)
        scroll.do_scroll_y = details.height > available_height

    def _set_filter(self, value):
        self.current_filter = value
        for label, button in self.filter_buttons.items():
            active = label == value
            button.md_bg_color = self._filter_button_bg(label, active)
            button.text_color = TEXT if active else MUTED
        self.refresh()

    def _filter_button_bg(self, label, active):
        if not active:
            return with_alpha(BLUE, 0.10)
        if label == "Normal":
            return with_alpha(GREEN, 0.22)
        if label == "Alerte":
            return with_alpha(AMBER, 0.22)
        if label == "Critique":
            return with_alpha(RED, 0.22)
        return with_alpha(BLUE, 0.32)

    def _filtered_measurements(self, measurements):
        rows = []
        for row in measurements:
            status = self._status_from_severity(row["diagnostic_status"])
            if self.current_filter != "Tous" and status != self.current_filter:
                continue
            rows.append(row)
        return rows

    def _detail_line(self, label, value):
        row = MDCard(
            orientation="vertical",
            adaptive_height=True,
            padding=(dp(12), dp(10), dp(12), dp(10)),
            spacing=dp(4),
            radius=[dp(14)],
            elevation=0,
            md_bg_color=with_alpha(BLUE, 0.05),
            line_color=with_alpha(BORDER, 0.55),
        )
        label_widget = MDLabel(
            text=label,
            theme_text_color="Custom",
            text_color=MUTED,
            font_style="Caption",
            bold=True,
            adaptive_height=True,
        )
        value_widget = MDLabel(
            text=value,
            theme_text_color="Custom",
            text_color=TEXT,
            font_style="Subtitle2",
            adaptive_height=True,
        )
        label_widget.bind(width=lambda widget, width: setattr(widget, "text_size", (width, None)))
        value_widget.bind(width=lambda widget, width: setattr(widget, "text_size", (width, None)))
        row.add_widget(label_widget)
        row.add_widget(value_widget)
        return row

    def _dialog_section(self, title, value):
        card = MDCard(
            orientation="vertical",
            size_hint_y=None,
            adaptive_height=True,
            padding=(dp(14), dp(12), dp(14), dp(12)),
            spacing=dp(8),
            radius=[dp(14)],
            elevation=0,
            md_bg_color=with_alpha(BLUE, 0.05),
            line_color=with_alpha(BORDER, 0.55),
        )
        card.add_widget(self._section_title(title))
        value_label = MDLabel(
            text=value,
            theme_text_color="Custom",
            text_color=TEXT,
            font_style="Subtitle2",
            bold=(title == "Codes DTC"),
            adaptive_height=True,
            halign="left",
            valign="middle",
        )
        value_label.bind(width=lambda widget, width: setattr(widget, "text_size", (width, None)))
        card.add_widget(value_label)
        return card

    def _measure_row(self, label, value):
        row = MDGridLayout(cols=2, size_hint_y=None, height=dp(22), spacing=dp(8))
        left = MDLabel(
            text=label,
            theme_text_color="Custom",
            text_color=MUTED,
            font_style="Caption",
            bold=True,
            halign="left",
            valign="middle",
        )
        right = MDLabel(
            text=value,
            theme_text_color="Custom",
            text_color=TEXT,
            font_style="Subtitle2",
            bold=True,
            halign="right",
            valign="middle",
        )
        left.bind(size=lambda label_widget, size: setattr(label_widget, "text_size", size))
        right.bind(size=lambda label_widget, size: setattr(label_widget, "text_size", size))
        row.add_widget(left)
        row.add_widget(right)
        return row

    def _section_title(self, text):
        label = MDLabel(
            text=text,
            theme_text_color="Custom",
            text_color=MUTED,
            font_style="Caption",
            bold=True,
            size_hint_y=None,
            height=dp(18),
            halign="left",
            valign="middle",
        )
        label.bind(size=lambda widget, size: setattr(widget, "text_size", size))
        return label

    def _summary_item(self, label, value):
        item = MDBoxLayout(orientation="vertical", spacing=dp(2))
        label_widget = MDLabel(
            text=label,
            theme_text_color="Custom",
            text_color=MUTED,
            font_style="Caption",
            bold=True,
            halign="center",
            valign="middle",
            size_hint_y=None,
            height=dp(16),
        )
        value_widget = MDLabel(
            text=value,
            theme_text_color="Custom",
            text_color=TEXT,
            font_style="Subtitle2",
            bold=True,
            halign="center",
            valign="middle",
            size_hint_y=None,
            height=dp(30),
        )
        label_widget.bind(size=lambda widget, size: setattr(widget, "text_size", size))
        value_widget.bind(size=lambda widget, size: setattr(widget, "text_size", size))
        item.add_widget(label_widget)
        item.add_widget(value_widget)
        return item

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
            icon="history",
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
                text="Historique",
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
                text="Diagnostics enregistres",
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

    def _empty_card(self, title, message):
        card = GlowCard()
        card.size_hint_y = None
        card.height = dp(78)
        card.radius = [dp(18)]
        card.padding = (dp(16), dp(12), dp(16), dp(12))
        card.spacing = dp(4)
        card.add_widget(
            MDLabel(
                text=title,
                theme_text_color="Custom",
                text_color=TEXT,
                font_style="Subtitle2",
                bold=True,
                adaptive_height=True,
            )
        )
        card.add_widget(
            MDLabel(
                text=message,
                theme_text_color="Custom",
                text_color=MUTED,
                font_style="Caption",
                adaptive_height=True,
            )
        )
        return card

    def _row_dtc_count(self, row):
        value = row["dtc_count"] if "dtc_count" in row.keys() else None
        if value is not None:
            try:
                return int(value)
            except (TypeError, ValueError):
                pass
        return self._dtc_count_from_signature(row["dtc_signature"] if "dtc_signature" in row.keys() else "")

    @staticmethod
    def _dtc_count_from_signature(signature):
        text = str(signature or "").strip()
        if not text:
            return 0
        return len([item for item in text.split("|") if item.strip()])

    def _stored_summary(self, row):
        if "history_summary" in row.keys() and row["history_summary"]:
            return str(row["history_summary"]).strip()
        if "diagnostic_summary" in row.keys() and row["diagnostic_summary"]:
            return str(row["diagnostic_summary"]).strip()
        return "Aucune anomalie detectee."

    def _measurement_details_text(self, row):
        return (
            f"DTC: {self._row_dtc_count(row)} • "
            f"RPM: {self._display_number(row['rpm'])} • "
            f"Temp: {self._display_number(row['coolant_temp'])}°C"
        )

    @staticmethod
    def _display_number(value):
        if value is None:
            return "-"
        try:
            return str(int(round(float(value))))
        except (TypeError, ValueError):
            return str(value)

    @staticmethod
    def _card_title(main_issue, status):
        if status == "Normal" or main_issue == "Etat normal":
            return "Diagnostic normal"

        title_map = {
            "Regime moteur eleve": "Regime moteur eleve",
            "Temperature moteur elevee": "Temperature moteur elevee",
            "Batterie hybride basse": "Batterie hybride faible",
            "Batterie faible": "Batterie 12V faible",
            "Courant batterie HV eleve": "Courant batterie HV eleve",
            "Temperature MG1 elevee": "Temperature MG1 elevee",
            "Temperature MG2 elevee": "Temperature MG2 elevee",
            "Anomalie detectee": "Codes defaut detectes",
        }
        return title_map.get(main_issue, main_issue)

    @staticmethod
    def _alert_count(measurements):
        count = 0
        for row in measurements:
            if HistoryScreen._status_from_severity(row["diagnostic_status"]) != "Normal":
                count += 1
        return count

    @staticmethod
    def _last_scan_text(measurements, dtc_codes):
        if measurements:
            return measurements[0]["timestamp"]
        if dtc_codes:
            return dtc_codes[0]["timestamp"]
        return "-"

    @staticmethod
    def _compact_last_scan_text(measurements, dtc_codes):
        timestamp = HistoryScreen._last_scan_text(measurements, dtc_codes)
        parsed = HistoryScreen._parse_timestamp(timestamp)
        if parsed is None:
            return "-"
        month_names = {
            1: "Janvier",
            2: "Fevrier",
            3: "Mars",
            4: "Avril",
            5: "Mai",
            6: "Juin",
            7: "Juillet",
            8: "Aout",
            9: "Septembre",
            10: "Octobre",
            11: "Novembre",
            12: "Decembre",
        }
        return f"{parsed.day:02d} {month_names.get(parsed.month, '')}\n{parsed.hour:02d}:{parsed.minute:02d}"

    @staticmethod
    def _status_from_severity(severity):
        normalized = (severity or "").strip().lower()
        if normalized in {"critique", "critical"}:
            return "Critique"
        if normalized in {"alerte", "attention", "warning"}:
            return "Alerte"
        return "Normal"

    @staticmethod
    def _accent_for_status(status):
        if status == "Alerte":
            return AMBER
        if status == "Critique":
            return RED
        return GREEN

    @staticmethod
    def _date_group_key(timestamp):
        parsed = HistoryScreen._parse_timestamp(timestamp)
        if parsed is None:
            return str(timestamp)

        today = datetime.now().date()
        if parsed.date() == today:
            return "Aujourd'hui"
        if parsed.date().toordinal() == today.toordinal() - 1:
            return "Hier"

        month_names = {
            1: "Janvier",
            2: "Fevrier",
            3: "Mars",
            4: "Avril",
            5: "Mai",
            6: "Juin",
            7: "Juillet",
            8: "Aout",
            9: "Septembre",
            10: "Octobre",
            11: "Novembre",
            12: "Decembre",
        }
        return f"{parsed.day:02d} {month_names.get(parsed.month, '')}"

    @staticmethod
    def _format_history_time(timestamp):
        parsed = HistoryScreen._parse_timestamp(timestamp)
        if parsed is None:
            return str(timestamp)
        return f"{parsed.hour:02d}:{parsed.minute:02d}"

    @staticmethod
    def _format_history_timestamp(timestamp):
        if not timestamp:
            return "-"

        parsed = HistoryScreen._parse_timestamp(timestamp)
        if parsed is None:
            return str(timestamp).strip()

        month_names = {
            1: "Janvier",
            2: "Fevrier",
            3: "Mars",
            4: "Avril",
            5: "Mai",
            6: "Juin",
            7: "Juillet",
            8: "Aout",
            9: "Septembre",
            10: "Octobre",
            11: "Novembre",
            12: "Decembre",
        }
        month = month_names.get(parsed.month, "")
        return f"{parsed.day:02d} {month} {parsed.year} - {parsed.hour:02d}:{parsed.minute:02d}"

    @staticmethod
    def _split_timestamp(timestamp):
        formatted = HistoryScreen._format_history_timestamp(timestamp)
        if " - " in formatted:
            date_text, time_text = [part.strip() for part in formatted.split(" - ", 1)]
            return date_text, time_text
        return formatted, "-"

    @staticmethod
    def _parse_timestamp(timestamp):
        text = str(timestamp or "").strip()
        for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M"):
            try:
                return datetime.strptime(text, fmt)
            except ValueError:
                continue
        return None

    def _measurement_details_text(self, row):
        return (
            f"DTC: {self._row_dtc_count(row)} • "
            f"RPM: {self._display_number(row['rpm'])} • "
            f"Temp: {self._display_number(row['coolant_temp'])}°C"
        )

    def _date_header(self, label):
        row = MDBoxLayout(size_hint_y=None, height=dp(24), padding=(dp(2), dp(6), 0, 0))
        header = MDLabel(
            text=label,
            theme_text_color="Custom",
            text_color=with_alpha(TEXT, 0.9),
            font_style="Caption",
            bold=True,
            halign="left",
            valign="middle",
        )
        header.bind(size=lambda label_widget, size: setattr(label_widget, "text_size", size))
        row.add_widget(header)
        return row
