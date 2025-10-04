import sqlite3

conn = sqlite3.connect('data/expense_management.db')
cursor = conn.cursor()

print("=== Database Content ===")

# Check companies
cursor.execute('SELECT * FROM companies')
companies = cursor.fetchall()
print(f"Companies ({len(companies)}):")
for company in companies:
    print(f"  {company}")

print()

# Check users
cursor.execute('SELECT * FROM users')
users = cursor.fetchall()
print(f"Users ({len(users)}):")
for user in users:
    print(f"  {user}")

print()

# Check expenses
cursor.execute('SELECT * FROM expenses')
expenses = cursor.fetchall()
print(f"Expenses ({len(expenses)}):")
for expense in expenses:
    print(f"  {expense}")

print()

# Check approval workflows
cursor.execute('SELECT * FROM approval_workflows')
workflows = cursor.fetchall()
print(f"Approval Workflows ({len(workflows)}):")
for workflow in workflows:
    print(f"  {workflow}")

print()

# Check expense approvals
cursor.execute('SELECT * FROM expense_approvals')
approvals = cursor.fetchall()
print(f"Expense Approvals ({len(approvals)}):")
for approval in approvals:
    print(f"  {approval}")

conn.close()