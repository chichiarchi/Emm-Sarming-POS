import os
from datetime import datetime
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, QPushButton, 
    QTableWidget, QTableWidgetItem, QLabel, QMessageBox, QDialog, QFormLayout, QDateEdit, QHeaderView, QInputDialog,
    QDoubleSpinBox, QFileDialog
)
from PySide6.QtCore import Qt, QDate, QMarginsF
from PySide6.QtGui import QShortcut, QKeySequence, QTextDocument, QPageLayout
from PySide6.QtPrintSupport import QPrinter
import database

class InventoryModule(QWidget):
    def __init__(self, user_role="staff", username="admin"):
        super().__init__()
        self.user_role = user_role
        self.username = username
        self.current_page = 0
        self.page_size = 100
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)

        # Action Buttons
        top_layout = QHBoxLayout()

        self.btn_add_product = QPushButton("Add Product (Ctrl+I)")
        self.btn_add_product.setMinimumHeight(45)
        self.btn_add_product.setStyleSheet("font-size: 14px; font-weight: bold;")
        self.btn_add_product.clicked.connect(self.show_add_product_dialog)
        QShortcut(QKeySequence("Ctrl+I"), self, context=Qt.WidgetWithChildrenShortcut).activated.connect(self.show_add_product_dialog)
        top_layout.addWidget(self.btn_add_product)

        self.btn_edit_product = QPushButton("Edit Product (Ctrl+E)")
        self.btn_edit_product.setMinimumHeight(45)
        self.btn_edit_product.setStyleSheet("font-size: 14px; font-weight: bold;")
        self.btn_edit_product.clicked.connect(self.show_edit_dialog)
        QShortcut(QKeySequence("Ctrl+E"), self, context=Qt.WidgetWithChildrenShortcut).activated.connect(self.show_edit_dialog)
        top_layout.addWidget(self.btn_edit_product)

        self.btn_delete_product = QPushButton("Delete Product (Del)")
        self.btn_delete_product.setMinimumHeight(45)
        self.btn_delete_product.setStyleSheet("font-size: 14px; font-weight: bold; color: #ef4444;")
        self.btn_delete_product.clicked.connect(self.delete_product)
        QShortcut(QKeySequence(Qt.Key_Delete), self, context=Qt.WidgetWithChildrenShortcut).activated.connect(self.delete_product)
        top_layout.addWidget(self.btn_delete_product)

        self.btn_manage_bundles = QPushButton("Manage Bundles (Ctrl+B)")
        self.btn_manage_bundles.setMinimumHeight(45)
        self.btn_manage_bundles.setStyleSheet("font-size: 14px; font-weight: bold; color: #0f766e;")
        self.btn_manage_bundles.clicked.connect(self.show_manage_bundles_dialog)
        QShortcut(QKeySequence("Ctrl+B"), self, context=Qt.WidgetWithChildrenShortcut).activated.connect(self.show_manage_bundles_dialog)
        top_layout.addWidget(self.btn_manage_bundles)

        self.btn_generate_pdf = QPushButton("Generate Price List PDF")
        self.btn_generate_pdf.setMinimumHeight(45)
        self.btn_generate_pdf.setStyleSheet("font-size: 14px; font-weight: bold; color: #0284c7;")
        self.btn_generate_pdf.clicked.connect(self.generate_price_list_pdf)
        top_layout.addWidget(self.btn_generate_pdf)

        layout.addLayout(top_layout)

        # Search Bar
        search_layout = QHBoxLayout()
        search_layout.addWidget(QLabel("Search Product:"))
        self.search_input = QLineEdit()
        self.search_input.setMinimumHeight(45)
        self.search_input.setStyleSheet("font-size: 16px; padding: 5px;")
        self.search_input.setPlaceholderText("Enter Barcode or Product Name...")
        self.search_input.textChanged.connect(self.on_search_changed)
        self.search_input.returnPressed.connect(self.check_not_found_on_enter)
        search_layout.addWidget(self.search_input)
        layout.addLayout(search_layout)

        # Product Table
        self.inventory_table = QTableWidget(0, 6)
        self.inventory_table.setHorizontalHeaderLabels(["Barcode", "Name", "Cost", "Retail Price", "Wholesale Price", "Bundle"])
        self.inventory_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        for col in [0, 2, 3, 4, 5]:
            self.inventory_table.horizontalHeader().setSectionResizeMode(col, QHeaderView.ResizeToContents)
        self.inventory_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.inventory_table.setStyleSheet("font-size: 15px;")
        self.inventory_table.horizontalHeader().setStyleSheet("font-size: 15px; font-weight: bold;")
        self.inventory_table.verticalHeader().setDefaultSectionSize(35)
        layout.addWidget(self.inventory_table)

        # Pagination Controls
        pagination_layout = QHBoxLayout()
        self.btn_prev = QPushButton("Previous 100")
        self.btn_prev.clicked.connect(self.prev_page)
        self.btn_prev.setEnabled(False)
        
        self.page_label = QLabel("Page 1")
        self.page_label.setAlignment(Qt.AlignCenter)
        self.page_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        
        self.btn_next = QPushButton("Next 100")
        self.btn_next.clicked.connect(self.next_page)
        
        pagination_layout.addWidget(self.btn_prev)
        pagination_layout.addStretch()
        pagination_layout.addWidget(self.page_label)
        pagination_layout.addStretch()
        pagination_layout.addWidget(self.btn_next)
        layout.addLayout(pagination_layout)

        self.btn_refresh = QPushButton("Refresh (Ctrl+R)")
        self.btn_refresh.clicked.connect(self.refresh_all)
        QShortcut(QKeySequence("Ctrl+R"), self, context=Qt.WidgetWithChildrenShortcut).activated.connect(self.refresh_all)
        layout.addWidget(self.btn_refresh)

        self.load_inventory()

    def load_inventory(self):
        search_text = self.search_input.text().strip()
        conn = database.get_connection()
        cursor = conn.cursor()
        
        query = """
            SELECT id, name, cost, price, wholesale_price,
                   (CASE WHEN EXISTS (SELECT 1 FROM product_bundles WHERE product_id = products.id)
                         THEN 'With Bundle' ELSE 'Without Bundle' END)
            FROM products
        """
        
        params = ()
        if search_text:
            query += " WHERE id LIKE ? OR name LIKE ?"
            like_val = f"%{search_text}%"
            params = (like_val, like_val)
            
        query += f" LIMIT {self.page_size} OFFSET {self.current_page * self.page_size}"
            
        cursor.execute(query, params)
        rows = cursor.fetchall()
        
        cursor.execute(f"SELECT COUNT(*) FROM products {'WHERE id LIKE ? OR name LIKE ?' if search_text else ''}", params)
        total_count = cursor.fetchone()[0]
        conn.close()

        self.inventory_table.setRowCount(0)
        for i, row in enumerate(rows):
            self.inventory_table.insertRow(i)
            self.inventory_table.setItem(i, 0, QTableWidgetItem(str(row[0])))
            self.inventory_table.setItem(i, 1, QTableWidgetItem(str(row[1])))
            cost_val = row[2] if row[2] else 0.0
            self.inventory_table.setItem(i, 2, QTableWidgetItem(f"₱{cost_val:,.2f}"))
            self.inventory_table.setItem(i, 3, QTableWidgetItem(f"₱{row[3]:,.2f}"))
            self.inventory_table.setItem(i, 4, QTableWidgetItem(f"₱{row[4]:,.2f}"))
            self.inventory_table.setItem(i, 5, QTableWidgetItem(str(row[5]) if row[5] else "N/A"))

        self.page_label.setText(f"Page {self.current_page + 1} (Showing {len(rows)} of {total_count} items)")
        self.btn_prev.setEnabled(self.current_page > 0)
        self.btn_next.setEnabled((self.current_page + 1) * self.page_size < total_count)

    def on_search_changed(self):
        self.current_page = 0
        self.load_inventory()

    def next_page(self):
        self.current_page += 1
        self.load_inventory()

    def prev_page(self):
        if self.current_page > 0:
            self.current_page -= 1
            self.load_inventory()

    def refresh_all(self):
        self.current_page = 0
        self.load_inventory()

    def generate_price_list_pdf(self):
        # Open save file dialog
        default_name = os.path.join(os.path.expanduser("~"), "Documents", "Emma_Sarming_Store_Product_Price_List.pdf")
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Save Price List PDF",
            default_name,
            "PDF Files (*.pdf)"
        )
        
        if not file_path:
            return # User cancelled

        from PySide6.QtWidgets import QApplication
        QApplication.setOverrideCursor(Qt.WaitCursor)

        try:
            conn = database.get_connection()
            cursor = conn.cursor()
            
            # Fetch all products sorted alphabetically
            cursor.execute("""
                SELECT id, name, cost, price, wholesale_price 
                FROM products 
                ORDER BY name ASC
            """)
            products = cursor.fetchall()
            
            # Fetch all product bundles
            cursor.execute("""
                SELECT product_id, bundle_name, quantity, cost, price, wholesale_price 
                FROM product_bundles
                ORDER BY quantity ASC
            """)
            bundles = cursor.fetchall()
            conn.close()

            # Organize bundles by product_id
            bundles_by_product = {}
            for b in bundles:
                p_id = b[0]
                if p_id not in bundles_by_product:
                    bundles_by_product[p_id] = []
                bundles_by_product[p_id].append({
                    'name': b[1],
                    'qty': b[2],
                    'cost': b[3] if b[3] is not None else 0.0,
                    'price': b[4],
                    'wholesale_price': b[5] if b[5] is not None else 0.0
                })

            # Check role for cost visibility and dynamic column widths
            is_admin = (self.user_role == "admin")
            if is_admin:
                cost_header = '<th style="width: 12%; text-align: right;">Cost</th>'
                barcode_w = "15%"
                name_w = "43%"
                retail_w = "15%"
                wholesale_w = "15%"
            else:
                cost_header = ''
                barcode_w = "18%"
                name_w = "52%"
                retail_w = "15%"
                wholesale_w = "15%"
            
            # Build HTML rows
            table_rows = []
            for idx, p in enumerate(products):
                p_id, name, cost, price, wholesale_price = p
                row_class = "even" if idx % 2 == 0 else "odd"
                
                cost_val = cost if cost is not None else 0.0
                cost_td = f'<td class="currency">₱{cost_val:,.2f}</td>' if is_admin else ''
                
                table_rows.append(f"""
                    <tr class="{row_class}">
                        <td class="barcode-cell">{p_id}</td>
                        <td><strong>{name}</strong></td>
                        {cost_td}
                        <td class="currency">₱{price:,.2f}</td>
                        <td class="currency">₱{wholesale_price:,.2f}</td>
                    </tr>
                """)
                
                # Check for bundles
                if p_id in bundles_by_product:
                    for b in bundles_by_product[p_id]:
                        cost_b_td = f'<td class="currency" style="color: #64748b;">₱{b["cost"]:,.2f}</td>' if is_admin else ''
                        table_rows.append(f"""
                            <tr class="bundle-row">
                                <td></td>
                                <td>&nbsp;&nbsp;&nbsp;&nbsp;&bull; Bundle: {b['name']} ({b['qty']:g} pcs)</td>
                                {cost_b_td}
                                <td class="currency">₱{b['price']:,.2f}</td>
                                <td class="currency">₱{b['wholesale_price']:,.2f}</td>
                            </tr>
                        """)

            # Construct HTML page template
            current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            total_products = len(products)
            
            html_content = f"""
            <!DOCTYPE html>
            <html>
            <head>
            <meta charset="utf-8">
            <style>
                body {{
                    font-family: 'Segoe UI', 'Inter', -apple-system, sans-serif;
                    margin: 0;
                    padding: 0;
                    color: #1e293b;
                    font-size: 10px;
                }}
                .header {{
                    text-align: center;
                    border-bottom: 2px solid #0f766e;
                    padding-bottom: 6px;
                    margin-bottom: 12px;
                }}
                .header h1 {{
                    margin: 0;
                    color: #0f766e;
                    font-size: 20px;
                    font-weight: 800;
                    letter-spacing: 0.5px;
                }}
                .header p {{
                    margin: 3px 0 0 0;
                    color: #64748b;
                    font-size: 10px;
                }}
                .meta-table {{
                    width: 100%;
                    margin-bottom: 12px;
                    font-size: 9.5px;
                }}
                .meta-table td {{
                    padding: 2px 0;
                    color: #475569;
                }}
                .meta-table td.right {{
                    text-align: right;
                }}
                table.price-table {{
                    width: 100%;
                    border-collapse: collapse;
                    margin-bottom: 20px;
                }}
                table.price-table th {{
                    background-color: #0f766e;
                    color: white;
                    font-weight: bold;
                    text-align: left;
                    padding: 4px 6px;
                    font-size: 9px;
                    text-transform: uppercase;
                    border: 1px solid #0f766e;
                }}
                table.price-table td {{
                    padding: 3px 6px;
                    border-bottom: 1px solid #e2e8f0;
                    vertical-align: middle;
                    font-size: 8px;
                }}
                table.price-table tr.even {{
                    background-color: #f8fafc;
                }}
                table.price-table tr.bundle-row {{
                    background-color: #f1f5f9;
                    font-style: italic;
                }}
                table.price-table tr.bundle-row td {{
                    padding: 2px 6px 2px 18px;
                    color: #0f766e;
                    border-bottom: 1px solid #e2e8f0;
                }}
                .barcode-cell {{
                    white-space: nowrap;
                    font-family: Consolas, monospace;
                    font-size: 8px;
                }}
                .currency {{
                    text-align: right;
                    font-weight: 600;
                }}
                .text-center {{
                    text-align: center;
                }}
                .footer {{
                    text-align: center;
                    margin-top: 20px;
                    border-top: 1px solid #e2e8f0;
                    padding-top: 8px;
                    color: #64748b;
                    font-size: 8px;
                }}
            </style>
            </head>
            <body>
                <div class="header">
                    <h1>EMMA SARMING STORE PRODUCT PRICE LIST</h1>
                    <p>Narvacan, Ilocos Sur | Premium POS System Catalog</p>
                </div>
                
                <table class="meta-table">
                    <tr>
                        <td><strong>Date Generated:</strong> {current_time}</td>
                        <td class="right"><strong>Total Products:</strong> {total_products}</td>
                    </tr>
                    <tr>
                        <td><strong>Generated By:</strong> {self.username.upper()} ({self.user_role.upper()})</td>
                        <td class="right"><strong>Status:</strong> Active System Prices</td>
                    </tr>
                </table>
                
                <table class="price-table">
                    <thead>
                        <tr>
                            <th style="width: {barcode_w};">Barcode</th>
                            <th style="width: {name_w};">Product Name</th>
                            {cost_header}
                            <th style="width: {retail_w}; text-align: right;">Retail Price</th>
                            <th style="width: {wholesale_w}; text-align: right;">Wholesale Price</th>
                        </tr>
                    </thead>
                    <tbody>
                        {"".join(table_rows)}
                    </tbody>
                </table>
                
                <div class="footer">
                    <p>This is an automatically generated product price catalog from Emma Sarming Store. Prices are subject to change without prior notice.</p>
                    <p>Thank you for choosing Emma Sarming Store!</p>
                </div>
            </body>
            </html>
            """
            
            # Print to PDF using QPrinter
            printer = QPrinter(QPrinter.PrinterResolution)
            printer.setOutputFormat(QPrinter.PdfFormat)
            printer.setOutputFileName(file_path)
            printer.setPageMargins(QMarginsF(15, 15, 15, 15), QPageLayout.Unit.Millimeter)
            
            doc = QTextDocument()
            doc.setHtml(html_content)
            
            # Run the print safely using hasattr wrapper to support all PySide6 environments
            if hasattr(doc, 'print_'):
                doc.print_(printer)
            else:
                doc.print(printer)
                
            database.log_action(
                "PRICE_LIST_PDF_EXPORT", 
                f"Generated all product prices PDF saved to: {os.path.basename(file_path)}", 
                self.username
            )
            
            QMessageBox.information(
                self,
                "Success",
                f"Product price list has been successfully exported and saved to:\n{file_path}"
            )
            
        except Exception as e:
            QMessageBox.critical(
                self,
                "Export Error",
                f"An error occurred while generating the PDF:\n{e}"
            )
        finally:
            QApplication.restoreOverrideCursor()

    def show_add_product_dialog(self):
        if self.user_role != "admin":
            QMessageBox.warning(self, "Access Denied", "Only Admin can add new products.")
            return

        dialog = StockInDialog(self)
        if dialog.exec():
            data = dialog.get_data()
            conn = database.get_connection()
            try:
                cursor = conn.cursor()
                
                # Check if product exists
                cursor.execute("SELECT id FROM products WHERE id=?", (data["barcode"],))
                if cursor.fetchone() is None:
                    cursor.execute("""
                        INSERT INTO products (id, name, price, wholesale_price, cost, category)
                        VALUES (?, ?, ?, ?, ?, ?)
                    """, (data["barcode"], data["name"], data["sell_price"], data["wholesale_price"], data["cost"], data["category"]))
                    action = "PRODUCT_ADDED"
                    log_msg = f"Added product '{data['name']}' (Barcode: {data['barcode']})"
                else:
                    cursor.execute("""
                        UPDATE products SET name=?, price=?, wholesale_price=?, cost=?, category=?
                        WHERE id=?
                    """, (data["name"], data["sell_price"], data["wholesale_price"], data["cost"], data["category"], data["barcode"]))
                    action = "PRODUCT_UPDATED"
                    log_msg = f"Updated product details for '{data['name']}' (Barcode: {data['barcode']})"

                conn.commit()
                # Log action AFTER successful commit
                database.log_action(action, log_msg, self.username)
            except Exception as e:
                conn.rollback()
                QMessageBox.critical(self, "Database Error", f"Failed to save product: {e}")
            finally:
                conn.close()
            
            self.load_inventory()

    def show_edit_dialog(self):
        if self.user_role != "admin":
            QMessageBox.warning(self, "Access Denied", "Only Admin can edit products.")
            return
            
        current_row = self.inventory_table.currentRow()
        if current_row < 0:
            QMessageBox.warning(self, "Selection Required", "Please select a product from the table first.")
            return
            
        barcode = self.inventory_table.item(current_row, 0).text()
        
        conn = database.get_connection()
        cursor = conn.cursor()
        product = None
        try:
            cursor.execute("SELECT name, category, price, wholesale_price, cost FROM products WHERE id=?", (barcode,))
            product = cursor.fetchone()
        except Exception as e:
            QMessageBox.critical(self, "Database Error", f"Failed to fetch product details: {e}")
        finally:
            conn.close()
        
        if not product:
            return
            
        dialog = EditProductDialog(barcode, product, self)
        if dialog.exec():
            data = dialog.get_data()
            conn = database.get_connection()
            try:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE products SET name=?, category=?, price=?, wholesale_price=?, cost=?
                    WHERE id=?
                """, (data["name"], data["category"], data["sell_price"], data["wholesale_price"], data["cost"], barcode))
                conn.commit()
                # Log action
                database.log_action("PRODUCT_EDIT", f"Updated product '{data['name']}' (Barcode: {barcode}) details", self.username)
                QMessageBox.information(self, "Success", "Product updated successfully.")
            except Exception as e:
                conn.rollback()
                QMessageBox.critical(self, "Database Error", f"Failed to update product details: {e}")
            finally:
                conn.close()
            
            self.load_inventory()

    def delete_product(self):
        if self.user_role != "admin":
            QMessageBox.warning(self, "Access Denied", "Only Admin can delete products.")
            return
            
        current_row = self.inventory_table.currentRow()
        if current_row < 0:
            QMessageBox.warning(self, "Selection Required", "Please select a product from the table first.")
            return
            
        barcode = self.inventory_table.item(current_row, 0).text()
        product_name = self.inventory_table.item(current_row, 1).text()
        
        confirmation_text = (
            f"Are you sure you want to completely delete this product?\n\n"
            f"DETAILS:\n"
            f"• Name: {product_name}\n"
            f"• Barcode: {barcode}\n\n"
            f"This will permanently remove the product from the database."
        )

        reply = QMessageBox.question(
            self, "Confirm Deletion", 
            confirmation_text,
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
                                     
        if reply == QMessageBox.Yes:
            conn = database.get_connection()
            try:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM products WHERE id=?", (barcode,))
                conn.commit()
                # Log action
                database.log_action("PRODUCT_DELETED", f"Deleted product: {product_name} (Barcode: {barcode})", self.username)
                QMessageBox.information(self, "Success", f"Product '{product_name}' has been deleted.")
            except Exception as e:
                conn.rollback()
                QMessageBox.critical(self, "Database Error", f"Failed to delete product: {e}")
            finally:
                conn.close()
            
            self.load_inventory()

    def check_not_found_on_enter(self):
        barcode = self.search_input.text().strip()
        if not barcode:
            return
            
        conn = database.get_connection()
        cursor = conn.cursor()
        exists = None
        try:
            cursor.execute("SELECT id FROM products WHERE id=?", (barcode,))
            exists = cursor.fetchone()
        except Exception as e:
            QMessageBox.critical(self, "Database Error", f"Failed to search barcode: {e}")
        finally:
            conn.close()
        
        if not exists:
            reply = QMessageBox.question(
                self, "Product Not Found", 
                f"Barcode '{barcode}' is not in the database.\nWould you like to add it now?",
                QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes
            )
            if reply == QMessageBox.Yes:
                self.show_add_product_dialog_with_barcode(barcode)

    def show_add_product_dialog_with_barcode(self, barcode):
        if self.user_role != "admin":
            QMessageBox.warning(self, "Access Denied", "Only Admin can add products.")
            return

        dialog = StockInDialog(self)
        dialog.inp_barcode.setText(barcode)
        if dialog.exec():
            data = dialog.get_data()
            conn = database.get_connection()
            try:
                cursor = conn.cursor()
                cursor.execute("INSERT INTO products (id, name, price, wholesale_price, cost, category) VALUES (?, ?, ?, ?, ?, ?)", 
                               (data["barcode"], data["name"], data["sell_price"], data["wholesale_price"], data["cost"], data["category"]))
                conn.commit()
            except Exception as e:
                conn.rollback()
                QMessageBox.critical(self, "Database Error", f"Failed to save product: {e}")
            finally:
                conn.close()
            self.load_inventory()

    def show_manage_bundles_dialog(self):
        if self.user_role != "admin":
            QMessageBox.warning(self, "Access Denied", "Only Admin can manage product bundles.")
            return
            
        current_row = self.inventory_table.currentRow()
        if current_row < 0:
            QMessageBox.warning(self, "Selection Required", "Please select a product from the table first.")
            return
            
        barcode = self.inventory_table.item(current_row, 0).text()
        product_name = self.inventory_table.item(current_row, 1).text()
        
        dialog = ManageBundlesDialog(barcode, product_name, self)
        dialog.exec()


class StockInDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Product Details")
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        form = QFormLayout()

        self.inp_barcode = QLineEdit()
        self.inp_barcode.textChanged.connect(self.check_existing_product)
        self.inp_name = QLineEdit()
        self.inp_cost = QLineEdit()
        self.inp_cost.textEdited.connect(self.format_cash_input)
        self.inp_sell = QLineEdit()
        self.inp_sell.textEdited.connect(self.format_cash_input)
        self.inp_wholesale = QLineEdit()
        self.inp_wholesale.textEdited.connect(self.format_cash_input)

        form.addRow("Barcode / ID:", self.inp_barcode)
        form.addRow("Product Name:", self.inp_name)
        form.addRow("Cost (₱):", self.inp_cost)
        form.addRow("Retail Price (₱):", self.inp_sell)
        form.addRow("Wholesale Price (₱):", self.inp_wholesale)

        layout.addLayout(form)

        btn_save = QPushButton("Save Product")
        btn_save.setAutoDefault(False)
        btn_save.setDefault(False)
        btn_save.clicked.connect(self.accept)
        layout.addWidget(btn_save)

    def keyPressEvent(self, event):
        if event.key() in (Qt.Key_Return, Qt.Key_Enter):
            event.ignore()
            return
        super().keyPressEvent(event)

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

    def check_existing_product(self, barcode):
        barcode = barcode.strip()
        if not barcode:
            self.inp_name.clear()
            self.inp_cost.clear()
            self.inp_sell.clear()
            self.inp_wholesale.clear()
            return
            
        conn = database.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT name, category, price, wholesale_price, cost FROM products WHERE id=?", (barcode,))
        product = cursor.fetchone()
        conn.close()
        
        if product:
            self.inp_name.setText(product[0])
            self.inp_sell.setText(f"{product[2]:,.2f}" if product[2] else "0.00")
            self.inp_wholesale.setText(f"{product[3]:,.2f}" if product[3] else "0.00")
            cost_val = product[4] if product[4] is not None else 0.0
            self.inp_cost.setText(f"{cost_val:,.2f}")

    def get_data(self):
        return {
            "barcode": self.inp_barcode.text().strip(),
            "name": self.inp_name.text().strip() or "Unnamed",
            "category": "General",
            "cost": float(self.inp_cost.text().replace(',', '').strip() or 0.0),
            "sell_price": float(self.inp_sell.text().replace(',', '').strip() or 0.0),
            "wholesale_price": float(self.inp_wholesale.text().replace(',', '').strip() or 0.0)
        }


class EditProductDialog(QDialog):
    def __init__(self, barcode, product_data, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Edit Product")
        self.barcode = barcode
        self.product_data = product_data  # (name, category, price, wholesale_price, cost)
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        form = QFormLayout()

        name, category, sell_price, wholesale_price, cost = self.product_data
        cost = cost if cost is not None else 0.0

        self.inp_name = QLineEdit(name)
        self.inp_cost = QLineEdit(f"{cost:,.2f}")
        self.inp_cost.textEdited.connect(self.format_cash_input)
        self.inp_sell = QLineEdit(f"{sell_price:,.2f}")
        self.inp_sell.textEdited.connect(self.format_cash_input)
        self.inp_wholesale = QLineEdit(f"{wholesale_price:,.2f}")
        self.inp_wholesale.textEdited.connect(self.format_cash_input)

        form.addRow("Barcode / ID:", QLabel(self.barcode))
        form.addRow("Product Name:", self.inp_name)
        form.addRow("Cost (₱):", self.inp_cost)
        form.addRow("Retail Price (₱):", self.inp_sell)
        form.addRow("Wholesale Price (₱):", self.inp_wholesale)

        layout.addLayout(form)

        btn_save = QPushButton("Save Changes")
        btn_save.setAutoDefault(False)
        btn_save.setDefault(False)
        btn_save.clicked.connect(self.accept)
        layout.addWidget(btn_save)

    def keyPressEvent(self, event):
        if event.key() in (Qt.Key_Return, Qt.Key_Enter):
            event.ignore()
            return
        super().keyPressEvent(event)

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

    def get_data(self):
        return {
            "name": self.inp_name.text().strip() or "Unnamed",
            "category": "General",
            "cost": float(self.inp_cost.text().replace(',', '').strip() or 0.0),
            "sell_price": float(self.inp_sell.text().replace(',', '').strip() or 0.0),
            "wholesale_price": float(self.inp_wholesale.text().replace(',', '').strip() or 0.0),
        }


class ManageBundlesDialog(QDialog):
    def __init__(self, product_id, product_name, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Manage Bundles for: {product_name}")
        self.setMinimumSize(650, 400)
        self.product_id = product_id
        self.product_name = product_name
        self.setup_ui()
        self.load_bundles()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        
        lbl_header = QLabel(f"Configure packaging options/bundles for barcode:\n{self.product_id}")
        lbl_header.setStyleSheet("font-weight: bold; font-size: 14px; color: #1E293B; margin-bottom: 10px;")
        layout.addWidget(lbl_header)
        
        # Table of existing bundles
        self.table = QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels(["ID", "Bundle Name", "Quantity (pcs)", "Cost (₱)", "Retail Price (₱)", "Wholesale Price (₱)"])
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        for col in [0, 2, 3, 4, 5]:
            self.table.horizontalHeader().setSectionResizeMode(col, QHeaderView.ResizeToContents)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.SingleSelection)
        layout.addWidget(self.table)
        
        # Add new bundle form
        form_layout = QHBoxLayout()
        
        self.inp_name = QLineEdit()
        self.inp_name.setPlaceholderText("e.g. 15pcs Bundle")
        
        self.inp_qty = QDoubleSpinBox()
        self.inp_qty.setRange(1.0, 9999.0)
        self.inp_qty.setValue(15.0)
        self.inp_qty.setDecimals(1)

        self.inp_cost_bundle = QLineEdit()
        self.inp_cost_bundle.setPlaceholderText("Cost ₱")
        self.inp_cost_bundle.textEdited.connect(self.format_cash_input)
        
        self.inp_price = QLineEdit()
        self.inp_price.setPlaceholderText("Retail ₱")
        self.inp_price.textEdited.connect(self.format_cash_input)

        self.inp_wholesale_price = QLineEdit()
        self.inp_wholesale_price.setPlaceholderText("Wholesale ₱")
        self.inp_wholesale_price.textEdited.connect(self.format_cash_input)
        
        btn_add = QPushButton("Add Bundle")
        btn_add.setStyleSheet("background-color: #0f766e; color: white; font-weight: bold; padding: 8px 12px;")
        btn_add.clicked.connect(self.add_bundle)
        
        form_layout.addWidget(QLabel("Name:"))
        form_layout.addWidget(self.inp_name)
        form_layout.addWidget(QLabel("Qty:"))
        form_layout.addWidget(self.inp_qty)
        form_layout.addWidget(QLabel("Cost:"))
        form_layout.addWidget(self.inp_cost_bundle)
        form_layout.addWidget(QLabel("Retail:"))
        form_layout.addWidget(self.inp_price)
        form_layout.addWidget(QLabel("Wholesale:"))
        form_layout.addWidget(self.inp_wholesale_price)
        form_layout.addWidget(btn_add)
        layout.addLayout(form_layout)
        
        # Actions layout
        actions_layout = QHBoxLayout()
        btn_edit = QPushButton("Edit Selected")
        btn_edit.setStyleSheet("background-color: #0284c7; color: white; font-weight: bold; padding: 8px 12px;")
        btn_edit.clicked.connect(self.edit_bundle)
        actions_layout.addWidget(btn_edit)

        btn_delete = QPushButton("Delete Selected")
        btn_delete.setStyleSheet("background-color: #ef4444; color: white; font-weight: bold; padding: 8px 12px;")
        btn_delete.clicked.connect(self.delete_bundle)
        actions_layout.addWidget(btn_delete)
        
        actions_layout.addStretch()
        
        btn_close = QPushButton("Close")
        btn_close.clicked.connect(self.accept)
        actions_layout.addWidget(btn_close)
        
        layout.addLayout(actions_layout)

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

    def load_bundles(self):
        self.table.setRowCount(0)
        conn = database.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT id, bundle_name, quantity, cost, price, wholesale_price FROM product_bundles WHERE product_id=?", (self.product_id,))
            rows = cursor.fetchall()
            for i, row in enumerate(rows):
                self.table.insertRow(i)
                self.table.setItem(i, 0, QTableWidgetItem(str(row[0])))
                self.table.setItem(i, 1, QTableWidgetItem(str(row[1])))
                self.table.setItem(i, 2, QTableWidgetItem(f"{row[2]:g}"))
                cost_val = row[3] if row[3] is not None else 0.0
                self.table.setItem(i, 3, QTableWidgetItem(f"₱{cost_val:,.2f}"))
                self.table.setItem(i, 4, QTableWidgetItem(f"₱{row[4]:,.2f}"))
                wholesale_val = row[5] if row[5] is not None else 0.0
                self.table.setItem(i, 5, QTableWidgetItem(f"₱{wholesale_val:,.2f}"))
        finally:
            conn.close()

    def add_bundle(self):
        name = self.inp_name.text().strip()
        qty = self.inp_qty.value()
        cost_str = self.inp_cost_bundle.text().replace(',', '').strip()
        price_str = self.inp_price.text().replace(',', '').strip()
        price_wholesale_str = self.inp_wholesale_price.text().replace(',', '').strip()
        
        if not name:
            QMessageBox.warning(self, "Input Error", "Please enter a bundle name.")
            return
        try:
            cost = float(cost_str) if cost_str else 0.0
        except ValueError:
            QMessageBox.warning(self, "Input Error", "Please enter a valid cost.")
            return
        try:
            price = float(price_str)
        except ValueError:
            QMessageBox.warning(self, "Input Error", "Please enter a valid retail price.")
            return
        try:
            wholesale_price = float(price_wholesale_str) if price_wholesale_str else 0.0
        except ValueError:
            QMessageBox.warning(self, "Input Error", "Please enter a valid wholesale price.")
            return
            
        conn = database.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO product_bundles (product_id, bundle_name, quantity, cost, price, wholesale_price)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (self.product_id, name, qty, cost, price, wholesale_price))
            conn.commit()
            database.log_action("BUNDLE_ADDED", f"Added bundle '{name}' ({qty} pcs, Cost: ₱{cost:,.2f}, Retail: ₱{price:,.2f}, Wholesale: ₱{wholesale_price:,.2f}) for '{self.product_name}'", "admin")
            self.inp_name.clear()
            self.inp_cost_bundle.clear()
            self.inp_price.clear()
            self.inp_wholesale_price.clear()
            self.load_bundles()
        except Exception as e:
            conn.rollback()
            QMessageBox.critical(self, "Database Error", f"Failed to save bundle: {e}")
        finally:
            conn.close()

    def delete_bundle(self):
        row = self.table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "Selection Required", "Please select a bundle to delete.")
            return
        bundle_id = self.table.item(row, 0).text()
        bundle_name = self.table.item(row, 1).text()
        
        reply = QMessageBox.question(self, "Confirm Delete", f"Delete bundle '{bundle_name}'?", QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.Yes:
            conn = database.get_connection()
            try:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM product_bundles WHERE id=?", (bundle_id,))
                conn.commit()
                database.log_action("BUNDLE_DELETED", f"Deleted bundle '{bundle_name}' for product '{self.product_name}'", "admin")
                self.load_bundles()
            except Exception as e:
                conn.rollback()
                QMessageBox.critical(self, "Database Error", f"Failed to delete bundle: {e}")
            finally:
                conn.close()

    def edit_bundle(self):
        row = self.table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "Selection Required", "Please select a bundle to edit.")
            return
        bundle_id = self.table.item(row, 0).text()

        # Fetch bundle details from database
        conn = database.get_connection()
        cursor = conn.cursor()
        bundle = None
        try:
            cursor.execute("SELECT id, bundle_name, quantity, cost, price, wholesale_price FROM product_bundles WHERE id=?", (bundle_id,))
            bundle = cursor.fetchone()
        except Exception as e:
            QMessageBox.critical(self, "Database Error", f"Failed to fetch bundle details: {e}")
        finally:
            conn.close()

        if not bundle:
            return

        dialog = EditBundleDialog(bundle, self.product_name, self)
        if dialog.exec():
            data = dialog.get_data()
            conn = database.get_connection()
            try:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE product_bundles SET bundle_name=?, quantity=?, cost=?, price=?, wholesale_price=?
                    WHERE id=?
                """, (data["name"], data["quantity"], data["cost"], data["sell_price"], data["wholesale_price"], bundle_id))
                conn.commit()
                # Log action
                database.log_action("BUNDLE_EDITED", f"Updated bundle '{data['name']}' ({data['quantity']} pcs, Cost: ₱{data['cost']:,.2f}, Retail: ₱{data['sell_price']:,.2f}, Wholesale: ₱{data['wholesale_price']:,.2f}) for '{self.product_name}'", "admin")
                QMessageBox.information(self, "Success", "Bundle updated successfully.")
            except Exception as e:
                conn.rollback()
                QMessageBox.critical(self, "Database Error", f"Failed to update bundle details: {e}")
            finally:
                conn.close()

            self.load_bundles()


