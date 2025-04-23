import streamlit as st
import json
import os

# Save credentials file relative to this script
CREDENTIALS_FILE = os.path.join(os.path.dirname(__file__), "credentials.json")

def load_users():
    if not os.path.exists(CREDENTIALS_FILE):
        with open(CREDENTIALS_FILE, "w") as f:
            json.dump({}, f)
        return {}

    try:
        with open(CREDENTIALS_FILE, "r") as file:
            content = file.read().strip()
            if not content:
                return {}
            return json.loads(content)
    except (json.JSONDecodeError, IOError):
        # If corrupted, reinitialize
        with open(CREDENTIALS_FILE, "w") as f:
            json.dump({}, f)
        return {}

def save_users(users):
    with open(CREDENTIALS_FILE, "w") as file:
        json.dump(users, file, indent=4)

def register():
    st.subheader("👤 Register")
    username = st.text_input("Username", key="reg_username")
    password = st.text_input("Password", type="password", key="reg_password")
    confirm_password = st.text_input("Confirm Password", type="password", key="reg_confirm")
    role = st.selectbox("Role", ["admin", "user"], key="reg_role")

    if st.button("Register", key="reg_button"):
        users = load_users()

        if not username or not password or not confirm_password:
            st.warning("⚠️ Please fill all fields.")
        elif password != confirm_password:
            st.error("❌ Passwords do not match.")
        elif username in users:
            st.error("❌ Username already exists.")
        else:
            users[username] = {"password": password, "role": role}
            save_users(users)
            st.success("✅ Registered successfully. Please login.")
            st.info(f"📁 Credentials saved to: {CREDENTIALS_FILE}")

def login():
    st.subheader("🔐 Login")
    username = st.text_input("Username", key="login_username")
    password = st.text_input("Password", type="password", key="login_password")

    if st.button("Login", key="login_button"):
        users = load_users()
        user = users.get(username)
        if user and user["password"] == password:
            st.session_state.logged_in = True
            st.session_state.username = username
            st.session_state.role = user["role"]
            st.success(f"✅ Welcome back, {username}!")
        else:
            st.error("❌ Invalid credentials.")

def logout():
    st.session_state.logged_in = False
    st.session_state.username = ""
    st.session_state.role = ""
    st.success("👋 Logged out successfully.")
