import sqlite3
import os
from typing import Optional, Dict, List
import streamlit as st

def get_connection():
    """Get database connection using SQLite"""
    try:
        # Create data directory if it doesn't exist
        os.makedirs("data", exist_ok=True)
        conn = sqlite3.connect("data/expense_management.db")
        conn.row_factory = sqlite3.Row  # Enable column access by name
        return conn
    except Exception as e:
        st.error(f"Database connection failed: {e}")
        return None

def init_database():
    """Initialize database tables"""
    conn = get_connection()
    if not conn:
        return
    
    cursor = conn.cursor()
    
    try:
        # Companies table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS companies (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                default_currency TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Users table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                role TEXT NOT NULL CHECK (role IN ('admin', 'manager', 'employee')),
                company_id INTEGER,
                manager_id INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (company_id) REFERENCES companies (id),
                FOREIGN KEY (manager_id) REFERENCES users (id)
            )
        """)
        
        # Expenses table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS expenses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                employee_id INTEGER,
                company_id INTEGER,
                amount REAL NOT NULL,
                currency TEXT NOT NULL,
                converted_amount REAL,
                category TEXT NOT NULL,
                description TEXT,
                expense_date DATE NOT NULL,
                receipt_path TEXT,
                status TEXT DEFAULT 'pending' CHECK (status IN ('pending', 'approved', 'rejected')),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (employee_id) REFERENCES users (id),
                FOREIGN KEY (company_id) REFERENCES companies (id)
            )
        """)
        
        # Approval workflows table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS approval_workflows (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                company_id INTEGER,
                name TEXT NOT NULL,
                sequence_order INTEGER NOT NULL,
                approver_id INTEGER,
                is_manager_approver BOOLEAN DEFAULT FALSE,
                percentage_rule INTEGER,
                specific_approver_rule BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (company_id) REFERENCES companies (id),
                FOREIGN KEY (approver_id) REFERENCES users (id)
            )
        """)
        
        # Expense approvals table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS expense_approvals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                expense_id INTEGER,
                approver_id INTEGER,
                sequence_order INTEGER NOT NULL,
                status TEXT DEFAULT 'pending' CHECK (status IN ('pending', 'approved', 'rejected')),
                comments TEXT,
                approved_at TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (expense_id) REFERENCES expenses (id),
                FOREIGN KEY (approver_id) REFERENCES users (id)
            )
        """)
        
        conn.commit()
        
    except Exception as e:
        conn.rollback()
        st.error(f"Database initialization failed: {e}")
    finally:
        cursor.close()
        conn.close()

def create_company(name: str, currency: str) -> Optional[int]:
    """Create a new company"""
    conn = get_connection()
    if not conn:
        return None
        
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT INTO companies (name, default_currency) VALUES (?, ?)",
            (name, currency)
        )
        company_id = cursor.lastrowid
        conn.commit()
        return company_id
    except Exception as e:
        conn.rollback()
        st.error(f"Failed to create company: {e}")
        return None
    finally:
        cursor.close()
        conn.close()

def create_user(name: str, email: str, password_hash: str, role: str, company_id: int, manager_id: Optional[int] = None) -> Optional[int]:
    """Create a new user"""
    conn = get_connection()
    if not conn:
        return None
        
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT INTO users (name, email, password_hash, role, company_id, manager_id) VALUES (?, ?, ?, ?, ?, ?)",
            (name, email, password_hash, role, company_id, manager_id)
        )
        user_id = cursor.lastrowid
        conn.commit()
        return user_id
    except Exception as e:
        conn.rollback()
        st.error(f"Failed to create user: {e}")
        return None
    finally:
        cursor.close()
        conn.close()

def get_user_by_email(email: str) -> Optional[Dict]:
    """Get user by email"""
    conn = get_connection()
    if not conn:
        return None
        
    cursor = conn.cursor()
    try:
        cursor.execute("""
            SELECT u.id, u.name, u.email, u.password_hash, u.role, u.company_id, u.manager_id, c.name as company_name, c.default_currency
            FROM users u
            JOIN companies c ON u.company_id = c.id
            WHERE u.email = ?
        """, (email,))
        
        result = cursor.fetchone()
        if result:
            return {
                'id': result[0],
                'name': result[1],
                'email': result[2],
                'password_hash': result[3],
                'role': result[4],
                'company_id': result[5],
                'manager_id': result[6],
                'company_name': result[7],
                'default_currency': result[8]
            }
        return None
    except Exception as e:
        st.error(f"Failed to get user: {e}")
        return None
    finally:
        cursor.close()
        conn.close()

def get_user_by_id(user_id: int) -> Optional[Dict]:
    """Get user by ID"""
    conn = get_connection()
    if not conn:
        return None
        
    cursor = conn.cursor()
    try:
        cursor.execute("""
            SELECT u.id, u.name, u.email, u.role, u.company_id, u.manager_id, c.name as company_name, c.default_currency
            FROM users u
            JOIN companies c ON u.company_id = c.id
            WHERE u.id = ?
        """, (user_id,))
        
        result = cursor.fetchone()
        if result:
            return {
                'id': result[0],
                'name': result[1],
                'email': result[2],
                'role': result[3],
                'company_id': result[4],
                'manager_id': result[5],
                'company_name': result[6],
                'default_currency': result[7]
            }
        return None
    except Exception as e:
        st.error(f"Failed to get user: {e}")
        return None
    finally:
        cursor.close()
        conn.close()

