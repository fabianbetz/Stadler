import concurrent.futures
from openai import OpenAI
import os
import time
import traceback

# Initialize the OpenAI client
client = OpenAI(
    api_key="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"
)

def upload_file(file_path):
    try:
        with open(file_path, 'rb') as file:
            file_response = client.files.create(file=file, purpose='assistants')
        print(f"File uploaded successfully with ID: {file_response.id}")
        return file_response.id
    except Exception as e:
        print("Error uploading file:", e)
        traceback.print_exc()
        return None

def delete_file(file_id):
    try:
        client.files.delete(file_id=file_id)
        print(f"File deleted successfully with ID: {file_id}")
    except Exception as e:
        print("Error deleting file:", e)
        traceback.print_exc()

def verify_file_access(file_id):
    try:
        # Überprüfen, ob die Datei zugänglich ist
        file_info = client.files.retrieve(file_id=file_id)
        print(f"File verified with details: {file_info}")
        return True
    except Exception as e:
        print("File verification failed:", e)
        return False

def send_message(thread_id, user_message, file_id=None):
    try:
        # Sicherstellen, dass `file_id` ein String ist
        if isinstance(file_id, list):
            file_id = file_id[0]  # Falls `file_id` versehentlich als Liste übergeben wurde
        file_id = str(file_id)  # Erzwingt die Umwandlung in einen String
        
        # Struktur für attachments, korrekt formatiert mit `file_id` als String
        attachments = [{"file_id": file_id, "tools": [{"type": "file_search"}]}] if file_id else []
        
        # Ausgabe zur Überprüfung von attachments und `file_id`
        print(f"Sending message with file_id: {file_id} and structured attachments: {attachments}")

        # Senden der Nachricht und Hinzufügen der Datei (falls vorhanden)
        message = client.beta.threads.messages.create(
            thread_id=thread_id,
            role="user",
            content=user_message,
            attachments=attachments  # Verwenden Sie die strukturierte attachments-Liste
        )
        print(f"Message sent successfully with content: '{user_message}' and structured attachments: {attachments}")
        return message
    except Exception as e:
        print("Error sending message:", e)
        traceback.print_exc()
        return None

def run_assistant_and_get_response(assistant_id, user_message, file_id):
    try:
        # Create a new thread for each assistant
        thread = client.beta.threads.create()
        print(f"Thread created with ID: {thread.id}")

        # Send the user message
        send_message(thread.id, user_message, [file_id])

        # Create a run
        run = client.beta.threads.runs.create(
            thread_id=thread.id,
            assistant_id=assistant_id
        )
        print(f"Run created with ID: {run.id}")

        # Wait for the run to complete
        while True:
            run = client.beta.threads.runs.retrieve(
                thread_id=thread.id,
                run_id=run.id,
            )
            print(f"Run status: {run.status}")
            if run.status == "completed":
                break
            elif run.status == "failed":
                # Geben Sie die Fehlermeldung detailliert aus
                print("Run failed. Full run details:", run)
                raise Exception("Run failed due to an error. Check the 'run' details above for specifics.")
            elif run.status == "cancelled":
                print("Run was cancelled. Full run details:", run)
                raise Exception("Run was cancelled. Check the 'run' details above for specifics.")
            time.sleep(10)

        # Retrieve the assistant's messages
        messages = client.beta.threads.messages.list(
            thread_id=thread.id
        )
        print(f"Retrieved messages: {messages.data}")

        answers = []
        for message in messages.data:
            if message.role == "assistant":
                # Process message content based on expected format
                if isinstance(message.content, list):
                    for item in message.content:
                        if hasattr(item, 'text') and hasattr(item.text, 'value'):
                            answers.append(item.text.value)
                        elif isinstance(item, str):
                            answers.append(item)
                        else:
                            print(f"Unsupported message item format: {type(item)}")
                elif isinstance(message.content, str):
                    answers.append(message.content)
                else:
                    print(f"Unsupported message format: {type(message.content)}")

        return answers

    except Exception as e:
        print("An error occurred in assistant task:", e)
        traceback.print_exc()
        return []


# Main script

pdf_file_path = r"C:/Users/betfab/Downloads/Dokument1.pdf"
file_id = upload_file(pdf_file_path)

if file_id and verify_file_access(file_id):
    assistant_ids = [
        "asst_pq3Mgw1G8cAoX2CtixU2wjL2",
    ]

    user_messages = [
        "Analyze the PDF following your instructions. Analyze the whole document. Execute your whole task",
    ]

    # Create a ThreadPoolExecutor to run each assistant task in a separate thread
    with concurrent.futures.ThreadPoolExecutor(max_workers=len(assistant_ids)) as executor:
        futures = [
            executor.submit(run_assistant_and_get_response, assistant_id, user_message, file_id)
            for assistant_id, user_message in zip(assistant_ids, user_messages)
        ]

        # Process the results as they become available
        for future in concurrent.futures.as_completed(futures):
            try:
                answers = future.result()
                print(f"Assistant answers: {answers}")
            except Exception as exc:
                print("An exception occurred while processing assistant response:", exc)
                traceback.print_exc()

    delete_file(file_id)
else:
    print("File upload failed; skipping assistant tasks.")
