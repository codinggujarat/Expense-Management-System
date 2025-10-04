import streamlit as st

# Test navigation functionality
st.title("Navigation Test")

# Simulate navigation state
if 'navigate_to' not in st.session_state:
    st.session_state['navigate_to'] = None

st.write("Current navigate_to state:", st.session_state['navigate_to'])

# Button to set navigation
if st.button("Set navigation to expense_submission"):
    st.session_state['navigate_to'] = 'expense_submission'
    st.write("Navigation set! The app should navigate to Expense Submission page.")

# Button to clear navigation
if st.button("Clear navigation"):
    st.session_state['navigate_to'] = None
    st.write("Navigation cleared!")

# Show how navigation would be handled
st.divider()
st.subheader("Navigation Handling Example")

# Simulate pages
pages = {
    "Dashboard": "dashboard",
    "Expense Submission": "expense_submission",
    "Approval Workflow": "approval_workflow"
}

# Check for navigation requests
navigate_to = st.session_state.get('navigate_to')
if navigate_to:
    st.write(f"Navigation request detected: {navigate_to}")
    # Find the page key that corresponds to the navigation target
    for page_key, page_path in pages.items():
        if navigate_to in page_path:
            selected_page = page_key
            st.write(f"Would navigate to: {selected_page}")
            break
    else:
        selected_page = st.selectbox("Select Page", list(pages.keys()))
else:
    selected_page = st.selectbox("Select Page", list(pages.keys()))

st.write(f"Currently selected page: {selected_page}")