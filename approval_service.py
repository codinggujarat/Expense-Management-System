import streamlit as st
from database import get_connection
from typing import List, Dict, Optional

def create_approval_workflow(company_id: int, expense_id: int) -> bool:
    """Create approval workflow for an expense"""
    conn = get_connection()
    if not conn:
        return False
    
    cursor = conn.cursor()
    
    try:
        # Get the employee's manager
        cursor.execute("""
            SELECT u.manager_id, u.id as employee_id
            FROM expenses e
            JOIN users u ON e.employee_id = u.id
            WHERE e.id = %s
        """, (expense_id,))
        
        result = cursor.fetchone()
        if not result:
            return False
        
        manager_id, employee_id = result
        
        # Create approval workflow starting with manager (if exists)
        sequence = 1
        if manager_id:
            cursor.execute("""
                INSERT INTO expense_approvals (expense_id, approver_id, sequence_order, status)
                VALUES (%s, %s, %s, 'pending')
            """, (expense_id, manager_id, sequence))
            sequence += 1
        
        # Get additional approval workflows for the company
        cursor.execute("""
            SELECT approver_id, sequence_order
            FROM approval_workflows
            WHERE company_id = %s AND is_manager_approver = FALSE
            ORDER BY sequence_order
        """, (company_id,))
        
        workflows = cursor.fetchall()
        
        for workflow in workflows:
            approver_id, _ = workflow
            cursor.execute("""
                INSERT INTO expense_approvals (expense_id, approver_id, sequence_order, status)
                VALUES (%s, %s, %s, 'pending')
            """, (expense_id, approver_id, sequence))
            sequence += 1
        
        conn.commit()
        return True
        
    except Exception as e:
        conn.rollback()
        st.error(f"Failed to create approval workflow: {e}")
        return False
    finally:
        cursor.close()
        conn.close()

def get_next_approver(expense_id: int) -> Optional[int]:
    """Get the next approver in the workflow"""
    conn = get_connection()
    if not conn:
        return None
    
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            SELECT approver_id
            FROM expense_approvals
            WHERE expense_id = %s AND status = 'pending'
            ORDER BY sequence_order
            LIMIT 1
        """, (expense_id,))
        
        result = cursor.fetchone()
        return result[0] if result else None
        
    except Exception as e:
        st.error(f"Failed to get next approver: {e}")
        return None
    finally:
        cursor.close()
        conn.close()

def process_approval(expense_id: int, approver_id: int, action: str, comments: str) -> bool:
    """Process an approval or rejection"""
    conn = get_connection()
    if not conn:
        return False
    
    cursor = conn.cursor()
    
    try:
        # Update the approval record
        cursor.execute("""
            UPDATE expense_approvals
            SET status = %s, comments = %s, approved_at = CURRENT_TIMESTAMP
            WHERE expense_id = %s AND approver_id = %s AND status = 'pending'
        """, (action, comments, expense_id, approver_id))
        
        if action == 'rejected':
            # If rejected, update expense status and reject all pending approvals
            cursor.execute("""
                UPDATE expenses SET status = 'rejected' WHERE id = %s
            """, (expense_id,))
            
            cursor.execute("""
                UPDATE expense_approvals 
                SET status = 'rejected', comments = 'Auto-rejected due to earlier rejection'
                WHERE expense_id = %s AND status = 'pending' AND approver_id != %s
            """, (expense_id, approver_id))
            
        elif action == 'approved':
            # Check if this was the last required approval
            cursor.execute("""
                SELECT COUNT(*) FROM expense_approvals
                WHERE expense_id = %s AND status = 'pending'
            """, (expense_id,))
            
            pending_count = cursor.fetchone()[0]
            
            if pending_count == 0:
                # All approvals complete, approve the expense
                cursor.execute("""
                    UPDATE expenses SET status = 'approved' WHERE id = %s
                """, (expense_id,))
        
        conn.commit()
        return True
        
    except Exception as e:
        conn.rollback()
        st.error(f"Failed to process approval: {e}")
        return False
    finally:
        cursor.close()
        conn.close()

def get_approval_history(expense_id: int) -> List[Dict]:
    """Get approval history for an expense"""
    conn = get_connection()
    if not conn:
        return []
    
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            SELECT ea.sequence_order, u.name, ea.status, ea.comments, ea.approved_at
            FROM expense_approvals ea
            JOIN users u ON ea.approver_id = u.id
            WHERE ea.expense_id = %s
            ORDER BY ea.sequence_order
        """, (expense_id,))
        
        results = cursor.fetchall()
        history = []
        
        for result in results:
            history.append({
                'sequence': result[0],
                'approver_name': result[1],
                'status': result[2],
                'comments': result[3],
                'approved_at': result[4]
            })
        
        return history
        
    except Exception as e:
        st.error(f"Failed to get approval history: {e}")
        return []
    finally:
        cursor.close()
        conn.close()

