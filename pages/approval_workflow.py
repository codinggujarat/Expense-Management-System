import streamlit as st
from auth import get_current_user, require_role
from database import get_connection
from approval_service import get_approval_history, process_approval
from currency_service import format_currency

@require_role(['manager', 'admin'])
def show_approval_workflow():
    """Approval workflow management and history"""
    st.title("Approval Workflow")
    
    user = get_current_user()
    
    tab1, tab2 = st.tabs(["Pending Approvals", "Approval History"])
    
    with tab1:
        show_pending_approvals_detailed(user)
    
    with tab2:
        show_approval_history_view(user)

def show_pending_approvals_detailed(user):
    """Detailed view of pending approvals with batch actions"""
    st.header("Pending Approvals")
    
    # Get pending approvals with more details
    conn = get_connection()
    if not conn:
        st.error("Database connection failed")
        return
    
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            SELECT 
                e.id as expense_id,
                e.amount,
                e.currency,
                e.converted_amount,
                e.category,
                e.description,
                e.expense_date,
                e.receipt_path,
                u.name as employee_name,
                u.email as employee_email,
                ea.id as approval_id,
                ea.sequence_order,
                ea.created_at as submitted_at
            FROM expenses e
            JOIN users u ON e.employee_id = u.id
            JOIN expense_approvals ea ON e.id = ea.expense_id
            WHERE ea.approver_id = ? AND ea.status = 'pending'
            ORDER BY ea.created_at ASC
        """, (user['id'],))
        
        pending_approvals = cursor.fetchall()
        
        if pending_approvals:
            # Summary stats
            col1, col2, col3 = st.columns(3)
            
            total_pending = len(pending_approvals)
            total_amount = sum([approval[3] or approval[1] for approval in pending_approvals])
            
            with col1:
                st.metric("Total Pending", total_pending)
            with col2:
                st.metric("Total Amount", f"{user['default_currency']} {total_amount:,.2f}")
            with col3:
                avg_amount = total_amount / total_pending if total_pending > 0 else 0
                st.metric("Average Amount", f"{user['default_currency']} {avg_amount:,.2f}")
            
            st.divider()
            
            # Filters
            col1, col2 = st.columns(2)
            with col1:
                employee_filter = st.selectbox(
                    "Filter by Employee", 
                    ["All"] + list(set([approval[8] for approval in pending_approvals]))
                )
            with col2:
                category_filter = st.selectbox(
                    "Filter by Category",
                    ["All"] + list(set([approval[4] for approval in pending_approvals]))
                )
            
            # Apply filters
            filtered_approvals = pending_approvals
            if employee_filter != "All":
                filtered_approvals = [a for a in filtered_approvals if a[8] == employee_filter]
            if category_filter != "All":
                filtered_approvals = [a for a in filtered_approvals if a[4] == category_filter]
            
            # Display approvals
            for approval in filtered_approvals:
                show_detailed_approval_item(approval, user['default_currency'])
        else:
            st.info("No pending approvals at this time.")
    
    except Exception as e:
        st.error(f"Failed to load pending approvals: {e}")
    finally:
        cursor.close()
        conn.close()

def show_detailed_approval_item(approval, default_currency):
    """Show detailed approval item with receipt preview"""
    expense_id = approval[0]
    amount = approval[1]
    currency = approval[2]
    converted_amount = approval[3]
    category = approval[4]
    description = approval[5]
    expense_date = approval[6]
    receipt_path = approval[7]
    employee_name = approval[8]
    employee_email = approval[9]
    approval_id = approval[10]
    sequence_order = approval[11]
    submitted_at = approval[12]
    
    # Handle submitted_at field which might be a string or datetime
    if isinstance(submitted_at, str):
        # If it's already a string, use it as is
        submitted_date = submitted_at.split(' ')[0]  # Get just the date part
        submitted_datetime = submitted_at  # Use the full string
    else:
        # If it's a datetime object, format it
        submitted_datetime = submitted_at.strftime('%Y-%m-%d %H:%M')
    
    with st.expander(f"#{expense_id} - {employee_name} - {category} - {format_currency(converted_amount or amount, currency)}"):
        col1, col2 = st.columns([2, 1])
        
        with col1:
            st.write(f"**Employee:** {employee_name} ({employee_email})")
            st.write(f"**Category:** {category}")
            st.write(f"**Description:** {description}")
            st.write(f"**Expense Date:** {expense_date}")
            st.write(f"**Submitted:** {submitted_datetime}")
            st.write(f"**Original Amount:** {format_currency(amount, currency)}")
            if converted_amount and currency != default_currency:
                st.write(f"**Amount in {default_currency}:** {format_currency(converted_amount, default_currency)}")
            st.write(f"**Approval Step:** {sequence_order}")
            
            # Show receipt if available
            if receipt_path:
                try:
                    st.image(receipt_path, caption="Receipt", width=300)
                except:
                    st.write("**Receipt:** Available (unable to display)")
            else:
                st.write("**Receipt:** Not provided")
        
        with col2:
            # Quick approval buttons
            col_approve, col_reject = st.columns(2)
            
            with col_approve:
                if st.button("✅ Quick Approve", key=f"quick_approve_{approval_id}"):
                    if process_approval(expense_id, st.session_state['user_id'], 'approved', 'Quick approval'):
                        st.success("Approved!")
                        st.rerun()
            
            with col_reject:
                if st.button("❌ Quick Reject", key=f"quick_reject_{approval_id}"):
                    if process_approval(expense_id, st.session_state['user_id'], 'rejected', 'Quick rejection'):
                        st.success("Rejected!")
                        st.rerun()
            
            st.divider()
            
            # Detailed approval form
            with st.form(f"detailed_approval_{approval_id}"):
                st.write("**Detailed Review:**")
                action = st.radio("Decision", ["Approve", "Reject"], key=f"action_detailed_{approval_id}")
                comments = st.text_area("Comments", key=f"comments_detailed_{approval_id}")
                
                submitted = st.form_submit_button("Submit Review")
                
                if submitted:
                    action_value = "approved" if action == "Approve" else "rejected"
                    
                    if process_approval(expense_id, st.session_state['user_id'], action_value, comments):
                        st.success(f"Expense {action_value}!")
                        st.rerun()
                    else:
                        st.error(f"Failed to {action.lower()} expense")
            
            # Show approval history for this expense
            if st.button("View History", key=f"history_{expense_id}"):
                show_expense_approval_detail(expense_id)

def show_approval_history_view(user):
    """Show approval history and statistics"""
    st.header("Approval History")
    
    conn = get_connection()
    if not conn:
        st.error("Database connection failed")
        return
    
    cursor = conn.cursor()
    
    try:
        # Get approval history
        cursor.execute("""
            SELECT 
                e.id as expense_id,
                u.name as employee_name,
                e.category,
                e.converted_amount,
                ea.status,
                ea.comments,
                ea.approved_at
            FROM expense_approvals ea
            JOIN expenses e ON ea.expense_id = e.id
            JOIN users u ON e.employee_id = u.id
            WHERE ea.approver_id = ? AND ea.status IN ('approved', 'rejected')
            ORDER BY ea.approved_at DESC
            LIMIT 50
        """, (user['id'],))
        
        history = cursor.fetchall()
        
        if history:
            # Statistics
            approved_count = len([h for h in history if h[4] == 'approved'])
            rejected_count = len([h for h in history if h[4] == 'rejected'])
            total_approved_amount = sum([h[3] for h in history if h[4] == 'approved' and h[3]])
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric("Total Approved", approved_count)
            with col2:
                st.metric("Total Rejected", rejected_count)
            with col3:
                st.metric("Total Approved Amount", f"{user['default_currency']} {total_approved_amount:,.2f}")
            
            st.divider()
            
            # History table
            st.subheader("Recent Approvals")
            
            for record in history:
                expense_id, employee_name, category, amount, status, comments, approved_at = record
                
                # Handle approved_at field which might be a string or datetime
                if isinstance(approved_at, str):
                    # If it's already a string, use it as is
                    approved_datetime = approved_at  # Use the full string
                else:
                    # If it's a datetime object, format it
                    approved_datetime = approved_at.strftime('%Y-%m-%d %H:%M')
                
                col1, col2, col3, col4 = st.columns([2, 2, 1, 2])
                
                with col1:
                    st.write(f"**#{expense_id}** - {employee_name}")
                
                with col2:
                    st.write(f"{category}")
                    if amount:
                        st.write(f"{user['default_currency']} {amount:,.2f}")
                
                with col3:
                    if status == 'approved':
                        st.success("✅ Approved")
                    else:
                        st.error("❌ Rejected")
                
                with col4:
                    st.write(approved_datetime)
                    if comments:
                        st.caption(f"💬 {comments}")
                
                st.divider()
        else:
            st.info("No approval history found.")
    
    except Exception as e:
        st.error(f"Failed to load approval history: {e}")
    finally:
        cursor.close()
        conn.close()

def show_expense_approval_detail(expense_id: int):
    """Show detailed approval workflow for a specific expense"""
    st.subheader(f"Approval Details - Expense #{expense_id}")
    
    history = get_approval_history(expense_id)
    
    if history:
        for step in history:
            col1, col2, col3 = st.columns([1, 2, 3])
            
            with col1:
                st.write(f"**Step {step['sequence']}**")
            
            with col2:
                st.write(step['approver_name'])
            
            with col3:
                if step['status'] == 'pending':
                    st.warning("⏳ Pending")
                elif step['status'] == 'approved':
                    st.success(f"✅ Approved")
                    # Handle approved_at field which might be a string or datetime
                    if isinstance(step['approved_at'], str):
                        # If it's already a string, use it as is
                        approved_datetime = step['approved_at']  # Use the full string
                    else:
                        # If it's a datetime object, format it
                        approved_datetime = step['approved_at'].strftime('%Y-%m-%d %H:%M')
                    st.caption(f"Date: {approved_datetime}")
                    if step['comments']:
                        st.caption(f"Comments: {step['comments']}")
                elif step['status'] == 'rejected':
                    st.error(f"❌ Rejected")
                    # Handle approved_at field which might be a string or datetime
                    if isinstance(step['approved_at'], str):
                        # If it's already a string, use it as is
                        approved_datetime = step['approved_at']  # Use the full string
                    else:
                        # If it's a datetime object, format it
                        approved_datetime = step['approved_at'].strftime('%Y-%m-%d %H:%M')
                    st.caption(f"Date: {approved_datetime}")
                    if step['comments']:
                        st.caption(f"Comments: {step['comments']}")
    else:
        st.info("No approval workflow found.")
