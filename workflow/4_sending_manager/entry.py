from email.message import EmailMessage
import base64
import requests
from email.parser import BytesParser


class EmailManager:
    def __init__(self, pd, sending_manager_config):
        print("Initializing EmailManager...")
        self.pd = pd
        self.sending_email_address = sending_manager_config["sending_email_address"]
        self.whitelisted_domains = sending_manager_config["whitelisted_domains"]
        self.draft_or_autosend = sending_manager_config["draft_or_autosend"]
        self.headers = {
            "Authorization": f'Bearer {pd.inputs["gmail_custom_oauth"]["$auth"]["oauth_access_token"]}',
            "Content-Type": "application/json"
        }

    def is_domain_whitelisted(self, email_address):
        if self.whitelisted_domains["enabled"]:
            domain = email_address.split('@')[-1].lower()
            return domain in self.whitelisted_domains["domains"]
        return True  # If whitelisting is disabled, allow all domains

    def handle_email(self, to, subject, content, thread_id, message_id):
        if self.draft_or_autosend == 0:
            # Create draft logic
            self.create_draft_existing_thread(to, subject, content, thread_id, message_id)
        else:
            # Send email logic
            self.send_email(to, subject, content, thread_id, message_id)

    def create_draft_existing_thread(self, to, subject, content, thread_id, message_id):
    # Construct the email message
        message = EmailMessage()
        message.set_content(content, subtype="html")
        message["To"] = to
        message["From"] = self.sending_email_address
        message["Subject"] = subject
        message["In-Reply-To"] = message_id
        message["References"] = message_id
        raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode("utf-8")

        # Create the draft with the correct headers for threading
        url = 'https://gmail.googleapis.com/gmail/v1/users/me/drafts'
        payload = {
            "message": {
                "raw": raw_message,
                "threadId": thread_id,
                "headers": [
                    {"name": "In-Reply-To", "value": message_id},
                    {"name": "References", "value": message_id}
                ]
            }
        }
        response = requests.post(url, headers=self.headers, json=payload)
        print(f"create_draft_existing_thread() response: {response.json()}")
        return response

    def send_email(self, to, subject, content, thread_id, message_id):
        print("Preparing to send email...")
        message = EmailMessage()
        message.set_content(content, subtype="html")
        message["To"] = to
        message["From"] = self.sending_email_address
        message["Subject"] = subject
        message["In-Reply-To"] = message_id
        message["References"] = message_id
        raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode("utf-8")
        self._send(raw_message, thread_id)

    def get_original_email(self, message_id):
        print("Retrieving original email...")
        url = f"https://gmail.googleapis.com/gmail/v1/users/me/messages/{message_id}?format=raw"
        response = requests.get(url, headers=self.headers)
        print(f"get_original_email response: {response}")
        if response.status_code != 200:
            raise Exception(f"Error occurred while retrieving the email. Status code: {response.status_code}")
        return response.json()['raw']

    def forward_email(self, message_id, to_email):
        print("Forwarding email...")
        raw_message = self.get_original_email(message_id)
        decoded_message = base64.urlsafe_b64decode(raw_message.encode('ASCII'))
        
        # Parse the MIME message
        email_message = BytesParser().parsebytes(decoded_message)
        
        # Initialize an empty string to hold the plain text parts
        plain_text_content = ""
        
        # Iterate over all parts of the email
        for part in email_message.walk():
            # Check if the part is a text part and is plain text
            if part.get_content_maintype() == 'text' and part.get_content_subtype() == 'plain':
                # Decode the part's payload
                payload = part.get_payload(decode=True)
                charset = part.get_content_charset() or 'utf-8'
                text = payload.decode(charset)
                plain_text_content += text + "\n\n"
        
        # Create the full content with the forwarding message
        notification = "A review of the original thread is required for full context and any possible attachments.\n\n"
        forwarding_message = f"---------- Forwarded message ---------\nFrom: {email_message['From']}\nDate: {email_message['Date']}\nSubject: {email_message['Subject']}\n\n"
        full_content = notification + forwarding_message + plain_text_content.strip()
        
        # Create a new EmailMessage object for the forwarded email
        forwarded_email = EmailMessage()
        forwarded_email.set_content(full_content)
        forwarded_email['To'] = to_email
        forwarded_email['From'] = self.sending_email_address
        forwarded_email['Subject'] = f"Fwd: {email_message['Subject']}"
        
        # Re-encode the modified email
        raw_forwarded_message = base64.urlsafe_b64encode(forwarded_email.as_bytes()).decode('utf-8')
        
        # Send the modified email
        self._send(raw_forwarded_message, email_message['threadId'])

    def _send(self, raw_message, thread_id):
        print("Sending email...")
        url = 'https://gmail.googleapis.com/gmail/v1/users/me/messages/send'
        payload = {"raw": raw_message, "threadId": thread_id}
        response = requests.post(url, headers=self.headers, json=payload)
        if response.status_code != 200:
            raise Exception(f"Error occurred while sending the email. Status code: {response.status_code}")
        print(f"Email sent. Status code: {response.status_code}")
        self.pd.export("email_send_status_code", response.status_code)

