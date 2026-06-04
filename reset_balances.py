import sqlite3

def reset_balances():
    conn = sqlite3.connect("emma_sarming_store.db")
    cursor = conn.cursor()
    
    print("Checking for balances to fix...")
    
    # 1. Find negative balances and set them to 0
    cursor.execute("SELECT id, balance_amount FROM debtors WHERE balance_amount < 0")
    negatives = cursor.fetchall()
    
    if negatives:
        print(f"Found {len(negatives)} negative balances. Resetting to 0...")
        cursor.execute("UPDATE debtors SET balance_amount = 0 WHERE balance_amount < 0")
        
        # Also update the corresponding sales records
        for debtor_id, _ in negatives:
            cursor.execute("SELECT sale_id FROM debtors WHERE id = ?", (debtor_id,))
            sale_id = cursor.fetchone()[0]
            cursor.execute("UPDATE sales SET balance_due = 0 WHERE id = ?", (sale_id,))
            
        print("Negative balances fixed.")
    else:
        print("No negative balances found.")
        
    # 2. Log the action
    cursor.execute("""
        INSERT INTO audit_logs (action, details, user_id, timestamp) 
        VALUES ('SYSTEM_FIX', 'Automated reset of negative balances to zero.', 'system', datetime('now', '+8 hours'))
    """)
    
    conn.commit()
    conn.close()
    print("Database update complete.")

if __name__ == "__main__":
    reset_balances()
