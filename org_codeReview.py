
import streamlit as st
import os
from dotenv import load_dotenv
import openai

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

    Please review the following code and give a feedbacl in three sections:

    1. Style
    2. Errors
    3. Clarity

    Here is the code 
    {code}
    """
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "user", "content": prompt}],
        temperature=0.4   
    )

    return response.choices[0].message['content']

load_dotenv()
api_key = os.getenv("OPENAI_API_KEY")
st.write("key loaded:", api_key is not None)


st.set_page_config(page_title="Code Review Assistance", layout="wide")
st.title ("Code Review Assistant")

col1, col2 = st.columns([1, 1])

with col1:
    st.subheader("paste your code here for review")
    code_input = st.text_area("Your Code Here", height=300)


with col2:
    st.subheader("Review output")

if st.session_state.get("feedback"):
    st.markdown("### AI Code Review")
    st.markdown(st.session_state["feedback"])
elif code_input:
    st.write("review will appear here")
else:
    st.info("paste some code to review or upload a file")

uploaded_file = st.file_uploader("Or upload a file", type=["py", "txt"])

if uploaded_file is not None:
    try:
        code_input = uploaded_file.read().decode("utf-8")
        st.text_area("File Content", code_input, height=300)
    except Exception:
        st.error("Could not read the file. Please upload a valid .py or .txt file.")

tone = st.selectbox("choose Feedback Tone", ["Supportive", "Direct", "Humorous"])

if st.button("Run Review"):
    if not code_input.strip:
        st.warning("Please enter or upload some code before running a review.")
    elif len(code_input) > MAX_CHARS:
        st.error(f"Code exceeds {MAX_CHARS} characters limit. Please shorten it.")
    else:
        with st.spinner("Reviewing your code..."):
            try:
                feedback = get_code_feedback(code_input, api_key, tone)
                st.session_state["feedback"] = feedback
            except Exception as e:
                st.error(f"something went wrong: {str(e)}")
