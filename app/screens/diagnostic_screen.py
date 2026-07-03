from threading import Thread

from kivy.clock import Clock
from kivy.metrics import dp, sp
from kivy.properties import BooleanProperty
from kivy.uix.anchorlayout import AnchorLayout
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.card import MDCard
from kivymd.uix.dialog import MDDialog
from kivymd.uix.label import MDIcon, MDLabel

from app.core.measurement_mapper import measurement_from_readings
from app.core.theme import AMBER, BLUE, GREEN, MUTED, PANEL_BG, RED, TEXT, status_color, with_alpha
from app.screens.base_screen import BaseScreen
from app.widgets.ui_components import Badge, GlowCard, SectionLabel


class DiagnosticActionButton(MDCard):
    disabled = BooleanProperty(False)

    def __init__(self, text: str, text_color=TEXT, fill_color=None, line_color=None, on_release=None, **kwargs):
        self.on_release_callback = on_release
        super().__init__(**kwargs)
        self.orientation = "vertical"
        self.padding = (dp(14), 0, dp(14), 0)
        self.radius = [dp(14)]
        self.elevation = 0
        self.size_hint = (1, None)
        self.height = dp(48)
        self.md_bg_color = fill_color or with_alpha(BLUE, 0.18)
        self.line_color = line_color or with_alpha(BLUE, 0)

        anchor = AnchorLayout(anchor_x="center", anchor_y="center")
        self.label = MDLabel(
            text=text,
            theme_text_color="Custom",
            text_color=text_color,
            font_style="Button",
            bold=True,
            halign="center",
            valign="middle",
            size_hint=(None, None),
        )
        self.label.bind(texture_size=self._sync_label_size)
        anchor.add_widget(self.label)
        self.add_widget(anchor)

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
    def _sync_label_size(label, _texture_size):
        label.text_size = (None, None)
        label.width = max(dp(1), label.texture_size[0])
        label.height = max(dp(1), label.texture_size[1])


class DiagnosticDialogButton(MDCard):
    disabled = BooleanProperty(False)

    def __init__(self, text: str, text_color=TEXT, fill_color=None, line_color=None, on_release=None, **kwargs):
        self.on_release_callback = on_release
        super().__init__(**kwargs)
        self.orientation = "vertical"
        self.padding = (dp(14), 0, dp(14), 0)
        self.radius = [dp(12)]
        self.elevation = 0
        self.size_hint = (1, None)
        self.height = dp(44)
        self.md_bg_color = fill_color or (0, 0, 0, 0)
        self.line_color = line_color or with_alpha(MUTED, 0.4)

        anchor = AnchorLayout(anchor_x="center", anchor_y="center")
        self.label = MDLabel(
            text=text,
            theme_text_color="Custom",
            text_color=text_color,
            font_style="Button",
            bold=True,
            halign="center",
            valign="middle",
            size_hint=(None, None),
        )
        self.label.bind(texture_size=self._sync_label_size)
        anchor.add_widget(self.label)
        self.add_widget(anchor)

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
    def _sync_label_size(label, _texture_size):
        label.text_size = (None, None)
        label.width = max(dp(1), label.texture_size[0])
        label.height = max(dp(1), label.texture_size[1])


