from kivy.metrics import dp
from kivymd.uix.button import MDRaisedButton
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.gridlayout import MDGridLayout
from kivymd.uix.label import MDIcon, MDLabel

from app.core.theme import AMBER, BLUE, GREEN, MUTED, RED, TEXT, with_alpha
from app.screens.base_screen import BaseScreen
from app.widgets.ui_components import Badge, GlowCard, HeaderBlock, MiniTrend, SectionLabel


class HistoryScreen(BaseScreen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        layout = self.build_page()
        layout.add_widget(HeaderBlock("Historique", "Mesures et diagnostics locaux", icon="history"))

        tabs = MDBoxLayout(adaptive_height=True, spacing=dp(8))
        self.measurements_tab = MDRaisedButton(
            text="Mesures",
            md_bg_color=with_alpha(BLUE, 0.32),
            text_color=TEXT,
            size_hint=(1, None),
            height=dp(42),
            on_release=lambda *_: self.show_mode("measurements"),
        )
        tabs.add_widget(self.measurements_tab)
        self.codes_tab = MDRaisedButton(
            text="Codes defaut",
            md_bg_color=with_alpha(BLUE, 0.10),
            text_color=MUTED,
            size_hint=(1, None),
            height=dp(42),
            on_release=lambda *_: self.show_mode("codes"),
        )
        tabs.add_widget(self.codes_tab)
        layout.add_widget(tabs)

        layout.add_widget(SectionLabel("Tendances analytiques"))
        self.trends_box = MDBoxLayout(orientation="vertical", adaptive_height=True, spacing=dp(10))
        layout.add_widget(self.trends_box)

        layout.add_widget(SectionLabel("Mesures enregistrees"))
        self.history_list = MDBoxLayout(orientation="vertical", adaptive_height=True, spacing=dp(10))
        layout.add_widget(self.history_list)
        layout.add_widget(MDLabel(size_hint_y=None, height=dp(16)))

    def show_mode(self, mode):
        self.refresh(mode=mode)

    def refresh(self, mode="measurements"):
        self._sync_tabs(mode)
        self.trends_box.clear_widgets()
        self.history_list.clear_widgets()
        measurements = self.app.database.get_measurements()
        dtc_codes = self.app.database.get_dtc_history()

        if mode == "codes":
            self._render_code_history(dtc_codes)
            return

        self._render_trends(measurements)
        if not measurements:
            self.history_list.add_widget(self._empty_card("Aucun historique", "Les lectures reelles apparaitront ici."))
            return

        for row in measurements[:10]:
            self.history_list.add_widget(self._measurement_card(row))

    def _sync_tabs(self, mode):
        measurements_active = mode == "measurements"
        self.measurements_tab.md_bg_color = with_alpha(BLUE, 0.32 if measurements_active else 0.10)
        self.measurements_tab.text_color = TEXT if measurements_active else MUTED
        self.codes_tab.md_bg_color = with_alpha(BLUE, 0.32 if not measurements_active else 0.10)
        self.codes_tab.text_color = TEXT if not measurements_active else MUTED

    def _render_trends(self, measurements):
        if not measurements:
            self.trends_box.add_widget(self._empty_card("Aucune tendance", "Effectue une lecture pour afficher les courbes."))
            return
        newest = measurements[0]
        ordered = list(reversed(measurements[:6]))
        self.trends_box.add_widget(
            MiniTrend("RPM moteur", self._value(newest["rpm"]), "tr/min", [row["rpm"] or 0 for row in ordered], BLUE)
        )
        self.trends_box.add_widget(
            MiniTrend("Temp. moteur", self._value(newest["coolant_temp"]), "C", [row["coolant_temp"] or 0 for row in ordered], AMBER)
        )
        self.trends_box.add_widget(
            MiniTrend("SOC Batterie HV", self._value(newest["hybrid_soc"]), "%", [row["hybrid_soc"] or 0 for row in ordered], GREEN)
        )

    def _render_code_history(self, dtc_codes):
        self.trends_box.add_widget(self._empty_card("Codes defaut DTC", f"{len(dtc_codes)} entree(s) memorisee(s)."))
        if not dtc_codes:
            self.history_list.add_widget(self._empty_card("Aucun code defaut", "Aucun DTC n'a ete sauvegarde."))
            return
        for row in dtc_codes[:50]:
            card = GlowCard(accent=RED)
            card.size_hint_y = None
            card.height = dp(112)
            card.add_widget(Badge(row["code"], RED))
            card.add_widget(
                MDLabel(
                    text=row["description"] or "Description indisponible",
                    theme_text_color="Custom",
                    text_color=TEXT,
                    font_style="Subtitle2",
                    bold=True,
                    adaptive_height=True,
                )
            )
            card.add_widget(
                MDLabel(
                    text=f"{row['severity'] or 'Non classee'} - {row['timestamp']}",
                    theme_text_color="Custom",
                    text_color=MUTED,
                    font_style="Caption",
                    adaptive_height=True,
                )
            )
            self.history_list.add_widget(card)

    def _measurement_card(self, row):
        card = GlowCard(accent=BLUE)
        card.size_hint_y = None
        card.height = dp(246)
        header = MDBoxLayout(adaptive_height=True, spacing=dp(8))
        header.add_widget(
            MDIcon(
                icon="clock-outline",
                theme_text_color="Custom",
                text_color=BLUE,
                size_hint_x=None,
                width=dp(24),
                font_size=dp(18),
            )
        )
        header.add_widget(
            MDLabel(
                text=row["timestamp"],
                theme_text_color="Custom",
                text_color=TEXT,
                font_style="Subtitle2",
                bold=True,
            )
        )
        header.add_widget(
            MDLabel(
                text=f"{self._value(row['odometer'])} km",
                theme_text_color="Custom",
                text_color=MUTED,
                font_style="Caption",
                halign="right",
            )
        )
        card.add_widget(header)

        grid = MDGridLayout(cols=3, spacing=dp(6), adaptive_height=True)
        items = (
            ("VITESSE", self._value(row["speed"]), "km/h"),
            ("RPM", self._value(row["rpm"]), ""),
            ("SOC", self._value(row["hybrid_soc"]), "%"),
            ("T.MOT.", self._value(row["coolant_temp"]), "C"),
            ("I HV", self._value(row["hybrid_battery_current"]), "A"),
            ("T.MG1", self._value(row["mg1_temp"]), "C"),
            ("T.MG2", self._value(row["mg2_temp"]), "C"),
        )
        for label, value, unit in items:
            grid.add_widget(self._mini_value(label, value, unit))
        card.add_widget(grid)
        return card

    def _mini_value(self, label, value, unit):
        box = GlowCard()
        box.md_bg_color = with_alpha(BLUE, 0.06)
        box.size_hint_y = None
        box.height = dp(58)
        box.padding = dp(8)
        box.spacing = dp(2)
        box.add_widget(
            MDLabel(
                text=label,
                theme_text_color="Custom",
                text_color=MUTED,
                font_style="Caption",
                bold=True,
                halign="center",
                size_hint_y=None,
                height=dp(18),
            )
        )
        box.add_widget(
            MDLabel(
                text=f"{value} {unit}".strip(),
                theme_text_color="Custom",
                text_color=TEXT,
                font_style="Subtitle2",
                bold=True,
                halign="center",
            )
        )
        return box

    def _empty_card(self, title, message):
        card = GlowCard()
        card.size_hint_y = None
        card.height = dp(82)
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

    @staticmethod
    def _value(value):
        return "-" if value is None else f"{value:g}" if isinstance(value, float) else str(value)