def get_company_users(company_id: int) -> List[Dict]:
    """Get all users in a company"""
    conn = get_connection()
    if not conn:
        return []
        
    cursor = conn.cursor()
    try:
        cursor.execute("""
            SELECT u.id, u.name, u.email, u.role, u.manager_id, m.name as manager_name
            FROM users u
            LEFT JOIN users m ON u.manager_id = m.id
            WHERE u.company_id = ?
            ORDER BY u.role, u.name
        """, (company_id,))
        
        results = cursor.fetchall()
        users = []
        for result in results:
            users.append({
                'id': result[0],
                'name': result[1],
                'email': result[2],
                'role': result[3],
                'manager_id': result[4],
                'manager_name': result[5]
            })
        return users
    except Exception as e:
        st.error(f"Failed to get company users: {e}")
        return []
    finally:
        cursor.close()
        conn.close()

def create_expense(employee_id: int, company_id: int, amount: float, currency: str, 
                 converted_amount: float, category: str, description: str, 
                 expense_date: str, receipt_path: Optional[str] = None) -> Optional[int]:
    """Create a new expense"""
    conn = get_connection()
    if not conn:
        return None
        
    cursor = conn.cursor()
    try:
        cursor.execute("""
            INSERT INTO expenses (employee_id, company_id, amount, currency, converted_amount, 
                                category, description, expense_date, receipt_path)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (employee_id, company_id, amount, currency, converted_amount, 
              category, description, expense_date, receipt_path))
        
        expense_id = cursor.lastrowid
        conn.commit()
        return expense_id
    except Exception as e:
        conn.rollback()
        st.error(f"Failed to create expense: {e}")
        return None
    finally:
        cursor.close()
        conn.close()

def get_expenses_by_user(user_id: int) -> List[Dict]:
    """Get expenses by user ID"""
    conn = get_connection()
    if not conn:
        return []
        
    cursor = conn.cursor()
    try:
        cursor.execute("""
            SELECT id, amount, currency, converted_amount, category, description, 
                   expense_date, status, created_at
            FROM expenses
            WHERE employee_id = ?
            ORDER BY created_at DESC
        """, (user_id,))
        
        results = cursor.fetchall()
        expenses = []
        for result in results:
            expenses.append({
                'id': result[0],
                'amount': result[1],
                'currency': result[2],
                'converted_amount': result[3],
                'category': result[4],
                'description': result[5],
                'expense_date': result[6],
                'status': result[7],
                'created_at': result[8]
            })
        return expenses
    except Exception as e:
        st.error(f"Failed to get expenses: {e}")
        return []
    finally:
        cursor.close()
        conn.close()

def get_pending_approvals(approver_id: int) -> List[Dict]:
    """Get pending approvals for a manager/admin"""
    conn = get_connection()
    if not conn:
        return []
        
    cursor = conn.cursor()
    try:
        cursor.execute("""
            SELECT e.id, e.amount, e.converted_amount, e.currency, e.category, 
                   e.description, e.expense_date, u.name as employee_name,
                   ea.sequence_order, ea.id as approval_id
            FROM expenses e
            JOIN users u ON e.employee_id = u.id
            JOIN expense_approvals ea ON e.id = ea.expense_id
            WHERE ea.approver_id = ? AND ea.status = 'pending'
            ORDER BY e.created_at DESC
        """, (approver_id,))
        
        results = cursor.fetchall()
        approvals = []
        for result in results:
            approvals.append({
                'expense_id': result[0],
                'amount': result[1],
                'converted_amount': result[2],
                'currency': result[3],
                'category': result[4],
                'description': result[5],
                'expense_date': result[6],
                'employee_name': result[7],
                'sequence_order': result[8],
                'approval_id': result[9]
            })
        return approvals
    except Exception as e:
        st.error(f"Failed to get pending approvals: {e}")
        return []
    finally:
        cursor.close()
        conn.close()

def update_approval(approval_id: int, status: str, comments: str) -> bool:
    """Update approval status"""
    conn = get_connection()
    if not conn:
        return False
        
    cursor = conn.cursor()
    try:
        cursor.execute("""
            UPDATE expense_approvals 
            SET status = ?, comments = ?, approved_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (status, comments, approval_id))
        
        conn.commit()
        return True
    except Exception as e:
        conn.rollback()
        st.error(f"Failed to update approval: {e}")
        return False
    finally:
        cursor.close()
        conn.close()

def update_user_role(user_id: int, new_role: str) -> bool:
    """Update user role"""
    conn = get_connection()
    if not conn:
        return False
        
    cursor = conn.cursor()
    try:
        cursor.execute("""
            UPDATE users SET role = ? WHERE id = ?
        """, (new_role, user_id))
        
        conn.commit()
        return True
    except Exception as e:
        conn.rollback()
        st.error(f"Failed to update user role: {e}")
        return False
    finally:
        cursor.close()
        conn.close()

def update_user_manager(user_id: int, manager_id: Optional[int]) -> bool:
    """Update user manager"""
    conn = get_connection()
    if not conn:
        return False
        
    cursor = conn.cursor()
    try:
        cursor.execute("""
            UPDATE users SET manager_id = ? WHERE id = ?
        """, (manager_id, user_id))
        
        conn.commit()
        return True
    except Exception as e:
        conn.rollback()
        st.error(f"Failed to update user manager: {e}")
        return False
    finally:
        cursor.close()
        conn.close()
