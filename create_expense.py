from database import *

expense_id = create_expense(
    employee_id=1,
    company_id=1,
    amount=150.0,
    currency='USD',
    converted_amount=150.0,
    category='Travel',
    description='Business trip',
    expense_date='2025-10-05'
)

print(f'New expense created: {expense_id}')

if expense_id:
    from approval_service import create_approval_workflow
    workflow_created = create_approval_workflow(1, expense_id)
    print(f'Approval workflow created: {workflow_created}')
    
    # Check pending approvals
    from database import get_pending_approvals
    approvals = get_pending_approvals(1)
    print(f'Pending approvals for user 1: {len(approvals)}')