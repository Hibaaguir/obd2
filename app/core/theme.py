APP_BG = (0.008, 0.018, 0.022, 1)
PANEL_BG = (0.035, 0.055, 0.105, 1)
PANEL_DARK = (0.018, 0.028, 0.052, 1)
PANEL_ALT = (0.055, 0.09, 0.17, 1)
BORDER = (0.08, 0.15, 0.29, 1)
BORDER_ACTIVE = (0.22, 0.43, 0.82, 1)

TEXT = (0.92, 0.95, 1.0, 1)
MUTED = (0.43, 0.52, 0.68, 1)
DIM = (0.25, 0.31, 0.45, 1)

BLUE = (0.27, 0.51, 1.0, 1)
GREEN = (0.0, 0.86, 0.48, 1)
AMBER = (1.0, 0.66, 0.16, 1)
RED = (1.0, 0.22, 0.38, 1)
CYAN = (0.12, 0.82, 0.95, 1)


def with_alpha(color, alpha):
    return color[:3] + (alpha,)


def status_color(status: str):
    normalized = (status or "").lower()
    if normalized in {"critical", "critique", "elevee"}:
        return RED
    if normalized in {"warning", "alerte", "moyenne"}:
        return AMBER
    if normalized in {"normal", "ok", "faible"}:
        return GREEN
    return BLUE
