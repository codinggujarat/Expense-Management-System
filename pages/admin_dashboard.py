import streamlit as st
from auth import get_current_user, require_role
from database import get_company_users, create_user, get_connection
from approval_service import create_approval_rule, get_company_approval_rules
import hashlib

@require_role(['admin'])
def show_admin_dashboard():
    """Admin dashboard with user management and approval rules"""
    st.title("Admin Dashboard")
    
    user = get_current_user()
    company_id = user['company_id']
    
    # Create tabs for different admin functions
    tab1, tab2, tab3, tab4 = st.tabs(["User Management", "Approval Rules", "Company Overview", "Expense Reports"])
    
    with tab1:
        show_user_management(company_id)
    
    with tab2:
        show_approval_rules(company_id)
    
    with tab3:
        show_company_overview(company_id)
    
    with tab4:
        show_expense_reports(company_id)

def show_user_management(company_id: int):
    """User management interface"""
    st.header("User Management")
    
    # Display existing users
    users = get_company_users(company_id)
    
    if users:
        st.subheader("Current Users")
        for user in users:
            col1, col2, col3, col4 = st.columns([3, 2, 2, 2])
            with col1:
                st.write(f"**{user['name']}**")
                st.write(user['email'])
            with col2:
                st.write(user['role'].title())
            with col3:
                st.write(user['manager_name'] if user['manager_name'] else "No Manager")
            with col4:
                if st.button(f"Edit {user['id']}", key=f"edit_{user['id']}"):
                    st.session_state[f"edit_user_{user['id']}"] = True
    
    st.divider()
    
    # Add new user form
    st.subheader("Add New User")
    with st.form("add_user_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            name = st.text_input("Full Name")
            email = st.text_input("Email")
            password = st.text_input("Password", type="password")
        
        with col2:
            role = st.selectbox("Role", ["employee", "manager"])
            
            # Manager selection (for employees and managers)
            managers = [user for user in users if user['role'] in ['admin', 'manager']]
            manager_options = ["No Manager"] + [f"{mgr['name']} ({mgr['email']})" for mgr in managers]
            selected_manager = st.selectbox("Manager", manager_options)
        
        submitted = st.form_submit_button("Add User")
        
        if submitted:
            if all([name, email, password]):
                # Get manager ID
                manager_id = None
                if selected_manager != "No Manager":
                    manager_email = selected_manager.split('(')[1].split(')')[0]
                    manager_id = next((mgr['id'] for mgr in managers if mgr['email'] == manager_email), None)
                
                # Hash password
                password_hash = hashlib.sha256(password.encode()).hexdigest()
                
                # Create user
                user_id = create_user(name, email, password_hash, role, company_id, manager_id)
                
                if user_id:
                    st.success(f"User {name} created successfully!")
                    st.rerun()
                else:
                    st.error("Failed to create user")
            else:
                st.error("Please fill in all required fields")

def show_approval_rules(company_id: int):
    """Approval rules management"""
    st.header("Approval Rules Configuration")
    
    # Display existing rules
    rules = get_company_approval_rules(company_id)
    
    if rules:
        st.subheader("Current Approval Rules")
        for rule in rules:
            with st.expander(f"Rule: {rule['name']} (Sequence: {rule['sequence_order']})"):
                col1, col2 = st.columns(2)
                with col1:
                    st.write(f"**Approver:** {rule['approver_name']}")
                    st.write(f"**Manager Approver:** {'Yes' if rule['is_manager_approver'] else 'No'}")
                with col2:
                    if rule['percentage_rule']:
                        st.write(f"**Percentage Rule:** {rule['percentage_rule']}%")
                    if rule['specific_approver_rule']:
                        st.write("**Specific Approver Rule:** Active")
    
    st.divider()
    
    # Add new approval rule
    st.subheader("Add Approval Rule")
    
    users = get_company_users(company_id)
    approvers = [user for user in users if user['role'] in ['admin', 'manager']]
    
    if not approvers:
        st.warning("No managers or admins available for approval rules")
        return
    
    with st.form("add_approval_rule"):
        col1, col2 = st.columns(2)
        
        with col1:
            rule_name = st.text_input("Rule Name")
            approver_options = [f"{user['name']} ({user['email']})" for user in approvers]
            selected_approver = st.selectbox("Approver", approver_options)
            sequence_order = st.number_input("Sequence Order", min_value=1, value=1)
        
        with col2:
            is_manager_approver = st.checkbox("Is Manager Approver")
            percentage_rule = st.number_input("Percentage Rule (%)", min_value=0, max_value=100, value=0)
            specific_approver_rule = st.checkbox("Specific Approver Rule (auto-approve)")
        
        submitted = st.form_submit_button("Add Rule")
        
        if submitted:
            if rule_name and selected_approver:
                # Get approver ID
                approver_email = selected_approver.split('(')[1].split(')')[0]
                approver_id = next((user['id'] for user in approvers if user['email'] == approver_email), None)
                
                if approver_id:
                    success = create_approval_rule(
                        company_id=company_id,
                        name=rule_name,
                        approver_id=approver_id,
                        sequence_order=sequence_order,
                        percentage_rule=percentage_rule if percentage_rule > 0 else None,
                        specific_approver_rule=specific_approver_rule,
                        is_manager_approver=is_manager_approver
                    )
                    
                    if success:
                        st.success("Approval rule created successfully!")
                        st.rerun()
                    else:
                        st.error("Failed to create approval rule")
            else:
                st.error("Please fill in all required fields")

def show_company_overview(company_id: int):
    """Company overview and statistics"""
    st.header("Company Overview")
    
    conn = get_connection()
    if not conn:
        st.error("Database connection failed")
        return
    
    cursor = conn.cursor()
    
    try:
        # Get company stats
        cursor.execute("""
            SELECT 
                COUNT(CASE WHEN role = 'employee' THEN 1 END) as employees,
                COUNT(CASE WHEN role = 'manager' THEN 1 END) as managers,
                COUNT(CASE WHEN role = 'admin' THEN 1 END) as admins
            FROM users WHERE company_id = %s
        """, (company_id,))
        
        user_stats = cursor.fetchone()
        
        cursor.execute("""
            SELECT 
                COUNT(*) as total_expenses,
                COUNT(CASE WHEN status = 'pending' THEN 1 END) as pending,
                COUNT(CASE WHEN status = 'approved' THEN 1 END) as approved,
                COUNT(CASE WHEN status = 'rejected' THEN 1 END) as rejected,
                SUM(CASE WHEN status = 'approved' THEN converted_amount END) as total_approved_amount
            FROM expenses WHERE company_id = %s
        """, (company_id,))
        
        expense_stats = cursor.fetchone()
        
        # Display stats
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("Total Employees", user_stats[0])
            st.metric("Managers", user_stats[1])
            st.metric("Admins", user_stats[2])
        
        with col2:
            st.metric("Total Expenses", expense_stats[0])
            st.metric("Pending Approval", expense_stats[1])
        
        with col3:
            st.metric("Approved Expenses", expense_stats[2])
            st.metric("Rejected Expenses", expense_stats[3])
            if expense_stats[4]:
                user = get_current_user()
                st.metric("Total Approved Amount", f"{user['default_currency']} {expense_stats[4]:,.2f}")
        
    except Exception as e:
        st.error(f"Failed to load company overview: {e}")
    finally:
        cursor.close()
        conn.close()

def show_expense_reports(company_id: int):
    """Expense reports and analytics"""
    st.header("Expense Reports")
    
    conn = get_connection()
    if not conn:
        st.error("Database connection failed")
        return
    
    cursor = conn.cursor()
    
    try:
        # Get all expenses for the company
        cursor.execute("""
            SELECT e.id, u.name as employee_name, e.amount, e.currency, e.converted_amount,
                   e.category, e.description, e.expense_date, e.status, e.created_at
            FROM expenses e
            JOIN users u ON e.employee_id = u.id
            WHERE e.company_id = %s
            ORDER BY e.created_at DESC
        """, (company_id,))
        
        expenses = cursor.fetchall()
        
        if expenses:
            st.subheader("All Expenses")
            
            # Create expense table
            expense_data = []
            for expense in expenses:
                expense_data.append({
                    'ID': expense[0],
                    'Employee': expense[1],
                    'Amount': f"{expense[3]} {expense[2]}",
                    'Converted Amount': f"{expense[4]:.2f}" if expense[4] else "N/A",
                    'Category': expense[5],
                    'Description': expense[6],
                    'Date': expense[7],
                    'Status': expense[8].title(),
                    'Created': expense[9].strftime('%Y-%m-%d')
                })
            
            st.dataframe(expense_data)
        else:
            st.info("No expenses found")
        
    except Exception as e:
        st.error(f"Failed to load expense reports: {e}")
    finally:
        cursor.close()
        conn.close()
