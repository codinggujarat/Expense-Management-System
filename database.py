import psycopg2
import os
from typing import Optional, Dict, List
import streamlit as st

def get_connection():
    """Get database connection using environment variables"""
    try:
        conn = psycopg2.connect(
            host=os.getenv("PGHOST"),
            database=os.getenv("PGDATABASE"),
            user=os.getenv("PGUSER"),
            password=os.getenv("PGPASSWORD"),
            port=os.getenv("PGPORT", 5432)
        )
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
                id SERIAL PRIMARY KEY,
                name VARCHAR(255) NOT NULL,
                default_currency VARCHAR(10) NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Users table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                name VARCHAR(255) NOT NULL,
                email VARCHAR(255) UNIQUE NOT NULL,
                password_hash VARCHAR(255) NOT NULL,
                role VARCHAR(50) NOT NULL CHECK (role IN ('admin', 'manager', 'employee')),
                company_id INTEGER REFERENCES companies(id),
                manager_id INTEGER REFERENCES users(id),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Expenses table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS expenses (
                id SERIAL PRIMARY KEY,
                employee_id INTEGER REFERENCES users(id),
                company_id INTEGER REFERENCES companies(id),
                amount DECIMAL(10,2) NOT NULL,
                currency VARCHAR(10) NOT NULL,
                converted_amount DECIMAL(10,2),
                category VARCHAR(100) NOT NULL,
                description TEXT,
                expense_date DATE NOT NULL,
                receipt_path VARCHAR(500),
                status VARCHAR(50) DEFAULT 'pending' CHECK (status IN ('pending', 'approved', 'rejected')),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Approval workflows table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS approval_workflows (
                id SERIAL PRIMARY KEY,
                company_id INTEGER REFERENCES companies(id),
                name VARCHAR(255) NOT NULL,
                sequence_order INTEGER NOT NULL,
                approver_id INTEGER REFERENCES users(id),
                is_manager_approver BOOLEAN DEFAULT FALSE,
                percentage_rule INTEGER,
                specific_approver_rule BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Expense approvals table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS expense_approvals (
                id SERIAL PRIMARY KEY,
                expense_id INTEGER REFERENCES expenses(id),
                approver_id INTEGER REFERENCES users(id),
                sequence_order INTEGER NOT NULL,
                status VARCHAR(50) DEFAULT 'pending' CHECK (status IN ('pending', 'approved', 'rejected')),
                comments TEXT,
                approved_at TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
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
            "INSERT INTO companies (name, default_currency) VALUES (%s, %s) RETURNING id",
            (name, currency)
        )
        company_id = cursor.fetchone()[0]
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
            "INSERT INTO users (name, email, password_hash, role, company_id, manager_id) VALUES (%s, %s, %s, %s, %s, %s) RETURNING id",
            (name, email, password_hash, role, company_id, manager_id)
        )
        user_id = cursor.fetchone()[0]
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
            WHERE u.email = %s
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
            WHERE u.id = %s
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
            WHERE u.company_id = %s
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
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s) RETURNING id
        """, (employee_id, company_id, amount, currency, converted_amount, 
              category, description, expense_date, receipt_path))
        
        expense_id = cursor.fetchone()[0]
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
            WHERE employee_id = %s
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
            WHERE ea.approver_id = %s AND ea.status = 'pending'
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
            SET status = %s, comments = %s, approved_at = CURRENT_TIMESTAMP
            WHERE id = %s
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
