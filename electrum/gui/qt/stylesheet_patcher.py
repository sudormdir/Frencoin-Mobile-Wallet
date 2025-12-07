"""
This is used to patch the QApplication style sheet.
It reads the current stylesheet, appends our modifications and sets the new stylesheet.
"""

import sys

from PyQt5 import QtWidgets


CUSTOM_PATCH_FOR_DARK_THEME = '''
/* 
   Professional dark theme with grey backgrounds, green primary accents, and blue secondary highlights.
   Uses sharp, narrow borders for a clean, modern appearance.
*/

/* 1) Overall application background and text color */
QWidget {
    background-color: #121212; /* Dark grey background */
    color: #cccccc;            /* Medium light grey text */
    border: none;
}

/* 2) Main window */
QMainWindow {
    background-color: #1e1e1e; /* Medium dark grey background */
    border: 1px solid #2e7d32;   /* Muted green border */
}

/* 3) Menubar */
QMenuBar {
    background-color: #1e1e1e; /* Medium dark grey */
    color: #cccccc;            /* Medium light grey text */
    border: 1px solid #2e7d32; /* Muted green border */
    padding: 2px;
}
QMenuBar::item:selected {
    background-color: #2e7d32; /* Muted green when selected */
    color: #ffffff;            /* White text on selection */
}

/* 4) Drop-down menus */
QMenu {
    background-color: #121212; /* Dark grey */
    color: #cccccc;            /* Medium light grey text */
    border: 1px solid #2e7d32; /* Muted green border */
    padding: 4px;
}
QMenu::item:selected {
    background-color: #1976d2; /* Blue selection */
    color: #ffffff;            /* White text */
}

/* 5) Toolbars */
QToolBar {
    background-color: #1e1e1e; /* Medium dark grey */
    border: 1px solid #2e7d32; /* Muted green border */
    padding: 2px;
}

/* 6) Tabs and tab bars */
QTabWidget::pane {
    background-color: #121212; /* Dark grey */
    border: 1px solid #1e1e1e; /* Medium dark grey border */
    padding: 2px;
}
QTabBar::tab {
    background-color: #2e7d32; /* Muted green */
    color: #cccccc;            /* Medium light grey text */
    border: 1px solid #2e7d32; /* Muted green border */
    padding: 4px;
    margin: 2px;
}
QTabBar::tab:selected {
    background-color: #1e1e1e; /* Medium dark grey */
    color: #ffffff;            /* White text */
    border-bottom: 2px solid #1976d2; /* Blue underline for selected tab */
}

/* 7) StatusBarButton (e.g., bottom-right icons) */
StatusBarButton {
    background-color: transparent;
    border: 1px solid transparent;
    margin: 0px;
    padding: 2px;
}
StatusBarButton:checked {
    border: 1px solid #2e7d32; /* Muted green border */
}
StatusBarButton:pressed,
StatusBarButton:hover {
    border: 1px solid #1976d2; /* Blue border on hover/press */
}

/* 8) Table headers (e.g., transaction history columns) */
QHeaderView::section {
    background-color: #1e1e1e; /* Medium dark grey */
    color: #cccccc;            /* Medium light grey text */
    padding: 4px;
    border: 1px solid #2e7d32; /* Muted green border */
}

/* 9) Table contents (e.g., transaction history rows) */
QTableView {
    background-color: #121212; /* Dark grey */
    gridline-color: #1976d2;   /* Blue gridlines */
    border: 1px solid #2e7d32; /* Muted green border */
    padding: 0px;
}
QTableView::item:selected {
    background-color: #1976d2; /* Blue selection */
    color: #ffffff;            /* White text */
}

/* 10) Scroll areas, line edits, and combo boxes */
QAbstractScrollArea {
    padding: 0px;
    border: 1px solid #2e7d32; /* Muted green border */
}
QLineEdit {
    background-color: #1e1e1e; /* Medium dark grey */
    border: 1px solid #2e7d32; /* Muted green border */
    padding: 4px;
    color: #cccccc;
    selection-background-color: #1976d2; /* Blue selection */
    selection-color: #ffffff;
}
QAbstractItemView QLineEdit {
    padding: 0px;
    show-decoration-selected: 1;
}
QComboBox {
    background-color: #1e1e1e; /* Medium dark grey */
    border: 1px solid #2e7d32; /* Muted green border */
    padding: 2px;
    color: #cccccc;
}
QComboBox::drop-down {
    border: 1px solid #2e7d32; /* Muted green */
}
QComboBox::item:checked {
    font-weight: bold;
    max-height: 30px;
    background-color: #1976d2; /* Blue */
    color: #ffffff;
}

/* 11) Push buttons */
QPushButton {
    background-color: #1e1e1e; /* Medium dark grey */
    color: #cccccc;            /* Medium light grey text */
    border: 1px solid #2e7d32; /* Muted green border */
    padding: 5px 10px;
}
QPushButton:hover {
    background-color: #1976d2; /* Blue hover */
    color: #ffffff;
}
QPushButton:pressed {
    background-color: #2e7d32; /* Muted green pressed */
    color: #ffffff;
}
'''

