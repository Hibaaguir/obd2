from threading import Thread

from kivy.clock import Clock
from kivy.metrics import dp
from kivymd.uix.button import MDFlatButton, MDRaisedButton
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.dialog import MDDialog
from kivymd.uix.label import MDIcon, MDLabel

from app.core.measurement_mapper import measurement_from_readings
from app.core.theme import AMBER, BLUE, GREEN, MUTED, RED, TEXT, status_color, with_alpha
from app.screens.base_screen import BaseScreen
from app.widgets.ui_components import Badge, GlowCard, HeaderBlock, SectionLabel


class DiagnosticScreen(BaseScreen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.clear_dialog = None
        self.last_diagnostics = []
        self.last_codes = []
        self.loading = False

        layout = self.build_page()
        layout.add_widget(HeaderBlock("Diagnostic ECU", "Analyse systeme vehicule hybride", icon="clipboard-pulse-outline"))

        self.summary = GlowCard(accent=BLUE)
        self.summary.size_hint_y = None
        self.summary.height = dp(122)
        layout.add_widget(self.summary)
        self._render_summary("En attente", "Lance une lecture pour analyser l'ECU.", "normal", 0, 0, 0)

        self.report_button = MDRaisedButton(
            text="  Generer le rapport intelligent",
            icon="file-document-outline",
            md_bg_color=with_alpha(BLUE, 0.86),
            text_color=TEXT,
            size_hint=(1, None),
            height=dp(48),
            on_release=self.generate_report,
        )
        layout.add_widget(self.report_button)

        actions = MDBoxLayout(adaptive_height=True, spacing=dp(10))
        actions.add_widget(
            MDRaisedButton(
                text="  Lecture",
                icon="magnify-scan",
                md_bg_color=with_alpha(BLUE, 0.18),
                text_color=TEXT,
                size_hint=(1, None),
                height=dp(48),
                on_release=self.scan_codes,
            )
        )
        actions.add_widget(
            MDRaisedButton(
                text="  Effacer codes",
                icon="delete-outline",
                md_bg_color=with_alpha(RED, 0.12),
                text_color=RED,
                size_hint=(1, None),
                height=dp(48),
                on_release=self.confirm_clear_codes,
            )
        )
        layout.add_widget(actions)

        layout.add_widget(SectionLabel("Resultats de l'analyse"))
        self.results_box = MDBoxLayout(orientation="vertical", adaptive_height=True, spacing=dp(10))
        layout.add_widget(self.results_box)

        layout.add_widget(SectionLabel("Codes defaut DTC"))
        self.codes_box = MDBoxLayout(orientation="vertical", adaptive_height=True, spacing=dp(10))
        layout.add_widget(self.codes_box)
        layout.add_widget(MDLabel(size_hint_y=None, height=dp(16)))
        self._render_empty_state()

    def scan_codes(self, *_):
        if self.loading:
            return
        service = self.app.obd_service
        if not service.is_connected():
            self._set_message("Connexion requise", "Aucun adaptateur OBD2 connecte.", "warning")
            return

        self.loading = True
        self._set_message("Lecture...", "Analyse ECU en cours.", "normal")
        Thread(target=self._scan_worker, daemon=True).start()

    def _scan_worker(self):
        try:
            service = self.app.obd_service
            readings = service.read_live_data()
            codes = service.read_error_codes()
            Clock.schedule_once(lambda *_: self._finish_scan(readings, codes, None), 0)
        except Exception as exc:
            Clock.schedule_once(lambda *_, error=exc: self._finish_scan([], [], error), 0)

    def _finish_scan(self, readings, codes, error):
        self.loading = False
        if error is not None:
            self._set_message("Lecture impossible", str(error), "critical")
            return
        try:
            self.app.database.save_measurement(measurement_from_readings(readings))
            self.app.database.save_dtc_codes(codes)
            diagnostics = self.app.diagnostic_service.analyze(readings, codes)
        except Exception as exc:
            self._set_message("Lecture impossible", str(exc), "critical")
            return

        self.last_diagnostics = diagnostics
        self.last_codes = codes
        normal_count = sum(1 for item in diagnostics if item.severity == "normal")
        warning_count = sum(1 for item in diagnostics if item.severity == "warning")
        critical_count = sum(1 for item in diagnostics if item.severity == "critical") + len(codes)
        overall = self.app.diagnostic_service.overall_severity(diagnostics)
        title = {
            "normal": "Systeme normal",
            "warning": "Attention requise",
            "critical": "Anomalie critique",
        }.get(overall, "Diagnostic termine")
        message = {
            "normal": "Aucune anomalie detectee avec les donnees disponibles.",
            "warning": "Points a surveiller detectes. Controle recommande.",
            "critical": "Anomalie critique detectee. Verification immediate recommandee.",
        }.get(overall, "Analyse terminee.")
        self._render_summary(title, message, overall, normal_count, warning_count, critical_count)
        self._render_results(diagnostics)
        self._render_codes(codes)

    def confirm_clear_codes(self, *_):
        if not self.app.obd_service.is_connected():
            self._set_message("Connexion requise", "Aucun adaptateur OBD2 connecte.", "warning")
            return
        self.clear_dialog = MDDialog(
            title="Confirmer la suppression",
            text=(
                "Vous etes sur le point d'effacer les codes defaut memorises dans l'ECU. "
                "Cette action peut eteindre les voyants tableau de bord mais ne repare pas le probleme sous-jacent."
            ),
            buttons=[
                MDFlatButton(text="Annuler", on_release=lambda *_: self.clear_dialog.dismiss()),
                MDFlatButton(text="Confirmer", theme_text_color="Custom", text_color=RED, on_release=self.clear_codes),
            ],
        )
        self.clear_dialog.open()

    def clear_codes(self, *_):
        if self.clear_dialog:
            self.clear_dialog.dismiss()
        service = self.app.obd_service
        try:
            success = service.clear_error_codes()
        except Exception as exc:
            self._set_message("Effacement impossible", str(exc), "critical")
            return
        message = "Commande d'effacement envoyee." if success else "Effacement non confirme par l'ECU."
        self._set_message("Codes effaces" if success else "Non confirme", message, "normal" if success else "warning")

    def generate_report(self, *_):
        if not self.last_diagnostics:
            self._set_message("Rapport indisponible", "Lance d'abord une analyse ECU.", "warning")
            return
        positives = sum(1 for item in self.last_diagnostics if item.severity == "normal")
        warnings = sum(1 for item in self.last_diagnostics if item.severity == "warning")
        critical = sum(1 for item in self.last_diagnostics if item.severity == "critical") + len(self.last_codes)
        score = max(0, 100 - warnings * 12 - critical * 24)
        text = (
            f"Score de sante: {score}/100\n"
            f"Points positifs: {positives}\n"
            f"Points a surveiller: {warnings}\n"
            f"Anomalies critiques: {critical}\n\n"
            "Actions recommandees: verifier les alertes affichees, controler les niveaux, "
            "et consulter un technicien si des codes DTC restent actifs."
        )
        dialog = MDDialog(title="Rapport intelligent", text=text)
        dialog.buttons = [MDFlatButton(text="Fermer", on_release=lambda *_: dialog.dismiss())]
        dialog.open()

    def refresh(self):
        if not self.app.obd_service.is_connected() and not self.last_diagnostics:
            self._render_empty_state()

    def _render_empty_state(self):
        self.results_box.clear_widgets()
        self.codes_box.clear_widgets()
        self.results_box.add_widget(self._result_card("Pret pour diagnostic", "Lecture des codes defaut depuis le calculateur.", "normal"))
        self.codes_box.add_widget(self._result_card("Aucun code charge", "Les codes DTC apparaitront apres l'analyse.", "normal"))

    def _render_results(self, diagnostics):
        self.results_box.clear_widgets()
        for diagnostic in diagnostics:
            self.results_box.add_widget(self._result_card(diagnostic.title, diagnostic.message, diagnostic.severity))

    def _render_codes(self, codes):
        self.codes_box.clear_widgets()
        if not codes:
            self.codes_box.add_widget(self._result_card("Aucun code defaut OBD2", "L'ECU ne signale aucun DTC actif.", "normal"))
            return
        for dtc in codes:
            self.codes_box.add_widget(self._dtc_card(dtc))

    def _render_summary(self, title, message, severity, normal_count, warning_count, critical_count):
        color = status_color(severity)
        self.summary.clear_widgets()
        self.summary.line_color = with_alpha(color, 0.75)
        row = MDBoxLayout(adaptive_height=True, spacing=dp(12))
        row.add_widget(
            MDIcon(
                icon="check-circle-outline" if severity == "normal" else "close-circle-outline",
                theme_text_color="Custom",
                text_color=color,
                size_hint_x=None,
                width=dp(48),
                font_size=dp(42),
            )
        )
        copy = MDBoxLayout(orientation="vertical", adaptive_height=True, spacing=dp(6))
        copy.add_widget(
            MDLabel(
                text=title,
                theme_text_color="Custom",
                text_color=TEXT,
                font_style="H6",
                bold=True,
                size_hint_y=None,
                height=dp(28),
            )
        )
        copy.add_widget(
            MDLabel(
                text=message,
                theme_text_color="Custom",
                text_color=MUTED,
                font_style="Caption",
                adaptive_height=True,
            )
        )
        badges = MDBoxLayout(adaptive_height=True, spacing=dp(6))
        badges.add_widget(Badge(f"{normal_count} normal", GREEN))
        badges.add_widget(Badge(f"{warning_count} alerte", AMBER))
        badges.add_widget(Badge(f"{critical_count} critique", RED))
        copy.add_widget(badges)
        row.add_widget(copy)
        self.summary.add_widget(row)

    def _set_message(self, title, message, severity):
        self._render_summary(title, message, severity, 0, 0, 0)

    def _result_card(self, title, message, severity):
        color = status_color(severity)
        card = GlowCard(accent=color)
        card.size_hint_y = None
        card.height = dp(104)
        row = MDBoxLayout(spacing=dp(8))
        row.add_widget(
            MDIcon(
                icon="check-circle-outline" if severity == "normal" else "alert-outline",
                theme_text_color="Custom",
                text_color=color,
                size_hint_x=None,
                width=dp(28),
                font_size=dp(22),
            )
        )
        copy = MDBoxLayout(orientation="vertical", spacing=dp(4))
        title_row = MDBoxLayout(adaptive_height=True, spacing=dp(8))
        title_row.add_widget(
            MDLabel(text=title, theme_text_color="Custom", text_color=TEXT, font_style="Subtitle2", bold=True)
        )
        title_row.add_widget(Badge(self._severity_label(severity), color))
        copy.add_widget(title_row)
        copy.add_widget(MDLabel(text=message, theme_text_color="Custom", text_color=MUTED, font_style="Caption"))
        row.add_widget(copy)
        card.add_widget(row)
        return card

    def _dtc_card(self, dtc):
        card = GlowCard(accent=RED)
        card.size_hint_y = None
        card.height = dp(118)
        card.add_widget(
            MDBoxLayout(
                adaptive_height=True,
                spacing=dp(8),
            )
        )
        header = card.children[0]
        header.add_widget(Badge(dtc.code, RED))
        header.add_widget(Badge(dtc.severity or "critique", RED))
        card.add_widget(
            MDLabel(
                text=dtc.description,
                theme_text_color="Custom",
                text_color=TEXT,
                font_style="Subtitle2",
                bold=True,
                size_hint_y=None,
                height=dp(28),
            )
        )
        card.add_widget(
            MDLabel(
                text="Consultez un technicien avant toute remise a zero definitive.",
                theme_text_color="Custom",
                text_color=MUTED,
                font_style="Caption",
                adaptive_height=True,
            )
        )
        return card

    @staticmethod
    def _severity_label(severity):
        return {"normal": "normal", "warning": "alerte", "critical": "critique"}.get(severity, severity)