class EditBundleDialog(QDialog):
    def __init__(self, bundle_data, product_name, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Edit Bundle for: {product_name}")
        self.bundle_data = bundle_data # (bundle_id, name, qty, cost, price, wholesale_price)
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        form = QFormLayout()

        bundle_id, name, qty, cost, price, wholesale_price = self.bundle_data

        self.inp_name = QLineEdit(name)
        
        self.inp_qty = QDoubleSpinBox()
        self.inp_qty.setRange(1.0, 9999.0)
        self.inp_qty.setValue(float(qty))
        self.inp_qty.setDecimals(1)

        self.inp_cost = QLineEdit(f"{cost:,.2f}" if cost is not None else "0.00")
        self.inp_cost.textEdited.connect(self.format_cash_input)

        self.inp_sell = QLineEdit(f"{price:,.2f}" if price is not None else "0.00")
        self.inp_sell.textEdited.connect(self.format_cash_input)

        self.inp_wholesale = QLineEdit(f"{wholesale_price:,.2f}" if wholesale_price is not None else "0.00")
        self.inp_wholesale.textEdited.connect(self.format_cash_input)

        form.addRow("Bundle Name:", self.inp_name)
        form.addRow("Quantity (pcs):", self.inp_qty)
        form.addRow("Cost (₱):", self.inp_cost)
        form.addRow("Retail Price (₱):", self.inp_sell)
        form.addRow("Wholesale Price (₱):", self.inp_wholesale)

        layout.addLayout(form)

        btn_save = QPushButton("Save Changes")
        btn_save.setAutoDefault(False)
        btn_save.setDefault(False)
        btn_save.clicked.connect(self.accept)
        layout.addWidget(btn_save)

    def keyPressEvent(self, event):
        if event.key() in (Qt.Key_Return, Qt.Key_Enter):
            event.ignore()
            return
        super().keyPressEvent(event)

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

    def get_data(self):
        return {
            "name": self.inp_name.text().strip() or "Unnamed",
            "quantity": self.inp_qty.value(),
            "cost": float(self.inp_cost.text().replace(',', '').strip() or 0.0),
            "sell_price": float(self.inp_sell.text().replace(',', '').strip() or 0.0),
            "wholesale_price": float(self.inp_wholesale.text().replace(',', '').strip() or 0.0)
        }
