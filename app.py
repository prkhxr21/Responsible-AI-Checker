import streamlit as st
st.markdown("""
    <style>
        section[data-testid="stSidebar"] {
            display: none !important;
        }
    </style>
""", unsafe_allow_html=True)
import os
from pymongo import MongoClient
from dotenv import load_dotenv
from urllib.parse import unquote
from datetime import datetime
import time

load_dotenv()

client = MongoClient(os.getenv("MONGO_URI"))
db = client["auth_system"]
pending_users = db["pending_users"]
verified_users = db["verified_users"]


if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False
if 'user_email' not in st.session_state:
    st.session_state.user_email = None
if 'user_name' not in st.session_state:
    st.session_state.user_name = None

def verify_email():
    query_params = st.query_params
    # st.write("Full Query Params:", query_params)
    email = unquote(query_params.get("email", "")).lower().strip()
    token = unquote(query_params.get("token", "")).strip()
    # st.write("Debug Info:")
    # st.write("Email from URL:", email)
    # st.write("Token from URL:", token)
    
    if not email or not token:
        st.error("Missing verification parameters")
        return
    
    st.title("Email Verification")
    
    try:
        user = pending_users.find_one({
            "email": email,
            "verification_token": token
        })
        
        if not user:
            st.error("Invalid verification link or email already verified.")
            return

        if user["token_expiry"] < datetime.now():
            st.error("Verification link has expired. Please register again.")
            pending_users.delete_one({"email": email})
            return
        
        verified_users.insert_one({
            "name": user["name"],
            "email": user["email"],
            "password": user["password"],
            "verified_at": datetime.now()
        })
        
        pending_users.delete_one({"email": email})
        
        st.success("""
            Email verified successfully! 
            You can now login to your account.
        """)
        st.balloons()
        
        st.write("Redirecting to login page...")
        time.sleep(3)
        st.session_state.verified = True
        st.query_params.clear()
        st.rerun()
        
    except Exception as e:
        st.error(f"Verification failed: {str(e)}")
st.title("Welcome to AI Checker!")

query_params = st.query_params
if "email" in query_params and "token" in query_params:
    # Forward verification parameters to auth.py
    verify_email()
    

else:
    # Normal app flow
    if st.button("Log In"):
        st.switch_page("pages/auth.py")
