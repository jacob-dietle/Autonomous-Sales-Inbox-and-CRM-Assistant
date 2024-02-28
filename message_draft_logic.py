import base64
import requests
from email.message import EmailMessage

# Constants
THREAD_NO_DRAFT = "thread_no_draft"
STANDALONE_DRAFT = "standalone_draft"
THREAD_AND_DRAFT = "thread_and_draft"

# Helper functions

# Function to retrieve message details from the pipedream steps
def get_message_details(pd):
    """Retrieve message details from the pipedream steps."""
    print(f"Latest message ID: {pd.steps['parse_and_filter_new_email']['most_recent_message_id']}")
    return {
        "message_id": pd.steps["trigger"]["event"]["labelsAdded"][0]["message"]["id"],
        "email_type": pd.steps["parse_and_filter_new_email"]["email_type"],
        "existing_draft_id": pd.steps["parse_and_filter_new_email"]["draft_id"],
        "new_raw_message": pd.steps["draft_response"]["$return_value"]["generated_message"]["content"],
        "sender": pd.steps["parse_and_filter_new_email"]["sender"],
        "recipient": pd.steps["parse_and_filter_new_email"]["recipient"],
        "subject": pd.steps["parse_and_filter_new_email"]["subject"],
        "thread_id": pd.steps["parse_and_filter_new_email"]["thread_id"],
        "latest_message_id": pd.steps["parse_and_filter_new_email"]["most_recent_message_id"]
    }


# Function to generate headers for API requests
def get_headers(token):
    """Generate headers for API requests."""
    authorization = f'Bearer {token}'
    return {"Authorization": authorization, "Content-Type": "application/json"}


# Function to retrieve the IMAP message ID for the latest message
def get_imap_message_id(headers, latest_message_id):
    """Retrieve the IMAP message ID for the latest message."""
    url = f"https://gmail.googleapis.com/gmail/v1/users/me/messages/{latest_message_id}?format=metadata&metadataHeaders=message-id"
    response = requests.get(url, headers=headers).json()
    print(f"get_imap_message_id() response: {response}")  # Log the response
    if "payload" not in response:
        raise Exception("Error: 'payload' key not found in the response")
    imap_message_id = ""
    for header in response["payload"]["headers"]:
        if header["name"] == "Message-ID":
            imap_message_id = header["value"]
    return imap_message_id


# Function to update an existing draft with new content
def update_draft(headers, draft_id, raw_message, in_reply_to, references):
    """Update an existing draft with new content."""
    url = f'https://gmail.googleapis.com/gmail/v1/users/me/drafts/{draft_id}'
    payload = {
        "id": draft_id,
        "message": {
            "raw": raw_message,
            "headers": [
                {"name": "In-Reply-To", "value": in_reply_to},
                {"name": "References", "value": references}
            ]
        }
    }
    response = requests.put(url, headers=headers, json=payload)
    return response


# Function to create a new draft in a new thread
def create_draft_new_thread(headers, raw_message, thread_id):
    url = 'https://gmail.googleapis.com/gmail/v1/users/me/drafts'
    payload = {
        "message": {
            "raw": raw_message,
            "threadId": thread_id
        }
    }
    response = requests.post(url, headers=headers, json=payload)
    print(f"create_draft_new_thread() response: {response.json()}")  # Log the response
    return response


# Function to create a new draft in an existing thread
def create_draft_existing_thread(headers, raw_message, thread_id, in_reply_to, references):
    url = 'https://gmail.googleapis.com/gmail/v1/users/me/drafts'
    payload = {
        "message": {
            "raw": raw_message,
            "threadId": thread_id,
            "headers": [
                {"name": "In-Reply-To", "value": in_reply_to},
                {"name": "References", "value": references}
            ]
        }
    }
    response = requests.post(url, headers=headers, json=payload)
    print(f"create_draft_existing_thread() response: {response.json()}")  # Log the response
    return response    


# Function to delete an existing draft
def delete_draft(headers, draft_id):
    """Delete an existing draft."""
    print(f"delete_draft() called with draft_id: {draft_id}")  # Debugging print
    url = f'https://gmail.googleapis.com/gmail/v1/users/me/drafts/{draft_id}'
    response = requests.delete(url, headers=headers)
    print(f"delete_draft() response: {response.text}")  # Log the response
    print(f"delete_draft() response status code: {response.status_code}")  # Debugging print
    return response


