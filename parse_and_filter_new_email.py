import base64
import re
import requests
from talon.quotations import extract_from
from bs4 import BeautifulSoup
from dateutil.parser import parse

# Function to get label IDs from Gmail API
def get_label_ids(headers):
    url = "https://gmail.googleapis.com/gmail/v1/users/me/labels"
    response = requests.get(url, headers=headers).json()
    labels = {}
    for label in response['labels']:
        labels[label['name']] = label['id']
    return labels

# Function to remove HTML tags from content
def remove_html(html_content):
    soup = BeautifulSoup(html_content, "html.parser")
    return soup.get_text()


# Function to extract email address from string
def extract_email_address(string):
    email_regex = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
    result = re.search(email_regex, string)
    return result.group(0) if result else ""

# Function to get thread messages from Gmail API
def get_thread_messages(thread_id, headers):
    url = f"https://gmail.googleapis.com/gmail/v1/users/me/threads/{thread_id}"
    response = requests.get(url, headers=headers).json()
    messages = response.get("messages", [])
    return [(message["id"], message.get("labelIds", [])) for message in messages]


# Function to remove quoted content from the email
def remove_quoted_content(content):
    # Function to remove quoted content from email
    return extract_from(content)

# Function to get header value from payload
def get_header_value(headers, header_name):
    for header in headers:
        if header["name"] == header_name:
            return header["value"]
    return None


# Function to extract payload details from the Gmail API response
def extract_payload_details(payload):
    sender_value = get_header_value(payload["headers"], "From")
    recipient_value = get_header_value(payload["headers"], "To")
    subject_value = get_header_value(payload["headers"], "Subject")
    date_value = get_header_value(payload["headers"], "Date")
    message_labels = payload.get("labelIds", [])

    sender = extract_email_address(sender_value) if sender_value else None
    recipient = recipient_value if recipient_value else None
    subject = subject_value if subject_value else None
    date = date_value if date_value else None

    content_type = None
    content = ""

    if "parts" in payload:
        for part in payload["parts"]:
            if part["mimeType"] == "text/plain" or part["mimeType"] == "text/html":
                content_type = part["mimeType"]
                content = base64.urlsafe_b64decode(part["body"]["data"]).decode("utf-8")
    elif payload["mimeType"] in ["text/plain", "text/html"]:
        content_type = payload["mimeType"]
        content = base64.urlsafe_b64decode(payload["body"]["data"]).decode("utf-8")

    content_structure = {
        "content_type": content_type,
        "raw_content": content
    }

    return sender, recipient, subject, content_structure, message_labels, date

# Function to process message content and remove HTML and quoted content
def process_message_content(content):
    content_type = content["content_type"]
    raw_content = content["raw_content"]
    
    if content_type == "text/html":
        cleaned_content = remove_html(raw_content)
    else:
        cleaned_content = raw_content

    cleaned_content = remove_quoted_content(cleaned_content)
    
    return cleaned_content.strip()


# Function to get Gmail data from the API
def get_gmail_data(url, headers):
    response = requests.get(url, headers=headers)
    if response.status_code != 200:
        raise requests.HTTPError(f"The request failed with status code: {response.status_code}")
    return response.json()


# Function to get message data from Gmail API
def get_message_data(message_id, headers):
    url = f"https://gmail.googleapis.com/gmail/v1/users/me/messages/{message_id}?format=full"
    response_data = get_gmail_data(url, headers)
    payload = response_data.get("payload", {})

    if not payload:
        raise KeyError(f"The 'payload' key is missing from the API response for message id {message_id}")

    message_sender, message_recipient, message_subject, content, message_labels, message_date = extract_payload_details(payload)

    processed_content = process_message_content(content)

    message_information = {
        "labels": message_labels,
        "sender": message_sender,
        "recipient": message_recipient,
        "subject": message_subject,
        "date": message_date,
        "content": processed_content
    }

    return message_information

# Function to determine email scenario based on the structure of the messages list
def determine_email_scenario(messages):
    """
    Determine the email scenario based on the structure of the messages list.

    :param messages: List of messages in the thread
    :return: Email scenario as a string ("thread_no_draft", "thread_and_draft", or "standalone_draft")
    """
    if len(messages) == 1:
        if "DRAFT" in messages[0][1]:
            return "standalone_draft"
        else:
            return "thread_no_draft"
    elif len(messages) > 1:
        if "DRAFT" in messages[-1][1]:
            return "thread_and_draft"
        else:
            return "thread_no_draft"   


# Function to format email information
def format_email_information(sender, recipient, subject, date, content):
    formatted_content = f"From: {sender}\nTo: {recipient}\nSubject: {subject}\nDate: {date}\n\n{content}"
    return formatted_content


# Function to get draft ID from Gmail API
def get_draft_id(message_id, headers):
    url = f'https://gmail.googleapis.com/gmail/v1/users/me/drafts'
    response = requests.get(url, headers=headers).json()

    for draft in response['drafts']:
        if draft['message']['id'] == message_id:
            return draft['id']

    return None

