from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QDoubleSpinBox,
    QTextEdit, QPushButton, QTableWidget, QTableWidgetItem, QHeaderView,
    QFrame, QDateEdit, QMessageBox, QFormLayout, QInputDialog, QComboBox
)
from PySide6.QtCore import Qt, QDate, QDateTime, QTimer
from PySide6.QtGui import QIcon, QFont, QKeySequence, QShortcut
import database
import logging
from datetime import datetime

class PaymentNotesModule(QWidget):
    def __init__(self, user_role="staff", username="admin"):
        super().__init__()
        self.user_role = user_role
        self.username = username
        self.setup_ui()

    def setup_ui(self):
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(20)

        # ─── LEFT COLUMN: ENTRY FORM ───
        left_panel = QFrame()
        left_panel.setFixedWidth(400)
        left_panel.setStyleSheet("""
            QFrame {
                background-color: #FFFFFF;
                border: 1px solid #CBD5E1;
                border-radius: 12px;
            }
            QLabel {
                border: none;
                font-weight: 600;
                color: #334155;
            }
        """)
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(24, 24, 24, 24)
        left_layout.setSpacing(16)

        form_title = QLabel("Log New Payment / Note")
        form_title.setStyleSheet("font-size: 20px; font-weight: 900; color: #064E3B; border: none; padding-bottom: 8px;")
        left_layout.addWidget(form_title)

        form_layout = QFormLayout()
        form_layout.setSpacing(14)
        form_layout.setLabelAlignment(Qt.AlignRight)

        # 1. Amount Input
        self.inp_amount = QLineEdit()
        self.inp_amount.setPlaceholderText("0.00")
        self.inp_amount.setMinimumHeight(45)
        self.inp_amount.setStyleSheet("font-size: 16px; font-weight: bold; padding: 6px 12px; border-radius: 6px; border: 1px solid #CBD5E1;")
        self.inp_amount.textEdited.connect(self.format_cash_input)
        lbl_amount = QLabel("Amount (₱):")
        lbl_amount.setStyleSheet("font-size: 14px;")
        form_layout.addRow(lbl_amount, self.inp_amount)

        # 2. Recipient Input with Autocomplete Combo
        self.combo_recipient = QComboBox()
        self.combo_recipient.setEditable(True)
        self.combo_recipient.setInsertPolicy(QComboBox.NoInsert)
        self.combo_recipient.setMinimumHeight(45)
        self.combo_recipient.setStyleSheet("font-size: 14px; padding: 6px 12px; border-radius: 6px; border: 1px solid #CBD5E1;")
        self.combo_recipient.lineEdit().setPlaceholderText("e.g. Vendor A, Meralco, Rent")
        lbl_recipient = QLabel("Payee / Recipient:")
        lbl_recipient.setStyleSheet("font-size: 14px;")
        form_layout.addRow(lbl_recipient, self.combo_recipient)

        # 3. Purpose / Details
        self.inp_purpose = QTextEdit()
        self.inp_purpose.setPlaceholderText("Describe what you paid for...")
        self.inp_purpose.setMinimumHeight(100)
        self.inp_purpose.setStyleSheet("font-size: 14px; padding: 8px 12px; border-radius: 6px; border: 1px solid #CBD5E1;")
        lbl_purpose = QLabel("What I Paid:")
        lbl_purpose.setStyleSheet("font-size: 14px;")
        form_layout.addRow(lbl_purpose, self.inp_purpose)

        # 4. Custom Timestamp
        self.inp_date = QDateEdit()
        self.inp_date.setCalendarPopup(True)
        self.inp_date.setDate(QDate.currentDate())
        self.inp_date.setMinimumHeight(40)
        self.inp_date.setStyleSheet("font-size: 14px; padding: 6px 12px; border-radius: 6px; border: 1px solid #CBD5E1;")
        lbl_date = QLabel("Payment Date:")
        lbl_date.setStyleSheet("font-size: 14px;")
        form_layout.addRow(lbl_date, self.inp_date)

        left_layout.addLayout(form_layout)

        # Save Button
        self.btn_save = QPushButton("Save Payment Note (Enter)")
        self.btn_save.setMinimumHeight(50)
        self.btn_save.setStyleSheet("""
            QPushButton {
                background-color: #064E3B;
                color: white;
                font-size: 16px;
                font-weight: bold;
                border-radius: 8px;
                border: none;
            }
            QPushButton:hover {
                background-color: #047857;
            }
            QPushButton:pressed {
                background-color: #064E3B;
            }
        """)
        self.btn_save.clicked.connect(self.save_note)
        left_layout.addWidget(self.btn_save)

        # Clear Fields Button
        self.btn_clear = QPushButton("Clear Form")
        self.btn_clear.setMinimumHeight(35)
        self.btn_clear.setStyleSheet("""
            QPushButton {
                background-color: #F1F5F9;
                color: #475569;
                font-size: 13px;
                border: 1px solid #CBD5E1;
                border-radius: 6px;
            }
            QPushButton:hover {
                background-color: #E2E8F0;
            }
        """)
        self.btn_clear.clicked.connect(self.clear_form)
        left_layout.addWidget(self.btn_clear)

        left_layout.addStretch()
        main_layout.addWidget(left_panel)

        # ─── RIGHT COLUMN: HISTORY TABLE & SEARCH ───
        right_panel = QFrame()
        right_panel.setStyleSheet("""
            QFrame {
                background-color: #FFFFFF;
                border: 1px solid #CBD5E1;
                border-radius: 12px;
            }
            QLabel {
                border: none;
            }
        """)
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(24, 24, 24, 24)
        right_layout.setSpacing(16)

        # Header Row: Title and Date Filters
        header_layout = QHBoxLayout()
        header_title = QLabel("Payment & Payout History")
        header_title.setStyleSheet("font-size: 20px; font-weight: 900; color: #064E3B;")
        header_layout.addWidget(header_title)
        header_layout.addStretch()

        header_layout.addWidget(QLabel("From:"))
        self.filter_from = QDateEdit()
        self.filter_from.setCalendarPopup(True)
        self.filter_from.setDate(QDate.currentDate().addDays(-7))
        self.filter_from.setMinimumHeight(35)
        self.filter_from.setStyleSheet("font-size: 13px; padding: 4px 8px; border-radius: 6px; border: 1px solid #CBD5E1;")
        self.filter_from.dateChanged.connect(self.load_notes)
        header_layout.addWidget(self.filter_from)

        header_layout.addWidget(QLabel("To:"))
        self.filter_to = QDateEdit()
        self.filter_to.setCalendarPopup(True)
        self.filter_to.setDate(QDate.currentDate())
        self.filter_to.setMinimumHeight(35)
        self.filter_to.setStyleSheet("font-size: 13px; padding: 4px 8px; border-radius: 6px; border: 1px solid #CBD5E1;")
        self.filter_to.dateChanged.connect(self.load_notes)
        header_layout.addWidget(self.filter_to)

        self.btn_refresh = QPushButton("Refresh")
        self.btn_refresh.setMinimumHeight(35)
        self.btn_refresh.setStyleSheet("background-color: #F1F5F9; border: 1px solid #CBD5E1; font-weight: bold; border-radius: 6px; padding: 0 15px;")
        self.btn_refresh.clicked.connect(self.load_notes)
        header_layout.addWidget(self.btn_refresh)

        right_layout.addLayout(header_layout)

        # Search Bar
        search_layout = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search history by payee/recipient or notes...")
        self.search_input.setMinimumHeight(40)
        self.search_input.setStyleSheet("font-size: 14px; padding: 6px 12px; border-radius: 6px; border: 1px solid #CBD5E1;")
        self.search_input.textChanged.connect(self.load_notes)
        search_layout.addWidget(self.search_input)
        right_layout.addLayout(search_layout)

        # Table Widget
        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(["Date & Time", "Recipient / Payee", "What I Paid (Notes)", "Amount (₱)", "Action"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Interactive)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeToContents)
        
        self.table.horizontalHeader().setDefaultSectionSize(140)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setStyleSheet("""
            QTableWidget {
                border: none;
                background-color: #FFFFFF;
                font-size: 14px;
            }
            QHeaderView::section {
                background-color: #F8FAFC;
                padding: 10px;
                font-weight: bold;
                color: #475569;
                font-size: 13px;
                border: none;
                border-bottom: 2px solid #E2E8F0;
            }
        """)
        self.table.verticalHeader().setVisible(False)
        self.table.verticalHeader().setDefaultSectionSize(45)
        right_layout.addWidget(self.table)

        # Summary Bar
        summary_layout = QHBoxLayout()
        summary_layout.addStretch()
        self.lbl_total_summary = QLabel("Total Payouts: ₱0.00")
        self.lbl_total_summary.setStyleSheet("font-size: 18px; font-weight: bold; color: #1E293B; background-color: #F8FAFC; border-radius: 8px; border: 1px solid #E2E8F0; padding: 10px 20px;")
        summary_layout.addWidget(self.lbl_total_summary)
        right_layout.addLayout(summary_layout)

        main_layout.addWidget(right_panel)

        # Load Recipient List and History logs
        self.load_recipients()
        self.load_notes()

    def format_cash_input(self, text):
        line_edit = self.sender()
        if not isinstance(line_edit, QLineEdit):
            return
            
        pos = line_edit.cursorPosition()
        old_text = line_edit.text()
        raw_val = text.replace(',', '')
        if not raw_val:
            return

        try:
            if '.' in raw_val:
                parts = raw_val.split('.')
                whole = parts[0]
                decimal = ".".join(parts[1:])
                formatted = (f"{int(whole):,}" if whole else "0") + "." + decimal
            else:
                formatted = f"{int(raw_val):,}"
            
            if formatted != old_text:
                line_edit.setText(formatted)
                new_pos = pos + (len(formatted) - len(old_text))
                line_edit.setCursorPosition(max(0, new_pos))
        except ValueError:
            pass

    def clear_form(self):
        self.inp_amount.clear()
        self.combo_recipient.setCurrentText("")
        self.inp_purpose.clear()
        self.inp_date.setDate(QDate.currentDate())
        self.inp_amount.setFocus()

    def verify_admin(self):
        if self.user_role == "admin":
            return True
        password, ok = QInputDialog.getText(self, "Admin Required", "Enter Admin Password to delete this note:", QLineEdit.Password)
        if ok and password:
            user_data = database.verify_login("admin", password)
            if user_data and user_data[1] == "admin":
                return True
        QMessageBox.warning(self, "Access Denied", "Invalid Admin Password")
        return False

    def load_recipients(self):
        """Populates the recipient auto-complete combo box with unique past recipients."""
        current_text = self.combo_recipient.currentText()
        self.combo_recipient.clear()
        
        try:
            conn = database.get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT DISTINCT recipient FROM payment_notes ORDER BY recipient ASC")
            recipients = [r[0] for r in cursor.fetchall()]
            conn.close()
            
            self.combo_recipient.addItems(recipients)
            self.combo_recipient.setCurrentText(current_text)
        except Exception as e:
            logging.error(f"Failed to load past recipients: {e}")

    def load_notes(self):
        """Loads payment logs and applies date range / search filters."""
        date_from_str = self.filter_from.date().toString("yyyy-MM-dd")
        date_to_str = self.filter_to.date().toString("yyyy-MM-dd")
        search_query = self.search_input.text().strip().lower()

        # Fetch records using database function
        rows = database.get_payment_notes(date_from_str, date_to_str)

        # Filter manually by search query if text is present
        if search_query:
            rows = [
                r for r in rows 
                if search_query in str(r[2]).lower() or search_query in str(r[3]).lower()
            ]

        self.table.setRowCount(0)
        total_payout = 0.0

        for i, row in enumerate(rows):
            self.table.insertRow(i)
            
            # Format datetime nicely
            dt = datetime.strptime(row[4], "%Y-%m-%d %H:%M:%S")
            formatted_dt = dt.strftime("%b %d, %Y %I:%M %p")
            
            self.table.setItem(i, 0, QTableWidgetItem(formatted_dt))
            self.table.setItem(i, 1, QTableWidgetItem(str(row[2])))
            self.table.setItem(i, 2, QTableWidgetItem(str(row[3]) if row[3] else ""))
            
            # Amount
            amount_val = float(row[1])
            total_payout += amount_val
            amount_item = QTableWidgetItem(f"₱{amount_val:,.2f}")
            amount_item.setFont(QFont("Segoe UI", 10, QFont.Bold))
            self.table.setItem(i, 3, QTableWidgetItem(amount_item))

            # Delete Button
            btn_delete = QPushButton("Delete")
            btn_delete.setStyleSheet("""
                QPushButton {
                    background-color: #EF4444;
                    color: white;
                    border: none;
                    border-radius: 4px;
                    padding: 4px 8px;
                    font-weight: bold;
                    font-size: 11px;
                }
                QPushButton:hover {
                    background-color: #DC2626;
                }
            """)
            btn_delete.clicked.connect(lambda checked=False, r_id=row[0]: self.delete_note(r_id))
            
            # Center widget in table column
            btn_container = QWidget()
            btn_layout = QHBoxLayout(btn_container)
            btn_layout.setContentsMargins(0, 0, 0, 0)
            btn_layout.setAlignment(Qt.AlignCenter)
            btn_layout.addWidget(btn_delete)
            self.table.setCellWidget(i, 4, btn_container)

        self.lbl_total_summary.setText(f"Total Payouts: ₱{total_payout:,.2f}")

    def save_note(self):
        amount_str = self.inp_amount.text().replace(',', '').strip()
        recipient = self.combo_recipient.currentText().strip()
        purpose = self.inp_purpose.toPlainText().strip()
        selected_date = self.inp_date.date().toString("yyyy-MM-dd")
        
        if not amount_str:
            QMessageBox.warning(self, "Missing Info", "Please enter a valid amount.")
            self.inp_amount.setFocus()
            return
            
        try:
            amount = float(amount_str)
            if amount <= 0:
                raise ValueError()
        except ValueError:
            QMessageBox.warning(self, "Invalid Amount", "Please enter a positive numeric value for the amount.")
            self.inp_amount.setFocus()
            return

        if not recipient:
            QMessageBox.warning(self, "Missing Info", "Please specify a payee / recipient.")
            self.combo_recipient.setFocus()
            return

        # Prepare timestamp using selected date + current time
        current_time_str = datetime.now().strftime("%H:%M:%S")
        timestamp = f"{selected_date} {current_time_str}"

        try:
            # Save to Database
            database.add_payment_note(amount, recipient, purpose, timestamp)
            
            # Log action
            database.log_action("PAYMENT_NOTE_SAVED", f"Paid ₱{amount:,.2f} to {recipient} for '{purpose or 'No notes'}'", self.username)
            
            # Refresh Table & Autocomplete list
            self.load_recipients()
            self.load_notes()
            
            # Success feedback & reset form
            self.clear_form()
            
        except Exception as e:
            QMessageBox.critical(self, "Database Error", f"Failed to save payment note: {e}")

    def delete_note(self, note_id):
        if not self.verify_admin():
            return

        reply = QMessageBox.question(
            self, "Confirm Delete", 
            "Are you sure you want to delete this payment note permanently?",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            try:
                # Log action before deleting
                conn = database.get_connection()
                cursor = conn.cursor()
                cursor.execute("SELECT amount, recipient, purpose FROM payment_notes WHERE id=?", (note_id,))
                note = cursor.fetchone()
                conn.close()

                if note:
                    database.log_action("PAYMENT_NOTE_DELETED", f"Deleted payment note: ₱{note[0]:,.2f} to {note[1]} for '{note[2]}'", self.username)

                # Delete from database
                database.delete_payment_note(note_id)
                
                # Reload UI elements
                self.load_recipients()
                self.load_notes()
                
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to delete payment note: {e}")