def check_conditional_approval(expense_id: int, company_id: int) -> bool:
    """Check if conditional approval rules are met"""
    conn = get_connection()
    if not conn:
        return False
    
    cursor = conn.cursor()
    
    try:
        # Get conditional approval workflows
        cursor.execute("""
            SELECT aw.percentage_rule, aw.specific_approver_rule, aw.approver_id
            FROM approval_workflows aw
            WHERE aw.company_id = %s AND (aw.percentage_rule IS NOT NULL OR aw.specific_approver_rule = TRUE)
        """, (company_id,))
        
        workflows = cursor.fetchall()
        
        for workflow in workflows:
            percentage_rule, specific_approver_rule, specific_approver_id = workflow
            
            # Check specific approver rule
            if specific_approver_rule:
                cursor.execute("""
                    SELECT COUNT(*) FROM expense_approvals
                    WHERE expense_id = %s AND approver_id = %s AND status = 'approved'
                """, (expense_id, specific_approver_id))
                
                if cursor.fetchone()[0] > 0:
                    return True
            
            # Check percentage rule
            if percentage_rule:
                cursor.execute("""
                    SELECT 
                        COUNT(*) as total_approvers,
                        COUNT(CASE WHEN status = 'approved' THEN 1 END) as approved_count
                    FROM expense_approvals
                    WHERE expense_id = %s
                """, (expense_id,))
                
                result = cursor.fetchone()
                total_approvers, approved_count = result
                
                if total_approvers > 0:
                    approval_percentage = (approved_count / total_approvers) * 100
                    if approval_percentage >= percentage_rule:
                        return True
        
        return False
        
    except Exception as e:
        st.error(f"Failed to check conditional approval: {e}")
        return False
    finally:
        cursor.close()
        conn.close()

def create_approval_rule(company_id: int, name: str, approver_id: int, sequence_order: int,
                        percentage_rule: Optional[int] = None, specific_approver_rule: bool = False,
                        is_manager_approver: bool = False) -> bool:
    """Create a new approval rule"""
    conn = get_connection()
    if not conn:
        return False
    
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            INSERT INTO approval_workflows 
            (company_id, name, approver_id, sequence_order, percentage_rule, 
             specific_approver_rule, is_manager_approver)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (company_id, name, approver_id, sequence_order, percentage_rule, 
              specific_approver_rule, is_manager_approver))
        
        conn.commit()
        return True
        
    except Exception as e:
        conn.rollback()
        st.error(f"Failed to create approval rule: {e}")
        return False
    finally:
        cursor.close()
        conn.close()

def get_company_approval_rules(company_id: int) -> List[Dict]:
    """Get all approval rules for a company"""
    conn = get_connection()
    if not conn:
        return []
    
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            SELECT aw.id, aw.name, u.name as approver_name, aw.sequence_order,
                   aw.percentage_rule, aw.specific_approver_rule, aw.is_manager_approver
            FROM approval_workflows aw
            JOIN users u ON aw.approver_id = u.id
            WHERE aw.company_id = %s
            ORDER BY aw.sequence_order
        """, (company_id,))
        
        results = cursor.fetchall()
        rules = []
        
        for result in results:
            rules.append({
                'id': result[0],
                'name': result[1],
                'approver_name': result[2],
                'sequence_order': result[3],
                'percentage_rule': result[4],
                'specific_approver_rule': result[5],
                'is_manager_approver': result[6]
            })
        
        return rules
        
    except Exception as e:
        st.error(f"Failed to get approval rules: {e}")
        return []
    finally:
        cursor.close()
        conn.close()