# Function to process messages and extract relevant information
def process_messages(messages, email_scenario, headers):
    sender = None
    recipient = None
    subject = None
    user_instructions = None
    contents = []
    message_dates = {}

    for idx, message_data in enumerate(messages):
        message_id, message_labels = message_data
        message_information = get_message_data(message_id, headers)

        # Assign sender, recipient, and subject for all email scenarios
        if idx == 0:
            sender = message_information["sender"]
            recipient = message_information["recipient"]
            subject = message_information["subject"]

        formatted_content = f"From: {message_information['sender']}\nTo: {message_information['recipient']}\nSubject: {message_information['subject']}\nDate: {message_information['date']}\n\n{message_information['content']}"

        if (email_scenario == "thread_and_draft" or email_scenario == "standalone_draft") and idx == len(messages) - 1:
            user_instructions = formatted_content
        else:
            contents.append(formatted_content)
        
        # Store the date and message id in the message_dates dict
        message_dates[message_id] = parse(message_information["date"])

    # Find the last non-draft message in the messages list
    last_non_draft_message = None
    if email_scenario != "standalone_draft":
        for message_data in reversed(messages):
            message_id, message_labels = message_data
            if "DRAFT" not in message_labels:
                last_non_draft_message = message_data
                break

    if last_non_draft_message is None and email_scenario != "standalone_draft":
        raise ValueError("No non-draft message found in the thread")

    # Extract the message ID and date of the last non-draft message
    most_recent_message_id = last_non_draft_message[0] if last_non_draft_message else None
    most_recent_date = message_dates[most_recent_message_id] if last_non_draft_message else None

    draft_id = None
    if email_scenario == "thread_and_draft" or email_scenario == "standalone_draft":
        draft_message_id = messages[-1][0]
        draft_id = get_draft_id(draft_message_id, headers)

    return sender, recipient, subject, contents, user_instructions, most_recent_message_id, most_recent_date, draft_id


# Function to print debugging information in pipedream logs
def print_debug_info(email_type, message_id, thread_id, sender, recipient, subject, contents, user_instructions, draft_id):
    print("MESSAGE PROCESSING DEBUGGING INFO:")
    print(f"Message ID: {message_id}")
    print(f"Message ID: {message_id}")
    if email_type == "existing thread":
        print(f"Sender: {sender if sender else 'Not available'}")
        print(f"Recipient: {recipient if recipient else 'Not available'}")
        print(f"Subject: {subject if subject else 'Not available'}")
    elif email_type == "new draft":
        print(f"Sender: {sender if sender else 'Not available'}")
        print(f"Recipient: {recipient if recipient else 'Not set'}")
        print(f"Subject: {subject if subject else 'Not set'}")
    print(f"Contents: {contents}")
    print(f"User Instructions: {user_instructions}")  
    print(f"Draft ID: {draft_id}")


 # Main handler function   
def handler(pd: "pipedream"):
    try:
        print(f"DEBUG: pd.steps['trigger']['event']: {pd.steps['trigger']['event']}")

        message_id = pd.steps["trigger"]["event"]["messages"][0]["id"]
        thread_id = pd.steps["trigger"]["event"]["messages"][0]["threadId"]

        token = f'{pd.inputs["gmail_custom_oauth"]["$auth"]["oauth_access_token"]}'
        authorization = f'Bearer {token}'
        headers = {"Authorization": authorization}

        messages = get_thread_messages(thread_id, headers)
        print(f"DEBUG: messages: {messages}")  # Added print statement

        email_scenario = determine_email_scenario(messages)

        sender, recipient, subject, contents, user_instructions, most_recent_message_id, most_recent_date, draft_id = process_messages(messages, email_scenario, headers)

        print_debug_info(email_scenario, message_id, thread_id, sender, recipient, subject, contents, user_instructions, draft_id)

        # Export variables
        pd.export("message_id", message_id)
        pd.export("thread_id", thread_id)
        pd.export("sender", sender)
        pd.export("recipient", recipient)
        pd.export("subject", subject)
        pd.export("contents", contents)
        pd.export("user_instructions", user_instructions)
        pd.export("email_type", email_scenario)
        pd.export("most_recent_message_id", most_recent_message_id)
        if most_recent_date is not None:
            pd.export("most_recent_date", most_recent_date.isoformat())
        else:
            pd.export("most_recent_date", None)
        pd.export("draft_id", draft_id) #if existing draft, existing 

    except KeyError as error:
        import traceback
        print(f"An error occurred: {error}")
        print("Traceback details:")
        traceback.print_exc()
        print(f"Entire pd.steps['trigger']['event'] dictionary: {pd.steps['trigger']['event']}")
        return pd.flow.exit(f"Error: {error}")

    except (ValueError, requests.HTTPError) as error:
        print(f"An error occurred: {error}")
        return pd.flow.exit(f"Error: {error}")