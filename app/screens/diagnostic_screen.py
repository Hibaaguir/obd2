from threading import Thread

from kivy.clock import Clock
from kivy.metrics import dp, sp
from kivy.properties import BooleanProperty
from kivy.uix.anchorlayout import AnchorLayout
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.card import MDCard
from kivymd.uix.dialog import MDDialog
from kivymd.uix.gridlayout import MDGridLayout
from kivymd.uix.label import MDIcon, MDLabel

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
        self._render_summary("En attente", "Lance une lecture depuis le Dashboard pour afficher les priorites.", "normal", 0, 0, 0, 0)

        actions = MDBoxLayout(adaptive_height=True, spacing=dp(12))
        actions.add_widget(
            DiagnosticActionButton(
                text="Effacer les codes defaut",
                fill_color=with_alpha(RED, 0.08),
                line_color=with_alpha(RED, 0.28),
                text_color=RED,
                on_release=self.confirm_clear_codes,
            )
        )
        layout.add_widget(actions)

        layout.add_widget(SectionLabel("Synthese des alertes"))
        self.results_box = MDBoxLayout(orientation="vertical", adaptive_height=True, spacing=dp(12))
        layout.add_widget(self.results_box)

        layout.add_widget(SectionLabel("Detail des codes DTC"))
        self.codes_box = MDBoxLayout(orientation="vertical", adaptive_height=True, spacing=dp(12))
        layout.add_widget(self.codes_box)
        layout.add_widget(MDLabel(size_hint_y=None, height=dp(88)))
        self._render_empty_state()

    def _apply_snapshot(self, snapshot):
        diagnostics = snapshot.diagnostics
        overall = snapshot.overall_severity
        normal_count = sum(1 for item in diagnostics if item.severity == "normal")
        warning_count = sum(1 for item in diagnostics if item.severity == "warning")
        critical_count = sum(1 for item in diagnostics if item.severity == "critical")
        has_active_dtc = bool(snapshot.codes)
        title = {
            "normal": "Synthese stable",
            "warning": "Point prioritaire",
            "critical": "Priorite critique",
        }.get(overall, "Diagnostic termine")
        primary = snapshot.primary_diagnostic
        if overall == "critical":
            message = (
                "Un defaut critique a ete detecte. Verifie d'abord la cause principale ci-dessous."
                if has_active_dtc
                else "Une mesure critique a ete detectee. Verifie la cause principale ci-dessous."
            )
        elif overall == "warning":
            message = "Un point a surveiller a ete detecte. Controle recommande."
        else:
            message = "Aucune anomalie immediate n'a ete detectee avec les donnees disponibles."
        self._render_summary(
            title,
            message,
            overall,
            normal_count,
            warning_count,
            critical_count,
            snapshot.dtc_count,
            snapshot.timestamp,
            primary.title if primary else None,
            primary.message if primary else None,
        )
        self._render_results(diagnostics)
        self._render_codes(snapshot.codes)

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
            snapshot = self.app.vehicle_state_service.clear_codes_and_refresh()
            Clock.schedule_once(
                lambda *_: self._finish_clear_refresh(snapshot, None),
                0,
            )
        except Exception as exc:
            Clock.schedule_once(
                lambda *_, error=exc: self._finish_clear_refresh(None, error),
                0,
            )

    def _finish_clear_refresh(self, snapshot, error):
        self.loading = False
        if error is not None:
            self._set_message(
                "Effacement confirme",
                "Les codes ont ete effaces, mais la relecture de la synthese a echoue.",
                "warning",
            )
            return
        if snapshot is None:
            self._set_message("Lecture impossible", "Aucune donnee n'a ete recue.", "critical")
            return
        self._apply_snapshot(snapshot)

    def refresh(self):
        if not self.app.obd_service.is_connected():
            self._render_empty_state()
            return
        snapshot = self.app.vehicle_state_service.latest_snapshot
        if snapshot is not None:
            self._apply_snapshot(snapshot)
            return
        self._set_message(
            "Diagnostic en attente",
            "Aucune synthese n'est encore disponible. Lance une lecture depuis le Dashboard.",
            "normal",
        )

    def _render_empty_state(self):
        self.results_box.clear_widgets()
        self.codes_box.clear_widgets()
        self.results_box.add_widget(
            self._analysis_summary_card(
                "normal",
                "Aucune alerte prioritaire.",
                "Les mesures live et l'etat ECU ne signalent aucun point critique avec les donnees disponibles.",
            )
        )
        self.codes_box.add_widget(
            self._codes_summary_card(
                False,
                "Aucun code defaut actif.",
                "Lorsqu'un DTC est present, son detail apparait ici avec son niveau de gravite.",
            )
        )

    def _render_results(self, diagnostics):
        self.results_box.clear_widgets()
        if not diagnostics:
            self.results_box.add_widget(
                self._analysis_summary_card(
                    "normal",
                    "Aucune alerte prioritaire.",
                    "Les mesures live sont coherentes avec un fonctionnement normal sur cet echantillon.",
                )
            )
            return
        visible_diagnostics = [item for item in diagnostics if item.severity != "normal"]
        if not visible_diagnostics:
            visible_diagnostics = diagnostics[:1]
        for diagnostic in visible_diagnostics:
            self.results_box.add_widget(
                self._analysis_detail_card(
                    self._analysis_card_title(diagnostic.title),
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
        for code in codes:
            self.codes_box.add_widget(self._dtc_detail_card(code))

    def _render_summary(
        self,
        title,
        message,
        severity,
        normal_count,
        warning_count,
        critical_count,
        dtc_count,
        timestamp=None,
        primary_title=None,
        primary_message=None,
    ):
        color = status_color(severity)
        self.summary.clear_widgets()
        self.summary.adaptive_height = True
        self.summary.height = dp(0)
        self.summary.padding = (dp(16), dp(16), dp(16), dp(16))
        self.summary.spacing = dp(10)
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
                adaptive_height=True,
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

        badges = MDGridLayout(cols=2, adaptive_height=True, spacing=dp(6))
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
            adaptive_height=True,
            radius=[dp(14)],
            elevation=0,
            md_bg_color=with_alpha(color, 0.16),
            line_color=with_alpha(color, 0.55),
            padding=(dp(8), dp(6), dp(8), dp(6)),
        )
        text = MDLabel(
            text=f"{count} {label}".upper(),
            theme_text_color="Custom",
            text_color=color,
            font_style="Caption",
            bold=True,
            halign="center",
            valign="middle",
            adaptive_height=True,
        )
        text.bind(size=lambda label_widget, size: setattr(label_widget, "text_size", size))
        badge.add_widget(text)
        return badge

    def _analysis_summary_card(self, severity, title, message):
        color = status_color(severity)
        card = GlowCard(accent=color)
        card.size_hint_y = None
        card.adaptive_height = True
        card.radius = [dp(18)]
        card.padding = (dp(16), dp(14), dp(16), dp(14))
        card.spacing = dp(8)
        header = MDBoxLayout(adaptive_height=True, spacing=dp(8))
        title_label = MDLabel(
            text=title,
            theme_text_color="Custom",
            text_color=TEXT,
            font_style="Subtitle2",
            bold=True,
            size_hint_x=1,
            adaptive_height=True,
            valign="middle",
            pos_hint={"center_y": 0.5},
        )
        title_label.bind(width=lambda label, width: setattr(label, "text_size", (width, None)))
        header.add_widget(title_label)
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
        card.adaptive_height = True
        card.radius = [dp(18)]
        card.padding = (dp(16), dp(14), dp(16), dp(14))
        card.spacing = dp(10)

        header = MDBoxLayout(adaptive_height=True, spacing=dp(8))
        title_label = MDLabel(
            text=title,
            theme_text_color="Custom",
            text_color=TEXT if severity == "normal" else color,
            font_style="Subtitle2",
            bold=True,
            size_hint_x=1,
            adaptive_height=True,
            valign="middle",
            pos_hint={"center_y": 0.5},
        )
        title_label.bind(width=lambda label, width: setattr(label, "text_size", (width, None)))
        header.add_widget(title_label)
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
        card.adaptive_height = True
        card.radius = [dp(18)]
        card.padding = (dp(16), dp(14), dp(16), dp(14))
        card.spacing = dp(8)
        card.line_color = with_alpha(color, 0.75)
        header = MDBoxLayout(adaptive_height=True, spacing=dp(8))
        title_label = MDLabel(
            text="Codes DTC detectes",
            theme_text_color="Custom",
            text_color=TEXT,
            font_style="Subtitle2",
            bold=True,
            size_hint_x=1,
            adaptive_height=True,
            valign="middle",
            pos_hint={"center_y": 0.5},
        )
        title_label.bind(width=lambda label, width: setattr(label, "text_size", (width, None)))
        header.add_widget(title_label)
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
        card.adaptive_height = True
        card.radius = [dp(18)]
        card.padding = (dp(16), dp(14), dp(16), dp(14))
        card.spacing = dp(4)
        card.line_color = with_alpha(color, 0.75) if severity != "normal" else with_alpha(BLUE, 0)

        header = MDBoxLayout(adaptive_height=True, spacing=dp(8))
        code_label = MDLabel(
            text=code.code,
            theme_text_color="Custom",
            text_color=color,
            font_style="H5",
            font_size=sp(26),
            bold=True,
            size_hint_x=1,
            adaptive_height=True,
            halign="left",
            valign="middle",
        )
        code_label.bind(width=lambda label, width: setattr(label, "text_size", (width, None)))
        header.add_widget(code_label)
        header.add_widget(self._dtc_severity_badge(self._severity_label(severity), color))
        card.add_widget(header)

        title_label = MDLabel(
            text=self._dtc_title(code),
            theme_text_color="Custom",
            text_color=TEXT,
            font_style="Subtitle2",
            bold=True,
            adaptive_height=True,
            halign="left",
            valign="middle",
        )
        title_label.bind(width=lambda label, width: setattr(label, "text_size", (width, None)))
        card.add_widget(title_label)

        summary_label = MDLabel(
            text=self._dtc_summary(code.code, severity),
            theme_text_color="Custom",
            text_color=MUTED,
            font_style="Caption",
            adaptive_height=True,
            halign="left",
            valign="middle",
        )
        summary_label.bind(width=lambda label, width: setattr(label, "text_size", (width, None)))
        card.add_widget(summary_label)
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
        return Badge(text, color)

    @staticmethod
    def _analysis_card_title(title):
        normalized = str(title or "").strip().lower()
        replacements = {
            "code dtc critique actif": "Defauts DTC actifs",
            "code dtc actif": "Defauts DTC actifs",
        }
        return replacements.get(normalized, title)

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
                text="Synthese des anomalies detectees",
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
