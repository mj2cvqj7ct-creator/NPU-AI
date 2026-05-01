"""
Modern Dark Theme Stylesheet for NPU Audio Enhancer.

Provides a sleek, professional dark UI with accent colors and
smooth gradients inspired by high-end audio equipment interfaces.
"""

ACCENT_PRIMARY = "#6C5CE7"
ACCENT_SECONDARY = "#00CEC9"
ACCENT_WARM = "#E17055"
ACCENT_SUCCESS = "#00B894"
ACCENT_WARNING = "#FDCB6E"

BG_DARK = "#0D1117"
BG_MEDIUM = "#161B22"
BG_LIGHT = "#21262D"
BG_CARD = "#1C2128"
BG_HOVER = "#2D333B"

TEXT_PRIMARY = "#E6EDF3"
TEXT_SECONDARY = "#8B949E"
TEXT_MUTED = "#484F58"

BORDER_COLOR = "#30363D"
BORDER_FOCUS = "#6C5CE7"

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

/* Cards / Panels */
QGroupBox {{
    background-color: {BG_CARD};
    border: 1px solid {BORDER_COLOR};
    border-radius: 12px;
    margin-top: 16px;
    padding: 20px 16px 16px 16px;
    font-weight: 600;
    font-size: 14px;
    color: {TEXT_PRIMARY};
}}

QGroupBox::title {{
    subcontrol-origin: margin;
    subcontrol-position: top left;
    padding: 4px 12px;
    color: {ACCENT_PRIMARY};
    font-weight: 700;
    font-size: 13px;
    letter-spacing: 0.5px;
    text-transform: uppercase;
}}

/* Buttons */
QPushButton {{
    background-color: {BG_LIGHT};
    color: {TEXT_PRIMARY};
    border: 1px solid {BORDER_COLOR};
    border-radius: 8px;
    padding: 8px 20px;
    font-weight: 600;
    font-size: 13px;
    min-height: 32px;
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
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 {ACCENT_PRIMARY}, stop:1 #A29BFE);
    color: white;
    border: none;
    font-weight: 700;
}}

QPushButton#primaryButton:hover {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #7C6CF7, stop:1 #B2ABFE);
}}

QPushButton#dangerButton {{
    background-color: {ACCENT_WARM};
    color: white;
    border: none;
}}

/* Sliders */
QSlider::groove:horizontal {{
    height: 6px;
    background: {BG_LIGHT};
    border-radius: 3px;
}}

QSlider::handle:horizontal {{
    width: 18px;
    height: 18px;
    margin: -6px 0;
    background: qradialgradient(
        cx:0.5, cy:0.5, radius:0.5,
        fx:0.5, fy:0.3,
        stop:0 white, stop:1 {ACCENT_PRIMARY}
    );
    border-radius: 9px;
    border: 2px solid {ACCENT_PRIMARY};
}}

QSlider::handle:horizontal:hover {{
    border-color: {ACCENT_SECONDARY};
    background: qradialgradient(
        cx:0.5, cy:0.5, radius:0.5,
        fx:0.5, fy:0.3,
        stop:0 white, stop:1 {ACCENT_SECONDARY}
    );
}}

QSlider::sub-page:horizontal {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 {ACCENT_PRIMARY}, stop:1 {ACCENT_SECONDARY});
    border-radius: 3px;
}}

/* Combo Boxes */
QComboBox {{
    background-color: {BG_LIGHT};
    color: {TEXT_PRIMARY};
    border: 1px solid {BORDER_COLOR};
    border-radius: 8px;
    padding: 6px 12px;
    min-height: 28px;
    font-size: 13px;
}}

QComboBox:hover {{
    border-color: {ACCENT_PRIMARY};
}}

QComboBox::drop-down {{
    border: none;
    width: 28px;
}}

QComboBox QAbstractItemView {{
    background-color: {BG_MEDIUM};
    border: 1px solid {BORDER_COLOR};
    border-radius: 8px;
    selection-background-color: {ACCENT_PRIMARY};
    color: {TEXT_PRIMARY};
    padding: 4px;
}}

/* Labels */
QLabel {{
    color: {TEXT_PRIMARY};
    font-size: 13px;
}}

QLabel#sectionTitle {{
    color: {ACCENT_PRIMARY};
    font-size: 16px;
    font-weight: 700;
    letter-spacing: 0.5px;
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

/* Tab Widget */
QTabWidget::pane {{
    border: 1px solid {BORDER_COLOR};
    border-radius: 8px;
    background-color: {BG_CARD};
    padding: 8px;
}}

QTabBar::tab {{
    background-color: {BG_MEDIUM};
    color: {TEXT_SECONDARY};
    border: none;
    padding: 10px 24px;
    margin-right: 2px;
    font-weight: 600;
    font-size: 13px;
    border-top-left-radius: 8px;
    border-top-right-radius: 8px;
}}

QTabBar::tab:selected {{
    background-color: {BG_CARD};
    color: {ACCENT_PRIMARY};
    border-bottom: 2px solid {ACCENT_PRIMARY};
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

/* Progress Bar */
QProgressBar {{
    background-color: {BG_LIGHT};
    border: none;
    border-radius: 4px;
    height: 8px;
    text-align: center;
    font-size: 11px;
    color: transparent;
}}

QProgressBar::chunk {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 {ACCENT_PRIMARY}, stop:1 {ACCENT_SECONDARY});
    border-radius: 4px;
}}

/* Spin Box */
QSpinBox, QDoubleSpinBox {{
    background-color: {BG_LIGHT};
    color: {TEXT_PRIMARY};
    border: 1px solid {BORDER_COLOR};
    border-radius: 6px;
    padding: 4px 8px;
    min-height: 24px;
}}

QSpinBox:hover, QDoubleSpinBox:hover {{
    border-color: {ACCENT_PRIMARY};
}}

/* Check Box */
QCheckBox {{
    color: {TEXT_PRIMARY};
    spacing: 8px;
    font-size: 13px;
}}

QCheckBox::indicator {{
    width: 20px;
    height: 20px;
    border-radius: 4px;
    border: 2px solid {BORDER_COLOR};
    background-color: {BG_LIGHT};
}}

QCheckBox::indicator:checked {{
    background-color: {ACCENT_PRIMARY};
    border-color: {ACCENT_PRIMARY};
}}

/* Tooltips */
QToolTip {{
    background-color: {BG_MEDIUM};
    color: {TEXT_PRIMARY};
    border: 1px solid {BORDER_COLOR};
    border-radius: 6px;
    padding: 6px 10px;
    font-size: 12px;
}}

/* Status Bar */
QStatusBar {{
    background-color: {BG_MEDIUM};
    color: {TEXT_SECONDARY};
    border-top: 1px solid {BORDER_COLOR};
    font-size: 12px;
    padding: 4px;
}}

/* Menu Bar */
QMenuBar {{
    background-color: {BG_MEDIUM};
    color: {TEXT_PRIMARY};
    border-bottom: 1px solid {BORDER_COLOR};
    padding: 2px;
}}

QMenuBar::item:selected {{
    background-color: {BG_HOVER};
    border-radius: 4px;
}}

QMenu {{
    background-color: {BG_MEDIUM};
    color: {TEXT_PRIMARY};
    border: 1px solid {BORDER_COLOR};
    border-radius: 8px;
    padding: 4px;
}}

QMenu::item:selected {{
    background-color: {ACCENT_PRIMARY};
    border-radius: 4px;
}}
"""
