import os
import sys
from datetime import datetime

# Add workspace directory to python path
workspace_dir = r"c:\Users\USER\Documents\System-Project\Emm-Sarming-POS"
sys.path.insert(0, workspace_dir)

from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QTextDocument
from PySide6.QtPrintSupport import QPrinter
import database

def mock_generate_pdf(role, output_path):
    print(f"\n--- Testing PDF Generation for Role: {role.upper()} ---")
    conn = database.get_connection()
    cursor = conn.cursor()
    
    # Check if we have products, if not insert dummy data for testing
    cursor.execute("SELECT COUNT(*) FROM products")
    if cursor.fetchone()[0] == 0:
        print("No products in DB, adding temporary test products...")
        cursor.execute("INSERT OR REPLACE INTO products (id, name, cost, price, wholesale_price) VALUES ('11111', 'Test Apple', 10.00, 15.00, 12.00)")
        cursor.execute("INSERT OR REPLACE INTO products (id, name, cost, price, wholesale_price) VALUES ('22222', 'Test Orange', 20.00, 25.00, 22.00)")
        cursor.execute("INSERT OR REPLACE INTO product_bundles (product_id, bundle_name, quantity, cost, price, wholesale_price) VALUES ('22222', 'Orange Box', 10.0, 180.00, 230.00, 200.00)")
        conn.commit()

    # Fetch products
    cursor.execute("SELECT id, name, cost, price, wholesale_price FROM products ORDER BY name ASC")
    products = cursor.fetchall()
    
    # Fetch bundles
    cursor.execute("SELECT product_id, bundle_name, quantity, cost, price, wholesale_price FROM product_bundles ORDER BY quantity ASC")
    bundles = cursor.fetchall()
    conn.close()

    # Organize bundles
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

    is_admin = (role == "admin")
    cost_header = '<th style="width: 12%; text-align: right;">Cost</th>' if is_admin else ''
    
    # Build HTML rows
    table_rows = []
    for idx, p in enumerate(products):
        p_id, name, cost, price, wholesale_price = p
        row_class = "even" if idx % 2 == 0 else "odd"
        
        cost_val = cost if cost is not None else 0.0
        cost_td = f'<td class="currency">₱{cost_val:,.2f}</td>' if is_admin else ''
        
        table_rows.append(f"""
            <tr class="{row_class}">
                <td>{p_id}</td>
                <td><strong>{name}</strong></td>
                {cost_td}
                <td class="currency">₱{price:,.2f}</td>
                <td class="currency">₱{wholesale_price:,.2f}</td>
            </tr>
        """)
        
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
            font-size: 11px;
        }}
        .header {{
            text-align: center;
            border-bottom: 2px solid #0f766e;
            padding-bottom: 12px;
            margin-bottom: 20px;
        }}
        .header h1 {{
            margin: 0;
            color: #0f766e;
            font-size: 24px;
            font-weight: 800;
            letter-spacing: 0.5px;
        }}
        .header p {{
            margin: 4px 0 0 0;
            color: #64748b;
            font-size: 11px;
        }}
        .meta-table {{
            width: 100%;
            margin-bottom: 20px;
            font-size: 11px;
        }}
        .meta-table td {{
            padding: 3px 0;
            color: #475569;
        }}
        .meta-table td.right {{
            text-align: right;
        }}
        table.price-table {{
            width: 100%;
            border-collapse: collapse;
            margin-bottom: 30px;
        }}
        table.price-table th {{
            background-color: #0f766e;
            color: white;
            font-weight: bold;
            text-align: left;
            padding: 8px 10px;
            font-size: 11px;
            text-transform: uppercase;
            border: 1px solid #0f766e;
        }}
        table.price-table td {{
            padding: 7px 10px;
            border-bottom: 1px solid #e2e8f0;
            vertical-align: top;
            font-size: 10px;
        }}
        table.price-table tr.even {{
            background-color: #f8fafc;
        }}
        table.price-table tr.bundle-row {{
            background-color: #f1f5f9;
            font-style: italic;
        }}
        table.price-table tr.bundle-row td {{
            padding: 5px 10px 5px 25px;
            color: #0f766e;
            border-bottom: 1px solid #e2e8f0;
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
            margin-top: 30px;
            border-top: 1px solid #e2e8f0;
            padding-top: 10px;
            color: #64748b;
            font-size: 9px;
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
                <td><strong>Generated By:</strong> {role.upper()}</td>
                <td class="right"><strong>Status:</strong> Active System Prices</td>
            </tr>
        </table>
        
        <table class="price-table">
            <thead>
                <tr>
                    <th style="width: 20%;">Barcode</th>
                    <th style="width: 38%;">Product Name</th>
                    {cost_header}
                    <th style="width: 15%; text-align: right;">Retail Price</th>
                    <th style="width: 15%; text-align: right;">Wholesale Price</th>
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
    
    # Render PDF
    printer = QPrinter(QPrinter.PrinterResolution)
    printer.setOutputFormat(QPrinter.PdfFormat)
    printer.setOutputFileName(output_path)
    printer.setPageMargins(15, 15, 15, 15, QPrinter.Millimeter)
    
    doc = QTextDocument()
    doc.setHtml(html_content)
    
    if hasattr(doc, 'print_'):
        doc.print_(printer)
    else:
        doc.print(printer)
        
    print(f"Successfully generated PDF saved to: {output_path}")
    print(f"File size: {os.path.getsize(output_path)} bytes")

if __name__ == "__main__":
    # QPrinter needs a QApplication instance to run
    app = QApplication(sys.argv)
    
    os.makedirs("test_outputs", exist_ok=True)
    admin_pdf = os.path.join(workspace_dir, "test_outputs", "test_price_list_admin.pdf")
    staff_pdf = os.path.join(workspace_dir, "test_outputs", "test_price_list_staff.pdf")
    
    mock_generate_pdf("admin", admin_pdf)
    mock_generate_pdf("staff", staff_pdf)
    
    print("\nVerification successful!")
