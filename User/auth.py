import streamlit as st
import json
import os

CREDENTIALS_FILE = "credentials.json"

# Load users from file
def load_users():
    if not os.path.exists(CREDENTIALS_FILE):
        # Create empty file if it doesn't exist
        with open(CREDENTIALS_FILE, "w") as f:
            json.dump({}, f)
        return {}

    try:
        with open(CREDENTIALS_FILE, "r") as f:
            content = f.read().strip()
            if not content:
                return {}
            return json.loads(content)
    except json.JSONDecodeError:
        # Corrupt or invalid JSON – reset to empty
        with open(CREDENTIALS_FILE, "w") as f:
            json.dump({}, f)
        return {}

# Save users to file
def save_users(users):
    with open(CREDENTIALS_FILE, "w") as f:
        json.dump(users, f, indent=4)

# Initialize users in session state from file
if "users" not in st.session_state:
    st.session_state.users = load_users()

def register():
    st.subheader("👤 Register")
    username = st.text_input("Username", key="reg_username")
    password = st.text_input("Password", type="password", key="reg_password")
    confirm_password = st.text_input("Confirm Password", type="password", key="reg_confirm")
    role = st.selectbox("Role", ["admin", "user"], key="reg_role")

    if st.button("Register", key="reg_button"):
        if not username or not password or not confirm_password:
            st.warning("⚠️ Please fill all fields.")
        elif password != confirm_password:
            st.error("❌ Passwords do not match.")
        elif username in st.session_state.users:
            st.error("❌ Username already exists.")
        else:
            st.session_state.users[username] = {"password": password, "role": role}
            save_users(st.session_state.users)
            st.success("✅ Registered successfully. Please login.")

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
