import sys
import os
# pyrefly: ignore [missing-import]
from PySide6.QtWidgets import QApplication, QMainWindow, QTabWidget, QVBoxLayout, QWidget, QMessageBox
# pyrefly: ignore [missing-import]
from PySide6.QtGui import QShortcut, QKeySequence, QIcon
import database
from pos_module import POSModule
from inventory_module import InventoryModule
from dashboard_module import DashboardModule
from balance_module import BalanceModule
from logs_module import LogsModule
from account_module import AccountModule
from payment_notes_module import PaymentNotesModule

def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

class EmmaSarmingStore(QMainWindow):
    def __init__(self, user_role="staff", username="admin"):
        super().__init__()
        self.user_role = user_role
        self.username = username
        self.setWindowTitle("Emma Sarming Store - Dashboard") 
        self.setWindowIcon(QIcon(resource_path("emma_sarming_logo.png")))
        self.showMaximized()
        self.setup_ui()

    def setup_ui(self):
        # Modern Emerald & Gold Theme for Main Window
        self.setStyleSheet("""
            QMainWindow {
                background-color: #F3F4F1;
            }
            QWidget {
                background-color: #F3F4F1;
                color: #1F2937;
                font-family: 'Segoe UI', 'Inter', sans-serif;
            }
            QTabWidget::pane {
                border: 1px solid #D1D5DB;
                border-top: 3px solid #064E3B;
                background-color: #FFFFFF;
                border-radius: 8px;
            }
            QTabBar::tab {
                background-color: #E5E7EB;
                color: #4B5563;
                padding: 12px 24px;
                margin-right: 4px;
                border-top-left-radius: 8px;
                border-top-right-radius: 8px;
                font-weight: 600;
                font-size: 14px;
                border: 1px solid #D1D5DB;
                border-bottom: none;
            }
            QTabBar::tab:selected {
                background-color: #FFFFFF;
                color: #064E3B;
                border-color: #D1D5DB;
                border-top: 3px solid #D97706;
            }
            QTabBar::tab:hover:!selected {
                background-color: #F3F4F6;
                color: #064E3B;
            }
            QTableWidget {
                background-color: #FFFFFF;
                alternate-background-color: #F9FAFB;
                gridline-color: #E5E7EB;
                border: 1px solid #E5E7EB;
                border-radius: 8px;
                color: #1F2937;
                font-size: 14px;
            }
            QTableView::item {
                padding: 5px;
            }
            QTableView::item:selected {
                background-color: #E6F4EA;
                color: #064E3B;
            }
            QHeaderView::section {
                background-color: #F3F4F6;
                color: #374151;
                padding: 10px;
                border: none;
                border-bottom: 2px solid #064E3B;
                border-right: 1px solid #F3F4F6;
                font-weight: 700;
                font-size: 13px;
                text-transform: uppercase;
            }
            QLineEdit {
                background-color: #FFFFFF;
                border: 1px solid #D1D5DB;
                border-radius: 6px;
                padding: 10px 14px;
                color: #1F2937;
                font-size: 14px;
            }
            QDateEdit, QDoubleSpinBox {
                background-color: #FFFFFF;
                border: 1px solid #D1D5DB;
                border-radius: 6px;
                padding: 4px 34px 4px 8px; /* Leave space on the right for buttons */
                color: #1F2937;
                font-size: 14px;
                min-height: 28px;
            }
            QDoubleSpinBox::up-button, QDateEdit::up-button {
                subcontrol-origin: border;
                subcontrol-position: top right;
                width: 26px;
                border-left: 1px solid #D1D5DB;
                border-bottom: 1px solid #D1D5DB;
                background-color: #F9FAFB;
                border-top-right-radius: 6px;
            }
            QDoubleSpinBox::down-button, QDateEdit::down-button {
                subcontrol-origin: border;
                subcontrol-position: bottom right;
                width: 26px;
                border-left: 1px solid #D1D5DB;
                background-color: #F9FAFB;
                border-bottom-right-radius: 6px;
            }
            QDoubleSpinBox::up-button:hover, QDateEdit::up-button:hover, QDoubleSpinBox::down-button:hover, QDateEdit::down-button:hover {
                background-color: #E5E7EB;
            }
            QDoubleSpinBox::up-arrow, QDateEdit::up-arrow {
                image: url(up_arrow.svg);
                width: 12px;
                height: 12px;
            }
            QDoubleSpinBox::down-arrow, QDateEdit::down-arrow {
                image: url(down_arrow.svg);
                width: 12px;
                height: 12px;
            }
            QLineEdit:focus, QDateEdit:focus, QDoubleSpinBox:focus {
                border: 2px solid #064E3B;
                background-color: #FFFFFF;
            }
            QPushButton {
                background-color: #FFFFFF;
                color: #4B5563;
                border: 1px solid #D1D5DB;
                border-radius: 6px;
                padding: 10px 18px;
                font-weight: 600;
                font-size: 13px;
                letter-spacing: 0.5px;
            }
            QPushButton:hover {
                background-color: #ECFDF5;
                border: 1px solid #064E3B;
                color: #064E3B;
            }
            QPushButton:pressed {
                background-color: #D1FAE5;
            }
            /* Custom Scrollbar */
            QScrollBar:vertical {
                border: none;
                background: #F3F4F1;
                width: 8px;
                margin: 0px 0px 0px 0px;
                border-radius: 4px;
            }
            QScrollBar::handle:vertical {
                background: #D1D5DB;
                min-height: 20px;
                border-radius: 4px;
            }
            QScrollBar::handle:vertical:hover {
                background: #9CA3AF;
            }
        """)

        # Central widget and layout
        central_widget = QWidget()
        layout = QVBoxLayout(central_widget)
        
        # Tabs
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet("""
            QTabBar::tab {
                height: 38px;
                width: 160px;
                font-size: 12px;
                font-weight: bold;
                padding: 6px 10px;
            }
        """)
        layout.addWidget(self.tabs)

        # Tab 1: Dashboard
        self.dashboard_tab = DashboardModule(self.user_role, self.username)
        self.tabs.addTab(self.dashboard_tab, QIcon(resource_path("emma_sarming_logo.png")), "Dashboard (F1)")

        # Tab 2: POS
        self.pos_tab = POSModule(self.user_role, self.username)
        self.tabs.addTab(self.pos_tab, QIcon(resource_path("emma_sarming_logo.png")), "Point of Sale (F2)")

        # Tab 3: Inventory
        self.inventory_tab = InventoryModule(self.user_role, self.username)
        self.tabs.addTab(self.inventory_tab, QIcon(resource_path("emma_sarming_logo.png")), "Product Manager (F3)")

        # Tab 4: Balance
        self.balance_tab = BalanceModule(self.user_role, self.username)
        self.tabs.addTab(self.balance_tab, QIcon(resource_path("emma_sarming_logo.png")), "Balance Manager (F5)")

        # Tab 5: Data Logs
        self.logs_tab = LogsModule(self.user_role, self.username)
        self.tabs.addTab(self.logs_tab, QIcon(resource_path("emma_sarming_logo.png")), "Data Logs (F6)")

        # Tab 6: Account Details
        self.account_tab = AccountModule(self.username, self.user_role)
        self.account_tab.logout_requested.connect(self.handle_logout)
        self.tabs.addTab(self.account_tab, QIcon(resource_path("emma_sarming_logo.png")), "Account Settings (F7)")

        # Tab 7: Payment Notes
        self.payment_notes_tab = PaymentNotesModule(self.user_role, self.username)
        self.tabs.addTab(self.payment_notes_tab, QIcon(resource_path("emma_sarming_logo.png")), "Payment Notes (F8)")

        # Keyboard shortcuts for Tabs
        QShortcut(QKeySequence("F1"), self).activated.connect(lambda: self.tabs.setCurrentIndex(0))
        QShortcut(QKeySequence("F2"), self).activated.connect(lambda: self.tabs.setCurrentIndex(1))
        QShortcut(QKeySequence("F3"), self).activated.connect(lambda: self.tabs.setCurrentIndex(2))
        QShortcut(QKeySequence("F5"), self).activated.connect(lambda: self.tabs.setCurrentIndex(3))
        QShortcut(QKeySequence("F6"), self).activated.connect(lambda: self.tabs.setCurrentIndex(4))
        QShortcut(QKeySequence("F7"), self).activated.connect(lambda: self.tabs.setCurrentIndex(5))
        QShortcut(QKeySequence("F8"), self).activated.connect(lambda: self.tabs.setCurrentIndex(6))
        
        # Update dashboard elements every time user clicks tabs (Refresh warnings)
        self.tabs.currentChanged.connect(self.on_tab_change)

        self.setCentralWidget(central_widget)

    def on_tab_change(self, index):
        # Refresh Data dynamically if needed
        if index == 0:
            self.dashboard_tab.load_all()
        elif index == 1:
            self.pos_tab.refresh_completer()
            self.pos_tab.search_input.setFocus()
        elif index == 2:
            self.inventory_tab.load_inventory()
        elif index == 3:
            self.balance_tab.load_balances()
        elif index == 4:
            self.logs_tab.reset_dates()
            self.logs_tab.load_logs()
        elif index == 6:
            self.payment_notes_tab.load_recipients()
            self.payment_notes_tab.load_notes()

    def handle_logout(self):
        reply = QMessageBox.question(
            self, "Confirm Logout", "Are you sure you want to logout and return to the login screen?",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            try:
                # Import here to avoid circular import at the top
                from login import LoginWindow
                
                # Create the login window. 
                # We don't set a parent so it stays open when this window closes.
                self.login_window = LoginWindow()
                self.login_window.show()
                
                # Close the current window
                self.close()
            except Exception as e:
                QMessageBox.critical(self, "Logout Error", f"An error occurred during logout: {e}")

if __name__ == "__main__":
    database.init_db()
    app = QApplication(sys.argv)
    
    # Import and show the login window first
    from login import LoginWindow
    login_window = LoginWindow()
    login_window.show()
    
    sys.exit(app.exec())
