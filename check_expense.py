import sqlite3

conn = sqlite3.connect('data/expense_management.db')
cursor = conn.cursor()
cursor.execute('SELECT status FROM expenses WHERE id = 1')
status = cursor.fetchone()
conn.close()
print(f'Expense 1 status: {status[0] if status else "Not found"}')