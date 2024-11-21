import streamlit as st
from openai import OpenAI
import traceback
import time

# Zugriff auf den API-Schlüssel aus Streamlit-Secrets
api_key = st.secrets["OPENAI_API_KEY"]

# OpenAI initialisieren
client = OpenAI(api_key=api_key)

# Feste Assistant-ID und Nachricht
ASSISTANT_ID = "asst_pq3Mgw1G8cAoX2CtixU2wjL2"
DEFAULT_MESSAGE = "Analyze the PDF following your instructions. Analyze the whole document. Execute your whole task."

# Funktionen
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

        # Extrahiere nur den reinen Text
        plain_texts = []
        for answer in answers:
            if isinstance(answer, str):
                plain_texts.append(answer)
            elif isinstance(answer, list):
                for item in answer:
                    if isinstance(item, str):
                        plain_texts.append(item)
                    elif hasattr(item, "text") and hasattr(item.text, "value"):
                        plain_texts.append(item.text.value)

        return plain_texts
    except Exception as e:
        st.error(f"Error during assistant run: {e}")
        traceback.print_exc()
        return []

# Streamlit App
st.title("OpenAI PDF Analysis")

# Beschreibung des Tools
st.markdown(
    """
    **Dieser Chatbot analysiert PDF-Dokumente und erstellt eine übersichtliche und strukturierte Zusammenfassung.**
    \nLaden Sie einfach Ihre Dateien hoch, und das Tool übernimmt den Rest!
    """
)

uploaded_files = st.file_uploader("Upload multiple PDF files", type="pdf", accept_multiple_files=True)

if st.button("Run Analysis"):
    if uploaded_files:
        all_answers = {}
        for uploaded_file in uploaded_files:
            with open(uploaded_file.name, "wb") as f:
                f.write(uploaded_file.read())
            file_id = upload_file(uploaded_file.name)
            if file_id and verify_file_access(file_id):
                with st.spinner(f"Running analysis for {uploaded_file.name}..."):
                    answers = run_assistant_and_get_response(ASSISTANT_ID, DEFAULT_MESSAGE, file_id)
                all_answers[uploaded_file.name] = answers
                delete_file(file_id)
            else:
                st.error(f"File upload or verification failed for {uploaded_file.name}.")
        
        st.success("Analysis complete!")
        st.write("### Answers (Clean Text):")
        for file_name, answers in all_answers.items():
            st.write(f"#### {file_name}")
            for answer in answers:
                st.write(answer)
    else:
        st.error("Please upload at least one PDF file.")
