from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QTableWidget, QTableWidgetItem, QHeaderView, 
    QPushButton, QHBoxLayout, QLabel, QDateEdit, QMessageBox, QDialog
)
from PySide6.QtCore import Qt, QDate
from PySide6.QtGui import QShortcut, QKeySequence
import database
from printer_helper import ReceiptPrinter, clean_receipt_item_name, get_formatted_bundle_qty, split_item_for_receipt
from datetime import datetime

class ReceiptPreviewDialog(QDialog):
    def __init__(self, receipt_data, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Receipt Preview - Sale #{receipt_data['sale_id']}")
        self.setMinimumWidth(450)
        self.setMinimumHeight(600)
        self.receipt_data = receipt_data
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        # "Receipt" Styled Container
        receipt_container = QWidget()
        receipt_container.setStyleSheet("""
            QWidget {
                background-color: #FFFFFF;
                border: 2px solid #E2E8F0;
                border-radius: 8px;
            }
        """)
        receipt_layout = QVBoxLayout(receipt_container)
        
        header_lbl = QLabel(self.receipt_data['header'])
        header_lbl.setAlignment(Qt.AlignCenter)
        header_lbl.setStyleSheet("font-size: 20px; font-weight: 900; color: #1E293B; border: none;")
        receipt_layout.addWidget(header_lbl)

        info_lbl = QLabel(f"Sale ID: {self.receipt_data['sale_id']}\nCashier: {self.receipt_data['cashier']}")
        info_lbl.setStyleSheet("font-size: 13px; color: #64748B; border: none;")
        receipt_layout.addWidget(info_lbl)

        # Split items to match receipt printout exactly
        split_items = []
        for raw_item in self.receipt_data.get('items', []):
            split_items.extend(split_item_for_receipt(raw_item))
            
        # Items Table
        items_table = QTableWidget(len(split_items), 3)
        items_table.setHorizontalHeaderLabels(["Item", "Qty", "Price"])
        items_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        items_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        items_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        items_table.verticalHeader().setVisible(False)
        items_table.setEditTriggers(QTableWidget.NoEditTriggers)
        items_table.setStyleSheet("border: none; background-color: transparent;")
        
        for i, s_item in enumerate(split_items):
            items_table.setItem(i, 0, QTableWidgetItem(s_item['name']))
            
            qty_val = s_item['qty']
            unit_name = s_item.get('unit_name', 'pcs')
            if isinstance(qty_val, float) and qty_val.is_integer():
                qty_str = f"{int(qty_val):,d}"
            elif isinstance(qty_val, int):
                qty_str = f"{qty_val:,d}"
            else:
                qty_str = f"{qty_val:,.2f}"
                
            qty_display = qty_str
            items_table.setItem(i, 1, QTableWidgetItem(qty_display))
            
            items_table.setItem(i, 2, QTableWidgetItem(f"₱{s_item['total']:,.2f}"))

        items_table.resizeRowsToContents()
        receipt_layout.addWidget(items_table)

        # Totals
        totals_layout = QVBoxLayout()
        totals_layout.setSpacing(5)
        
        def add_total_line(label, value, is_bold=False):
            line = QHBoxLayout()
            lbl = QLabel(label)
            val = QLabel(f"₱{value:,.2f}")
            if is_bold:
                lbl.setStyleSheet("font-weight: bold; font-size: 16px; border: none;")
                val.setStyleSheet("font-weight: bold; font-size: 16px; border: none; color: #0072FF;")
            else:
                lbl.setStyleSheet("border: none;")
                val.setStyleSheet("border: none;")
            line.addWidget(lbl)
            line.addStretch()
            line.addWidget(val)
            totals_layout.addLayout(line)

        total = self.receipt_data.get('total', 0.0)
        paid = self.receipt_data.get('amount_paid', 0.0)
        change = max(0.0, paid - total)

        add_total_line("Subtotal:", total)
        add_total_line("Cash Received:", paid)
        add_total_line("Change Given:", change)
        add_total_line("Total Amount:", total, True)
        if self.receipt_data.get('balance_due', 0.0) > 0:
            add_total_line("Balance Due:", self.receipt_data['balance_due'])
        
        receipt_layout.addLayout(totals_layout)
        layout.addWidget(receipt_container)

        # Buttons
        btn_layout = QHBoxLayout()
        self.btn_print = QPushButton("Print Receipt")
        self.btn_print.setMinimumHeight(50)
        self.btn_print.setStyleSheet("""
            background-color: #0072FF;
            color: white;
            font-weight: bold;
            font-size: 16px;
            border-radius: 6px;
        """)
        self.btn_print.clicked.connect(self.accept)
        
        self.btn_cancel = QPushButton("Close")
        self.btn_cancel.setMinimumHeight(50)
        self.btn_cancel.setStyleSheet("font-size: 16px;")
        self.btn_cancel.clicked.connect(self.reject)
        
        btn_layout.addWidget(self.btn_cancel)
        btn_layout.addWidget(self.btn_print)
        layout.addLayout(btn_layout)

class LogsModule(QWidget):
    PAGE_SIZE = 100  # rows per page

    def __init__(self, user_role="staff", username="admin"):
        super().__init__()
        self.user_role = user_role
        self.username = username
        self._current_page = 1
        self._total_count = 0
        self._log_rows = []  # Cache of current page's raw DB rows
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        
        # Actions
        top_layout = QHBoxLayout()
        
        # Date Filters
        top_layout.addWidget(QLabel("From:"))
        self.date_from = QDateEdit()
        self.date_from.setCalendarPopup(True)
        self.date_from.setDate(QDate.currentDate().addDays(-7)) # Default to last 7 days
        self.date_from.dateChanged.connect(self.update_date_limits)
        top_layout.addWidget(self.date_from)
        
        top_layout.addWidget(QLabel("To:"))
        self.date_to = QDateEdit()
        self.date_to.setCalendarPopup(True)
        self.date_to.setDate(QDate.currentDate())
        self.date_to.setMinimumDate(self.date_from.date())
        self.date_to.dateChanged.connect(self.update_date_limits)
        top_layout.addWidget(self.date_to)
        
        # Initial set of limits
        self.date_from.setMaximumDate(self.date_to.date())

        self.btn_refresh = QPushButton("Refresh Logs (Ctrl+R)")
        self.btn_refresh.clicked.connect(self.load_logs)
        QShortcut(QKeySequence("Ctrl+R"), self, context=Qt.WidgetWithChildrenShortcut).activated.connect(self.load_logs)
        top_layout.addWidget(self.btn_refresh)
        
        self.btn_reprint = QPushButton("Reprint Receipt (Ctrl+P)")
        self.btn_reprint.clicked.connect(self.reprint_receipt)
        QShortcut(QKeySequence("Ctrl+P"), self, context=Qt.WidgetWithChildrenShortcut).activated.connect(self.reprint_receipt)
        top_layout.addWidget(self.btn_reprint)
        
        self.btn_void_sale = QPushButton("Void Sale")
        self.btn_void_sale.setStyleSheet("background-color: #EF4444; color: white; font-weight: bold;")
        self.btn_void_sale.clicked.connect(self.void_sale)
        top_layout.addWidget(self.btn_void_sale)
        
        top_layout.addStretch()
        layout.addLayout(top_layout)

        # Logs Table
        self.logs_table = QTableWidget(0, 4)
        self.logs_table.setHorizontalHeaderLabels(["Timestamp", "User Role", "Action", "Details"])
        self.logs_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.Stretch)
        for col in [0, 1, 2]:
            self.logs_table.horizontalHeader().setSectionResizeMode(col, QHeaderView.ResizeToContents)
        self.logs_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.logs_table.setStyleSheet("font-size: 14px;")
        layout.addWidget(self.logs_table)

        # ── Pagination Bar ──────────────────────────────────────────────────
        pag_layout = QHBoxLayout()
        pag_layout.setContentsMargins(0, 4, 0, 4)

        btn_style = """
            QPushButton {
                background-color: #1E40AF;
                color: white;
                font-weight: bold;
                font-size: 13px;
                border-radius: 6px;
                padding: 6px 14px;
                border: none;
            }
            QPushButton:hover { background-color: #2563EB; }
            QPushButton:disabled { background-color: #CBD5E1; color: #94A3B8; }
        """

        self.btn_first = QPushButton("\u23EE First")
        self.btn_first.setStyleSheet(btn_style)
        self.btn_first.clicked.connect(self.go_first)
        pag_layout.addWidget(self.btn_first)

        self.btn_prev = QPushButton("\u2039 Prev")
        self.btn_prev.setStyleSheet(btn_style)
        self.btn_prev.clicked.connect(self.go_prev)
        pag_layout.addWidget(self.btn_prev)

        self.lbl_page = QLabel("Page 1 of 1  (0 records)")
        self.lbl_page.setStyleSheet("font-size: 13px; font-weight: bold; color: #334155; padding: 0 12px;")
        self.lbl_page.setAlignment(Qt.AlignCenter)
        pag_layout.addWidget(self.lbl_page)

        self.btn_next = QPushButton("Next \u203A")
        self.btn_next.setStyleSheet(btn_style)
        self.btn_next.clicked.connect(self.go_next)
        pag_layout.addWidget(self.btn_next)

        self.btn_last = QPushButton("Last \u23ED")
        self.btn_last.setStyleSheet(btn_style)
        self.btn_last.clicked.connect(self.go_last)
        pag_layout.addWidget(self.btn_last)

        pag_layout.addStretch()
        layout.addLayout(pag_layout)
        # ───────────────────────────────────────────────────────────────────

        self.load_logs()

    def reset_dates(self):
        # Reset to Today
        today = QDate.currentDate()
        # To avoid mutual constraint blocking, reset To first if we were moving to past, 
        # but since we move to Today, setting both to today is safer.
        self.date_from.setMaximumDate(today.addDays(3650)) # Temporarily lift
        self.date_to.setMinimumDate(today.addDays(-3650)) # Temporarily lift
        
        self.date_from.setDate(today)
        self.date_to.setDate(today)
        self.update_date_limits()

    def update_date_limits(self):
        # Mutual constraints
        self.date_to.setMinimumDate(self.date_from.date())
        self.date_from.setMaximumDate(self.date_to.date())
        # Date range changed → reset to page 1 then reload
        self._current_page = 1
        self.load_logs()

    # ── Pagination helpers ────────────────────────────────────────────────
    def _total_pages(self):
        return max(1, -(-self._total_count // self.PAGE_SIZE))  # ceiling div

    def go_first(self):
        if self._current_page != 1:
            self._current_page = 1
            self.load_logs()

    def go_prev(self):
        if self._current_page > 1:
            self._current_page -= 1
            self.load_logs()

    def go_next(self):
        if self._current_page < self._total_pages():
            self._current_page += 1
            self.load_logs()

    def go_last(self):
        last = self._total_pages()
        if self._current_page != last:
            self._current_page = last
            self.load_logs()

    def _update_pagination_controls(self):
        total_pages = self._total_pages()
        self.lbl_page.setText(
            f"Page {self._current_page} of {total_pages}  ({self._total_count:,} records)"
        )
        self.btn_first.setEnabled(self._current_page > 1)
        self.btn_prev.setEnabled(self._current_page > 1)
        self.btn_next.setEnabled(self._current_page < total_pages)
        self.btn_last.setEnabled(self._current_page < total_pages)
    # ─────────────────────────────────────────────────────────────────────

    def load_logs(self):
        date_from_str = self.date_from.date().toString("yyyy-MM-dd")
        date_to_str = self.date_to.date().toString("yyyy-MM-dd")
        offset = (self._current_page - 1) * self.PAGE_SIZE

        conn = database.get_connection()
        cursor = conn.cursor()

        # 1. Total count for pagination
        cursor.execute("""
            SELECT COUNT(*)
            FROM audit_logs a
            WHERE DATE(a.timestamp) BETWEEN ? AND ?
        """, (date_from_str, date_to_str))
        self._total_count = cursor.fetchone()[0]

        # 2. Page slice
        cursor.execute("""
            SELECT a.timestamp, a.user_id, a.action, a.details, s.voided
            FROM audit_logs a
            LEFT JOIN sales s ON (a.details LIKE 'Sale #' || s.id || ' %')
            WHERE DATE(a.timestamp) BETWEEN ? AND ?
            ORDER BY a.id DESC
            LIMIT ? OFFSET ?
        """, (date_from_str, date_to_str, self.PAGE_SIZE, offset))
        rows = cursor.fetchall()
        conn.close()

        # Cache for reprint/void to avoid re-reading table widget items
        self._log_rows = rows

        self.logs_table.setRowCount(0)
        for i, row in enumerate(rows):
            self.logs_table.insertRow(i)
            
            # Format datetime nicely to be readable (e.g., May 22, 2026 08:44 AM)
            try:
                dt = datetime.strptime(row[0], "%Y-%m-%d %H:%M:%S")
                formatted_dt = dt.strftime("%b %d, %Y %I:%M %p")
            except Exception:
                formatted_dt = str(row[0])

            self.logs_table.setItem(i, 0, QTableWidgetItem(formatted_dt))
            self.logs_table.setItem(i, 1, QTableWidgetItem(str(row[1])))

            action_text = str(row[2]).replace('_', ' ') if row[2] else ""
            self.logs_table.setItem(i, 2, QTableWidgetItem(action_text))

            self.logs_table.setItem(i, 3, QTableWidgetItem(str(row[3]) if row[3] else ""))

            # Visual feedback for voided sales
            if row[4] == 1:
                for col in range(4):
                    self.logs_table.item(i, col).setForeground(Qt.red)
                    font = self.logs_table.item(i, col).font()
                    font.setStrikeOut(True)
                    self.logs_table.item(i, col).setFont(font)

        self._update_pagination_controls()

    def reprint_receipt(self):
        current_row = self.logs_table.currentRow()
        if current_row < 0 or current_row >= len(self._log_rows):
            QMessageBox.warning(self, "Selection Required", "Please select a sale log entry first.")
            return

        row_data = self._log_rows[current_row]
        action = str(row_data[2])
        if action != "POS_SALE":
            QMessageBox.warning(self, "Invalid Selection", "Reprinting is only available for Sales.")
            return

        details = str(row_data[3]) if row_data[3] else ""
        try:
            if "Sale #" in details:
                sale_id = int(details.split("Sale #")[1].split(" ")[0].strip())
            else:
                raise ValueError("Sale ID not found in details")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Could not determine Sale ID from logs: {e}")
            return

        # Fetch Sale and Items from database
        conn = database.get_connection()
        cursor = conn.cursor()
        
        # Get Sale details
        cursor.execute("SELECT total_amount, amount_paid, balance_due, timestamp FROM sales WHERE id = ?", (sale_id,))
        sale = cursor.fetchone()
        if not sale:
            conn.close()
            QMessageBox.critical(self, "Error", f"Sale #{sale_id} not found in database.")
            return
        
        total, paid, due, timestamp = sale
        
        # Get Items
        cursor.execute("SELECT product_name, quantity, price, product_id FROM sale_items WHERE sale_id = ?", (sale_id,))
        items_rows = cursor.fetchall()
        conn.close()

        if not items_rows:
            QMessageBox.information(self, "No Items Found", f"No detailed item data found for Sale #{sale_id}. Only transactions recorded after this update will have detailed item logs.")
            # We can still print a summary receipt if they want, but usually users want the items.
            return

        # Prepare receipt data
        receipt_data = {
            'header': 'EMMA SARMING STORE (REPRINT)',
            'cashier': self.username.capitalize(),
            'sale_id': sale_id,
            'items': [{'barcode': row[3], 'name': row[0], 'qty': row[1], 'price': row[2]} for row in items_rows],
            'total': total,
            'amount_paid': paid,
            'balance_due': due,
            'footer': f'Reprinted on: {QDate.currentDate().toString("yyyy-MM-dd")}'
        }

        # Show Preview Dialog
        preview = ReceiptPreviewDialog(receipt_data, self)
        if preview.exec():
            printer = ReceiptPrinter()
            # Rely on print_receipt() to handle connection/reconnection
            success = printer.print_receipt(receipt_data)
            if success:
                QMessageBox.information(self, "Success", "Receipt reprinted successfully.")
            else:
                QMessageBox.warning(self, "Printer Error", "Printer Not Detected or Failed to Print.\nPlease check settings and connections.")

    def void_sale(self):
        current_row = self.logs_table.currentRow()
        if current_row < 0 or current_row >= len(self._log_rows):
            QMessageBox.warning(self, "Selection Required", "Please select a sale log entry first.")
            return

        row_data = self._log_rows[current_row]
        action = str(row_data[2])
        if action != "POS_SALE":
            QMessageBox.warning(self, "Invalid Selection", "Only sales can be voided.")
            return

        details = str(row_data[3]) if row_data[3] else ""
        try:
            sale_id = int(details.split("Sale #")[1].split(" ")[0].strip())
        except:
            QMessageBox.critical(self, "Error", "Could not determine Sale ID.")
            return

        # Verification
        if self.user_role != "admin":
            from PySide6.QtWidgets import QInputDialog, QLineEdit
            password, ok = QInputDialog.getText(self, "Admin Required", "Enter Admin Password to Void Sale:", QLineEdit.Password)
            if not ok or not password:
                return
            user_data = database.verify_login("admin", password)
            if not user_data:
                QMessageBox.warning(self, "Access Denied", "Invalid Admin Password")
                return

        reply = QMessageBox.question(
            self, "Confirm Void Sale", 
            f"Are you sure you want to VOID Sale #{sale_id}?\nThis will mark the sale as inactive.",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            conn = database.get_connection()
            cursor = conn.cursor()
            
            # Check if already voided
            cursor.execute("SELECT voided FROM sales WHERE id = ?", (sale_id,))
            res = cursor.fetchone()
            if res and res[0] == 1:
                conn.close()
                QMessageBox.warning(self, "Already Voided", "This sale has already been voided.")
                return

            try:
                # 1. Mark Sale as voided
                cursor.execute("UPDATE sales SET voided = 1 WHERE id = ?", (sale_id,))
                
                # 2. Handle Debtors if any
                cursor.execute("DELETE FROM debtors WHERE sale_id = ?", (sale_id,))
                
                conn.commit()
                database.log_action("VOID_SALE", f"Voided Sale #{sale_id}", self.username)
                QMessageBox.information(self, "Success", f"Sale #{sale_id} has been voided successfully.")
                self.load_logs()
                
            except Exception as e:
                conn.rollback()
                QMessageBox.critical(self, "Error", f"Failed to void sale: {e}")
            finally:
                conn.close()
