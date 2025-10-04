import streamlit as st
from auth import get_current_user, require_role
from models import EXPENSE_CATEGORIES
from currency_service import get_popular_currencies, convert_currency
from ocr_service import process_receipt_upload
from database import create_expense
from approval_service import create_approval_workflow
from datetime import date, datetime

@require_role(['employee', 'manager', 'admin'])
def show_expense_submission():
    """Expense submission form with OCR receipt scanning"""
    st.title("Submit Expense")
    
    user = get_current_user()
    
    # Choose input method
    input_method = st.radio("How would you like to submit your expense?", 
                           ["Manual Entry", "Upload Receipt (OCR)"])
    
    if input_method == "Manual Entry":
        show_manual_expense_form(user)
    else:
        show_ocr_expense_form(user)

def show_manual_expense_form(user):
    """Manual expense submission form"""
    st.header("Manual Expense Entry")
    
    with st.form("expense_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            amount = st.number_input("Amount", min_value=0.01, step=0.01)
            currency = st.selectbox("Currency", get_popular_currencies())
            category = st.selectbox("Category", EXPENSE_CATEGORIES)
        
        with col2:
            expense_date = st.date_input("Expense Date", value=date.today(), max_value=date.today())
            description = st.text_area("Description")
        
        # Optional receipt upload
        st.subheader("Receipt (Optional)")
        receipt_file = st.file_uploader("Upload Receipt", type=['png', 'jpg', 'jpeg', 'pdf'])
        
        submitted = st.form_submit_button("Submit Expense")
        
        if submitted:
            if amount and currency and category and description:
                # Convert currency if different from company default
                converted_amount = amount
                if currency != user['default_currency']:
                    converted_amount = convert_currency(amount, currency, user['default_currency'])
                    if converted_amount is None:
                        st.error(f"Unable to convert {currency} to {user['default_currency']}. Please try again.")
                        return
                
                # Save receipt file if uploaded
                receipt_path = None
                if receipt_file:
                    from ocr_service import save_uploaded_file
                    receipt_path = save_uploaded_file(receipt_file)
                
                # Create expense
                expense_id = create_expense(
                    employee_id=user['id'],
                    company_id=user['company_id'],
                    amount=amount,
                    currency=currency,
                    converted_amount=converted_amount,
                    category=category,
                    description=description,
                    expense_date=expense_date.isoformat(),
                    receipt_path=receipt_path
                )
                
                if expense_id:
                    # Create approval workflow
                    workflow_created = create_approval_workflow(user['company_id'], expense_id)
                    
                    if workflow_created:
                        st.success("Expense submitted successfully and sent for approval!")
                    else:
                        st.warning("Expense created but approval workflow failed. Please contact admin.")
                    
                    # Show conversion info if applicable
                    if currency != user['default_currency']:
                        st.info(f"Amount converted: {currency} {amount:,.2f} = {user['default_currency']} {converted_amount:,.2f}")
                else:
                    st.error("Failed to submit expense. Please try again.")
            else:
                st.error("Please fill in all required fields")

def show_ocr_expense_form(user):
    """OCR-based expense submission"""
    st.header("Upload Receipt for OCR Processing")
    
    uploaded_file = st.file_uploader("Upload Receipt Image", type=['png', 'jpg', 'jpeg'])
    
    if uploaded_file:
        # Display the uploaded image
        st.image(uploaded_file, caption="Uploaded Receipt", width=300)
        
        if st.button("Process Receipt"):
            with st.spinner("Processing receipt with OCR..."):
                receipt_data = process_receipt_upload(uploaded_file)
            
            if receipt_data:
                st.success("Receipt processed successfully!")
                
                # Show extracted data with edit options
                st.subheader("Extracted Information")
                st.info("Please review and edit the extracted information before submitting:")
                
                with st.form("ocr_expense_form"):
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        amount = st.number_input("Amount", 
                                               value=receipt_data.get('amount', 0.0),
                                               min_value=0.01, 
                                               step=0.01)
                        
                        currency = st.selectbox("Currency", 
                                              get_popular_currencies(),
                                              index=0)  # Default to first currency
                        
                        category = st.selectbox("Category", 
                                              EXPENSE_CATEGORIES,
                                              index=0)  # Default to first category
                    
                    with col2:
                        default_date = receipt_data.get('date', date.today())
                        if isinstance(default_date, str):
                            try:
                                default_date = datetime.strptime(default_date, '%Y-%m-%d').date()
                            except:
                                default_date = date.today()
                        
                        expense_date = st.date_input("Expense Date", 
                                                   value=default_date,
                                                   max_value=date.today())
                        
                        description = st.text_area("Description", 
                                                 value=receipt_data.get('description', ''))
                    
                    # Show extracted text for reference
                    with st.expander("View Extracted Text"):
                        st.text(receipt_data.get('extracted_text', 'No text extracted'))
                    
                    submitted = st.form_submit_button("Submit Expense")
                    
                    if submitted:
                        if amount and currency and category and description:
                            # Convert currency if different from company default
                            converted_amount = amount
                            if currency != user['default_currency']:
                                converted_amount = convert_currency(amount, currency, user['default_currency'])
                                if converted_amount is None:
                                    st.error(f"Unable to convert {currency} to {user['default_currency']}. Please try again.")
                                    return
                            
                            # Create expense with receipt path
                            expense_id = create_expense(
                                employee_id=user['id'],
                                company_id=user['company_id'],
                                amount=amount,
                                currency=currency,
                                converted_amount=converted_amount,
                                category=category,
                                description=description,
                                expense_date=expense_date.isoformat(),
                                receipt_path=receipt_data.get('receipt_path')
                            )
                            
                            if expense_id:
                                # Create approval workflow
                                workflow_created = create_approval_workflow(user['company_id'], expense_id)
                                
                                if workflow_created:
                                    st.success("Expense submitted successfully and sent for approval!")
                                else:
                                    st.warning("Expense created but approval workflow failed. Please contact admin.")
                                
                                # Show conversion info if applicable
                                if currency != user['default_currency']:
                                    st.info(f"Amount converted: {currency} {amount:,.2f} = {user['default_currency']} {converted_amount:,.2f}")
                                
                                # Clear the form
                                st.rerun()
                            else:
                                st.error("Failed to submit expense. Please try again.")
                        else:
                            st.error("Please fill in all required fields")
            else:
                st.error("Failed to process receipt. Please try manual entry or upload a clearer image.")

def show_expense_tips():
    """Show helpful tips for expense submission"""
    with st.expander("💡 Tips for Better Expense Management"):
        st.write("""
        **For Manual Entry:**
        - Include detailed descriptions for faster approval
        - Upload receipts when possible for verification
        - Submit expenses promptly after incurring them
        
        **For OCR Processing:**
        - Ensure receipts are clear and well-lit
        - Avoid blurry or damaged receipts
        - Review all extracted information before submitting
        - Common categories like 'Meals & Entertainment' or 'Travel' are processed better
        
        **General Guidelines:**
        - Follow your company's expense policy
        - Include business justification in descriptions
        - Keep original receipts for your records
        """)
