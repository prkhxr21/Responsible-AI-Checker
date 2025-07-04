import streamlit as st

st.markdown("""
    <style>
        section[data-testid="stSidebar"] {
            display: none !important;
        }
    </style>
""", unsafe_allow_html=True)

st.title("Welcome to AI Checker!")

st.markdown("""
Click below to login or signup.
""")

if st.button("Log In"):
    st.switch_page("pages/auth.py")