# Existing function to retrieve the IMAP message ID
def get_imap_message_id(headers, latest_message_id):
    print("Retrieving IMAP message ID...")
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

def handler(pd: "pipedream"):
    print("Starting handler...")
    sending_manager_config = pd.steps["workflow_config"]["sending_manager_config"]
    email_manager = EmailManager(pd, sending_manager_config)
    
    try:
        # Define a list of whitelisted domains. If the list is empty, all domains are allowed.
        whitelisted_domains = ["makebttr.com", "jdietle.me"]
        
        sensitivity_result = pd.steps["semantic_routers"]["sensitivity result:"]["isSensitive"]
        print(f"Sensitivity result: {sensitivity_result}")
        subject = pd.steps["parse_thread"]["subject"]
        thread_id = pd.steps["parse_thread"]["thread_id"]
        most_recent_sender = pd.steps["parse_thread"]["most_recent_sender"]

        # Perform domain check only if whitelisted domains are defined
        if whitelisted_domains:
            print("Checking recipient domain...")
            recipient_domain = most_recent_sender.split('@')[-1].lower()
            if recipient_domain not in whitelisted_domains:
                print(f"Recipient domain '{recipient_domain}' is not allowed. Exiting workflow.")
                pd.export("email_status", f"Recipient domain '{recipient_domain}' is not allowed.")
                return  # Exit the handler early

        if sensitivity_result == 1:
            # Forward the original email to the stakeholder
            print("Forwarding original email to stakeholder...")
            original_message_id = pd.steps["parse_thread"]["message_id"]
            email_manager.forward_email(original_message_id, "jacob@jdietle.me")
            return pd.flow.exit("Sensitive Thread. Skipping Hubspot & Forwarding")
        else:
            print("Checking draft or autosend setting...")
            if sending_manager_config["draft_or_autosend"] == 0:
                print("Drafting email...")
                context_block = pd.steps["reply_drafter_and_assembler"]["Context Block Email: "]
                if isinstance(context_block, list):
                    context_block = '\n'.join(context_block)
                message_id = get_imap_message_id(email_manager.headers, pd.steps["parse_thread"]["message_id"])
                email_manager.create_draft_existing_thread(most_recent_sender, subject, context_block, thread_id, message_id)
            else:
                print("Sending email...")
                context_block = pd.steps["reply_drafter_and_assembler"]["Context Block Email: "]
                if isinstance(context_block, list):
                    context_block = '\n'.join(context_block)
                message_id = get_imap_message_id(email_manager.headers, pd.steps["parse_thread"]["message_id"])
                email_manager.send_email(most_recent_sender, subject, context_block, thread_id, message_id)
    except Exception as e:
        print(f"An error occurred: {str(e)}")
        pd.export("email_status", f"Error: {str(e)}")
