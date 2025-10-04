import streamlit as st
from auth import get_current_user, require_role
from database import get_pending_approvals, get_connection
from approval_service import process_approval
from currency_service import format_currency

@require_role(['manager', 'admin'])
def show_manager_dashboard():
    """Manager dashboard for approving expenses"""
    st.title("Manager Dashboard")
    
    user = get_current_user()
    
    # Get pending approvals
    pending_approvals = get_pending_approvals(user['id'])
    
    # Dashboard stats
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("Pending Approvals", len(pending_approvals))
    
    with col2:
        # Get team size
        team_size = get_team_size(user['id'])
        st.metric("Team Size", team_size)
    
    with col3:
        # Get approved this month
        approved_this_month = get_approved_count_this_month(user['id'])
        st.metric("Approved This Month", approved_this_month)
    
    st.divider()
    
    # Pending approvals section
    st.header("Pending Approvals")
    
    if pending_approvals:
        for approval in pending_approvals:
            show_approval_item(approval, user['default_currency'])
    else:
        st.info("No pending approvals at this time.")
    
    st.divider()
    
    # Team expenses overview
    show_team_expenses_overview(user['id'])

def show_approval_item(approval, default_currency):
    """Display an individual approval item"""
    with st.expander(f"{approval['employee_name']} - {approval['category']} - {format_currency(approval['amount'], approval['currency'])}"):
        col1, col2 = st.columns([2, 1])
        
        with col1:
            st.write(f"**Employee:** {approval['employee_name']}")
            st.write(f"**Category:** {approval['category']}")
            st.write(f"**Description:** {approval['description']}")
            st.write(f"**Date:** {approval['expense_date']}")
            st.write(f"**Original Amount:** {format_currency(approval['amount'], approval['currency'])}")
            if approval['converted_amount']:
                st.write(f"**Amount in {default_currency}:** {format_currency(approval['converted_amount'], default_currency)}")
        
        with col2:
            st.write(f"**Approval Step:** {approval['sequence_order']}")
            
            # Approval form
            with st.form(f"approval_form_{approval['approval_id']}"):
                action = st.radio("Action", ["Approve", "Reject"], key=f"action_{approval['approval_id']}")
                comments = st.text_area("Comments", key=f"comments_{approval['approval_id']}")
                
                submitted = st.form_submit_button("Submit Decision")
                
                if submitted:
                    action_value = "approved" if action == "Approve" else "rejected"
                    
                    success = process_approval(
                        expense_id=approval['expense_id'],
                        approver_id=st.session_state['user_id'],
                        action=action_value,
                        comments=comments
                    )
                    
                    if success:
                        st.success(f"Expense {action_value} successfully!")
                        st.rerun()
                    else:
                        st.error(f"Failed to {action.lower()} expense")

def get_team_size(manager_id: int) -> int:
    """Get the size of manager's team"""
    conn = get_connection()
    if not conn:
        return 0
    
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            SELECT COUNT(*) FROM users 
            WHERE manager_id = %s
        """, (manager_id,))
        
        result = cursor.fetchone()
        return result[0] if result else 0
        
    except Exception as e:
        st.error(f"Failed to get team size: {e}")
        return 0
    finally:
        cursor.close()
        conn.close()

def get_approved_count_this_month(approver_id: int) -> int:
    """Get count of expenses approved this month"""
    conn = get_connection()
    if not conn:
        return 0
    
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            SELECT COUNT(*) FROM expense_approvals 
            WHERE approver_id = %s 
            AND status = 'approved' 
            AND DATE_TRUNC('month', approved_at) = DATE_TRUNC('month', CURRENT_DATE)
        """, (approver_id,))
        
        result = cursor.fetchone()
        return result[0] if result else 0
        
    except Exception as e:
        st.error(f"Failed to get approved count: {e}")
        return 0
    finally:
        cursor.close()
        conn.close()

def show_team_expenses_overview(manager_id: int):
    """Show overview of team expenses"""
    st.header("Team Expenses Overview")
    
    conn = get_connection()
    if not conn:
        st.error("Database connection failed")
        return
    
    cursor = conn.cursor()
    
    try:
        # Get team expenses summary
        cursor.execute("""
            SELECT 
                u.name as employee_name,
                COUNT(e.id) as total_expenses,
                COUNT(CASE WHEN e.status = 'pending' THEN 1 END) as pending_expenses,
                COUNT(CASE WHEN e.status = 'approved' THEN 1 END) as approved_expenses,
                COUNT(CASE WHEN e.status = 'rejected' THEN 1 END) as rejected_expenses,
                SUM(CASE WHEN e.status = 'approved' THEN e.converted_amount END) as total_approved_amount
            FROM users u
            LEFT JOIN expenses e ON u.id = e.employee_id
            WHERE u.manager_id = %s
            GROUP BY u.id, u.name
            ORDER BY u.name
        """, (manager_id,))
        
        team_expenses = cursor.fetchall()
        
        if team_expenses:
            for employee_data in team_expenses:
                employee_name = employee_data[0]
                total = employee_data[1]
                pending = employee_data[2]
                approved = employee_data[3]
                rejected = employee_data[4]
                total_amount = employee_data[5] or 0
                
                with st.expander(f"{employee_name} - {total} expenses"):
                    col1, col2, col3, col4 = st.columns(4)
                    
                    with col1:
                        st.metric("Total", total)
                    with col2:
                        st.metric("Pending", pending)
                    with col3:
                        st.metric("Approved", approved)
                    with col4:
                        st.metric("Rejected", rejected)
                    
                    if total_amount > 0:
                        user = get_current_user()
                        st.write(f"**Total Approved Amount:** {format_currency(total_amount, user['default_currency'])}")
        else:
            st.info("No team members found or no expenses submitted yet.")
        
    except Exception as e:
        st.error(f"Failed to load team expenses overview: {e}")
    finally:
        cursor.close()
        conn.close()
