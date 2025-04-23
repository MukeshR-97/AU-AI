import streamlit as st
import json
import bcrypt
import os

CREDENTIALS_FILE = "credentials.json"

def load_credentials():
    if not os.path.exists(CREDENTIALS_FILE):
        with open(CREDENTIALS_FILE, "w") as f:
            json.dump({"users": []}, f)
    with open(CREDENTIALS_FILE, "r") as f:
        return json.load(f)

def save_credentials(creds):
    with open(CREDENTIALS_FILE, "w") as f:
        json.dump(creds, f, indent=4)

def hash_password(password):
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

def verify_password(password, hashed):
    return bcrypt.checkpw(password.encode(), hashed.encode())

def register():
    st.subheader("📝 Register")
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")
    role = st.selectbox("Role", ["admin", "user"])
    if st.button("Register"):
        creds = load_credentials()
        if any(u["username"] == username for u in creds["users"]):
            st.warning("🚫 Username already exists.")
            return
        creds["users"].append({
            "username": username,
            "password": hash_password(password),
            "role": role
        })
        save_credentials(creds)
        st.success("✅ Registered! Please login.")

def login():
    st.subheader("🔐 Login")
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")
    if st.button("Login"):
        creds = load_credentials()
        user = next((u for u in creds["users"] if u["username"] == username), None)
        if user and verify_password(password, user["password"]):
            st.session_state.logged_in = True
            st.session_state.username = username
            st.session_state.role = user["role"]
            st.experimental_rerun()
        else:
            st.error("Invalid credentials")

def logout():
    st.session_state.logged_in = False
    st.session_state.username = None
    st.session_state.role = None
    st.experimental_rerun()