CUSTOM_PATCH_FOR_DEFAULT_THEME_MACOS = '''
/* 
   Professional dark theme with grey backgrounds, green primary accents, and blue secondary highlights, adapted for macOS.
   Uses sharp, narrow borders for a clean, modern appearance.
*/

/* 1) Overall application background and text color for all widgets */
QWidget {
    background-color: #121212; /* Dark grey background */
    color: #cccccc;            /* Medium light grey text */
    border: none;
}

/* 2) Main window specifically */
QMainWindow {
    background-color: #1e1e1e; /* Medium dark grey */
    border: 1px solid #2e7d32; /* Muted green border */
}

/* 3) Menubar */
QMenuBar {
    background-color: #1e1e1e; /* Medium dark grey */
    color: #cccccc;            /* Medium light grey text */
    border: 1px solid #2e7d32; /* Muted green border */
    padding: 2px;
}
QMenuBar::item:selected {
    background-color: #2e7d32; /* Muted green */
    color: #ffffff;            /* White text */
}

/* 4) Drop-down menus */
QMenu {
    background-color: #121212; /* Dark grey */
    color: #cccccc;            /* Medium light grey text */
    border: 1px solid #2e7d32; /* Muted green border */
    padding: 4px;
}
QMenu::item:selected {
    background-color: #1976d2; /* Blue selection */
    color: #ffffff;            /* White text */
}

/* 5) Toolbars */
QToolBar {
    background-color: #1e1e1e; /* Medium dark grey */
    border: 1px solid #2e7d32; /* Muted green border */
    padding: 2px;
}

/* 6) Tabs and tab bars */
QTabWidget::pane {
    background-color: #121212; /* Dark grey */
    border: 1px solid #1e1e1e; /* Medium dark grey border */
    padding: 2px;
}
QTabBar::tab {
    background-color: #2e7d32; /* Muted green */
    color: #cccccc;            /* Medium light grey text */
    border: 1px solid #2e7d32; /* Muted green border */
    padding: 4px;
    margin: 2px;
}
QTabBar::tab:selected {
    background-color: #1e1e1e; /* Medium dark grey */
    color: #ffffff;            /* White text */
    border-bottom: 2px solid #1976d2; /* Blue underline for selected tab */
}

/* 7) StatusBarButton (bottom-right icons) */
StatusBarButton {
    background-color: transparent;
    border: 1px solid transparent;
    margin: 0px;
    padding: 2px;
}
StatusBarButton:checked {
    border: 1px solid #2e7d32; /* Muted green border */
}
StatusBarButton:pressed,
StatusBarButton:hover {
    border: 1px solid #1976d2; /* Blue border on hover/press */
}

/* 8) Table headers (e.g., transaction history columns) */
QHeaderView::section {
    background-color: #1e1e1e; /* Medium dark grey */
    color: #cccccc;            /* Medium light grey text */
    padding: 4px;
    border: 1px solid #2e7d32; /* Muted green border */
}

/* 9) Table contents (e.g., transaction history rows) */
QTableView {
    background-color: #121212; /* Dark grey */
    gridline-color: #1976d2;   /* Blue gridlines */
    border: 1px solid #2e7d32; /* Muted green border */
    padding: 0px;
}
QTableView::item:selected {
    background-color: #1976d2; /* Blue selection */
    color: #ffffff;            /* White text */
}

/* 10) Scroll areas, line edits, combo boxes */
QAbstractScrollArea {
    padding: 0px;
    border: 1px solid #2e7d32; /* Muted green border */
}
QLineEdit {
    background-color: #1e1e1e; /* Medium dark grey */
    border: 1px solid #2e7d32; /* Muted green border */
    padding: 4px;
    color: #cccccc;
    selection-background-color: #1976d2; /* Blue selection */
    selection-color: #ffffff;
}
QAbstractItemView QLineEdit {
    padding: 0px;
    show-decoration-selected: 1;
}
QComboBox {
    background-color: #1e1e1e; /* Medium dark grey */
    border: 1px solid #2e7d32; /* Muted green border */
    padding: 2px;
    color: #cccccc;
}
QComboBox::drop-down {
    border: 1px solid #2e7d32; /* Muted green */
}
QComboBox::item:checked {
    font-weight: bold;
    max-height: 30px;
    background-color: #1976d2; /* Blue */
    color: #ffffff;
}

/* 11) Push buttons */
QPushButton {
    background-color: #1e1e1e; /* Medium dark grey */
    color: #cccccc;            /* Medium light grey text */
    border: 1px solid #2e7d32; /* Muted green border */
    padding: 5px 10px;
}
QPushButton:hover {
    background-color: #1976d2; /* Blue hover */
    color: #ffffff;
}
QPushButton:pressed {
    background-color: #2e7d32; /* Muted green pressed */
    color: #ffffff;
}
'''


