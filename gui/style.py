"""Dark-Palette (verbindlich) + App-Stylesheet."""
BG = "#16181d"; PANEL = "#1b1e24"; BORDER = "#262a32"; TEXT = "#d7dae0"; MUTED = "#aab2bf"
ACCENT = "#8ab4f8"; SELECT = "#2b3a55"; OK = "#5fb36a"; ERR = "#d9534f"
# Farbe je Verbindung (Out→In-Paarung), dunkeltauglich; Index stabil über Namens-Hash
ROUTE_COLORS = ["#8ab4f8", "#98c379", "#d19a66", "#c586c0", "#56b6c2", "#e5c07b", "#e06c75", "#61afef"]


def route_color(out: str, in_: str) -> str:
    import zlib
    return ROUTE_COLORS[zlib.crc32(f"{out}\x00{in_}".encode()) % len(ROUTE_COLORS)]

QSS = f"""
QWidget {{ background: {BG}; color: {TEXT}; font-size: 12px; }}
QMainWindow::separator {{ background: {BORDER}; width: 1px; height: 1px; }}
QSplitter::handle {{ background: {BORDER}; }}
QMenuBar, QMenu {{ background: {PANEL}; color: {TEXT}; }}
QMenuBar::item:selected, QMenu::item:selected {{ background: {SELECT}; }}
QLineEdit, QComboBox, QTableWidget, QTableView, QListWidget {{
  background: {PANEL}; border: 1px solid {BORDER}; selection-background-color: {SELECT}; color: {TEXT}; }}
QComboBox QAbstractItemView {{ background: {PANEL}; color: {TEXT}; border: 1px solid {BORDER}; selection-background-color: {SELECT}; outline: 0; }}
QComboBox QAbstractItemView::item {{ padding: 3px 6px; background: {PANEL}; color: {TEXT}; }}
QComboBox QAbstractItemView::item:hover, QComboBox QAbstractItemView::item:selected {{ background: {SELECT}; color: {TEXT}; }}
QComboBox QAbstractItemView::indicator {{ width: 13px; height: 13px; border: 1px solid {BORDER}; background: {PANEL}; }}
QComboBox QAbstractItemView::indicator:checked {{ background: {ACCENT}; }}
QDialog {{ background: {BG}; }}
QHeaderView::section {{ background: {PANEL}; color: {MUTED}; border: 0; border-bottom: 1px solid {BORDER}; padding: 3px; }}
QTableWidget {{ gridline-color: {BORDER}; }}
QPushButton {{ background: {PANEL}; border: 1px solid {BORDER}; padding: 4px 10px; min-width: 70px; }}  /* einheitliche Breite (wie "Import…") */
QPushButton:hover {{ border-color: {ACCENT}; }}
QCheckBox::indicator {{ width: 13px; height: 13px; border: 1px solid {BORDER}; background: {PANEL}; }}
QCheckBox::indicator:checked {{ background: {ACCENT}; }}
QLabel[role="h"] {{ color: #8b93a1; font-weight: bold; }}
QGroupBox {{ border: 1px solid {BORDER}; margin-top: 8px; }}
QGroupBox::title {{ color: #8b93a1; subcontrol-origin: margin; left: 6px; }}
QScrollBar:vertical {{ background: {BG}; width: 10px; }} QScrollBar::handle:vertical {{ background: {BORDER}; min-height: 20px; }}
QScrollBar:horizontal {{ background: {BG}; height: 10px; }} QScrollBar::handle:horizontal {{ background: {BORDER}; min-width: 20px; }}
QScrollBar::add-line, QScrollBar::sub-line {{ height: 0; width: 0; }}
QStatusBar {{ background: {PANEL}; color: {MUTED}; border-top: 1px solid {BORDER}; }}
QStatusBar::item {{ border: 0; }}
QWidget#connpanel {{ background: {PANEL}; border: 1px solid {BORDER}; }}
QWidget#connpanel QWidget {{ background: {PANEL}; }}
QWidget#connpanel QLineEdit, QWidget#connpanel QComboBox {{ background: {BG}; }}
QToolTip {{ background: {PANEL}; color: {TEXT}; border: 1px solid {BORDER}; }}
"""
