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
import hashlib
import secrets
import smtplib
from email.mime.text import MIMEText
from datetime import datetime, timedelta
from urllib.parse import quote, unquote, urlencode
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

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def generate_verification_token():
    return secrets.token_urlsafe(32)

def send_verification_email(email, name, token):
    safe_email = quote(email)
    safe_token = quote(token)
    
    verification_link = f"http://localhost:8501/?email={safe_email}&token={safe_token}"
    
    subject = "Please verify your email"
    body = f"""
    <html>
        <body>
            <p>Hi {name},</p>
            <p>Thank you for registering! Please click the link below to verify your email:</p>
            <p><a href="{verification_link}">Verify Email</a></p>
            <p>If you didn't request this, please ignore this email.</p>
        </body>
    </html>
    """
    
    msg = MIMEText(body, 'html')
    msg['Subject'] = subject
    msg['From'] = os.getenv("EMAIL_USER")
    msg['To'] = email
    
    try:
        with smtplib.SMTP(os.getenv("EMAIL_HOST"), os.getenv("EMAIL_PORT")) as server:
            server.starttls()
            server.login(os.getenv("EMAIL_USER"), os.getenv("EMAIL_PASS"))
            server.send_message(msg)
        return True
    except Exception as e:
        st.error(f"Failed to send verification email: {e}")
        return False

def signup():
    st.subheader("Create New Account")
    name = st.text_input("Full Name", key="signup_name")
    email = st.text_input("Email", key="signup_email")
    password = st.text_input("Password", type="password", key="signup_pass")
    confirm_password = st.text_input("Confirm Password", type="password", key="signup_pass_confirm")
    
    if st.button("Sign Up"):
     
        if not name or not email or not password:
            st.error("Please fill in all fields!")
            return
        
        if password != confirm_password:
            st.error("Passwords do not match!")
            return
        
        if verified_users.find_one({"email": email}) or pending_users.find_one({"email": email}):
            st.error("Email already registered!")
            return
        
        verification_token = generate_verification_token()
        expiry_time = datetime.now() + timedelta(hours=24)

        pending_users.insert_one({
            "name": name,
            "email": email,
            "password": hash_password(password),
            "verification_token": verification_token,
            "token_expiry": expiry_time,
            "created_at": datetime.now()
        })
        
        if send_verification_email(email, name, verification_token):
            st.success("Registration successful! Please check your email for verification instructions.")
        else:
            st.error("Failed to send verification email. Please try again.")

def verify_email():
    query_params = st.query_params
    st.write("Full Query Params:", query_params)
    email = unquote(query_params.get("email", [None])[0]).lower().strip()
    token = unquote(query_params.get("token", [None])[0]).strip()
    st.write("Debug Info:")
    st.write("Email from URL:", email)
    st.write("Token from URL:", token)
    
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

def login():
    st.subheader("Login")
    email = st.text_input("Email", key="login_email")
    password = st.text_input("Password", type="password", key="login_pass")
    
    if st.button("Login"):
        user = verified_users.find_one({"email": email})
        
        if user and user["password"] == hash_password(password):
            st.session_state.authenticated = True
            st.session_state.user_email = email
            st.session_state.user_name = user["name"]
            st.success(f"Welcome back, {user['name']}!")
            st.query_params["page"]="checker"
            st.rerun()
        else:
            st.error("Invalid email or password")

def logout():
    st.session_state.authenticated = False
    st.session_state.user_email = None
    st.session_state.user_name = None
    st.success("You have been logged out.")

def main():
    st.title("Welcome to AI Checker")
    
    query_params = st.query_params
    if "email" in query_params and "token" in query_params:
        st.switch_page("pages/verify.py")
    if st.query_params.get("page") == "auth":
        st.switch_page("pages/auth.py")
    if st.query_params.get("page") == "checker":
        st.switch_page("pages/checker.py")
        
    else:
        tab1, tab2 = st.tabs(["Login", "Sign Up"])
        with tab1:
            login()
        with tab2:
            signup()

if __name__ == "__main__":
    main()
