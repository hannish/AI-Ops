import streamlit as st
import os
import sqlite3
import bcrypt
import openai
from dotenv import load_dotenv
#from openai import OpenAI 

MAX_CHARS = 6000

# ------------------------------
# Database utilities
# ------------------------------

def init_db():
    with sqlite3.connect("users.db", timeout=10) as conn:
        conn.execute("PRAGMA journal_mode=WAL;")  # better concurrency
        c = conn.cursor()
        c.execute(
            """CREATE TABLE IF NOT EXISTS users (
                username TEXT PRIMARY KEY,
                name TEXT,
                password TEXT,
                role TEXT
            )"""
        )
        conn.commit()
    # Ensure admin user exists
    if not verify_user("admin", "admin"):
        add_user("admin", "Administrator", "admin", "admin")

def add_user(username, name, password, role="user"):
    hashed_pw = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
    with sqlite3.connect("users.db", timeout=10) as conn:
        c = conn.cursor()
        c.execute(
            "INSERT OR REPLACE INTO users (username, name, password, role) VALUES (?, ?, ?, ?)",
            (username, name, hashed_pw, role),
        )
        conn.commit()

def verify_user(username, password):
    with sqlite3.connect("users.db", timeout=10) as conn:
        c = conn.cursor()
        c.execute("SELECT username, name, password, role FROM users WHERE username=?", (username,))
        row = c.fetchone()
    if row and bcrypt.checkpw(password.encode(), row[2].encode()):
        return {"username": row[0], "name": row[1], "role": row[3]}
    return None

def get_all_users():
    with sqlite3.connect("users.db", timeout=10) as conn:
        c = conn.cursor()
        c.execute("SELECT username, name, role FROM users")
        return c.fetchall()

def delete_user(username):
    if username == "admin":
        return False
    with sqlite3.connect("users.db", timeout=10) as conn:
        c = conn.cursor()
        c.execute("DELETE FROM users WHERE username=?", (username,))
        conn.commit()
    return True

# ------------------------------
# OpenAI logic
# ------------------------------

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
       temperature=0.4,
     )

#    client = OpenAI(
#        base_url="https://openrouter.ai/api/v1",
#        api_key=api_key,  
#    )

#   completion = client.chat.completions.create(
#        model="openai/gpt-4-turbo",
#        messages=[{"role": "user", "content": prompt}],
#        temperature=0.4,
#    )

    print(completion.choices[0].message.content)

# ------------------------------
# Streamlit pages
# ------------------------------

def login_page():
    st.title("🔑 Login")
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")
    if st.button("Login"):
        user = verify_user(username, password)
        if user:
            st.session_state["user"] = user
            st.session_state["logged_in"] = True
            st.success(f"Welcome, {user['name']}!")
            st.rerun()
        else:
            st.error("Invalid username or password")

def user_management_page():
    st.title("👥 User Management")

    st.subheader("Add User")
    with st.form("add_user_form"):
        username = st.text_input("Username")
        name = st.text_input("Name")
        password = st.text_input("Password", type="password")
        role = st.selectbox("Role", ["user", "admin"])
        submitted = st.form_submit_button("Add User")
        if submitted:
            if username and password:
                add_user(username, name, password, role)
                st.success(f"User {username} added!")
                st.rerun()
            else:
                st.error("Username and password required!")

    st.subheader("User List")
    users = get_all_users()
    for u in users:
        col1, col2, col3 = st.columns([2, 2, 1])
        col1.write(u[0])  # username
        col2.write(f"{u[1]} ({u[2]})")
        if u[0] != "admin":
            if col3.button("Delete", key=f"del_{u[0]}"):
                if delete_user(u[0]):
                    st.success(f"Deleted {u[0]}")
                    st.rerun()
                else:
                    st.error("Cannot delete admin user")

def code_review_page(api_key):
    st.title("💻 Code Review Assistant")

    col1, col2 = st.columns([1, 1])
    with col1:
        st.subheader("Paste your code here")
        code_input = st.text_area("Your Code Here", height=300)

    if st.session_state.get("feedback"):
        st.markdown("### AI Code Review")
        st.markdown(st.session_state["feedback"])
    elif code_input:
        st.write("Review will appear here")
    else:
        st.info("Paste some code to review or upload a file")

    uploaded_file = st.file_uploader("Or upload a file", type=["py", "sh", "tf", "yaml", "yml", "json"])
    if uploaded_file is not None:
        try:
            code_input = uploaded_file.read().decode("utf-8")
            st.text_area("File Content", code_input, height=300)
        except Exception:
            st.error("Could not read the file. Please upload a valid .py, .sh, .tf, .yaml, .yml, .json")

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
                    st.rerun()
                except Exception as e:
                    st.error(f"Something went wrong: {str(e)}")

# ------------------------------
# Main app
# ------------------------------

def main():
    load_dotenv()
    api_key = os.getenv("OPENAI_API_KEY")
    st.set_page_config(page_title="Code Review Assistant", layout="wide")
    st.write("OpenAI key loaded:", api_key is not None)

    # Initialize DB
    init_db()

    if not st.session_state.get("logged_in"):
        login_page()
        return

    user = st.session_state["user"]

    st.sidebar.title(f"Welcome, {user['name']}")
    page = st.sidebar.radio("Navigation", ["Code Review", "User Management"])
    if st.sidebar.button("Logout"):
        st.session_state.clear()
        st.rerun()

    if page == "Code Review":
        code_review_page(api_key)
    elif page == "User Management":
        if user["role"] == "admin":
            user_management_page()
        else:
            st.error("Access denied. Admins only.")

if __name__ == "__main__":
    main()


