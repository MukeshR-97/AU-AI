import streamlit as st
import boto3
from botocore.exceptions import ClientError
import bcrypt

# AWS DynamoDB Setup
dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
users_table = dynamodb.Table('users')

# Password utilities
def hash_password(password):
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')

def check_password(stored_password, input_password):
    return bcrypt.checkpw(input_password.encode('utf-8'), stored_password.encode('utf-8'))

# Inject refined CSS
def set_business_ui():
    st.markdown("""
        <style>
            body, html {
                background-color: #f9f9f9;
                font-family: 'Segoe UI', sans-serif;
            }

            .form-box {
                background-color: white;
                padding: 25px 30px 35px 30px;
                margin: 40px auto;
                border-radius: 10px;
                box-shadow: 0 2px 12px rgba(0, 0, 0, 0.07);
                max-width: 580px;
                position: relative;
            }

            .form-header {
                background: linear-gradient(90deg, #2c3e50, #34495e);
                padding: 15px;
                border-radius: 8px 8px 0 0;
                text-align: center;
                margin: -25px -30px 25px -30px;
            }

            .form-header h5 {
                margin: 0;
                font-size: 22px;
                font-weight: 700;
                color: white;
            }

            label {
                font-weight: 600 !important;
                color: #333 !important;
            }

            .stButton>button {
                background-color: #2c3e50;
                color: white;
                font-weight: 600;
                font-size: 14px;
                padding: 6px 20px;
                border-radius: 4px;
                border: none;
                margin-top: 12px;
            }

            .stButton>button:hover {
                background-color: #34495e;
            }

            section.main > div {
                padding-top: 15px;
                padding-bottom: 10px;
            }
        </style>
    """, unsafe_allow_html=True)

# Registration Page
def register():
    set_business_ui()
    st.markdown("<div class='form-box'><div class='form-header'><h5>Registration</h5></div>", unsafe_allow_html=True)
    with st.form("register_form", clear_on_submit=True):
        name = st.text_input("Full Name")
        email = st.text_input("Email")
        role = st.selectbox("Role", ["admin", "user"])
        password = st.text_input("Password", type="password")
        submit = st.form_submit_button("Register")

        if submit:
            if not name or not email or not password:
                st.warning("All fields are required.")
                return
            try:
                response = users_table.get_item(Key={'email': email, 'role': role})
                if 'Item' in response:
                    st.error("User already exists with this email and role.")
                    return
                users_table.put_item(Item={
                    'email': email,
                    'role': role,
                    'name': name,
                    'password': hash_password(password)
                })
                st.success("Registration successful. Please log in.")
            except ClientError as e:
                st.error(f"DynamoDB error: {e.response['Error']['Message']}")
            except Exception as e:
                st.error(f"Unexpected error: {e}")
    st.markdown("</div>", unsafe_allow_html=True)

# Login Page
def login():
    set_business_ui()
    st.markdown("<div class='form-box'><div class='form-header'><h5>Login</h5></div>", unsafe_allow_html=True)
    with st.form("login_form", clear_on_submit=True):
        email = st.text_input("Email")
        password = st.text_input("Password", type="password")
        role = st.selectbox("Role", ["admin", "user"])
        submit = st.form_submit_button("Login")

        if submit:
            try:
                response = users_table.get_item(Key={'email': email, 'role': role})
                user = response.get('Item')
                if user and check_password(user['password'], password):
                    st.success(f"Welcome, {user['name']} ({role})")
                    # Set the session state
                    st.session_state.user = {
                        "email": user["email"],
                        "name": user["name"],
                        "role": role
                    }

                    # Define URLs based on the role
                    if role == "admin":
                        redirect_url = "http://13.203.229.21/:8083"
                    elif role == "user":
                        redirect_url = "http://13.203.229.21/:8084"
                    
                    # Redirect to the specific dashboard URL
                    st.markdown(f'<a href="{redirect_url}" target="_self">Go to {role.capitalize()} Dashboard</a>', unsafe_allow_html=True)
                    
                else:
                    st.error("Invalid email, password, or role.")
            except ClientError as e:
                st.error(f"DynamoDB error: {e.response['Error']['Message']}")
            except Exception as e:
                st.error(f"Unexpected error: {e}")
    st.markdown("</div>", unsafe_allow_html=True)

# Sidebar Navigation
st.sidebar.title("Navigation")
page = st.sidebar.radio("Select Action", ["Login", "Register"])

if page == "Register":
    register()
elif page == "Login":
    login()