CUSTOM_PATCH_FOR_DEFAULT_THEME_LINUX = '''
/* 
   Professional dark theme with grey backgrounds, green primary accents, and blue secondary highlights, adapted for Linux.
   Uses sharp, narrow borders for a clean, modern appearance.
*/

/* 1) Overall application background and text color for all widgets */
QWidget {
    background-color: #121212; /* Dark grey background */
    color: #cccccc;            /* Medium light grey text */
    border: none;
}

/* 2) Main window specifically */
QMainWindow {
    background-color: #1e1e1e; /* Medium dark grey */
    border: 1px solid #2e7d32; /* Muted green border */
}

/* 3) Menubar (File, Wallet, Tools, Help) */
QMenuBar {
    background-color: #1e1e1e; /* Medium dark grey */
    color: #cccccc;            /* Medium light grey text */
    border: 1px solid #2e7d32; /* Muted green border */
    padding: 2px;
}
QMenuBar::item:selected {
    background-color: #2e7d32; /* Muted green */
    color: #ffffff;            /* White text */
}

/* 4) Drop-down menus */
QMenu {
    background-color: #121212; /* Dark grey */
    color: #cccccc;            /* Medium light grey text */
    border: 1px solid #2e7d32; /* Muted green border */
    padding: 4px;
}
QMenu::item:selected {
    background-color: #1976d2; /* Blue selection */
    color: #ffffff;            /* White text */
}

/* 5) Toolbars (if any) */
QToolBar {
    background-color: #1e1e1e; /* Medium dark grey */
    border: 1px solid #2e7d32; /* Muted green border */
    padding: 2px;
}

/* 6) Tabs and tab bars (History, Send, Receive, etc.) */
QTabWidget::pane {
    background-color: #121212; /* Dark grey */
    border: 1px solid #1e1e1e; /* Medium dark grey border */
    padding: 2px;
}
QTabBar::tab {
    background-color: #2e7d32; /* Muted green */
    color: #cccccc;            /* Medium light grey text */
    border: 1px solid #2e7d32; /* Muted green border */
    padding: 4px;
    margin: 2px;
}
QTabBar::tab:selected {
    background-color: #1e1e1e; /* Medium dark grey */
    color: #ffffff;            /* White text */
    border-bottom: 2px solid #1976d2; /* Blue underline for selected tab */
}

/* 7) StatusBarButton (bottom-right icons) */
StatusBarButton {
    background-color: transparent;
    border: 1px solid transparent;
    margin: 0px;
    padding: 2px;
}
StatusBarButton:checked {
    border: 1px solid #2e7d32; /* Muted green border */
}
StatusBarButton:pressed,
StatusBarButton:hover {
    border: 1px solid #1976d2; /* Blue border on hover/press */
}

/* 8) Table headers (e.g., transaction history columns) */
QHeaderView::section {
    background-color: #1e1e1e; /* Medium dark grey */
    color: #cccccc;            /* Medium light grey text */
    padding: 4px;
    border: 1px solid #2e7d32; /* Muted green border */
}

/* 9) Table contents (e.g., transaction history rows) */
QTableView {
    background-color: #121212; /* Dark grey */
    gridline-color: #1976d2;   /* Blue gridlines */
    border: 1px solid #2e7d32; /* Muted green border */
    padding: 0px;
}
QTableView::item:selected {
    background-color: #1976d2; /* Blue selection */
    color: #ffffff;            /* White text */
}

/* 10) Scroll areas, line edits, combo boxes */
QAbstractScrollArea {
    padding: 0px;
    border: 1px solid #2e7d32; /* Muted green border */
}
QLineEdit {
    background-color: #1e1e1e; /* Medium dark grey */
    border: 1px solid #2e7d32; /* Muted green border */
    padding: 4px;
    color: #cccccc;
    selection-background-color: #1976d2; /* Blue selection */
    selection-color: #ffffff;
}
QAbstractItemView QLineEdit {
    padding: 0px;
    show-decoration-selected: 1;
}
QComboBox {
    background-color: #1e1e1e; /* Medium dark grey */
    border: 1px solid #2e7d32; /* Muted green border */
    padding: 2px;
    color: #cccccc;
}
QComboBox::drop-down {
    border: 1px solid #2e7d32; /* Muted green */
}
QComboBox::item:checked {
    font-weight: bold;
    max-height: 30px;
    background-color: #1976d2; /* Blue */
    color: #ffffff;
}

/* 11) Push buttons */
QPushButton {
    background-color: #1e1e1e; /* Medium dark grey */
    color: #cccccc;            /* Medium light grey text */
    border: 1px solid #2e7d32; /* Muted green border */
    padding: 5px 10px;
}
QPushButton:hover {
    background-color: #1976d2; /* Blue hover */
    color: #ffffff;
}
QPushButton:pressed {
    background-color: #2e7d32; /* Muted green pressed */
    color: #ffffff;
}
'''

