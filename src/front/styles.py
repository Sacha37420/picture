"""
styles.py – shared stylesheet and palette constants.
"""

MAIN_STYLE = """
QMainWindow, QWidget {
    background-color: #1e1e2e;
    color: #cdd6f4;
    font-family: "Segoe UI", sans-serif;
    font-size: 13px;
}

QFrame#panel {
    background-color: #181825;
    border-radius: 8px;
}

QLabel#section_title {
    font-size: 11px;
    font-weight: bold;
    color: #89b4fa;
    letter-spacing: 1px;
    text-transform: uppercase;
}

QPushButton {
    background-color: #313244;
    color: #cdd6f4;
    border: 1px solid #45475a;
    border-radius: 6px;
    padding: 5px 12px;
}
QPushButton:hover {
    background-color: #45475a;
    border-color: #89b4fa;
}
QPushButton:pressed {
    background-color: #89b4fa;
    color: #1e1e2e;
}
QPushButton:disabled {
    background-color: #1e1e2e;
    color: #585b70;
    border-color: #313244;
}

QPushButton#accent {
    background-color: #89b4fa;
    color: #1e1e2e;
    font-weight: bold;
    border: none;
}
QPushButton#accent:hover {
    background-color: #b4d0fb;
}

QListWidget {
    background-color: #11111b;
    border: 1px solid #313244;
    border-radius: 6px;
    padding: 4px;
}
QListWidget::item {
    padding: 6px 8px;
    border-radius: 4px;
}
QListWidget::item:selected {
    background-color: #313244;
    color: #89b4fa;
}
QListWidget::item:hover {
    background-color: #1e1e2e;
}

QScrollArea {
    border: none;
}
QScrollBar:vertical {
    background: #11111b;
    width: 8px;
    margin: 0px;
    border-radius: 4px;
}
QScrollBar::handle:vertical {
    background: #45475a;
    border-radius: 4px;
    min-height: 20px;
}
QScrollBar::handle:vertical:hover {
    background: #89b4fa;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
}

QSpinBox, QDoubleSpinBox, QComboBox {
    background-color: #11111b;
    border: 1px solid #313244;
    border-radius: 6px;
    padding: 4px 8px;
    color: #cdd6f4;
}
QSpinBox:focus, QDoubleSpinBox:focus, QComboBox:focus {
    border-color: #89b4fa;
}
QComboBox::drop-down {
    border: none;
    width: 20px;
}
QComboBox QAbstractItemView {
    background-color: #11111b;
    selection-background-color: #313244;
    border: 1px solid #45475a;
    border-radius: 6px;
}

QLabel#status {
    color: #a6e3a1;
    font-size: 11px;
}

QSplitter::handle {
    background-color: #313244;
    width: 2px;
    height: 2px;
}

QGroupBox {
    border: 1px solid #313244;
    border-radius: 6px;
    margin-top: 18px;
    padding: 8px;
    color: #89b4fa;
    font-weight: bold;
    font-size: 11px;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 8px;
    top: -2px;
}
"""

# Named colours for convenience
BLUE   = "#89b4fa"
GREEN  = "#a6e3a1"
RED    = "#f38ba8"
YELLOW = "#f9e2af"
BG     = "#1e1e2e"
BG2    = "#181825"
BG3    = "#11111b"
