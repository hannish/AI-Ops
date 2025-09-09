import streamlit as st
import os
import sqlite3
import bcrypt
from dotenv import load_dotenv
import openai

# -----------------------------
# Database Setup & User Helpers
# -----------------------------
def init_db():
    conn = sqlite3.connect("users.db")
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users
                 (username TEXT PRIMARY KEY, 
                  name TEXT, 
                  password TEXT, 
                  role TEXT)''')
    conn.commit()
    conn.close()

def add_user(username, name, password, role="user"):
    conn = sqlite3.connect("users.db")
    c = conn.cursor()
    hashed_pw = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
    c.execute("INSERT INTO users (username, name, password, role) VALUES (?, ?, ?, ?)", 
              (username, name, hashed_pw, role))
    conn.commit()
    conn.close()

def verify_user(username, password):
    conn = sqlite3.connect("users.db")
    c = conn.cursor()
    c.execute("SELECT password, role, name FROM users WHERE username=?", (username,))
    row = c.fetchone()
    conn.close()
    if row and bcrypt.checkpw(password.encode(), row[0].encode()):
        return {"role": row[1], "name": row[2], "username": username}
    return None

def get_all_users():
    conn = sqlite3.connect("users.db")
    c = conn.cursor()
    c.execute("SELECT username, name, role FROM users")
    rows = c.fetchall()
    conn.close()
    return rows

def delete_user(username):
    if username == "admin":
        return False  # protect default admin
    conn = sqlite3.connect("users.db")
    c = conn.cursor()
    c.execute("DELETE FROM users WHERE username=?", (username,))
    conn.commit()
    conn.close()
    return True

# Initialize DB
init_db()
# Ensure there is at least one admin
try:
    add_user("admin", "Administrator", "admin123", "admin")
except:
    pass  # already exists


# -----------------------------
# OpenAI Code Review Function
# -----------------------------
MAX_CHARS = 4000

def get_code_feedback(code, api_key, tone_choice="Supportive"):
    openai.api_key = api_key

    if tone_choice == "Supportive":
        tone_instruction = "You are a kind and encouraging code review assistant."
    elif tone_choice == "Direct":
        tone_instruction = "You are a blunt, no-fluff code reviewer. Be short and clear."
    elif tone_choice == "Humorous":
        tone_instruction = "You are a funny but helpful python coach. Use light and witty tone."
    else:
        tone_instruction = "You are a helpful and friendly code review assistant."

    prompt = f"""
    {tone_instruction}

    Please review the following code and give feedback in three sections:

    1. Style
    2. Errors
    3. Clarity

    Here is the code:
    {code}
    """
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.4   
    )

    return response.choices[0].message['content']


# -----------------------------
# Pages
# -----------------------------
def login_page():
    st.title("🔑 Login")
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")
    if st.button("Login"):
        user = verify_user(username, password)
        if user:
            st.session_state["user"] = user
            st.session_state["logged_in"] = True
            st.experimental_rerun()
        else:
            st.error("Invalid username or password")


def user_management():
    st.title("👥 User Management")

    # --- Add User ---
    st.subheader("➕ Add New User")
    username = st.text_input("New Username")
    name = st.text_input("Full Name")
    password = st.text_input("Password", type="password")
    role = st.selectbox("Role", ["user", "admin"])

    if st.button("Add User"):
        try:
            add_user(username, name, password, role)
            st.success(f"✅ User {username} added successfully")
        except Exception as e:
            st.error(f"❌ Error: {e}")

    st.markdown("---")

    # --- User List ---
    st.subheader("📋 Existing Users")
    users = get_all_users()
    if not users:
        st.info("No users found.")
    else:
        for u in users:
            col1, col2, col3, col4 = st.columns([2, 2, 2, 1])
            with col1:
                st.write(f"**{u[0]}**")  # username
            with col2:
                st.write(u[1])  # name
            with col3:
                st.write(u[2])  # role
            with col4:
                if u[0] != "admin":  # prevent deleting default admin
                    if st.button("🗑️ Delete", key=f"del_{u[0]}"):
                        if delete_user(u[0]):
                            st.success(f"User {u[0]} deleted")
                            st.experimental_rerun()


def code_review_app(api_key):
    st.set_page_config(page_title="Code Review Assistance", layout="wide")
    st.title("🧑‍💻 Code Review Assistant")

    col1, col2 = st.columns([1, 1])

    with col1:
        st.subheader("Paste your code here for review")
        code_input = st.text_area("Your Code Here", height=300)

    with col2:
        st.subheader("Review output")

    if st.session_state.get("feedback"):
        st.markdown("### AI Code Review")
        st.markdown(st.session_state["feedback"])
    elif code_input:
        st.write("Review will appear here")
    else:
        st.info("Paste some code to review or upload a file")

    uploaded_file = st.file_uploader("Or upload a file", type=["py", "txt"])

    if uploaded_file is not None:
        try:
            code_input = uploaded_file.read().decode("utf-8")
            st.text_area("File Content", code_input, height=300)
        except Exception:
            st.error("Could not read the file. Please upload a valid .py or .txt file.")

    tone = st.selectbox("Choose Feedback Tone", ["Supportive", "Direct", "Humorous"])

    if st.button("Run Review"):
        if not code_input.strip():
            st.warning("Please enter or upload some code before running a review.")
        elif len(code_input) > MAX_CHARS:
            st.error(f"Code exceeds {MAX_CHARS} characters limit. Please shorten it.")
        else:
            with st.spinner("Reviewing your code..."):
                try:
                    feedback = get_code_feedback(code_input, api_key, tone)
                    st.session_state["feedback"] = feedback
                except Exception as e:
                    st.error(f"Something went wrong: {str(e)}")


# -----------------------------
# Main App Routing
# -----------------------------
load_dotenv()
api_key = os.getenv("OPENAI_API_KEY")

if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False

if not st.session_state["logged_in"]:
    login_page()
else:
    st.sidebar.write(f"👋 Welcome, {st.session_state['user']['name']} ({st.session_state['user']['role']})")
    if st.sidebar.button("Logout"):
        st.session_state.clear()
        st.experimental_rerun()

    if st.session_state["user"]["role"] == "admin":
        page = st.sidebar.selectbox("Choose Page", ["Code Review", "User Management"])
    else:
        page = "Code Review"

    if page == "User Management":
        user_management()
    else:
        code_review_app(api_key)