# Function to handle the thread_no_draft email scenario
def handle_thread_no_draft(headers, existing_draft_id, raw_message, thread_id):
    print("handle_thread_no_draft() called")  # Debugging print
    return create_draft_new_thread(headers, raw_message, thread_id)


# Function to handle the standalone_draft email scenario
def handle_standalone_draft(headers, existing_draft_id, raw_message, thread_id, imap_message_id):
    print("handle_standalone_draft() called")  # Debugging print
    in_reply_to = imap_message_id if imap_message_id else ""
    references = imap_message_id if imap_message_id else ""
    return create_draft_existing_thread(headers, raw_message, thread_id, in_reply_to, references)


# Function to handle the thread_and_draft email scenario
def handle_thread_and_draft(pd, headers, existing_draft_id, raw_message, thread_id, imap_message_id):
    if existing_draft_id:
        delete_response = delete_draft(headers, existing_draft_id)
        if delete_response.status_code == 204:
            pd.export("existing_draft_deleted", True)
        else:
            print(f"Error: Failed to delete the existing draft. Status Code: {delete_response.status_code}")
            raise Exception("Error in deleting the existing draft")
    in_reply_to = imap_message_id if imap_message_id else ""
    references = imap_message_id if imap_message_id else ""
    return create_draft_existing_thread(headers, raw_message, thread_id, in_reply_to, references)

# Function to print debugging information in pipedream logs
def print_debug_info(message_details, imap_message_id, raw_message):
    print("MESSAGE DRAFT LOGIC DEBUGGING INFO:")
    print(f"Message ID: {message_details['message_id']}")
    print(f"Thread ID: {message_details['thread_id']}")
    print(f"Email Type: {message_details['email_type']}")
    print(f"Existing Draft ID: {message_details['existing_draft_id']}")
    print(f"New Raw Message: {message_details['new_raw_message']}")
    print(f"Sender: {message_details['sender']}")
    print(f"Recipient: {message_details['recipient'] if message_details['recipient'] != 'Not set' else message_details['sender']}")
    print(f"Subject: {message_details['subject'] if message_details['subject'] else 'No Subject'}")
    print(f"IMAP Message ID: {imap_message_id}")
    print(f"Raw Message: {raw_message}")
    

# Main handler function
def handler(pd: "pipedream"):
    try:
        token = f'{pd.inputs["gmail_custom_oauth"]["$auth"]["oauth_access_token"]}'
        headers = get_headers(token)
        message_details = get_message_details(pd)

        imap_message_id = None
        if message_details["latest_message_id"] is not None:
            imap_message_id = get_imap_message_id(headers, message_details["latest_message_id"])

        message = EmailMessage()
        message.set_content(message_details["new_raw_message"])
        message["To"] = message_details["sender"] #send back to original message sender
        message["From"] = message_details["recipient"] if message_details["recipient"] != "Not set" else message_details["sender"]
        message["Subject"] = message_details["subject"] or "No Subject"
        message["In-Reply-To"] = imap_message_id
        message["References"] = imap_message_id

        print(f"Full MIME message:\n{message}")

        raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode("utf-8")

        print_debug_info(message_details, imap_message_id, raw_message)

        email_type = message_details['email_type']
        thread_id = message_details['thread_id']
        existing_draft_id = message_details['existing_draft_id']

        if email_type == THREAD_NO_DRAFT:
            response = handle_thread_no_draft(headers, existing_draft_id, raw_message, thread_id)
        elif email_type == STANDALONE_DRAFT:
            response = handle_standalone_draft(headers, existing_draft_id, raw_message, thread_id, imap_message_id)
        elif email_type == THREAD_AND_DRAFT:
            response = handle_thread_and_draft(pd, headers, existing_draft_id, raw_message, thread_id, imap_message_id)

    except KeyError as error:
        import traceback
        print(f"An error occurred: {error}")
        print("Traceback details:")
        traceback.print_exc()
        print(f"Entire pd.steps dictionary: {pd.steps}")
        return pd.flow.exit(f"Error: {error}")

    except (ValueError, requests.HTTPError) as error:
        print(f"An error occurred: {error}")
        return pd.flow.exit(f"Error: {error}")