class DiagnosticScreen(BaseScreen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.clear_dialog = None
        self.loading = False

        layout = self.build_page()
        layout.add_widget(self._build_header())

        self.summary = GlowCard(accent=BLUE)
        self.summary.size_hint_y = None
        self.summary.height = dp(154)
        layout.add_widget(self.summary)
        self._render_summary("En attente", "Lance une lecture pour analyser l'ECU.", "normal", 0, 0, 0, 0)

        actions = MDBoxLayout(adaptive_height=True, spacing=dp(12))
        actions.add_widget(
            DiagnosticActionButton(
                text="Lire les codes",
                fill_color=with_alpha(BLUE, 0.86),
                line_color=with_alpha(BLUE, 0),
                text_color=TEXT,
                on_release=self.scan_codes,
            )
        )
        actions.add_widget(
            DiagnosticActionButton(
                text="Effacer les codes",
                fill_color=with_alpha(RED, 0.22),
                line_color=with_alpha(RED, 0.45),
                text_color=RED,
                on_release=self.confirm_clear_codes,
            )
        )
        layout.add_widget(actions)

        layout.add_widget(SectionLabel("Resultats de l'analyse"))
        self.results_box = MDBoxLayout(orientation="vertical", adaptive_height=True, spacing=dp(12))
        layout.add_widget(self.results_box)

        layout.add_widget(SectionLabel("Codes defaut DTC"))
        self.codes_box = MDBoxLayout(orientation="vertical", adaptive_height=True, spacing=dp(12))
        layout.add_widget(self.codes_box)
        layout.add_widget(MDLabel(size_hint_y=None, height=dp(88)))
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
            diagnostics = self.app.diagnostic_service.analyze(readings, codes)
            overall = self.app.diagnostic_service.overall_severity(diagnostics)
            main_issue = diagnostics[0].title if diagnostics else "Etat normal"
            summary = diagnostics[0].message if diagnostics else "Aucune anomalie detectee avec les donnees disponibles."
            self.app.database.save_history_snapshot(
                measurement_from_readings(readings),
                diagnostic_status=overall,
                main_issue=main_issue,
                diagnostic_summary=summary,
                dtc_codes=codes,
            )
        except Exception as exc:
            self._set_message("Lecture impossible", str(exc), "critical")
            return

        normal_count = sum(1 for item in diagnostics if item.severity == "normal")
        warning_count = sum(1 for item in diagnostics if item.severity == "warning")
        critical_count = sum(1 for item in diagnostics if item.severity == "critical")
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
        self._render_summary(title, message, overall, normal_count, warning_count, critical_count, len(codes))
        self._render_results(diagnostics)
        self._render_codes(codes)

    def confirm_clear_codes(self, *_):
        if not self.app.obd_service.is_connected():
            self._set_message("Connexion requise", "Aucun adaptateur OBD2 connecte.", "warning")
            return
        content = MDBoxLayout(
            orientation="vertical",
            adaptive_height=True,
            spacing=dp(14),
            padding=(dp(22), dp(22), dp(22), dp(22)),
        )
        content.add_widget(
            MDLabel(
                text="Effacer les codes defaut ?",
                theme_text_color="Custom",
                text_color=TEXT,
                font_style="H6",
                font_size=dp(20),
                bold=True,
                size_hint_y=None,
                height=dp(28),
            )
        )
        badge_row = MDBoxLayout(size_hint_y=None, height=dp(28))
        badge_row.add_widget(Badge("Action sensible", AMBER))
        badge_row.add_widget(MDBoxLayout())
        content.add_widget(badge_row)
        warning = MDLabel(
            text=(
                "Cette action supprimera les codes defaut enregistres dans l'ECU.\n\n"
                "Elle peut eteindre certains voyants du tableau de bord, "
                "mais ne repare pas la cause du probleme."
            ),
            theme_text_color="Custom",
            text_color=MUTED,
            font_style="Caption",
            line_height=1.35,
            adaptive_height=True,
        )
        warning.bind(width=lambda label, width: setattr(label, "text_size", (width, None)))
        content.add_widget(warning)

        buttons = MDBoxLayout(size_hint_y=None, height=dp(44), spacing=dp(10))
        buttons.add_widget(
            DiagnosticDialogButton(
                text="Annuler",
                text_color=TEXT,
                fill_color=(0, 0, 0, 0),
                line_color=with_alpha(MUTED, 0.45),
                on_release=lambda *_: self.clear_dialog.dismiss(),
            )
        )
        buttons.add_widget(
            DiagnosticDialogButton(
                text="Effacer",
                text_color=RED,
                fill_color=with_alpha(RED, 0.22),
                line_color=with_alpha(RED, 0.45),
                on_release=self.clear_codes,
            )
        )
        content.add_widget(buttons)

        self.clear_dialog = MDDialog(
            type="custom",
            content_cls=content,
            auto_dismiss=False,
        )
        self.clear_dialog.md_bg_color = PANEL_BG
        self.clear_dialog.radius = [dp(18), dp(18), dp(18), dp(18)]
        self.clear_dialog.line_color = with_alpha(RED, 0.28)
        self.clear_dialog.width = min(self.width * 0.9, dp(420))
        self.clear_dialog.open()

    def clear_codes(self, *_):
        if self.clear_dialog:
            self.clear_dialog.dismiss()
            self.clear_dialog = None
        service = self.app.obd_service
        try:
            success = service.clear_error_codes()
        except Exception as exc:
            self._set_message("Effacement impossible", str(exc), "critical")
            return
        if not success:
            self._set_message(
                "Non confirme",
                "Effacement non confirme par l'ECU.",
                "warning",
            )
            return

        self.loading = True
        self._set_message(
            "Codes effaces",
            "Effacement confirme. Actualisation du diagnostic en cours.",
            "normal",
        )
        Thread(target=self._refresh_after_clear_worker, daemon=True).start()

    def _refresh_after_clear_worker(self):
        try:
            service = self.app.obd_service
            readings = service.read_live_data()
            codes = service.read_error_codes()
            Clock.schedule_once(
                lambda *_: self._finish_clear_refresh(readings, codes, None),
                0,
            )
        except Exception as exc:
            Clock.schedule_once(
                lambda *_, error=exc: self._finish_clear_refresh([], [], error),
                0,
            )

    def _finish_clear_refresh(self, readings, codes, error):
        self.loading = False
        if error is not None:
            self._set_message(
                "Effacement confirme",
                "Les codes ont ete effaces, mais la relecture du diagnostic a echoue.",
                "warning",
            )
            return
        self._finish_scan(readings, codes, None)

    def refresh(self):
        if not self.app.obd_service.is_connected():
            self._render_empty_state()

    def _render_empty_state(self):
        self.results_box.clear_widgets()
        self.codes_box.clear_widgets()
        self.results_box.add_widget(
            self._analysis_summary_card(
                "normal",
                "Aucune anomalie detectee.",
                "Les mesures live et l'etat ECU ne signalent aucun point critique avec les donnees disponibles.",
            )
        )
        self.codes_box.add_widget(
            self._codes_summary_card(
                False,
                "Aucun code defaut actif.",
                "Quand un DTC est present, l'application doit afficher le code, sa gravite et sa description.",
            )
        )

    def _render_results(self, diagnostics):
        self.results_box.clear_widgets()
        if not diagnostics:
            self.results_box.add_widget(
                self._analysis_summary_card(
                    "normal",
                    "Aucune anomalie detectee.",
                    "Les mesures live sont coherentes avec un fonctionnement normal sur cet echantillon.",
                )
            )
            return
        overall = self.app.diagnostic_service.overall_severity(diagnostics)
        title = {
            "normal": "Resultat global stable",
            "warning": "Resultat global a surveiller",
            "critical": "Resultat global critique",
        }.get(overall, "Analyse terminee")
        detail = {
            "normal": "Aucune anomalie immediate n'a ete deduite des mesures live.",
            "warning": "Certaines mesures meritent un controle ou une verification complementaire.",
            "critical": "Des anomalies importantes ont ete detectees et doivent etre verifiees rapidement.",
        }.get(overall, "Analyse terminee.")
        self.results_box.add_widget(self._analysis_summary_card(overall, title, detail))
        for diagnostic in diagnostics:
            self.results_box.add_widget(
                self._analysis_detail_card(
                    diagnostic.title,
                    diagnostic.message,
                    diagnostic.severity,
                )
            )

    def _render_codes(self, codes):
        self.codes_box.clear_widgets()
        if not codes:
            self.codes_box.add_widget(
                self._codes_summary_card(
                    False,
                    "Aucun code defaut actif.",
                    "Aucun DTC n'est actuellement remonte par l'ECU.",
                )
            )
            return
        critical_codes = sum(1 for code in codes if self._normalize_severity(code.severity) == "critical")
        warning_codes = sum(1 for code in codes if self._normalize_severity(code.severity) == "warning")
        summary = f"{len(codes)} code(s) detecte(s)."
        detail = (
            f"{critical_codes} critique(s), {warning_codes} a surveiller. "
            "Chaque code ci-dessous doit afficher son identifiant, sa description et son niveau de gravite."
        )
        self.codes_box.add_widget(self._codes_summary_card(True, summary, detail))
        for code in codes:
            self.codes_box.add_widget(self._dtc_detail_card(code))

    def _render_summary(self, title, message, severity, normal_count, warning_count, critical_count, dtc_count):
        color = status_color(severity)
        self.summary.clear_widgets()
        self.summary.height = dp(154)
        self.summary.padding = (dp(16), dp(16), dp(16), dp(16))
        self.summary.spacing = dp(12)
        self.summary.radius = [dp(18)]
        self.summary.line_color = with_alpha(GREEN, 0.75) if severity == "normal" else with_alpha(color, 0.75)

        copy = MDBoxLayout(orientation="vertical", adaptive_height=True, spacing=dp(8))
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

        badges = MDBoxLayout(size_hint_y=None, height=dp(36), spacing=dp(6))
        badges.add_widget(self._summary_stat_badge(normal_count, "normal", GREEN))
        badges.add_widget(self._summary_stat_badge(warning_count, "alerte", AMBER))
        badges.add_widget(self._summary_stat_badge(critical_count, "critique", RED))
        badges.add_widget(self._summary_stat_badge(dtc_count, "DTC", RED if dtc_count else BLUE))
        copy.add_widget(badges)
        self.summary.add_widget(copy)

    def _set_message(self, title, message, severity):
        self._render_summary(title, message, severity, 0, 0, 0, 0)

    def _summary_stat_badge(self, count, label, color):
        badge = MDCard(
            orientation="vertical",
            size_hint=(1, None),
            height=dp(36),
            radius=[dp(14)],
            elevation=0,
            md_bg_color=with_alpha(color, 0.16),
            line_color=with_alpha(color, 0.55),
            padding=(dp(6), 0, dp(6), 0),
        )
        text = MDLabel(
            text=f"{count} {label}".upper(),
            theme_text_color="Custom",
            text_color=color,
            font_style="Caption",
            bold=True,
            halign="center",
            valign="middle",
            shorten=True,
            shorten_from="right",
        )
        text.bind(size=lambda label_widget, size: setattr(label_widget, "text_size", size))
        badge.add_widget(text)
        return badge

    def _analysis_summary_card(self, severity, title, message):
        color = status_color(severity)
        card = GlowCard(accent=color)
        card.size_hint_y = None
        card.height = dp(112)
        card.radius = [dp(18)]
        card.padding = (dp(16), dp(14), dp(16), dp(14))
        card.spacing = dp(8)
        header = MDBoxLayout(size_hint_y=None, height=dp(28), spacing=dp(8))
        title_label = MDLabel(
            text=title,
            theme_text_color="Custom",
            text_color=TEXT,
            font_style="Subtitle2",
            bold=True,
        )
        title_label.bind(size=lambda label, size: setattr(label, "text_size", size))
        header.add_widget(title_label)
        header.add_widget(MDBoxLayout())
        header.add_widget(self._dtc_severity_badge(self._severity_label(severity), color))
        card.add_widget(header)
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

    def _analysis_detail_card(self, title, message, severity):
        color = status_color(severity)
        card = GlowCard(accent=color)
        card.size_hint_y = None
        card.height = dp(108)
        card.radius = [dp(18)]
        card.padding = (dp(16), dp(14), dp(16), dp(14))
        card.spacing = dp(10)

        header = MDBoxLayout(size_hint_y=None, height=dp(28), spacing=dp(8))
        title_label = MDLabel(
            text=title,
            theme_text_color="Custom",
            text_color=TEXT if severity == "normal" else color,
            font_style="Subtitle2",
            bold=True,
            size_hint_y=None,
            height=dp(28),
            valign="middle",
            shorten=True,
            shorten_from="right",
        )
        title_label.bind(size=lambda label, size: setattr(label, "text_size", size))
        header.add_widget(title_label)
        header.add_widget(MDBoxLayout())
        header.add_widget(self._dtc_severity_badge(self._severity_label(severity), color))
        card.add_widget(header)
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

    def _codes_summary_card(self, has_codes, message, detail):
        color = RED if has_codes else GREEN
        card = GlowCard(accent=color)
        card.size_hint_y = None
        card.height = dp(116)
        card.radius = [dp(18)]
        card.padding = (dp(16), dp(14), dp(16), dp(14))
        card.spacing = dp(8)
        card.line_color = with_alpha(color, 0.75)
        header = MDBoxLayout(size_hint_y=None, height=dp(28), spacing=dp(8))
        title_label = MDLabel(
            text="Codes defaut DTC",
            theme_text_color="Custom",
            text_color=TEXT,
            font_style="Subtitle2",
            bold=True,
        )
        title_label.bind(size=lambda label, size: setattr(label, "text_size", size))
        header.add_widget(title_label)
        header.add_widget(MDBoxLayout())
        header.add_widget(Badge(f"{message.split()[0]} DTC" if has_codes else "aucun", color))
        card.add_widget(header)
        card.add_widget(
            MDLabel(
                text=message,
                theme_text_color="Custom",
                text_color=MUTED,
                font_style="Caption",
                adaptive_height=True,
            )
        )
        card.add_widget(
            MDLabel(
                text=detail,
                theme_text_color="Custom",
                text_color=with_alpha(MUTED, 0.82),
                font_style="Caption",
                adaptive_height=True,
            )
        )
        return card

    def _dtc_detail_card(self, code):
        severity = self._normalize_severity(code.severity)
        color = status_color(severity)
        card = GlowCard(accent=color)
        card.size_hint_y = None
        card.height = dp(128)
        card.radius = [dp(18)]
        card.padding = (dp(16), dp(14), dp(16), dp(14))
        card.spacing = dp(6)
        card.line_color = with_alpha(color, 0.75)

        header = MDBoxLayout(size_hint_y=None, height=dp(44), spacing=dp(8))
        identity = MDBoxLayout(orientation="vertical", spacing=dp(2))
        code_label = MDLabel(
            text=code.code,
            theme_text_color="Custom",
            text_color=color,
            font_style="H6",
            font_size=sp(22),
            bold=True,
            size_hint_y=None,
            height=dp(24),
            halign="left",
            valign="middle",
        )
        code_label.bind(size=lambda label, size: setattr(label, "text_size", size))
        identity.add_widget(code_label)
        identity.add_widget(
            MDLabel(
                text=self._dtc_family_label(code.code),
                theme_text_color="Custom",
                text_color=with_alpha(MUTED, 0.88),
                font_style="Caption",
                size_hint_y=None,
                height=dp(16),
                halign="left",
                valign="middle",
            )
        )
        header.add_widget(identity)
        header.add_widget(MDBoxLayout())
        header.add_widget(self._dtc_severity_badge(self._severity_label(severity), color))
        card.add_widget(header)

        card.add_widget(
            MDLabel(
                text=self._dtc_title(code),
                theme_text_color="Custom",
                text_color=TEXT,
                font_style="Subtitle2",
                adaptive_height=True,
                bold=True,
            )
        )
        card.add_widget(
            MDLabel(
                text=self._dtc_summary(code.code, severity),
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

    @staticmethod
    def _normalize_severity(severity):
        normalized = (severity or "").strip().lower()
        if normalized in {"critical", "critique", "elevee", "haute"}:
            return "critical"
        if normalized in {"warning", "alerte", "moyenne"}:
            return "warning"
        return "normal"

    @staticmethod
    def _dtc_family_label(code):
        prefix = (code or "").strip().upper()[:1]
        return {
            "P": "motopropulseur",
            "B": "carrosserie",
            "C": "chassis",
            "U": "reseau",
        }.get(prefix, "systeme")

    @classmethod
    def _dtc_summary(cls, code, severity):
        family = cls._dtc_family_label(code)
        if severity == "critical":
            return f"Defaut critique sur le systeme {family}; verification rapide recommandee."
        if severity == "warning":
            return f"Defaut a surveiller sur le systeme {family}; controle recommande."
        return f"Code memorise sur le systeme {family}; aucun niveau critique detecte."

    @staticmethod
    def _dtc_title(code):
        return code.description or "Description non disponible."

    @staticmethod
    def _dtc_severity_badge(text, color):
        badge = MDCard(
            orientation="vertical",
            size_hint=(None, None),
            height=dp(28),
            radius=[dp(14)],
            elevation=0,
            md_bg_color=with_alpha(color, 0.16),
            line_color=with_alpha(color, 0.55),
            padding=(dp(14), 0, dp(14), 0),
        )
        anchor = AnchorLayout(anchor_x="center", anchor_y="center")
        label = MDLabel(
            text=text.upper(),
            theme_text_color="Custom",
            text_color=color,
            font_style="Caption",
            bold=True,
            halign="center",
            valign="middle",
            size_hint=(None, None),
        )
        label.bind(texture_size=lambda widget, texture_size: setattr(badge, "width", texture_size[0] + dp(28)))
        label.bind(texture_size=lambda widget, texture_size: setattr(widget, "size", texture_size))
        anchor.add_widget(label)
        badge.add_widget(anchor)
        badge.width = dp(110)
        return badge

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
            icon="clipboard-pulse-outline",
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
                text="Diagnostic ECU",
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
                text="Analyse systeme vehicule hybride",
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
