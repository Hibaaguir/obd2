from threading import Thread

from kivy.clock import Clock
from kivy.metrics import dp
from kivymd.uix.button import MDRaisedButton
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.gridlayout import MDGridLayout
from kivymd.uix.label import MDIcon, MDLabel

from app.core.elm_pid_registry import ELM_EMULATOR_PIDS
from app.core.measurement_mapper import measurement_from_readings
from app.core.theme import AMBER, BLUE, GREEN, MUTED, RED, TEXT, status_color, with_alpha
from app.screens.base_screen import BaseScreen
from app.widgets.ui_components import CleanMetricCard, GlowCard, HeaderBlock, SectionLabel


PRIMARY_METRIC_KEYS = ("rpm", "speed", "coolant_temp", "hybrid_soc")

COMPACT_SECTIONS = (
    ("MOTEUR", ("engine_load", "intake_pressure", "intake_temp", "maf", "throttle_pos", "module_voltage")),
    ("HYBRIDE", ("hybrid_current", "mg1_temp", "mg2_temp", "mg1_torque", "mg2_torque")),
    ("VEHICULE", ("odometer", "fuel_level", "vin")),
    ("CONFORT / ENVIRONNEMENT", ("ambient_temp",)),
)


class DashboardScreen(BaseScreen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.loading = False
        self.cards = {}

        layout = self.build_page()
        layout.add_widget(HeaderBlock("Dashboard", "Donnees ECU temps reel", icon="gauge"))

        self.status_card = self._build_status_card()
        layout.add_widget(self.status_card)

        layout.add_widget(SectionLabel("Valeurs principales"))
        primary_grid = self._build_metric_grid(spacing=dp(12))
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
        self.recommendations.height = dp(112)
        layout.add_widget(self.recommendations)
        self._render_recommendations([])

        for title, keys in COMPACT_SECTIONS:
            layout.add_widget(SectionLabel(title))
            if title == "VEHICULE":
                vehicle_grid = self._build_metric_grid(spacing=dp(8))
                for key in ("odometer", "fuel_level"):
                    pid = self._pid(key)
                    if not pid:
                        continue
                    card = self._build_metric_card(pid)
                    self.cards[key] = card
                    vehicle_grid.add_widget(card)
                layout.add_widget(vehicle_grid)

                vin_pid = self._pid("vin")
                if vin_pid:
                    vin_card = self._build_metric_card(vin_pid)
                    self.cards["vin"] = vin_card
                    layout.add_widget(vin_card)
                continue

            grid = self._build_metric_grid(spacing=dp(8))
            for key in keys:
                pid = self._pid(key)
                if not pid:
                    continue
                card = self._build_metric_card(pid)
                self.cards[key] = card
                grid.add_widget(card)
            layout.add_widget(grid)

        layout.add_widget(MDLabel(size_hint_y=None, height=dp(12)))

    @staticmethod
    def _build_metric_grid(spacing):
        grid = MDGridLayout(cols=2, spacing=spacing, adaptive_height=True)
        grid.bind(width=lambda instance, value: setattr(instance, "cols", 1 if value < dp(320) else 2))
        return grid

    def _build_status_card(self):
        card = GlowCard(accent=BLUE)
        card.size_hint_y = None
        card.height = dp(138)

        top = MDBoxLayout(size_hint_y=None, height=dp(40), spacing=dp(10))
        top.add_widget(
            MDIcon(
                icon="access-point",
                theme_text_color="Custom",
                text_color=BLUE,
                size_hint_x=None,
                width=dp(28),
                font_size=dp(22),
            )
        )
        copy = MDBoxLayout(orientation="vertical", spacing=dp(1))
        self.connection_label = MDLabel(
            text="Etat connexion: hors ligne",
            theme_text_color="Custom",
            text_color=TEXT,
            font_style="Subtitle2",
            bold=True,
            size_hint_y=None,
            height=dp(21),
        )
        self.message = MDLabel(
            text="Connecte un adaptateur OBD2 depuis l'ecran Connexion.",
            theme_text_color="Custom",
            text_color=MUTED,
            font_style="Caption",
            size_hint_y=None,
            height=dp(18),
        )
        copy.add_widget(self.connection_label)
        copy.add_widget(self.message)
        top.add_widget(copy)

        self.refresh_button = MDRaisedButton(
            text="Actualiser",
            icon="refresh",
            md_bg_color=with_alpha(BLUE, 0.82),
            text_color=TEXT,
            size_hint=(1, None),
            height=dp(46),
            on_release=lambda *_: self.refresh(),
        )

        hint = MDLabel(
            text="Lecture ECU, recommandations systeme et sauvegarde locale.",
            theme_text_color="Custom",
            text_color=MUTED,
            font_style="Caption",
            size_hint_y=None,
            height=dp(18),
        )

        card.add_widget(top)
        card.add_widget(self.refresh_button)
        card.add_widget(hint)
        return card

    def refresh(self):
        if self.loading:
            return

        service = self.app.obd_service
        self._update_connection_status()
        if not service.is_connected():
            self.message.text = "Aucun adaptateur OBD2 connecte."
            for card in self.cards.values():
                card.set_data("-", "", "Hors ligne")
            self._render_recommendations([])
            return

        self.loading = True
        self.refresh_button.disabled = True
        self.refresh_button.text = "Lecture..."
        self.message.text = "Lecture ECU en cours..."
        Thread(target=self._read_worker, daemon=True).start()

    def _read_worker(self):
        try:
            readings = self.app.obd_service.read_live_data()
            Clock.schedule_once(lambda *_: self._finish_read(readings, None), 0)
        except Exception as exc:
            Clock.schedule_once(lambda *_, error=exc: self._finish_read([], error), 0)

    def _finish_read(self, readings, error):
        self.loading = False
        self.refresh_button.disabled = False
        self.refresh_button.text = "Actualiser"
        self._update_connection_status()
        if error is not None:
            self.message.text = str(error)
            return

        self.app.database.save_measurement(measurement_from_readings(readings))
        available = sum(1 for reading in readings if reading.available)
        self.message.text = f"Derniere lecture ECU: {available}/{len(readings)} donnees disponibles."

        for reading in readings:
            card = self.cards.get(reading.key)
            if not card:
                continue
            status = self._status_for_reading(reading)
            card.set_data(reading.value, reading.unit, status)

        diagnostics = self.app.diagnostic_service.analyze(readings, [])
        self._render_recommendations(diagnostics)

    def _update_connection_status(self):
        service = self.app.obd_service
        if service.is_connected():
            self.connection_label.text = f"Etat connexion: connecte a {service.current_host}:{service.current_port}"
            self.connection_label.text_color = GREEN
        else:
            self.connection_label.text = "Etat connexion: hors ligne"
            self.connection_label.text_color = MUTED

    def _render_recommendations(self, diagnostics):
        self.recommendations.clear_widgets()
        count = max(1, min(len(diagnostics), 3))
        self.recommendations.height = dp(58 + count * 58)
        self.recommendations.add_widget(
            MDLabel(
                text="RECOMMANDATIONS SYSTEME",
                theme_text_color="Custom",
                text_color=MUTED,
                font_style="Caption",
                bold=True,
                size_hint_y=None,
                height=dp(24),
            )
        )

        if not diagnostics:
            self.recommendations.add_widget(
                self._recommendation_row(
                    "Systeme en attente",
                    "Lance une lecture pour afficher les recommandations.",
                    "warning",
                )
            )
            return

        for result in diagnostics[:3]:
            self.recommendations.add_widget(
                self._recommendation_row(result.title, result.message, result.severity)
            )

    def _recommendation_row(self, title, message, severity):
        color = status_color(severity)
        row = MDBoxLayout(size_hint_y=None, height=dp(56), spacing=dp(8))
        row.add_widget(
            MDIcon(
                icon="check-circle-outline" if severity == "normal" else "alert-outline",
                theme_text_color="Custom",
                text_color=color,
                size_hint_x=None,
                width=dp(28),
                font_size=dp(20),
            )
        )
        copy = MDBoxLayout(orientation="vertical", spacing=dp(1))
        copy.add_widget(
            MDLabel(
                text=title,
                theme_text_color="Custom",
                text_color=TEXT if severity == "normal" else color,
                font_style="Subtitle2",
                bold=True,
                size_hint_y=None,
                height=dp(23),
            )
        )
        copy.add_widget(
            MDLabel(
                text=message,
                theme_text_color="Custom",
                text_color=MUTED,
                font_style="Caption",
                size_hint_y=None,
                height=dp(31),
            )
        )
        row.add_widget(copy)
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
        return reading.category

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
        return CleanMetricCard(
            title=self._card_label(pid.label),
            icon=pid.icon,
            unit=pid.unit,
            accent=self._accent_for_key(pid.key),
        )

    @staticmethod
    def _card_label(label):
        replacements = {
            "Temperature moteur": "Temp\u00e9rature moteur",
            "Temperature admission": "Temp\u00e9rature admission",
            "Odometre": "Odom\u00e8tre",
        }
        return replacements.get(label, label)

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
