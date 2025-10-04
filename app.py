import streamlit as st
import os
from database import init_database, get_user_by_email, create_user, create_company
from auth import authenticate_user, get_current_user
from currency_service import get_countries_and_currencies
import hashlib

# Initialize database
init_database()

# Configure page
st.set_page_config(
    page_title="Expense Management System",
    page_icon="💰",
    layout="wide"
)

def hash_password(password):
    """Hash password using SHA-256"""
    return hashlib.sha256(password.encode()).hexdigest()

def login_signup_page():
    """Handle login and signup functionality"""
    st.title("Expense Management System")
    
    tab1, tab2 = st.tabs(["Login", "Sign Up"])
    
    with tab1:
        st.header("Login")
        with st.form("login_form"):
            email = st.text_input("Email")
            password = st.text_input("Password", type="password")
            submitted = st.form_submit_button("Login")
            
            if submitted:
                if email and password:
                    user = get_user_by_email(email)
                    if user and user['password_hash'] == hash_password(password):
                        st.session_state['user_id'] = user['id']
                        st.session_state['email'] = user['email']
                        st.session_state['role'] = user['role']
                        st.session_state['company_id'] = user['company_id']
                        st.success("Login successful!")
                        st.rerun()
                    else:
                        st.error("Invalid email or password")
                else:
                    st.error("Please fill in all fields")
    
    with tab2:
        st.header("Sign Up (Admin)")
        st.info("First signup creates a company and admin user")
        
        with st.form("signup_form"):
            name = st.text_input("Full Name")
            email = st.text_input("Email")
            password = st.text_input("Password", type="password")
            confirm_password = st.text_input("Confirm Password", type="password")
            
            # Country selection for currency
            countries_data = get_countries_and_currencies()
            if countries_data:
                country_options = [f"{country['name']} ({list(country['currencies'].keys())[0] if country['currencies'] else 'No currency'})" 
                                 for country in countries_data if country.get('currencies')]
                selected_country = st.selectbox("Select Country", country_options)
            else:
                st.error("Unable to load countries data. Please check your internet connection.")
                selected_country = None
            
            company_name = st.text_input("Company Name")
            submitted = st.form_submit_button("Sign Up")
            
            if submitted:
                if all([name, email, password, confirm_password, company_name, selected_country]):
                    if password != confirm_password:
                        st.error("Passwords don't match")
                    elif get_user_by_email(email):
                        st.error("Email already exists")
                    else:
                        # Extract currency from selection
                        if selected_country and '(' in selected_country:
                            currency = selected_country.split('(')[1].split(')')[0]
                        else:
                            currency = 'USD'
                        
                        # Create company first
                        company_id = create_company(company_name, currency)
                        
                        if company_id:
                            # Create admin user
                            user_id = create_user(name, email, hash_password(password), 'admin', company_id)
                            
                            if user_id:
                                st.success("Account created successfully! Please login.")
                            else:
                                st.error("Failed to create account")
                        else:
                            st.error("Failed to create company")
                else:
                    st.error("Please fill in all fields")

def main_app():
    """Main application with role-based navigation"""
    user = get_current_user()
    
    if not user:
        st.error("Session expired. Please login again.")
        for key in ['user_id', 'email', 'role', 'company_id']:
            if key in st.session_state:
                del st.session_state[key]
        st.rerun()
        return
    
    # Sidebar navigation
    st.sidebar.title(f"Welcome, {user['name']}")
    st.sidebar.write(f"Role: {user['role'].title()}")
    st.sidebar.write(f"Company: {user['company_name']}")
    
    # Role-based navigation
    if user['role'] == 'admin':
        pages = {
            "Admin Dashboard": "pages.admin_dashboard",
            "Expense Submission": "pages.expense_submission",
            "Approval Workflow": "pages.approval_workflow"
        }
    elif user['role'] == 'manager':
        pages = {
            "Manager Dashboard": "pages.manager_dashboard",
            "Expense Submission": "pages.expense_submission",
            "Approval Workflow": "pages.approval_workflow"
        }
    else:  # employee
        pages = {
            "Employee Dashboard": "pages.employee_dashboard",
            "Expense Submission": "pages.expense_submission"
        }
    
    selected_page = st.sidebar.selectbox("Navigate", list(pages.keys()))
    
    # Logout button
    if st.sidebar.button("Logout"):
        for key in ['user_id', 'email', 'role', 'company_id']:
            if key in st.session_state:
                del st.session_state[key]
        st.rerun()
    
    # Load selected page
    if selected_page in pages:
        module_path = pages[selected_page]
        try:
            # Import and run the selected page
            if module_path == "pages.admin_dashboard":
                from pages.admin_dashboard import show_admin_dashboard
                show_admin_dashboard()
            elif module_path == "pages.manager_dashboard":
                from pages.manager_dashboard import show_manager_dashboard
                show_manager_dashboard()
            elif module_path == "pages.employee_dashboard":
                from pages.employee_dashboard import show_employee_dashboard
                show_employee_dashboard()
            elif module_path == "pages.expense_submission":
                from pages.expense_submission import show_expense_submission
                show_expense_submission()
            elif module_path == "pages.approval_workflow":
                from pages.approval_workflow import show_approval_workflow
                show_approval_workflow()
        except ImportError as e:
            st.error(f"Error loading page: {e}")

# Main application flow
if __name__ == "__main__":
    if 'user_id' not in st.session_state:
        login_signup_page()
    else:
        main_app()
