# pyrefly: ignore [missing-import]
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, QPushButton, 
    QTableWidget, QTableWidgetItem, QLabel, QMessageBox, QDialog, QFormLayout, QInputDialog, QHeaderView, QCompleter, QDoubleSpinBox, QSpinBox, QCheckBox, QComboBox,
    QListWidget, QListWidgetItem
)
# pyrefly: ignore [missing-import]
from PySide6.QtCore import Qt, QStringListModel, QTimer, QEvent
import time
import json
# pyrefly: ignore [missing-import]
from PySide6.QtGui import QKeySequence, QShortcut
import database
import printer_helper
from printer_helper import ReceiptPrinter
# Import StockInDialog for the "Add Product" prompt
from inventory_module import StockInDialog
import os
import sys

def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

class POSModule(QWidget):
    def __init__(self, user_role="staff", username="admin"):
        super().__init__()
        self.user_role = user_role
        self.username = username
        self.pricing_mode = "retail"  # Default: 'retail' or 'wholesale'
        self.cart = []  # List of dicts {barcode, name, price, qty}
        self._last_add_time = 0
        self.setup_ui()
        # Install event filter to catch keys globally within this module
        self.installEventFilter(self)

    def get_bold_font(self, size):
        # pyrefly: ignore [missing-import]
        from PySide6.QtGui import QFont
        font = QFont()
        font.setPointSize(size)
        font.setBold(True)
        return font

    def setup_ui(self):
        layout = QVBoxLayout(self)

        # Top Bar: Search and Actions
        top_layout = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Scan Barcode or Enter Product ID (F4)...")
        self.search_input.setMinimumHeight(50)
        self.search_input.setStyleSheet("font-size: 18px; font-weight: 500; padding: 5px;")
        self.search_input.returnPressed.connect(self.add_item_to_cart)
        
        self.completer = QCompleter()
        self.completer.setCaseSensitivity(Qt.CaseInsensitive)
        self.completer.setFilterMode(Qt.MatchContains)
        self.completer.activated.connect(self.on_completer_activated)
        # Completer popup font
        self.completer.popup().setStyleSheet("font-size: 16px;")
        self.search_input.setCompleter(self.completer)
        self.refresh_completer()
        
        top_layout.addWidget(self.search_input)

        # Quantity Pre-selection Spinbox
        self.qty_label = QLabel("Qty:")
        self.qty_label.setStyleSheet("font-size: 16px; font-weight: bold; color: #1E293B; margin-left: 10px;")
        top_layout.addWidget(self.qty_label)
        
        self.qty_input = QSpinBox()
        self.qty_input.setRange(1, 99999)
        self.qty_input.setValue(1)
        self.qty_input.setMinimumHeight(50)
        self.qty_input.setMinimumWidth(80)
        self.qty_input.setMaximumWidth(120)
        up_path = resource_path("up_arrow.svg").replace("\\", "/")
        down_path = resource_path("down_arrow.svg").replace("\\", "/")
        self.qty_input.setStyleSheet(f"""
            QSpinBox {{
                font-size: 18px; 
                font-weight: bold; 
                padding-left: 10px;
                padding-right: 32px; /* Leaves room for sleek custom buttons */
                background-color: #F8FAFC; 
                border: 2px solid #CBD5E1; 
                border-radius: 8px;
                color: #1E293B;
            }}
            QSpinBox:focus {{
                border: 2px solid #0072FF;
                background-color: #FFFFFF;
            }}
            QSpinBox::up-button {{
                subcontrol-origin: border;
                subcontrol-position: top right;
                width: 28px;
                height: 24px;
                border-left: 1px solid #CBD5E1;
                border-bottom: 1px solid #E2E8F0;
                border-top-right-radius: 6px;
                background-color: #F1F5F9;
            }}
            QSpinBox::up-button:hover {{
                background-color: #E2E8F0;
            }}
            QSpinBox::up-button:pressed {{
                background-color: #CBD5E1;
            }}
            QSpinBox::down-button {{
                subcontrol-origin: border;
                subcontrol-position: bottom right;
                width: 28px;
                height: 24px;
                border-left: 1px solid #CBD5E1;
                border-bottom-right-radius: 6px;
                background-color: #F1F5F9;
            }}
            QSpinBox::down-button:hover {{
                background-color: #E2E8F0;
            }}
            QSpinBox::down-button:pressed {{
                background-color: #CBD5E1;
            }}
            QSpinBox::up-arrow {{
                image: url("{up_path}");
                width: 10px;
                height: 10px;
            }}
            QSpinBox::down-arrow {{
                image: url("{down_path}");
                width: 10px;
                height: 10px;
            }}
        """)
        self.qty_input.setAlignment(Qt.AlignCenter)
        top_layout.addWidget(self.qty_input)

        # Global Pricing Mode Toggle Button
        self.btn_pricing_mode = QPushButton("Pricing: RETAIL (Ctrl+W)")
        self.btn_pricing_mode.setMinimumHeight(50)
        self.btn_pricing_mode.setMinimumWidth(240)
        self.btn_pricing_mode.setStyleSheet("""
            QPushButton {
                background-color: #0284c7; 
                color: #FFFFFF; 
                font-weight: bold; 
                font-size: 16px;
                border-radius: 8px;
                padding: 10px;
                border: none;
            }
            QPushButton:hover {
                background-color: #38bdf8; 
            }
        """)
        self.btn_pricing_mode.clicked.connect(self.toggle_global_pricing_mode)
        top_layout.addWidget(self.btn_pricing_mode)

        layout.addLayout(top_layout)

        # Cart Table
        self.cart_table = QTableWidget(0, 6)
        self.cart_table.setHorizontalHeaderLabels(["Barcode", "Product Name", "Pricing", "Price", "Total", "Qty"])
        self.cart_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Interactive)
        self.cart_table.setColumnWidth(0, 140)
        self.cart_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.cart_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Interactive)
        self.cart_table.setColumnWidth(2, 110)
        self.cart_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.Interactive)
        self.cart_table.setColumnWidth(3, 110)
        self.cart_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.Interactive)
        self.cart_table.setColumnWidth(4, 120)
        self.cart_table.horizontalHeader().setSectionResizeMode(5, QHeaderView.Interactive)
        self.cart_table.setColumnWidth(5, 150)
        self.cart_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.cart_table.setStyleSheet("font-size: 16px;")
        self.cart_table.horizontalHeader().setStyleSheet("font-size: 16px; font-weight: bold;")
        self.cart_table.verticalHeader().setDefaultSectionSize(40) # Taller rows
        self.cart_table.installEventFilter(self) # Catch keys when table is focused
        self.cart_table.cellDoubleClicked.connect(self.on_cell_double_clicked)
        self._qty_editor_row = -1  # Track which row has an active inline qty editor
        layout.addWidget(self.cart_table)

        # Action Buttons Layout
        btn_layout = QHBoxLayout()

        self.btn_qty = QPushButton("Change Qty (Ctrl+Q)")
        self.btn_qty.setMinimumHeight(45)
        self.btn_qty.setStyleSheet("font-size: 15px; font-weight: bold;")
        self.btn_qty.clicked.connect(self.change_qty)
        self.btn_qty.installEventFilter(self)
        QShortcut(QKeySequence("Ctrl+Q"), self, context=Qt.WidgetWithChildrenShortcut).activated.connect(self.change_qty)
        btn_layout.addWidget(self.btn_qty)

        self.btn_delete = QPushButton("Delete Item (Del)")
        self.btn_delete.setMinimumHeight(45)
        self.btn_delete.setStyleSheet("font-size: 15px; font-weight: bold;")
        self.btn_delete.clicked.connect(self.delete_item)
        self.btn_delete.installEventFilter(self)
        QShortcut(QKeySequence(Qt.Key_Delete), self, context=Qt.WidgetWithChildrenShortcut).activated.connect(self.delete_item)
        btn_layout.addWidget(self.btn_delete)

        self.btn_discount = QPushButton("Discount (Ctrl+D)")
        self.btn_discount.setMinimumHeight(45)
        self.btn_discount.setStyleSheet("font-size: 15px; font-weight: bold;")
        self.btn_discount.clicked.connect(self.apply_discount)
        self.btn_discount.installEventFilter(self)
        QShortcut(QKeySequence("Ctrl+D"), self, context=Qt.WidgetWithChildrenShortcut).activated.connect(self.apply_discount)
        btn_layout.addWidget(self.btn_discount)

        self.btn_toggle_pricing = QPushButton("Wholesale/Retail (Ctrl+W)")
        self.btn_toggle_pricing.setMinimumHeight(45)
        self.btn_toggle_pricing.setStyleSheet("font-size: 15px; font-weight: bold; background-color: #0f766e; color: white;")
        self.btn_toggle_pricing.clicked.connect(self.toggle_wholesale_shortcut)
        self.btn_toggle_pricing.installEventFilter(self)
        btn_layout.addWidget(self.btn_toggle_pricing)

        self.btn_quick_add = QPushButton("Quick Add (Ctrl+Shift+A)")
        self.btn_quick_add.setMinimumHeight(45)
        self.btn_quick_add.setStyleSheet("font-size: 15px; font-weight: bold; background-color: #0f766e; color: white;")
        self.btn_quick_add.clicked.connect(self.quick_add_item)
        self.btn_quick_add.installEventFilter(self)
        QShortcut(QKeySequence("Ctrl+Shift+A"), self, context=Qt.WidgetWithChildrenShortcut).activated.connect(self.quick_add_item)
        btn_layout.addWidget(self.btn_quick_add)

        layout.addLayout(btn_layout)

        # Bottom Bar: Total & Checkout
        bottom_layout = QHBoxLayout()
        
        self.btn_checkout = QPushButton("Checkout (F12)")
        self.btn_checkout.setMinimumWidth(180)
        self.btn_checkout.setStyleSheet("""
            QPushButton {
                background-color: qlineargradient(spread:pad, x1:0, y1:0, x2:1, y2:0, stop:0 #00C6FF, stop:1 #0072FF); 
                color: #FFFFFF; 
                font-weight: bold; 
                font-size: 24px;
                border-radius: 8px;
                padding: 20px;
                border: none;
            }
            QPushButton:hover {
                background-color: qlineargradient(spread:pad, x1:0, y1:0, x2:1, y2:0, stop:0 #00E5FF, stop:1 #0088FF); 
            }
            QPushButton:pressed {
                background-color: qlineargradient(spread:pad, x1:0, y1:0, x2:1, y2:0, stop:0 #0099CC, stop:1 #0055CC); 
            }
        """)
        self.btn_checkout.clicked.connect(self.checkout)
        self.btn_checkout.installEventFilter(self)
        QShortcut(QKeySequence("Ctrl+Return"), self, context=Qt.WidgetWithChildrenShortcut).activated.connect(self.checkout)
        QShortcut(QKeySequence("F12"), self, context=Qt.WidgetWithChildrenShortcut).activated.connect(self.checkout)
        bottom_layout.addWidget(self.btn_checkout)

        bottom_layout.addStretch()

        self.total_label = QLabel("Total: ₱0.00")
        self.total_label.setStyleSheet("""
            font-size: 42px; 
            font-weight: 900; 
            color: #0072FF; 
            background-color: #F8FAFC;
            border: 2px solid #0072FF;
            border-radius: 12px;
            padding: 15px 30px;
        """)
        bottom_layout.addWidget(self.total_label)

        layout.addLayout(bottom_layout)

        # Bottom Bar 2: Advanced Actions
        adv_layout = QHBoxLayout()
        
        self.btn_park = QPushButton("Park Sale (Ctrl+P)")
        self.btn_park.setStyleSheet("background-color: #64748B; color: white; font-weight: bold; padding: 10px;")
        self.btn_park.clicked.connect(self.park_sale)
        self.btn_park.installEventFilter(self)
        QShortcut(QKeySequence("Ctrl+P"), self, context=Qt.WidgetWithChildrenShortcut).activated.connect(self.park_sale)
        adv_layout.addWidget(self.btn_park)

        self.btn_recall = QPushButton("Recall Sale (Ctrl+R)")
        self.btn_recall.setStyleSheet("background-color: #64748B; color: white; font-weight: bold; padding: 10px;")
        self.btn_recall.clicked.connect(self.recall_sale)
        self.btn_recall.installEventFilter(self)
        QShortcut(QKeySequence("Ctrl+R"), self, context=Qt.WidgetWithChildrenShortcut).activated.connect(self.recall_sale)
        adv_layout.addWidget(self.btn_recall)

        adv_layout.addStretch()

        self.btn_void_cart = QPushButton("Void Cart (Ctrl+Shift+V)")
        self.btn_void_cart.setStyleSheet("background-color: #EF4444; color: white; font-weight: bold; padding: 10px;")
        self.btn_void_cart.clicked.connect(self.void_current_cart)
        self.btn_void_cart.installEventFilter(self)
        QShortcut(QKeySequence("Ctrl+Shift+V"), self, context=Qt.WidgetWithChildrenShortcut).activated.connect(self.void_current_cart)
        adv_layout.addWidget(self.btn_void_cart)

        layout.addLayout(adv_layout)

        # Global Search Focus
        QShortcut(QKeySequence("Ctrl+F"), self, context=Qt.WidgetWithChildrenShortcut).activated.connect(self.search_input.setFocus)
        
        # Toggle Wholesale / Retail Mode Shortcut
        QShortcut(QKeySequence("Ctrl+W"), self, context=Qt.WidgetWithChildrenShortcut).activated.connect(self.toggle_wholesale_shortcut)

    def toggle_global_pricing_mode(self):
        if self.pricing_mode == "retail":
            self.pricing_mode = "wholesale"
        else:
            self.pricing_mode = "retail"
        self.update_pricing_mode_ui()

    def update_pricing_mode_ui(self):
        if self.pricing_mode == "retail":
            self.btn_pricing_mode.setText("Pricing: RETAIL (Ctrl+W)")
            self.btn_pricing_mode.setStyleSheet("""
                QPushButton {
                    background-color: #0284c7; 
                    color: #FFFFFF; 
                    font-weight: bold; 
                    font-size: 16px;
                    border-radius: 8px;
                    padding: 10px;
                    border: none;
                }
                QPushButton:hover {
                    background-color: #38bdf8; 
                }
            """)
        else:
            self.btn_pricing_mode.setText("Pricing: WHOLESALE (Ctrl+W)")
            self.btn_pricing_mode.setStyleSheet("""
                QPushButton {
                    background-color: #ea580c; 
                    color: #FFFFFF; 
                    font-weight: bold; 
                    font-size: 16px;
                    border-radius: 8px;
                    padding: 10px;
                    border: none;
                }
                QPushButton:hover {
                    background-color: #f97316; 
                }
            """)

    def toggle_wholesale_shortcut(self):
        current_row = self.cart_table.currentRow()
        if current_row >= 0 and current_row < len(self.cart):
            # Toggle specific item in cart!
            item = self.cart[current_row]
            pricing_type = item.get("pricing_type", "retail")
            is_bundle = item.get("is_bundle", False)
            bundle_name = item.get("bundle_name")
            
            # Fetch prices from database to know wholesale and retail prices
            conn = database.get_connection()
            cursor = conn.cursor()
            if is_bundle:
                cursor.execute("SELECT price, wholesale_price FROM product_bundles WHERE product_id=? AND bundle_name=?", (item["barcode"], bundle_name))
            else:
                cursor.execute("SELECT price, wholesale_price FROM products WHERE id=?", (item["barcode"],))
            prod = cursor.fetchone()
            conn.close()
            
            if prod:
                retail_p, wholesale_p = prod
                if wholesale_p is None or wholesale_p <= 0:
                    QMessageBox.warning(self, "No Wholesale Price", f"Product/Bundle '{item['name']}' does not have a defined wholesale price.")
                    return
                
                # Check if current item price matches retail or wholesale
                if pricing_type == "wholesale":
                    # Toggle to retail
                    item["pricing_type"] = "retail"
                    item["price"] = retail_p
                    item["name"] = item["name"].replace(" (Wholesale)", "")
                    database.log_action("POS_ITEM_PRICE_TOGGLE", f"Marked {item['name']} price as Retail: ₱{retail_p:,.2f}", self.user_role)
                else:
                    # Toggle to wholesale
                    item["pricing_type"] = "wholesale"
                    item["price"] = wholesale_p
                    if " (Wholesale)" not in item["name"]:
                        item["name"] += " (Wholesale)"
                    database.log_action("POS_ITEM_PRICE_TOGGLE", f"Marked {item['name']} price as Wholesale: ₱{wholesale_p:,.2f}", self.user_role)
                
                self.update_cart_display()
        else:
            # Toggle global mode
            self.toggle_global_pricing_mode()

    def eventFilter(self, obj, event):
        # Commit inline qty editor when its spinbox loses focus, or handle Escape/Enter
        if self._qty_editor_row >= 0:
            widget = self.cart_table.cellWidget(self._qty_editor_row, 5)
            if isinstance(widget, QSpinBox) and (obj is widget or obj is widget.lineEdit()):
                if event.type() == QEvent.FocusOut:
                    self._commit_qty_editor()
                    return False  # Don't consume focus event
                if event.type() == QEvent.KeyPress:
                    if event.key() in (Qt.Key_Return, Qt.Key_Enter):
                        self._commit_qty_editor()
                        return True
                    if event.key() == Qt.Key_Escape:
                        # Cancel: discard editor without committing
                        self._qty_editor_row = -1
                        self.update_cart_display()
                        QTimer.singleShot(50, self.search_input.setFocus)
                        return True

        if event.type() == QEvent.KeyPress:
            # Arrow Up/Down on the cart table → increment/decrement qty (only when no inline editor is open)
            if obj == self.cart_table and self._qty_editor_row < 0:
                if event.key() == Qt.Key_Up and not event.modifiers():
                    self._arrow_adjust_qty(+1)
                    return True
                if event.key() == Qt.Key_Down and not event.modifiers():
                    self._arrow_adjust_qty(-1)
                    return True

            # If search input doesn't have focus, redirect printable keys and Return to it
            if obj != self.search_input and not self.search_input.hasFocus():
                # Don't steal keys when qty inline editor is active
                if self._qty_editor_row >= 0:
                    return super().eventFilter(obj, event)

                if event.key() in (Qt.Key_Return, Qt.Key_Enter):
                    if self.search_input.text().strip():
                        self.add_item_to_cart()
                        return True # Consume event
                
                text = event.text()
                if text and text.isprintable() and not (event.modifiers() & (Qt.ControlModifier | Qt.AltModifier)):
                    self.search_input.setFocus()
                    # Ensure we don't select-all on focus, which would overwrite the first character
                    self.search_input.deselect()
                    self.search_input.setCursorPosition(len(self.search_input.text()))
                    self.search_input.insert(text)
                    return True # Consume event
        
        return super().eventFilter(obj, event)

    def _arrow_adjust_qty(self, delta):
        """Increment or decrement the qty of the currently selected cart row by delta."""
        current_row = self.cart_table.currentRow()
        if current_row < 0 or current_row >= len(self.cart):
            return
        new_qty = max(1, self.cart[current_row]["qty"] + delta)
        self.cart[current_row]["qty"] = new_qty
        database.log_action(
            "POS_QTY_UPDATE",
            f"Arrow-adjusted qty of {self.cart[current_row]['name']} to {new_qty}",
            self.user_role
        )
        self.update_cart_display()
        # Re-select the same row after refresh
        self.cart_table.setCurrentCell(current_row, 5)

    def on_cell_double_clicked(self, row, col):
        """Open an inline QSpinBox editor in the Qty cell on double-click."""
        if col != 5:  # Only allow editing the Qty column
            return
        if row < 0 or row >= len(self.cart):
            return

        # Commit any existing editor first
        self._commit_qty_editor()

        self._qty_editor_row = row
        current_qty = int(self.cart[row]["qty"])

        editor = QSpinBox()
        editor.setRange(1, 100000)
        editor.setValue(current_qty)
        editor.setStyleSheet(
            "font-size: 16px; font-weight: bold; "
            "background-color: #FFF9C4; border: 2px solid #F59E0B; border-radius: 4px;"
        )
        editor.setAlignment(Qt.AlignCenter)

        # Commit on Enter/Return
        editor.editingFinished.connect(lambda: self._commit_qty_editor())
        # Also commit if focus leaves the spinbox, and capture key presses on the internal lineEdit!
        editor.installEventFilter(self)
        editor.lineEdit().installEventFilter(self)

        self.cart_table.setCellWidget(row, 5, editor)
        editor.setFocus()
        editor.selectAll()

    def _commit_qty_editor(self):
        """Read the inline QSpinBox value and apply it to the cart."""
        row = self._qty_editor_row
        if row < 0 or row >= len(self.cart):
            self._qty_editor_row = -1
            return

        widget = self.cart_table.cellWidget(row, 5)
        if isinstance(widget, QSpinBox):
            new_qty = widget.value()
            if new_qty > 0:
                self.cart[row]["qty"] = new_qty
                database.log_action(
                    "POS_QTY_UPDATE",
                    f"Inline-edited qty of {self.cart[row]['name']} to {new_qty}",
                    self.user_role
                )

        self._qty_editor_row = -1
        self.update_cart_display()
        QTimer.singleShot(50, self.search_input.setFocus)

    def refresh_completer(self):
        conn = database.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id, name, price, wholesale_price FROM products")
        products = cursor.fetchall()
        conn.close()
        
        self.product_list = []
        for p in products:
            barcode, name, retail_p, wholesale_p = p
            if wholesale_p and wholesale_p > 0:
                self.product_list.append(f"{barcode} - {name} - Retail: ₱{retail_p:,.2f} | Wholesale: ₱{wholesale_p:,.2f}")
            else:
                self.product_list.append(f"{barcode} - {name} - ₱{retail_p:,.2f}")
                
        model = QStringListModel(self.product_list)
        self.completer.setModel(model)

    def on_completer_activated(self, text):
        self.search_input.blockSignals(True)
        self.search_input.setText(text)
        self.add_item_to_cart()
        self.search_input.blockSignals(False)

    def add_item_to_cart(self):
        # Ultimate fix for double trigger: Disable input while processing
        if not self.search_input.isEnabled():
            return
            
        now = time.time()
        if now - self._last_add_time < 0.3: # 300ms debounce
            return
        
        text = self.search_input.text().strip()
        if not text:
            return

        self.search_input.setEnabled(False) # BLOCK FURTHER INPUT
        self.search_input.clear()
        
        is_deferred = False
        try:
            qty_to_add = 1.0
            barcode_raw = text.split(" - ")[0].strip()

            # Handle formatting like '5*12345' or '12345*5'
            if '*' in barcode_raw:
                parts = barcode_raw.split('*')
                try:
                    qty_to_add = float(parts[0])
                    barcode = parts[1].strip()
                except ValueError:
                    try:
                        qty_to_add = float(parts[1])
                        barcode = parts[0].strip()
                    except ValueError:
                        barcode = barcode_raw
            else:
                barcode = barcode_raw

            conn = database.get_connection()
            cursor = conn.cursor()
            product = None
            try:
                cursor.execute("SELECT id, name, price, wholesale_price FROM products WHERE id=?", (barcode,))
                product = cursor.fetchone()
            finally:
                conn.close()

            if product:
                p_id, p_name, retail_p, wholesale_p = product
                
                # Check active pricing mode
                if self.pricing_mode == "wholesale" and wholesale_p and wholesale_p > 0:
                    p_price = wholesale_p
                    p_type = "wholesale"
                    if " (Wholesale)" not in p_name:
                        p_name += " (Wholesale)"
                else:
                    p_price = retail_p
                    p_type = "retail"
                    
                is_manual_multiplier = '*' in text
                if not is_manual_multiplier:
                    final_qty = float(self.qty_input.value())
                else:
                    final_qty = qty_to_add
                
                # Reset quantity pre-selection spinbox to 1 after consumption
                self.qty_input.setValue(1)
                
                self.add_product_to_cart_record(p_id, p_name, p_price, final_qty, p_price, p_type)
            else:
                is_deferred = True
                # Defer prompting the add new product workflow after a 150ms delay.
                QTimer.singleShot(150, lambda: self.prompt_add_new_product(barcode))

        finally:
            if not is_deferred:
                self._last_add_time = time.time() # Update debounce AFTER processing
                self.search_input.setEnabled(True) # UNBLOCK
                self.search_input.setFocus()
                # Ensure input is cleared (handles completer re-fill race condition)
                QTimer.singleShot(50, self.search_input.clear)



    def prompt_add_new_product(self, barcode):
        self.search_input.setEnabled(False)
        try:
            # Prompt to add new product
            reply = QMessageBox.question(
                self, "Product Not Found", 
                f"Barcode '{barcode}' was not found in the database.\nWould you like to add this as a new product?",
                QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes
            )
            if reply == QMessageBox.Yes:
                if not self.verify_admin():
                    return
                
                dialog = StockInDialog(self)
                dialog.inp_barcode.setText(barcode)
                if dialog.exec():
                    data = dialog.get_data()
                    conn = database.get_connection()
                    try:
                        cursor = conn.cursor()
                        cursor.execute("""
                            INSERT INTO products (id, name, price, wholesale_price, category)
                            VALUES (?, ?, ?, ?, ?)
                        """, (data["barcode"], data["name"], data["sell_price"], data["wholesale_price"], data["category"]))
                        conn.commit()
                    except Exception as e:
                        conn.rollback()
                        QMessageBox.critical(self, "Database Error", f"Failed to save product: {e}")
                        return
                    finally:
                        conn.close()
                    
                    database.log_action("PRODUCT_ADDED", f"Quick-added product '{data['name']}' from POS", self.user_role)
                    self.refresh_completer()
                    
                    # Automatically trigger Add to Cart workflow
                    p_id, p_name, retail_p, wholesale_p = data["barcode"], data["name"], data["sell_price"], data["wholesale_price"]
                    if self.pricing_mode == "wholesale" and wholesale_p and wholesale_p > 0:
                        p_price = wholesale_p
                        p_type = "wholesale"
                        if " (Wholesale)" not in p_name:
                            p_name += " (Wholesale)"
                    else:
                        p_price = retail_p
                        p_type = "retail"
                    
                    dialog_cart = AddToCartDialog(p_name, 1, p_price, self)
                    if dialog_cart.exec():
                        final_qty, final_price = dialog_cart.get_data()
                        if final_qty > 0:
                            self.add_product_to_cart_record(p_id, p_name, p_price, final_qty, final_price, p_type)
        finally:
            self._last_add_time = time.time()
            self.search_input.setEnabled(True)
            self.search_input.setFocus()
            QTimer.singleShot(50, self.search_input.clear)



    def add_product_to_cart_record(self, p_id, p_name, p_price, final_qty, final_price, pricing_type="retail", is_bundle=False, bundle_name=None):
        # Check if already in cart with exact same barcode and pricing_type
        found_item = None
        for item in self.cart:
            if (item["barcode"] == p_id and 
                item.get("pricing_type", "retail") == pricing_type):
                found_item = item
                break

        if found_item:
            found_item["qty"] += final_qty
            # Move to the front (top) of the cart list
            self.cart.remove(found_item)
            self.cart.insert(0, found_item)
        else:
            # Insert at the beginning of self.cart
            self.cart.insert(0, {
                "barcode": p_id, 
                "name": p_name, 
                "price": final_price, 
                "qty": final_qty,
                "pricing_type": pricing_type,
            })
        
        self.update_cart_display()
        if self.cart_table.rowCount() > 0:
            self.cart_table.setCurrentCell(0, 5)

    def update_cart_display(self):
        # Dynamically apply volume-based and bundle-based pricing adjustments in the cart.
        conn = database.get_connection()
        cursor = conn.cursor()
        try:
            # Group items by barcode to process each product collectively
            barcodes_in_cart = set(item["barcode"] for item in self.cart)
            
            for barcode in barcodes_in_cart:
                # Fetch all bundle configurations for this barcode
                cursor.execute("SELECT bundle_name, quantity, price, wholesale_price FROM product_bundles WHERE product_id=?", (barcode,))
                bundles = cursor.fetchall()
                
                # Fetch base product details
                cursor.execute("SELECT name, price, wholesale_price FROM products WHERE id=?", (barcode,))
                prod_row = cursor.fetchone()
                if not prod_row:
                    continue
                
                base_name, base_retail, base_wholesale = prod_row
                
                # Filter cart items of this barcode
                prod_items = [item for item in self.cart if item["barcode"] == barcode]
                
                # Sum up total quantity of this barcode in the cart
                total_qty = sum(item["qty"] for item in prod_items)
                
                for item in prod_items:
                    pricing_type = item.get("pricing_type", "retail")
                    
                    # Determine base price
                    base_price = base_wholesale if (pricing_type == "wholesale" and base_wholesale and base_wholesale > 0) else base_retail
                    
                    # If no bundles are configured for this product, use the base price
                    if not bundles:
                        if not item.get("manually_discounted"):
                            item["price"] = base_price
                        continue
                    
                    # Find all unlocked per-piece rates based on the total quantity
                    unlocked_rates = []
                    
                    for b_name, b_qty, b_retail_price, b_wholesale_price in bundles:
                        qty_float = float(b_qty)
                        if qty_float > 0 and qty_float <= total_qty:
                            # Determine bundle price based on pricing type
                            bundle_price = b_wholesale_price if (pricing_type == "wholesale" and b_wholesale_price and b_wholesale_price > 0) else b_retail_price
                            # Per-piece rate is bundle price divided by bundle quantity
                            unlocked_rates.append(bundle_price / qty_float)
                    
                    # Apply the best unlocked rate (cheapest per-piece price), or revert to base price if none unlocked
                    if unlocked_rates:
                        best_rate = min(unlocked_rates)
                        if not item.get("manually_discounted"):
                            item["price"] = best_rate
                    else:
                        if not item.get("manually_discounted"):
                            item["price"] = base_price
                            
                    # Update cart display name to keep it clean (without any old bundle suffixes)
                    cleaned_name = base_name
                    if pricing_type == "wholesale" and base_wholesale and base_wholesale > 0:
                        if " (Wholesale)" not in cleaned_name:
                            cleaned_name += " (Wholesale)"
                    item["name"] = cleaned_name
                            
        except Exception as e:
            import logging
            logging.error(f"Error applying dynamic tiered bundle pricing: {e}")
        finally:
            conn.close()
 
        self.cart_table.setRowCount(0)
        total = 0.0
        for i, item in enumerate(self.cart):
            self.cart_table.insertRow(i)
            item_barcode = QTableWidgetItem(item["barcode"])
            item_name = QTableWidgetItem(item["name"])
            
            p_type = item.get("pricing_type", "retail")
            pricing_text = "WHOLESALE" if p_type == "wholesale" else "RETAIL"
            item_pricing = QTableWidgetItem(pricing_text)
            item_pricing.setFont(self.get_bold_font(14))
            if p_type == "wholesale":
                item_pricing.setForeground(Qt.darkYellow)
            else:
                item_pricing.setForeground(Qt.darkGreen)
            
            # Format unit price dynamically to show up to 3 decimal places if it has fractional cents
            price_str = f"{item['price']:.3f}".rstrip('0').rstrip('.')
            if '.' in price_str:
                parts = price_str.split('.')
                if len(parts[1]) < 2:
                    price_str = f"{item['price']:.2f}"
            else:
                price_str = f"{item['price']:.2f}"
                
            # Formatting with thousands separator
            try:
                whole, decimal = price_str.split('.')
                formatted_price = f"₱{int(whole):,}.{decimal}"
            except ValueError:
                formatted_price = f"₱{item['price']:,.2f}"
                
            item_price = QTableWidgetItem(formatted_price)
            item_price.setFont(self.get_bold_font(16))
            
            # Format subtotal/total of this item
            subtotal = item["price"] * item["qty"]
            subtotal_str = f"{subtotal:.3f}".rstrip('0').rstrip('.')
            if '.' in subtotal_str:
                sub_parts = subtotal_str.split('.')
                if len(sub_parts[1]) < 2:
                    subtotal_str = f"{subtotal:.2f}"
            else:
                subtotal_str = f"{subtotal:.2f}"
                
            try:
                sub_whole, sub_decimal = subtotal_str.split('.')
                formatted_subtotal = f"₱{int(sub_whole):,}.{sub_decimal}"
            except ValueError:
                formatted_subtotal = f"₱{subtotal:,.2f}"
                
            item_subtotal = QTableWidgetItem(formatted_subtotal)
            item_subtotal.setFont(self.get_bold_font(16))
            
            qty_val = item["qty"]
            display_qty = str(int(qty_val)) if qty_val.is_integer() else str(qty_val)
            
            item_qty = QTableWidgetItem(display_qty)
            item_qty.setFont(self.get_bold_font(16))
            
            self.cart_table.setItem(i, 0, item_barcode)
            self.cart_table.setItem(i, 1, item_name)
            self.cart_table.setItem(i, 2, item_pricing)
            self.cart_table.setItem(i, 3, item_price)
            self.cart_table.setItem(i, 4, item_subtotal)
            self.cart_table.setItem(i, 5, item_qty)
            total += round(item["price"] * item["qty"], 4)
 
        self.total_label.setText(f"Total: ₱{round(total, 2):,.2f}")

    def park_sale(self):
        if not self.cart:
            return
            
        label, ok = QInputDialog.getText(self, "Park Sale", "Enter Customer Label/Reference (e.g., Table 5, Name):")
        if not ok:
            return
            
        total = sum(item["price"] * item["qty"] for item in self.cart)
        cart_json = json.dumps(self.cart)
        
        conn = database.get_connection()
        cursor = conn.cursor()
        cursor.execute("INSERT INTO parked_sales (label, cart_data, total) VALUES (?, ?, ?)", (label or "No Label", cart_json, total))
        conn.commit()
        conn.close()
        
        self.cart.clear()
        self.update_cart_display()
        QMessageBox.information(self, "Sale Parked", f"Sale for '{label or 'No Label'}' has been parked.")
        self.search_input.setFocus()

    def recall_sale(self):
        conn = database.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id, label, cart_data, total, timestamp FROM parked_sales ORDER BY timestamp DESC")
        parked = cursor.fetchall()
        conn.close()
        
        if not parked:
            QMessageBox.information(self, "No Parked Sales", "There are no parked sales to recall.")
            return
            
        items = [f"Ref: {p[1]} - Total: ₱{p[3]:,.2f} ({p[4]})" for p in parked]
        item_text, ok = QInputDialog.getItem(self, "Recall Sale", "Select a parked sale to recall:", items, 0, False)
        
        if ok and item_text:
            # Extract label and timestamp to find the exact ID
            selected_parked = next(p for p in parked if f"Ref: {p[1]} - Total: ₱{p[3]:,.2f} ({p[4]})" == item_text)
            parked_id = selected_parked[0]
            
            # If current cart is not empty, ask to merge
            if self.cart:
                reply = QMessageBox.question(
                    self, "Cart Not Empty", 
                    "The current cart is not empty. Would you like to merge the recalled sale into the current cart?",
                    QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel, QMessageBox.Yes
                )
                if reply == QMessageBox.Cancel:
                    return
                if reply == QMessageBox.No:
                    self.cart.clear()

            recalled_cart = json.loads(selected_parked[2])
            self.cart.extend(recalled_cart)
            
            # Delete from parked_sales
            conn = database.get_connection()
            cursor = conn.cursor()
            cursor.execute("DELETE FROM parked_sales WHERE id = ?", (parked_id,))
            conn.commit()
            conn.close()
            
            self.update_cart_display()
            self.search_input.setFocus()

    def void_current_cart(self):
        if not self.cart:
            return
            
        if not self.verify_admin():
            return
            
        reply = QMessageBox.question(
            self, "Confirm Void", 
            "Are you sure you want to void the ENTIRE current cart?",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            details = f"Voided cart with {len(self.cart)} items, Total: {self.total_label.text()}"
            database.log_action("POS_VOID_CART", details, self.user_role)
            self.cart.clear()
            self.update_cart_display()
            self.search_input.setFocus()

    def verify_admin(self):
        if self.user_role == "admin":
            return True
        password, ok = QInputDialog.getText(self, "Admin Required", "Enter Admin Password:", QLineEdit.Password)
        if ok and password:
            user_data = database.verify_login("admin", password)
            if user_data and user_data[1] == "admin":
                return True
        QMessageBox.warning(self, "Access Denied", "Invalid Admin Password")
        return False

    def change_qty(self):
        current_row = self.cart_table.currentRow()
        if current_row < 0:
            QMessageBox.warning(self, "Selection Required", "Please select an item from the cart first.")
            return

        current_qty = self.cart[current_row]["qty"]
        new_qty, ok = QInputDialog.getInt(self, "Change Quantity", "Enter New Quantity:", int(current_qty), 1, 100000)
        if ok and new_qty > 0:
            self.cart[current_row]["qty"] = int(new_qty)
            database.log_action("POS_QTY_UPDATE", f"Changed qty of {self.cart[current_row]['name']} to {new_qty}", self.user_role)
            self.update_cart_display()
            self.search_input.setFocus()

    def delete_item(self):
        current_row = self.cart_table.currentRow()
        if current_row < 0:
            return
        
        if not self.verify_admin():
            return

        item = self.cart[current_row]
        reply = QMessageBox.question(
            self, "Confirm Removal", 
            f"Remove {item['qty']}x '{item['name']}' from cart?",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            self.cart.pop(current_row)
            database.log_action("POS_DELETE", f"Removed {item['qty']}x {item['name']} from cart", self.user_role)
            self.update_cart_display()

    def apply_discount(self):
        current_row = self.cart_table.currentRow()
        if current_row < 0:
            return
            
        if not self.verify_admin():
            return
 
        dialog = DiscountDialog(self.cart[current_row]["name"], self.cart[current_row]["price"], self)
        if dialog.exec():
            new_price = dialog.get_price()
            self.cart[current_row]["price"] = new_price
            self.cart[current_row]["manually_discounted"] = True
            database.log_action("POS_DISCOUNT", f"Discounted {self.cart[current_row]['name']} to ₱{new_price:,.2f}", self.user_role)
            self.update_cart_display()
            self.search_input.setFocus()

    def checkout(self):
        if not self.cart:
            QMessageBox.warning(self, "Empty Cart", "Cannot checkout an empty cart.")
            return

        total = sum(item["price"] * item["qty"] for item in self.cart)
        dialog = CheckoutDialog(total, self)
        if dialog.exec():
            amount_paid, customer_info = dialog.get_data()
            balance_due = total - amount_paid

            conn = database.get_connection()
            cursor = conn.cursor()
            
            customer_id = None
            if balance_due > 0 and customer_info:
                cursor.execute("""
                    INSERT INTO customers (name, phone, address) VALUES (?, ?, ?)
                """, (customer_info["name"], customer_info["phone"], customer_info["address"]))
                customer_id = cursor.lastrowid

            cursor.execute("""
                INSERT INTO sales (total_amount, amount_paid, balance_due, customer_id, timestamp)
                VALUES (?, ?, ?, ?, datetime('now', '+8 hours'))
            """, (total, amount_paid, balance_due, customer_id))
            sale_id = cursor.lastrowid
            
            # Save Debtors
            if balance_due > 0 and customer_id:
                cursor.execute("""
                    INSERT INTO debtors (customer_id, sale_id, balance_amount, created_at)
                    VALUES (?, ?, ?, datetime('now', '+8 hours'))
                """, (customer_id, sale_id, balance_due))
            
            # Save Sale Items
            for item in self.cart:
                cursor.execute("""
                    INSERT INTO sale_items (sale_id, product_id, product_name, quantity, price)
                    VALUES (?, ?, ?, ?, ?)
                """, (sale_id, item["barcode"], item["name"], item["qty"], item["price"]))


            # Save Split Payments (Always Cash now)
            cursor.execute("""
                INSERT INTO sale_payments (sale_id, payment_method, amount)
                VALUES (?, ?, ?)
            """, (sale_id, "Cash", amount_paid))

            conn.commit()
            conn.close()

            # Log
            log_details = f"Sale #{sale_id} - Total: ₱{total:,.2f}, Paid: ₱{amount_paid:,.2f}"
            if balance_due < 0:
                log_details += f", Change: ₱{abs(balance_due):,.2f}"
            else:
                log_details += f", Balance: ₱{balance_due:,.2f}"
                
            database.log_action("POS_SALE", log_details, self.username)

            # Optional Print Modal after transaction
            reply = QMessageBox.question(
                self, "Print Receipt", "Transaction successful! Would you like to print the receipt?",
                QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes
            )

            # Print Receipt
            if reply == QMessageBox.Yes:
                receipt_data = {
                    'header': 'EMMA SARMING STORE',
                    'cashier': self.username.capitalize(),
                    'sale_id': sale_id,
                    'items': [{'barcode': i["barcode"], 'name': i["name"], 'qty': i["qty"], 'price': i["price"]} for i in self.cart],
                    'total': total,
                    'amount_paid': amount_paid,
                    'balance_due': balance_due if balance_due > 0 else 0.0,
                    'footer': 'Thank you! Come again!'
                }
                printer = ReceiptPrinter()
                # Rely on print_receipt() to handle connection/reconnection
                success = printer.print_receipt(receipt_data)
                if not success:
                    err_msg = getattr(printer, 'last_error', 'Unknown Error')
                    QMessageBox.warning(self, "Printer Error", f"Printer Not Detected or Failed to Print.\nError: {err_msg}")

            change_amount = amount_paid - total if amount_paid > total else 0.0
            msg = f"Transaction Completed!\nChange: ₱{change_amount:,.2f}" if change_amount > 0 else "Transaction Completed!"
            
            # BIG SUCCESS MESSAGE
            msg_box = QMessageBox(self)
            msg_box.setWindowTitle("Transaction Successful")
            msg_box.setText(msg)
            msg_box.setIcon(QMessageBox.Information)
            msg_box.setStyleSheet("""
                QMessageBox {
                    background-color: #ECFDF5;
                    min-width: 500px;
                }
                QLabel {
                    font-size: 32px;
                    font-weight: 900;
                    color: #064E3B;
                    padding: 40px;
                }
                QPushButton {
                    background-color: #064E3B;
                    color: white;
                    font-size: 20px;
                    font-weight: bold;
                    padding: 15px 30px;
                    border-radius: 8px;
                    min-width: 120px;
                }
            """)
            msg_box.exec()

            # Clear Cart
            self.cart.clear()
            self.update_cart_display()
            self.search_input.setFocus()

    def quick_add_item(self):
        dialog = QuickAddItemDialog(self)
        if dialog.exec():
            data = dialog.get_data()
            custom_barcode = f"CUSTOM-{int(time.time() * 1000)}"
            
            # Add to cart
            self.add_product_to_cart_record(
                p_id=custom_barcode,
                p_name=data["name"],
                p_price=data["price"],
                final_qty=data["quantity"],
                final_price=data["price"],
                pricing_type="retail"
            )
            
            # Log action
            database.log_action("POS_QUICK_ADD", f"Quick added custom item '{data['name']}' x{data['quantity']} @ ₱{data['price']:,.2f} to cart", self.user_role)


class CheckoutDialog(QDialog):
    def __init__(self, total, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Checkout (Cash Only)")
        self.setMinimumWidth(400)
        self.total = total
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)

        lbl_total = QLabel(f"Total Amount: ₱{self.total:,.2f}")
        lbl_total.setStyleSheet("font-size: 32px; font-weight: 900; color: #064E3B; border-bottom: 2px solid #D1D5DB; padding-bottom: 10px;")
        layout.addWidget(lbl_total)

        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignRight)
        
        self.amount_paid_input = QLineEdit()
        self.amount_paid_input.setPlaceholderText("Enter Amount Received")
        self.amount_paid_input.setMinimumHeight(60)
        self.amount_paid_input.setStyleSheet("font-size: 28px; font-weight: bold; color: #1F2937;")
        
        lbl_paid = QLabel("Cash Received (₱):")
        lbl_paid.setStyleSheet("font-size: 18px; font-weight: bold;")
        form.addRow(lbl_paid, self.amount_paid_input)
        layout.addLayout(form)

        # Reactive Change Label
        self.lbl_change = QLabel("Change: ₱0.00")
        self.lbl_change.setStyleSheet("font-size: 26px; font-weight: 900; color: #047857; background-color: #ECFDF5; padding: 10px; border-radius: 8px;")
        self.lbl_change.setVisible(False)
        layout.addWidget(self.lbl_change)

        # Customer Info for balance
        self.customer_widget = QWidget()
        cust_form = QFormLayout(self.customer_widget)
        self.cust_name = QLineEdit()
        self.cust_phone = QLineEdit()
        self.cust_addr = QLineEdit()
        cust_form.addRow("Customer Name:", self.cust_name)
        cust_form.addRow("Phone Number:", self.cust_phone)
        cust_form.addRow("Address:", self.cust_addr)
        
        self.customer_widget.setVisible(False)
        layout.addWidget(self.customer_widget)

        self.amount_paid_input.textChanged.connect(self.calculate_change)
        self.amount_paid_input.textEdited.connect(self.format_cash_input)

        self.btn_confirm = QPushButton("Confirm Payment (Enter)")
        self.btn_confirm.setMinimumHeight(60)
        self.btn_confirm.setStyleSheet("""
            QPushButton {
                background-color: #064E3B;
                color: white;
                font-size: 22px;
                font-weight: bold;
                border-radius: 10px;
            }
            QPushButton:hover { background-color: #047857; }
            QPushButton:disabled { background-color: #E5E7EB; color: #9CA3AF; }
        """)
        self.btn_confirm.clicked.connect(self.accept)
        self.btn_confirm.setDefault(True)
        self.btn_confirm.setEnabled(False) # Disabled by default
        layout.addWidget(self.btn_confirm)



    def calculate_change(self):
        try:
            val_str = self.amount_paid_input.text().replace(',', '').strip()
            if not val_str:
                self.btn_confirm.setEnabled(False)
                self.customer_widget.setVisible(False)
                self.lbl_change.setVisible(False)
                return

            paid = float(val_str)
            self.btn_confirm.setEnabled(True) # Enable confirm when input is valid
            
            if paid < self.total:
                self.customer_widget.setVisible(True)
                self.lbl_change.setVisible(False)
            else:
                self.customer_widget.setVisible(False)
                change = paid - self.total
                self.lbl_change.setText(f"Change: ₱{change:,.2f}")
                self.lbl_change.setVisible(True if change > 0.001 else False)
        except ValueError:
            self.btn_confirm.setEnabled(False)
            self.customer_widget.setVisible(False)
            self.lbl_change.setVisible(False)

    def format_cash_input(self, text):
        # Save cursor position and text
        line_edit = self.sender()
        if not isinstance(line_edit, QLineEdit):
            return
            
        pos = line_edit.cursorPosition()
        old_text = line_edit.text()
        
        # Remove commas for processing
        raw_val = text.replace(',', '')
        if not raw_val:
            return

        try:
            # Handle decimal parts
            if '.' in raw_val:
                parts = raw_val.split('.')
                whole = parts[0]
                decimal = ".".join(parts[1:]) # Handle multiple dots just in case
                if whole:
                    formatted = f"{int(whole):,}" + "." + decimal
                else:
                    formatted = "0." + decimal
            else:
                formatted = f"{int(raw_val):,}"
            
            # Update text only if changed to avoid recursion/jitter
            if formatted != old_text:
                line_edit.setText(formatted)
                # Adjust cursor position
                new_pos = pos + (len(formatted) - len(old_text))
                line_edit.setCursorPosition(max(0, new_pos))
        except ValueError:
            pass

    def get_data(self):
        try:
            paid = float(self.amount_paid_input.text().replace(',', ''))
        except ValueError:
            paid = 0.0

        customer_info = None
        if paid < self.total:
            customer_info = {
                "name": self.cust_name.text().strip() or "Unknown",
                "phone": self.cust_phone.text().strip(),
                "address": self.cust_addr.text().strip()
            }
        
        return paid, customer_info

class AddToCartDialog(QDialog):
    def __init__(self, product_name, default_qty, default_price, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Add Item")
        self.setMinimumWidth(350)
        self.setup_ui(product_name, default_qty, default_price)

    def setup_ui(self, name, qty, price):
        layout = QVBoxLayout(self)
        
        lbl = QLabel(f"Adding: {name}")
        lbl.setStyleSheet("font-size: 22px; font-weight: 900; color: #0072FF; margin-bottom: 5px;")
        layout.addWidget(lbl)
        
        
        form = QFormLayout()
        form.setSpacing(15)
        
        self.inp_qty = QSpinBox()
        self.inp_qty.setMinimumHeight(50)
        self.inp_qty.setRange(1, 10000)
        self.inp_qty.setValue(max(1, int(qty)))
        self.inp_qty.setStyleSheet("font-size: 22px; font-weight: bold;")
        
        lbl_q = QLabel("Quantity:")
        lbl_q.setStyleSheet("font-size: 16px; font-weight: bold;")
        form.addRow(lbl_q, self.inp_qty)
        
        self.inp_price = QLineEdit(f"{price:,.2f}")
        self.inp_price.setMinimumHeight(50)
        self.inp_price.setStyleSheet("font-size: 22px; font-weight: bold;")
        self.inp_price.textEdited.connect(self.format_cash_input)
        
        lbl_p = QLabel("Custom Price (₱):")
        lbl_p.setStyleSheet("font-size: 16px; font-weight: bold;")
        form.addRow(lbl_p, self.inp_price)
        
        layout.addLayout(form)
        
        btn_confirm = QPushButton("Confirm (Enter)")
        btn_confirm.setStyleSheet("""
            QPushButton {
                background-color: qlineargradient(spread:pad, x1:0, y1:0, x2:1, y2:0, stop:0 #00C6FF, stop:1 #0072FF); 
                color: #FFFFFF; 
                font-weight: bold;
                border-radius: 6px;
                padding: 10px;
                border: none;
            }
            QPushButton:hover {
                background-color: qlineargradient(spread:pad, x1:0, y1:0, x2:1, y2:0, stop:0 #00E5FF, stop:1 #0088FF); 
            }
        """)
        btn_confirm.clicked.connect(self.accept)
        btn_confirm.setDefault(True)
        layout.addWidget(btn_confirm)



    def format_cash_input(self, text):
        line_edit = self.sender()
        if not isinstance(line_edit, QLineEdit):
            return
        pos = line_edit.cursorPosition()
        old_text = line_edit.text()
        raw_val = text.replace(',', '')
        if not raw_val: return
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
        except ValueError: pass

    def get_data(self):
        try:
            qty = self.inp_qty.value()
            price = float(self.inp_price.text().replace(',', ''))
            return qty, price
        except:
            return 0, 0.0

class DiscountDialog(QDialog):
    def __init__(self, product_name, current_price, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Apply Discount")
        self.setMinimumWidth(350)
        self.setup_ui(product_name, current_price)

    def setup_ui(self, name, price):
        layout = QVBoxLayout(self)
        
        lbl = QLabel(f"Item: {name}")
        lbl.setStyleSheet("font-size: 18px; font-weight: bold; color: #1E293B;")
        layout.addWidget(lbl)
        
        form = QFormLayout()
        self.inp_price = QLineEdit(f"{price:,.2f}")
        self.inp_price.setMinimumHeight(50)
        self.inp_price.setStyleSheet("font-size: 22px; font-weight: bold;")
        self.inp_price.textEdited.connect(self.format_cash_input)
        
        lbl_p = QLabel("New Price (₱):")
        lbl_p.setStyleSheet("font-size: 16px; font-weight: bold;")
        form.addRow(lbl_p, self.inp_price)
        layout.addLayout(form)
        
        btn_confirm = QPushButton("Apply Discount (Enter)")
        btn_confirm.setMinimumHeight(50)
        btn_confirm.setStyleSheet("""
            QPushButton {
                background-color: #0072FF;
                color: white;
                font-weight: bold;
                border-radius: 6px;
            }
            QPushButton:hover { background-color: #005F99; }
        """)
        btn_confirm.clicked.connect(self.accept)
        btn_confirm.setDefault(True)
        layout.addWidget(btn_confirm)



    def format_cash_input(self, text):
        line_edit = self.sender()
        if not isinstance(line_edit, QLineEdit): return
        pos = line_edit.cursorPosition()
        old_text = line_edit.text()
        raw_val = text.replace(',', '')
        if not raw_val: return
        try:
            if '.' in raw_val:
                parts = raw_val.split('.')
                whole, decimal = parts[0], ".".join(parts[1:])
                formatted = (f"{int(whole):,}" if whole else "0") + "." + decimal
            else:
                formatted = f"{int(raw_val):,}"
            if formatted != old_text:
                line_edit.setText(formatted)
                new_pos = pos + (len(formatted) - len(old_text))
                line_edit.setCursorPosition(max(0, new_pos))
        except ValueError: pass

    def get_price(self):
        try:
            return float(self.inp_price.text().replace(',', ''))
        except:
            return 0.0





class QuickAddItemDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Quick Add Custom Item")
        self.setMinimumWidth(380)
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        
        lbl = QLabel("Quick Add Custom Item")
        lbl.setStyleSheet("font-size: 20px; font-weight: 900; color: #0072FF; margin-bottom: 5px;")
        layout.addWidget(lbl)
        
        form = QFormLayout()
        form.setSpacing(15)
        
        self.inp_name = QLineEdit()
        self.inp_name.setPlaceholderText("e.g. Custom Item / Box / Service")
        self.inp_name.setMinimumHeight(45)
        self.inp_name.setStyleSheet("font-size: 18px;")
        
        lbl_n = QLabel("Item Name:")
        lbl_n.setStyleSheet("font-size: 14px; font-weight: bold;")
        form.addRow(lbl_n, self.inp_name)
        
        self.inp_qty = QDoubleSpinBox()
        self.inp_qty.setMinimumHeight(45)
        self.inp_qty.setRange(0.1, 10000.0)
        self.inp_qty.setValue(1.0)
        self.inp_qty.setDecimals(1)
        self.inp_qty.setStyleSheet("font-size: 18px; font-weight: bold;")
        self.inp_qty.valueChanged.connect(self.update_total_preview)
        
        lbl_q = QLabel("Quantity:")
        lbl_q.setStyleSheet("font-size: 14px; font-weight: bold;")
        form.addRow(lbl_q, self.inp_qty)
        
        self.inp_price = QLineEdit("0.00")
        self.inp_price.setMinimumHeight(45)
        self.inp_price.setStyleSheet("font-size: 18px; font-weight: bold;")
        self.inp_price.textEdited.connect(self.format_cash_input)
        self.inp_price.textChanged.connect(self.update_total_preview)
        
        lbl_p = QLabel("Price (₱):")
        lbl_p.setStyleSheet("font-size: 14px; font-weight: bold;")
        form.addRow(lbl_p, self.inp_price)
        
        layout.addLayout(form)
        
        # Gorgeous dynamic Total Preview display
        self.lbl_total_preview = QLabel("Total Preview: ₱0.00")
        self.lbl_total_preview.setStyleSheet("""
            QLabel {
                font-size: 20px; 
                font-weight: bold; 
                color: #2ECC71; 
                margin-top: 10px; 
                margin-bottom: 10px;
                background-color: #F8F9FA;
                border: 1px solid #E2E8F0;
                border-radius: 6px;
                padding: 10px;
            }
        """)
        self.lbl_total_preview.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.lbl_total_preview)
        
        btn_confirm = QPushButton("Add to Cart (Enter)")
        btn_confirm.setStyleSheet("""
            QPushButton {
                background-color: qlineargradient(spread:pad, x1:0, y1:0, x2:1, y2:0, stop:0 #00C6FF, stop:1 #0072FF); 
                color: #FFFFFF; 
                font-weight: bold;
                border-radius: 6px;
                padding: 10px;
                border: none;
                font-size: 16px;
            }
            QPushButton:hover {
                background-color: qlineargradient(spread:pad, x1:0, y1:0, x2:1, y2:0, stop:0 #00E5FF, stop:1 #0088FF); 
            }
        """)
        btn_confirm.clicked.connect(self.accept_validation)
        layout.addWidget(btn_confirm)
        
        # Initialize total preview with defaults
        self.update_total_preview()

    def format_cash_input(self, text):
        line_edit = self.sender()
        if not isinstance(line_edit, QLineEdit): return
        pos = line_edit.cursorPosition()
        old_text = line_edit.text()
        raw_val = text.replace(',', '')
        if not raw_val: return
        try:
            if '.' in raw_val:
                parts = raw_val.split('.')
                whole, decimal = parts[0], ".".join(parts[1:])
                formatted = (f"{int(whole):,}" if whole else "0") + "." + decimal
            else:
                formatted = f"{int(raw_val):,}"
            if formatted != old_text:
                line_edit.setText(formatted)
                new_pos = pos + (len(formatted) - len(old_text))
                line_edit.setCursorPosition(max(0, new_pos))
        except ValueError: pass

    def update_total_preview(self):
        try:
            qty = self.inp_qty.value()
            price_str = self.inp_price.text().replace(',', '').strip()
            price = float(price_str or 0.0)
            total = qty * price
            self.lbl_total_preview.setText(f"Total Preview: ₱{total:,.2f}")
        except Exception:
            self.lbl_total_preview.setText("Total Preview: ₱0.00")

    def accept_validation(self):
        if not self.inp_name.text().strip():
            QMessageBox.warning(self, "Input Required", "Please enter an item name.")
            return
        self.accept()

    def get_data(self):
        return {
            "name": self.inp_name.text().strip(),
            "quantity": self.inp_qty.value(),
            "price": float(self.inp_price.text().replace(',', '').strip() or 0.0)
        }
