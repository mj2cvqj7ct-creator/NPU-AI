"""
Modern Dark Theme Stylesheet for NPU Audio Enhancer (v3).

Premium glassmorphism-inspired dark UI with sophisticated accent colors,
gradient transitions, and depth effects befitting high-end audio equipment.
"""

# --- Accent Palette ---
ACCENT_PRIMARY = "#6C5CE7"
ACCENT_PRIMARY_LIGHT = "#A29BFE"
ACCENT_SECONDARY = "#00CEC9"
ACCENT_SECONDARY_LIGHT = "#55EFC4"
ACCENT_WARM = "#E17055"
ACCENT_SUCCESS = "#00B894"
ACCENT_WARNING = "#FDCB6E"
ACCENT_ROSE = "#FD79A8"

# --- Background Palette (deep, layered) ---
BG_DARK = "#0A0E14"
BG_MEDIUM = "#121820"
BG_LIGHT = "#1A2030"
BG_CARD = "#161D28"
BG_HOVER = "#2A3240"
BG_ELEVATED = "#1E2636"

# --- Text ---
TEXT_PRIMARY = "#E6EDF3"
TEXT_SECONDARY = "#8B949E"
TEXT_MUTED = "#484F58"
TEXT_ACCENT = "#A29BFE"

# --- Borders ---
BORDER_COLOR = "#2A3040"
BORDER_FOCUS = "#6C5CE7"
BORDER_GLOW = "#6C5CE750"

