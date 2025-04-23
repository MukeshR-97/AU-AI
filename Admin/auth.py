# main.py (runs on port 8080)
import streamlit as st
import boto3
from botocore.exceptions import ClientError
import hashlib

# Initialize DynamoDB
dynamodb = boto3.resource('dynamodb', region_name='us-east-1')  # Update region if needed
users_table = dynamodb.Table('users')

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def register():
    st.title("Register")
    name = st.text_input("Name")
    email = st.text_input("Email")
    role = st.selectbox("Role", ["admin", "user"])
    password = st.text_input("Password", type="password")

    if st.button("Register"):
        try:
            # Check if user already exists
            response = users_table.get_item(Key={'email': email})
            if 'Item' in response:
                st.error("User already exists!")
                return
            
            # Create new user
            users_table.put_item(
                Item={
                    'email': email,
                    'name': name,
                    'role': role,
                    'password': hash_password(password)
                }
            )
            st.success("Registered successfully! Please login.")
        except ClientError as e:
            st.error(f"Error registering user: {e.response['Error']['Message']}")

def login():
    st.title("Login")
    email = st.text_input("Email")
    password = st.text_input("Password", type="password")

    if st.button("Login"):
        try:
            response = users_table.get_item(Key={'email': email})
            user = response.get('Item')
            if user and user['password'] == hash_password(password):
                st.success(f"Welcome {user['name']}! Redirecting...")

                # Store user in session state
                st.session_state.user = user

                if user["role"] == "admin":
                    st.markdown("[Go to Admin Dashboard](http://13.234.186.216:8083)")
                else:
                    st.markdown("[Go to User Dashboard](http://13.234.186.216:8084)")
            else:
                st.error("Invalid credentials!")
        except ClientError as e:
            st.error(f"Error logging in: {e.response['Error']['Message']}")

page = st.sidebar.selectbox("Choose action", ["Login", "Register"])
if page == "Register":
    register()
else:
    login()
