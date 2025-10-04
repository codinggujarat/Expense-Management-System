import streamlit as st
from database import get_user_by_id
from typing import Optional, Dict

def authenticate_user() -> bool:
    """Check if user is authenticated"""
    return 'user_id' in st.session_state and st.session_state['user_id'] is not None

def get_current_user() -> Optional[Dict]:
    """Get current authenticated user"""
    if not authenticate_user():
        return None
    
    user_id = st.session_state['user_id']
    return get_user_by_id(user_id)

def require_role(allowed_roles: list):
    """Decorator to require specific roles"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            user = get_current_user()
            if not user or user['role'] not in allowed_roles:
                st.error("Access denied. Insufficient permissions.")
                st.stop()
            return func(*args, **kwargs)
        return wrapper
    return decorator

def logout():
    """Logout current user"""
    keys_to_remove = ['user_id', 'email', 'role', 'company_id']
    for key in keys_to_remove:
        if key in st.session_state:
            del st.session_state[key]