DARK_THEME = f"""
QMainWindow {{
    background-color: {BG_DARK};
    color: {TEXT_PRIMARY};
}}

QWidget {{
    background-color: transparent;
    color: {TEXT_PRIMARY};
    font-family: 'Segoe UI', 'SF Pro Display', 'Helvetica Neue', Arial, sans-serif;
    font-size: 13px;
}}

/* Cards / Panels - Glassmorphism style */
QGroupBox {{
    background-color: {BG_CARD};
    border: 1px solid {BORDER_COLOR};
    border-radius: 14px;
    margin-top: 18px;
    padding: 22px 18px 18px 18px;
    font-weight: 600;
    font-size: 14px;
    color: {TEXT_PRIMARY};
}}

QGroupBox::title {{
    subcontrol-origin: margin;
    subcontrol-position: top left;
    padding: 4px 14px;
    color: {ACCENT_PRIMARY_LIGHT};
    font-weight: 700;
    font-size: 12px;
    letter-spacing: 1.2px;
    text-transform: uppercase;
}}

/* Buttons - Premium feel */
QPushButton {{
    background-color: {BG_LIGHT};
    color: {TEXT_PRIMARY};
    border: 1px solid {BORDER_COLOR};
    border-radius: 10px;
    padding: 8px 22px;
    font-weight: 600;
    font-size: 13px;
    min-height: 34px;
}}

QPushButton:hover {{
    background-color: {BG_HOVER};
    border-color: {ACCENT_PRIMARY};
}}

QPushButton:pressed {{
    background-color: {ACCENT_PRIMARY};
    color: white;
}}

QPushButton:checked {{
    background-color: {ACCENT_PRIMARY};
    color: white;
    border-color: {ACCENT_PRIMARY};
}}

QPushButton#primaryButton {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
        stop:0 {ACCENT_PRIMARY}, stop:0.5 #7E6DF0, stop:1 {ACCENT_PRIMARY_LIGHT});
    color: white;
    border: none;
    font-weight: 700;
    font-size: 14px;
    border-radius: 12px;
    min-height: 38px;
}}

QPushButton#primaryButton:hover {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
        stop:0 #7C6CF7, stop:0.5 #8E7EFA, stop:1 #B2ABFE);
}}

QPushButton#secondaryButton {{
    background-color: {BG_ELEVATED};
    color: {ACCENT_SECONDARY_LIGHT};
    border: 1px solid {ACCENT_SECONDARY}60;
    border-radius: 12px;
    font-weight: 600;
    font-size: 13px;
    min-height: 38px;
    padding: 8px 16px;
}}

QPushButton#secondaryButton:hover {{
    background-color: {BG_HOVER};
    border-color: {ACCENT_SECONDARY};
}}

QPushButton#secondaryButton:disabled {{
    color: {TEXT_MUTED};
    border-color: {BORDER_COLOR};
}}

QPushButton#dangerButton {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 {ACCENT_WARM}, stop:1 #E84393);
    color: white;
    border: none;
    border-radius: 10px;
}}

QPushButton#successButton {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 {ACCENT_SUCCESS}, stop:1 {ACCENT_SECONDARY});
    color: white;
    border: none;
    border-radius: 10px;
}}

/* Sliders - Refined track and handle */
QSlider::groove:horizontal {{
    height: 6px;
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 {BG_LIGHT}, stop:1 {BG_HOVER});
    border-radius: 3px;
}}

QSlider::handle:horizontal {{
    width: 18px;
    height: 18px;
    margin: -6px 0;
    background: qradialgradient(
        cx:0.5, cy:0.5, radius:0.5,
        fx:0.4, fy:0.3,
        stop:0 white, stop:0.7 {ACCENT_PRIMARY_LIGHT}, stop:1 {ACCENT_PRIMARY}
    );
    border-radius: 9px;
    border: 2px solid {ACCENT_PRIMARY};
}}

QSlider::handle:horizontal:hover {{
    border-color: {ACCENT_SECONDARY};
    background: qradialgradient(
        cx:0.5, cy:0.5, radius:0.5,
        fx:0.4, fy:0.3,
        stop:0 white, stop:0.7 {ACCENT_SECONDARY_LIGHT}, stop:1 {ACCENT_SECONDARY}
    );
}}

QSlider::sub-page:horizontal {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 {ACCENT_PRIMARY}, stop:0.6 {ACCENT_SECONDARY}, stop:1 {ACCENT_SECONDARY_LIGHT});
    border-radius: 3px;
}}

/* Combo Boxes */
QComboBox {{
    background-color: {BG_LIGHT};
    color: {TEXT_PRIMARY};
    border: 1px solid {BORDER_COLOR};
    border-radius: 10px;
    padding: 6px 14px;
    min-height: 30px;
    font-size: 13px;
}}

QComboBox:hover {{
    border-color: {ACCENT_PRIMARY};
}}

QComboBox::drop-down {{
    border: none;
    width: 30px;
}}

QComboBox QAbstractItemView {{
    background-color: {BG_MEDIUM};
    border: 1px solid {BORDER_COLOR};
    border-radius: 10px;
    selection-background-color: {ACCENT_PRIMARY};
    color: {TEXT_PRIMARY};
    padding: 6px;
}}

/* Labels */
QLabel {{
    color: {TEXT_PRIMARY};
    font-size: 13px;
}}

QLabel#sectionTitle {{
    color: {ACCENT_PRIMARY_LIGHT};
    font-size: 17px;
    font-weight: 700;
    letter-spacing: 0.8px;
}}

QLabel#statusLabel {{
    color: {TEXT_SECONDARY};
    font-size: 12px;
}}

QLabel#valueLabel {{
    color: {ACCENT_SECONDARY};
    font-size: 14px;
    font-weight: 600;
    font-family: 'JetBrains Mono', 'Cascadia Code', 'Consolas', monospace;
}}

QLabel#headerTitle {{
    color: {TEXT_PRIMARY};
    font-size: 20px;
    font-weight: 800;
    letter-spacing: 1.5px;
}}

QLabel#npuBadge {{
    color: {ACCENT_SUCCESS};
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 0.5px;
    padding: 3px 10px;
    border: 1px solid {ACCENT_SUCCESS};
    border-radius: 10px;
}}

/* Tab Widget - Modern pill-style tabs */
QTabWidget::pane {{
    border: 1px solid {BORDER_COLOR};
    border-radius: 12px;
    background-color: {BG_CARD};
    padding: 10px;
}}

QTabBar::tab {{
    background-color: {BG_MEDIUM};
    color: {TEXT_SECONDARY};
    border: none;
    padding: 10px 26px;
    margin-right: 3px;
    font-weight: 600;
    font-size: 13px;
    border-top-left-radius: 10px;
    border-top-right-radius: 10px;
}}

QTabBar::tab:selected {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 {BG_CARD}, stop:1 {BG_ELEVATED});
    color: {ACCENT_PRIMARY_LIGHT};
    border-bottom: 3px solid {ACCENT_PRIMARY};
}}

QTabBar::tab:hover:!selected {{
    background-color: {BG_LIGHT};
    color: {TEXT_PRIMARY};
}}

/* Scroll Bar */
QScrollBar:vertical {{
    background-color: {BG_DARK};
    width: 8px;
    border-radius: 4px;
}}

QScrollBar::handle:vertical {{
    background-color: {BG_HOVER};
    border-radius: 4px;
    min-height: 30px;
}}

QScrollBar::handle:vertical:hover {{
    background-color: {TEXT_MUTED};
}}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0px;
}}

/* Progress Bar - Animated gradient feel */
QProgressBar {{
    background-color: {BG_LIGHT};
    border: none;
    border-radius: 5px;
    height: 10px;
    text-align: center;
    font-size: 11px;
    color: transparent;
}}

QProgressBar::chunk {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 {ACCENT_PRIMARY}, stop:0.5 {ACCENT_SECONDARY}, stop:1 {ACCENT_SUCCESS});
    border-radius: 5px;
}}

/* Spin Box */
QSpinBox, QDoubleSpinBox {{
    background-color: {BG_LIGHT};
    color: {TEXT_PRIMARY};
    border: 1px solid {BORDER_COLOR};
    border-radius: 8px;
    padding: 4px 10px;
    min-height: 26px;
}}

QSpinBox:hover, QDoubleSpinBox:hover {{
    border-color: {ACCENT_PRIMARY};
}}

QSpinBox:focus, QDoubleSpinBox:focus {{
    border-color: {ACCENT_PRIMARY};
}}

/* Check Box */
QCheckBox {{
    color: {TEXT_PRIMARY};
    spacing: 8px;
    font-size: 13px;
}}

QCheckBox::indicator {{
    width: 22px;
    height: 22px;
    border-radius: 6px;
    border: 2px solid {BORDER_COLOR};
    background-color: {BG_LIGHT};
}}

QCheckBox::indicator:checked {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
        stop:0 {ACCENT_PRIMARY}, stop:1 {ACCENT_PRIMARY_LIGHT});
    border-color: {ACCENT_PRIMARY};
}}

/* Tooltips */
QToolTip {{
    background-color: {BG_MEDIUM};
    color: {TEXT_PRIMARY};
    border: 1px solid {BORDER_COLOR};
    border-radius: 8px;
    padding: 8px 12px;
    font-size: 12px;
}}

/* Status Bar */
QStatusBar {{
    background-color: {BG_MEDIUM};
    color: {TEXT_SECONDARY};
    border-top: 1px solid {BORDER_COLOR};
    font-size: 12px;
    padding: 4px 8px;
}}

/* Menu Bar */
QMenuBar {{
    background-color: {BG_MEDIUM};
    color: {TEXT_PRIMARY};
    border-bottom: 1px solid {BORDER_COLOR};
    padding: 3px;
}}

QMenuBar::item:selected {{
    background-color: {BG_HOVER};
    border-radius: 6px;
}}

QMenu {{
    background-color: {BG_MEDIUM};
    color: {TEXT_PRIMARY};
    border: 1px solid {BORDER_COLOR};
    border-radius: 10px;
    padding: 6px;
}}

QMenu::item:selected {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 {ACCENT_PRIMARY}, stop:1 {ACCENT_PRIMARY_LIGHT});
    border-radius: 6px;
}}

/* Splitter */
QSplitter::handle {{
    background-color: {BORDER_COLOR};
    width: 2px;
    margin: 4px;
    border-radius: 1px;
}}

QSplitter::handle:hover {{
    background-color: {ACCENT_PRIMARY};
}}

/* Frame */
QFrame#separator {{
    background-color: {BORDER_COLOR};
    max-height: 1px;
}}
"""
