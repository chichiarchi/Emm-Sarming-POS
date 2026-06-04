import logging
import os
from datetime import datetime
import database

try:
    import win32print
    import win32ui
    import win32con
    WIN32_AVAILABLE = True
except ImportError:
    WIN32_AVAILABLE = False
def clean_receipt_item_name(barcode, name):
    # 1. Strip wholesale/retail tags
    for term in [" (Wholesale)", " (Retail)", " (Wholesales)", " (Retails)",
                 " (wholesale)", " (retail)", " (wholesales)", " (retails)",
                 "(Wholesale)", "(Retail)"]:
        name = name.replace(term, "")
    
    # 2. Get bundle names for this product from database to strip them
    if barcode:
        try:
            conn = database.get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT bundle_name FROM product_bundles WHERE product_id=?", (barcode,))
            bundles = cursor.fetchall()
            conn.close()
            for (b_name,) in bundles:
                name = name.replace(f" ({b_name})", "")
                name = name.replace(f"({b_name})", "")
        except Exception:
            pass
            
    return name.strip()

def get_formatted_bundle_qty(barcode, qty_val, name=""):
    if not barcode:
        return ""
    try:
        conn = database.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT bundle_name, quantity FROM product_bundles WHERE product_id=?", (barcode,))
        bundles = cursor.fetchall()
        conn.close()
        if not bundles:
            return ""
        
        # If the name already contains one of the bundle names in parentheses, 
        # then it is an explicitly scanned bundle package. We do not double-format it.
        if name:
            for b_name, b_qty in bundles:
                if f"({b_name})" in name or f" ({b_name})" in name:
                    return ""
        
        # Sort descending by quantity
        sorted_bundles = sorted([(b[0], b[1]) for b in bundles], key=lambda x: x[1], reverse=True)
        
        remaining = qty_val
        parts = []
        has_bundle_matched = False
        for b_name, b_qty in sorted_bundles:
            b_qty_float = float(b_qty)
            if b_qty_float <= 0:
                continue
            if remaining >= b_qty_float:
                b_count = int(remaining // b_qty_float)
                remaining = remaining % b_qty_float
                parts.append(f"{b_count}{b_name}")
                has_bundle_matched = True
        
        if has_bundle_matched:
            if remaining > 0:
                pcs_str = str(int(remaining)) if remaining.is_integer() else str(remaining)
                parts.append(f"{pcs_str}pcs")
            return " ".join(parts)
    except Exception as e:
        logging.error(f"Error formatting receipt bundle qty: {e}")
    return ""

def split_item_for_receipt(item):
    barcode = item.get('barcode')
    qty_val = item['qty']
    item_price = item['price']
    raw_name = item['name']
    
    clean_name = clean_receipt_item_name(barcode, raw_name)
    
    qty_int = int(qty_val) if qty_val.is_integer() else qty_val
    return [{'qty': qty_int, 'unit_name': '', 'name': clean_name, 'price': item_price, 'total': qty_val * item_price}]

def get_bundle_qty(barcode, name):
    # If the product name contains a bundle name in parentheses, return its multiplier, else 1.0.
    if not barcode or not name:
        return 1.0
    try:
        conn = database.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT bundle_name, quantity FROM product_bundles WHERE product_id=?", (barcode,))
        bundles = cursor.fetchall()
        conn.close()
        for b_name, b_qty in bundles:
            if f"({b_name})" in name or f" ({b_name})" in name:
                return float(b_qty)
    except Exception:
        pass
    return 1.0

class ReceiptPrinter:
    _instance = None

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(ReceiptPrinter, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self, printer_name=None):
        if self._initialized:
            return
        
        saved_name = database.get_setting('printer_name')
        self.printer_name = printer_name or saved_name
        self.is_connected = False
        self.last_error = ""
        self.connect()
        self._initialized = True

    def connect(self):
        """Attempts to find the thermal printer in Windows Spooler."""
        if not WIN32_AVAILABLE:
            return False

        try:
            if not self.printer_name:
                # Auto-discover
                printers = win32print.EnumPrinters(win32print.PRINTER_ENUM_LOCAL | win32print.PRINTER_ENUM_CONNECTIONS)
                for flags, description, name, comment in printers:
                    n = name.lower()
                    if any(x in n for x in ["pdf", "xps", "onenote", "fax", "webex", "snagit", "send to", "print to"]):
                        continue
                    if any(x in n for x in ["pos", "thermal", "58", "xp-", "xprinter", "receipt"]):
                        self.printer_name = name
                        break
                
                if not self.printer_name:
                    try:
                        default_printer = win32print.GetDefaultPrinter()
                        if not any(x in default_printer.lower() for x in ["pdf", "xps", "onenote", "fax"]):
                            self.printer_name = default_printer
                    except:
                        pass
                
                if not self.printer_name:
                    for flags, description, name, comment in printers:
                        n = name.lower()
                        if not any(x in n for x in ["pdf", "xps", "onenote", "fax", "webex", "snagit", "send to", "print to"]):
                            self.printer_name = name
                            break

            if self.printer_name:
                # Test connection and close handle immediately
                hprinter = win32print.OpenPrinter(self.printer_name)
                win32print.ClosePrinter(hprinter)
                self.is_connected = True
                return True
            else:
                self.is_connected = False
                self.last_error = "No valid printer found. Please go to System Settings -> Printer Settings, select your printer from the dropdown, and click 'Set as System Printer'."
                return False

        except Exception as e:
            self.last_error = str(e)
            logging.error(f"Failed to connect to Windows printer: {e}")
            self.is_connected = False
            return False

    def print_receipt(self, receipt_data):
        """
        Prints the receipt using GDI (Graphics Device Interface).
        This works on ALL Windows printers by 'drawing' the text.
        """
        if not WIN32_AVAILABLE:
            self.last_error = "Windows printing library (pywin32) is not installed in the virtual environment. Please run setup_project.bat to install it."
            return False

        if not self.is_connected or not self.printer_name:
            self.connect()
            if not self.is_connected:
                return False

        # Advanced Status Check (Non-blocking)
        try:
            hprinter = win32print.OpenPrinter(self.printer_name)
            try:
                printer_info = win32print.GetPrinter(hprinter, 2)
                status = printer_info['Status']
                paper_out = (status & win32print.PRINTER_STATUS_PAPER_OUT)
                offline = (status & win32print.PRINTER_STATUS_OFFLINE) or (status & win32print.PRINTER_STATUS_NOT_AVAILABLE) or (status & win32print.PRINTER_STATUS_ERROR)
                
                if paper_out:
                    logging.warning("Printer status reports OUT OF PAPER. Attempting to print anyway...")
                if offline:
                    logging.warning("Printer status reports OFFLINE or BUSY. Attempting to print anyway...")
            except Exception as status_err:
                logging.warning(f"Could not retrieve printer status flags: {status_err}")

            # Safe check of queue size without deleting jobs
            try:
                jobs = win32print.EnumJobs(hprinter, 0, -1, 1)
                if jobs:
                    logging.info(f"Printer spooler queue has {len(jobs)} active jobs.")
            except Exception as queue_err:
                logging.warning(f"Could not query print queue: {queue_err}")

            win32print.ClosePrinter(hprinter)
        except Exception as conn_err:
            logging.warning(f"Could not open printer to check status: {conn_err}")


        try:
            # Create a Device Context (DC) for the printer
            hdc = win32ui.CreateDC()
            hdc.CreatePrinterDC(self.printer_name)
            
            # Start the print job
            hdc.StartDoc("Emma Sarming Store Receipt")
            hdc.StartPage()
            
            # Dynamically determine the physical printable width of the printer in pixels
            try:
                printable_width = hdc.GetDeviceCaps(win32con.HORZRES)
                if printable_width <= 0 or printable_width > 1200:
                    printable_width = 384
            except Exception:
                printable_width = 384

            # Use monospaced fonts with explicit narrow widths to prevent clipping on standard 58mm POS thermal printers
            font_regular = win32ui.CreateFont({
                "name": "Consolas",
                "height": 26,
                "width": 11,
                "weight": 400,
            })
            
            font_bold = win32ui.CreateFont({
                "name": "Consolas",
                "height": 26,
                "width": 11,
                "weight": 700,
            })
            
            font_header = win32ui.CreateFont({
                "name": "Consolas",
                "height": 48,
                "width": 20,
                "weight": 900, # Bolder/larger brand
            })
            
            font_small = win32ui.CreateFont({
                "name": "Consolas",
                "height": 20,
                "width": 8,
                "weight": 400,
            })

            y = 20 # Start Y
            x_left = 4 # Shift left slightly to prevent right-edge clipping
            
            def draw_centered_text(text, y_pos, font_obj):
                hdc.SelectObject(font_obj)
                text_w, text_h = hdc.GetTextExtent(text)
                # Centered exactly between printable margin x_left and the dynamic printable width
                x_c = max(x_left, x_left + (printable_width - 8 - text_w) // 2)
                hdc.TextOut(x_c, y_pos, text)
                return text_h
                
            def draw_separator(y_pos):
                pen = win32ui.CreatePen(win32con.PS_SOLID, 2, 0) # Solid 2px line
                old_pen = hdc.SelectObject(pen)
                hdc.MoveTo(x_left, y_pos)
                hdc.LineTo(printable_width - 4, y_pos)
                hdc.SelectObject(old_pen)
                return 4 # Spacing height
                
            # Top Banner (Small, clean)
            y += draw_centered_text("CUSTOMER COPY / SALES SUMMARY", y, font_small)
            y += 8
            
            # Clean separator
            draw_separator(y)
            y += 12
            
            # Store Name (Big, Bold, Centered)
            header_txt = receipt_data.get('header', 'EMMA SARMING STORE')
            y += draw_centered_text(header_txt, y, font_header)
            y += 6
            
            # Sub-header details
            y += draw_centered_text("Narvacan, Ilocos Sur", y, font_regular)
            y += 10
            
            draw_separator(y)
            y += 12
            
            # Transaction Metadata in smaller font
            hdc.SelectObject(font_small)
            current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            sale_id = receipt_data.get('sale_id', 'N/A')
            cashier_name = receipt_data.get('cashier', 'Staff')
            
            hdc.TextOut(x_left, y, f"Receipt ID: #{sale_id}")
            y += 22
            hdc.TextOut(x_left, y, f"Date: {current_time}")
            y += 22
            hdc.TextOut(x_left, y, f"Cashier: {cashier_name}")
            y += 22
            
            y += 4
            draw_separator(y)
            y += 12
            
            # Items Header
            hdc.SelectObject(font_bold)
            # Layout budget: 34 chars
            header_line = f"{'Qty':<4} {'Name':<13}{'Unit Px':>7} {'Total':>8}"
            hdc.TextOut(x_left, y, header_line)
            y += 28
            
            draw_separator(y)
            y += 12
            
            # Items Details
            hdc.SelectObject(font_regular)
            for raw_item in receipt_data.get('items', []):
                split_rows = split_item_for_receipt(raw_item)
                for s_item in split_rows:
                    qty_val = s_item['qty']
                    qty_num_str = f"{qty_val:g}" if isinstance(qty_val, float) else f"{qty_val}"
                    qty_str = qty_num_str
                    
                    name = s_item['name']
                    unit_price = s_item['price']
                    total_price = s_item['total']
                    
                    unit_str = f"{unit_price:,.2f}"
                    total_str = f"{total_price:,.2f}"
                    
                    # Wrap name into 13-character chunks
                    name_chunks = [name[i:i+13] for i in range(0, len(name), 13)]
                    if not name_chunks:
                        name_chunks = [""]
                    
                    # First line contains Qty, Name, Unit Px, Total
                    first_line = f"{qty_str:<4} {name_chunks[0]:<13}{unit_str:>7} {total_str:>8}"
                    hdc.TextOut(x_left, y, first_line)
                    y += 28
                    
                    # Subsequent lines contain wrapped name chunks indented under the Name column (starts at index 5)
                    for chunk in name_chunks[1:]:
                        sub_line = f"     {chunk}"
                        hdc.TextOut(x_left, y, sub_line)
                        y += 28
                
            # Divider
            y += 4
            draw_separator(y)
            y += 12
            
            subtotal = receipt_data.get('total', 0.0)
            cash = receipt_data.get('amount_paid', 0.0)
            change = max(0.0, cash - subtotal)
            
            def format_currency_line(label, amount):
                amt_str = f"₱{amount:,.2f}"
                spaces = 34 - len(label) - len(amt_str)
                if spaces < 1:
                    spaces = 1
                return f"{label}{' ' * spaces}{amt_str}"
            
            hdc.SelectObject(font_regular)
            
            # Subtotal
            subtotal_line = format_currency_line("Subtotal:", subtotal)
            hdc.TextOut(x_left, y, subtotal_line)
            y += 28
            
            # Cash Received
            cash_line = format_currency_line("Cash Received:", cash)
            hdc.TextOut(x_left, y, cash_line)
            y += 28
            
            # Change Given
            change_line = format_currency_line("Change Given:", change)
            hdc.TextOut(x_left, y, change_line)
            y += 28
            
            # Total Box
            y += 4
            draw_separator(y)
            y += 12
            
            hdc.SelectObject(font_bold)
            total_line = format_currency_line("TOTAL AMOUNT:", subtotal)
            hdc.TextOut(x_left, y, total_line)
            y += 32
            
            draw_separator(y)
            y += 16
            
            # Footer (Centered)
            y += draw_centered_text(receipt_data.get('footer', 'Thank you! Come again!'), y, font_regular)
            y += 6
            y += draw_centered_text("Agyamanak unay!", y, font_regular)
            y += 16
            
            # Sub-footer non-official notice in clean small font
            y += draw_centered_text("--- CUSTOMER SALES SUMMARY ---", y, font_small)
            y += 4
            y += draw_centered_text("THIS IS NOT AN OFFICIAL RECEIPT", y, font_small)
            y += 4
            y += draw_centered_text("Thank you for shopping with us!", y, font_small)
            y += 40
            
            # Feed paper
            y += 400
            hdc.SelectObject(font_small)
            hdc.TextOut(x_left, y, ".")
            
            # Finish
            hdc.EndPage()
            hdc.EndDoc()
            hdc.DeleteDC()

            return True
            
        except Exception as e:
            self.last_error = str(e)
            logging.error(f"GDI Print Error: {e}")
            return False

    def reconnect(self):
        self._initialized = False
        self.connect()
        self._initialized = True
        return self.is_connected

if __name__ == "__main__":
    printer = ReceiptPrinter()
    print(f"Detected Printer: {printer.printer_name}")
    # Test printing helper without crashing
    printer = ReceiptPrinter() # No IDs provided -> Dummy fallback
    test_receipt = {
        'header': 'EMMA SARMING STORE',
        'subheader': 'Date: 2026-03-28\nCashier: admin',
        'items': [
            {'name': 'Apple', 'qty': 2, 'price': 3.50},
            {'name': 'Banana', 'qty': 5, 'price': 1.25}
        ],
        'total': 8.25,
        'amount_paid': 10.00,
        'balance_due': 0.00,
        'footer': 'Please come again!'
    }
    success = printer.print_receipt(test_receipt)
    if success:
        print("Test receipt processed successfully (Dummy or Physical).")
