import streamlit as st
from auth import get_current_user, require_role
from database import get_expenses_by_user
from currency_service import format_currency

@require_role(['employee', 'manager', 'admin'])
def show_employee_dashboard():
    """Employee dashboard showing expense history"""
    st.title("Employee Dashboard")
    
    user = get_current_user()
    if not user:
        st.error("User session not found")
        return
    
    # Welcome message
    st.header(f"Welcome, {user['name']}!")
    
    # Quick stats
    expenses = get_expenses_by_user(user['id'])
    
    if expenses:
        col1, col2, col3, col4 = st.columns(4)
        
        total_expenses = len(expenses)
        pending_expenses = len([e for e in expenses if e['status'] == 'pending'])
        approved_expenses = len([e for e in expenses if e['status'] == 'approved'])
        rejected_expenses = len([e for e in expenses if e['status'] == 'rejected'])
        
        with col1:
            st.metric("Total Expenses", total_expenses)
        with col2:
            st.metric("Pending", pending_expenses)
        with col3:
            st.metric("Approved", approved_expenses)
        with col4:
            st.metric("Rejected", rejected_expenses)
    
    st.divider()
    
    # Recent expenses
    st.header("Your Expenses")
    
    if expenses:
        # Filter options
        col1, col2, col3 = st.columns(3)
        
        with col1:
            status_filter = st.selectbox("Filter by Status", ["All", "Pending", "Approved", "Rejected"])
        
        with col2:
            categories = list(set([e['category'] for e in expenses]))
            category_filter = st.selectbox("Filter by Category", ["All"] + categories)
        
        with col3:
            sort_order = st.selectbox("Sort by", ["Newest First", "Oldest First", "Amount High to Low", "Amount Low to High"])
        
        # Apply filters
        filtered_expenses = expenses
        
        if status_filter != "All":
            filtered_expenses = [e for e in filtered_expenses if e['status'] == status_filter.lower()]
        
        if category_filter != "All":
            filtered_expenses = [e for e in filtered_expenses if e['category'] == category_filter]
        
        # Apply sorting
        if sort_order == "Newest First":
            filtered_expenses.sort(key=lambda x: x['created_at'], reverse=True)
        elif sort_order == "Oldest First":
            filtered_expenses.sort(key=lambda x: x['created_at'])
        elif sort_order == "Amount High to Low":
            filtered_expenses.sort(key=lambda x: x['amount'], reverse=True)
        elif sort_order == "Amount Low to High":
            filtered_expenses.sort(key=lambda x: x['amount'])
        
        # Display expenses
        if filtered_expenses:
            for expense in filtered_expenses:
                with st.expander(f"{expense['category']} - {format_currency(expense['amount'], expense['currency'])} ({expense['status'].title()})"):
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.write(f"**Description:** {expense['description']}")
                        st.write(f"**Date:** {expense['expense_date']}")
                        st.write(f"**Amount:** {format_currency(expense['amount'], expense['currency'])}")
                        if expense['converted_amount']:
                            st.write(f"**Converted Amount:** {format_currency(expense['converted_amount'], user['default_currency'])}")
                    
                    with col2:
                        st.write(f"**Category:** {expense['category']}")
                        st.write(f"**Status:** {expense['status'].title()}")
                        st.write(f"**Submitted:** {expense['created_at'].strftime('%Y-%m-%d %H:%M')}")
                        
                        # Show approval status button
                        if st.button(f"View Approval Status", key=f"status_{expense['id']}"):
                            show_expense_approval_status(expense['id'])
        else:
            st.info("No expenses match the selected filters")
    
    else:
        st.info("You haven't submitted any expenses yet. Use the 'Expense Submission' page to add your first expense!")
        
        # Quick action button
        if st.button("Submit Your First Expense"):
            st.session_state['navigate_to'] = 'expense_submission'
            st.rerun()

def show_expense_approval_status(expense_id: int):
    """Show approval status for a specific expense"""
    from approval_service import get_approval_history
    
    st.subheader(f"Approval Status - Expense #{expense_id}")
    
    history = get_approval_history(expense_id)
    
    if history:
        st.write("**Approval Workflow:**")
        
        for step in history:
            col1, col2, col3 = st.columns([1, 2, 3])
            
            with col1:
                st.write(f"Step {step['sequence']}")
            
            with col2:
                st.write(f"**{step['approver_name']}**")
            
            with col3:
                if step['status'] == 'pending':
                    st.warning("⏳ Pending")
                elif step['status'] == 'approved':
                    st.success(f"✅ Approved on {step['approved_at'].strftime('%Y-%m-%d %H:%M')}")
                    if step['comments']:
                        st.write(f"Comments: {step['comments']}")
                elif step['status'] == 'rejected':
                    st.error(f"❌ Rejected on {step['approved_at'].strftime('%Y-%m-%d %H:%M')}")
                    if step['comments']:
                        st.write(f"Comments: {step['comments']}")
    else:
        st.info("No approval workflow found for this expense.")