CUSTOM_PATCH_FOR_DEFAULT_THEME_WINDOWS = '''
/* 
   Professional dark theme with grey backgrounds, green primary accents, and blue secondary highlights, adapted for Windows.
   Uses sharp, narrow borders for a clean, modern appearance.
*/

/* 1) Overall application background and text color for all widgets */
QWidget {
    background-color: #121212; /* Dark grey background */
    color: #cccccc;            /* Medium light grey text */
    border: none;
}

/* 2) Main window specifically */
QMainWindow {
    background-color: #1e1e1e; /* Medium dark grey */
    border: 1px solid #2e7d32; /* Muted green border */
}

/* 3) Menubar */
QMenuBar {
    background-color: #1e1e1e; /* Medium dark grey */
    color: #cccccc;            /* Medium light grey text */
    border: 1px solid #2e7d32; /* Muted green border */
    padding: 2px;
}
QMenuBar::item:selected {
    background-color: #2e7d32; /* Muted green */
    color: #ffffff;            /* White text */
}

/* 4) Drop-down menus */
QMenu {
    background-color: #121212; /* Dark grey */
    color: #cccccc;            /* Medium light grey text */
    border: 1px solid #2e7d32; /* Muted green border */
    padding: 4px;
}
QMenu::item:selected {
    background-color: #1976d2; /* Blue selection */
    color: #ffffff;            /* White text */
}

/* 5) Toolbars */
QToolBar {
    background-color: #1e1e1e; /* Medium dark grey */
    border: 1px solid #2e7d32; /* Muted green border */
    padding: 2px;
}

/* 6) Tabs and tab bars */
QTabWidget::pane {
    background-color: #121212; /* Dark grey */
    border: 1px solid #1e1e1e; /* Medium dark grey border */
    padding: 2px;
}
QTabBar::tab {
    background-color: #2e7d32; /* Muted green */
    color: #cccccc;            /* Medium light grey text */
    border: 1px solid #2e7d32; /* Muted green border */
    padding: 4px;
    margin: 2px;
}
QTabBar::tab:selected {
    background-color: #1e1e1e; /* Medium dark grey */
    color: #ffffff;            /* White text */
    border-bottom: 2px solid #1976d2; /* Blue underline for selected tab */
}

/* 7) StatusBarButton */
StatusBarButton {
    background-color: transparent;
    border: 1px solid transparent;
    margin: 0px;
    padding: 2px;
}
StatusBarButton:checked {
    border: 1px solid #2e7d32; /* Muted green border */
}
StatusBarButton:pressed,
StatusBarButton:hover {
    border: 1px solid #1976d2; /* Blue border on hover/press */
}

/* 8) Table headers */
QHeaderView::section {
    background-color: #1e1e1e; /* Medium dark grey */
    color: #cccccc;            /* Medium light grey text */
    padding: 4px;
    border: 1px solid #2e7d32; /* Muted green border */
}

/* 9) Table contents */
QTableView {
    background-color: #121212; /* Dark grey */
    gridline-color: #1976d2;   /* Blue gridlines */
    border: 1px solid #2e7d32; /* Muted green border */
    padding: 0px;
}
QTableView::item:selected {
    background-color: #1976d2; /* Blue selection */
    color: #ffffff;            /* White text */
}

/* 10) Scroll areas, line edits, combo boxes */
QAbstractScrollArea {
    padding: 0px;
    border: 1px solid #2e7d32; /* Muted green border */
}
QLineEdit {
    background-color: #1e1e1e; /* Medium dark grey */
    border: 1px solid #2e7d32; /* Muted green border */
    padding: 4px;
    color: #cccccc;
    selection-background-color: #1976d2; /* Blue selection */
    selection-color: #ffffff;
}
QAbstractItemView QLineEdit {
    padding: 0px;
    show-decoration-selected: 1;
}
QComboBox {
    background-color: #1e1e1e; /* Medium dark grey */
    border: 1px solid #2e7d32; /* Muted green border */
    padding: 2px;
    color: #cccccc;
}
QComboBox::drop-down {
    border: 1px solid #2e7d32; /* Muted green */
}
QComboBox::item:checked {
    font-weight: bold;
    max-height: 30px;
    background-color: #1976d2; /* Blue */
    color: #ffffff;
}

/* 11) Push buttons */
QPushButton {
    background-color: #1e1e1e; /* Medium dark grey */
    color: #cccccc;            /* Medium light grey text */
    border: 1px solid #2e7d32; /* Muted green border */
    padding: 5px 10px;
}
QPushButton:hover {
    background-color: #1976d2; /* Blue hover */
    color: #ffffff;
}
QPushButton:pressed {
    background-color: #2e7d32; /* Muted green pressed */
    color: #ffffff;
}
'''

# Example dark theme placeholder (if needed)
# CUSTOM_PATCH_FOR_DARK_THEME = '/* dark theme styles go here */'

def patch_qt_stylesheet(use_dark_theme: bool) -> None:
    import sys
    from PyQt5 import QtWidgets  # or PySide2, depending on your setup

    custom_patch = ""
    if use_dark_theme:
        custom_patch = CUSTOM_PATCH_FOR_DARK_THEME
    else:  # default (light) theme
        if sys.platform == 'darwin':
            # macOS-specific theme (assumed to be defined elsewhere)
            custom_patch = CUSTOM_PATCH_FOR_DEFAULT_THEME_MACOS
        elif sys.platform == 'win32':
            custom_patch = CUSTOM_PATCH_FOR_DEFAULT_THEME_WINDOWS
        else:
            custom_patch = CUSTOM_PATCH_FOR_DEFAULT_THEME_LINUX

    app = QtWidgets.QApplication.instance()
    style_sheet = app.styleSheet() + custom_patch
    app.setStyleSheet(style_sheet)