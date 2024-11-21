import streamlit as st
import concurrent.futures
from openai import OpenAI
import traceback
import time

# Initialize the OpenAI client
client = OpenAI(
    api_key="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"
)

def upload_file(file_path):
    try:
        with open(file_path, 'rb') as file:
            file_response = client.files.create(file=file, purpose='assistants')
        return file_response.id
    except Exception as e:
        st.error(f"Error uploading file: {e}")
        traceback.print_exc()
        return None

def delete_file(file_id):
    try:
        client.files.delete(file_id=file_id)
    except Exception as e:
        st.error(f"Error deleting file: {e}")
        traceback.print_exc()

def verify_file_access(file_id):
    try:
        client.files.retrieve(file_id=file_id)
        return True
    except Exception as e:
        st.error(f"File verification failed: {e}")
        return False

def send_message(thread_id, user_message, file_id=None):
    try:
        attachments = [{"file_id": str(file_id), "tools": [{"type": "file_search"}]}] if file_id else []
        message = client.beta.threads.messages.create(
            thread_id=thread_id,
            role="user",
            content=user_message,
            attachments=attachments
        )
        return message
    except Exception as e:
        st.error(f"Error sending message: {e}")
        traceback.print_exc()
        return None

def run_assistant_and_get_response(assistant_id, user_message, file_id):
    try:
        thread = client.beta.threads.create()
        send_message(thread.id, user_message, file_id)
        run = client.beta.threads.runs.create(thread_id=thread.id, assistant_id=assistant_id)

        while True:
            run = client.beta.threads.runs.retrieve(thread_id=thread.id, run_id=run.id)
            if run.status == "completed":
                break
            elif run.status in ["failed", "cancelled"]:
                st.error(f"Run {run.status}. Details: {run}")
                return []
            time.sleep(5)

        messages = client.beta.threads.messages.list(thread_id=thread.id)
        answers = [msg.content for msg in messages.data if msg.role == "assistant"]
        return answers
    except Exception as e:
        st.error(f"Error during assistant run: {e}")
        traceback.print_exc()
        return []

# Streamlit app
st.title("OpenAI Assistant with File Upload")

uploaded_file = st.file_uploader("Upload a PDF file", type="pdf")
user_message = st.text_area("Enter your message")
assistant_id = st.text_input("Enter Assistant ID", value="asst_pq3Mgw1G8cAoX2CtixU2wjL2")

if st.button("Run Analysis"):
    if uploaded_file and user_message and assistant_id:
        with open("temp.pdf", "wb") as f:
            f.write(uploaded_file.read())
        file_id = upload_file("temp.pdf")
        if file_id and verify_file_access(file_id):
            with st.spinner("Running analysis..."):
                answers = run_assistant_and_get_response(assistant_id, user_message, file_id)
            st.success("Analysis complete!")
            st.write("Answers:", answers)
            delete_file(file_id)
        else:
            st.error("File upload or verification failed.")
    else:
        st.error("Please provide all required inputs.")
