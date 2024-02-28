import base64
import re
import requests
from bs4 import BeautifulSoup
from dateutil.parser import parse


class EmailParser:
    def __init__(self, payload):
        self.payload = payload
        print("EmailParser initialized with payload.")

    def extract_details(self):
        try:
            sender_value = self.get_header_value("From")
            recipient_value = self.get_header_value("To")
            subject_value = self.get_header_value("Subject")
            date_value = self.get_header_value("Date")

            sender = self.extract_email_address(sender_value) if sender_value else None
            recipients = [self.extract_email_address(email) for email in recipient_value.split(',')] if recipient_value else None
            subject = subject_value if subject_value else None
            date = parse(date_value) if date_value else None

            return sender, recipients, subject, date
        except Exception as e:
            print(f"Error extracting email details: {e}")
            return None, None, None, None

    def process_content(self, content_type, raw_content):
        try:
            if content_type == "text/html":
                cleaned_content = self.remove_html(raw_content)
            else:
                cleaned_content = raw_content

            cleaned_content = self.remove_quoted_content(cleaned_content)
            return cleaned_content.strip()
        except Exception as e:
            print(f"Error processing email content: {e}")
            return ""

    def remove_html(self, html_content):
        try:
            soup = BeautifulSoup(html_content, "html.parser")
            return soup.get_text()
        except Exception as e:
            print(f"Error removing HTML content: {e}")
            return html_content

    def remove_quoted_content(self, content, content_type='text/plain'):
        if content_type == 'text/plain':
            return self.remove_quoted_content_plain(content)
        elif content_type == 'text/html':
            return self.remove_quoted_content_html(content)
        else:
            raise ValueError('Unsupported content type: ' + content_type)

    def remove_quoted_content_plain(self, content):
        # Define regex patterns for quoted lines and splitter patterns
        quoted_line_pattern = re.compile(r'^\s*>+.*$', re.MULTILINE)
        splitter_pattern = re.compile(
            r'^\s*[-]+[ ]*Forwarded message[ ]*[-]+\s*$|'
            r'^\s*[-]+[ ]*Original Message[ ]*[-]+\s*$|'
            r'^\s*On.*wrote:$|'
            r'^\s*From:.*$|'
            r'^\s*Sent:.*$|'
            r'^\s*To:.*$|'
            r'^\s*Subject:.*$', re.MULTILINE | re.IGNORECASE)

        # Remove quoted lines
        content = re.sub(quoted_line_pattern, '', content)
        # Remove splitter patterns
        content = re.sub(splitter_pattern, '', content)
        # Clean up the content
        content = self.clean_up_content(content)
        return content

    def remove_quoted_content_html(self, content):
        # Parse the HTML content with BeautifulSoup
        soup = BeautifulSoup(content, 'html.parser')
        # Remove blockquote tags and other common quoting structures
        for blockquote in soup.find_all('blockquote'):
            blockquote.decompose()
        # Convert back to string and clean up the content
        content = str(soup)
        content = self.clean_up_content(content)
        return content

    def clean_up_content(self, content):
        # Trim excessive whitespace and newlines
        content = re.sub(r'\n\s*\n', '\n\n', content)  # Reduce multiple newlines to double newlines
        content = content.strip()  # Remove leading and trailing whitespace
        return content

    def get_header_value(self, header_name):
        try:
            for header in self.payload.get("headers", []):
                if header["name"].lower() == header_name.lower():
                    return header["value"]
            return None
        except Exception as e:
            print(f"Error getting header value for {header_name}: {e}")
            return None

    def extract_email_address(self, string):
        try:
            email_regex = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
            result = re.search(email_regex, string)
            return result.group(0) if result else ""
        except Exception as e:
            print(f"Error extracting email address from string: {e}")
            return ""

class GmailAPI:
    def __init__(self, headers):
        self.headers = headers
        print("GmailAPI initialized with headers.")

    def get_thread_messages(self, thread_id):
        try:
            url = f"https://gmail.googleapis.com/gmail/v1/users/me/threads/{thread_id}"
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()  # Will raise an HTTPError if the HTTP request returned an unsuccessful status code
            messages = response.json().get("messages", [])
            return [(message["id"], message.get("labelIds", [])) for message in messages]
        except requests.HTTPError as e:
            print(f"HTTPError while getting thread messages: {e}")
            raise
        except Exception as e:
            print(f"Error while getting thread messages: {e}")
            raise

    def get_message_data(self, message_id):
        try:
            url = f"https://gmail.googleapis.com/gmail/v1/users/me/messages/{message_id}"
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            message = response.json()
            message_payload = message.get('payload', {})
            content_type = message_payload.get('mimeType', '')

            # Check if the content type is 'multipart/report' which is used for DSNs
            if content_type == 'multipart/report':
                print(f"Message ID {message_id} is a delivery status notification. Skipping.")
                return None

            raw_content = None
            if 'parts' in message_payload:
                for part in message_payload['parts']:
                    if part['mimeType'] in ['text/plain', 'text/html']:
                        content_type = part['mimeType']
                        raw_content = base64.urlsafe_b64decode(part['body']['data']).decode("utf-8")
                        break
            elif 'mimeType' in message_payload and 'body' in message_payload and 'data' in message_payload['body']:
                content_type = message_payload.get('mimeType', 'text/plain')
                raw_content = base64.urlsafe_b64decode(message_payload['body']['data']).decode("utf-8")

            if raw_content is None:
                print(f"No content found for message ID {message_id}. Skipping.")
                return None

            email_parser = EmailParser({'headers': message_payload.get('headers', [])})
            processed_content = email_parser.process_content(content_type, raw_content)

            return {
                'sender': email_parser.extract_email_address(email_parser.get_header_value('From')),
                'recipients': [email_parser.extract_email_address(addr) for addr in email_parser.get_header_value('To').split(',')],
                'subject': email_parser.get_header_value('Subject'),
                'date': email_parser.get_header_value('Date'),
                'content': processed_content
            }
        except requests.HTTPError as e:
            print(f"HTTPError while getting message data: {e}")
            raise
        except Exception as e:
            print(f"Error while getting message data: {e}")
            raise

    def format_email_information(self, sender, recipient, subject, date, content):
        try:
            formatted_content = f"From: {sender}\nTo: {recipient}\nSubject: {subject}\nDate: {date}\n\n{content}"
            return formatted_content
        except Exception as e:
            print(f"Error while formatting email information: {e}")
            raise

    def process_messages(self, messages):
        all_senders = set()
        all_recipients = set()
        all_subjects = set()
        contents = []

        # Sort messages by date
        messages.sort(key=lambda msg: parse(self.get_message_data(msg[0])["date"]), reverse=True)

        most_recent_sender = None
        for idx, message_data in enumerate(messages):
            message_id, message_labels = message_data
            message_information = self.get_message_data(message_id)
            if message_information is None:
                continue  # Skip this message and continue with the next one
            sender = message_information["sender"]
            recipients = message_information["recipients"]
            subject = message_information["subject"]
            all_senders.add(sender)
            all_recipients.update(recipients)
            all_subjects.add(subject)
            cleaned_content = message_information["content"]
            content_processor = ContentProcessor(cleaned_content)
            cleaned_content = content_processor.remove_signatures()
            cleaned_content = content_processor.normalize_content()
            formatted_message = self.format_email_information(
                sender,
                recipients,
                subject,
                message_information["date"],
                cleaned_content
            )
            contents.append(formatted_message)

            # Update the most recent sender
            if idx == 0:  # This is the most recent message
                most_recent_sender = sender

        return most_recent_sender, all_senders, all_recipients, all_subjects, contents

    def print_debug_info(self, message_id, thread_id, all_senders, all_recipients, all_subjects, contents):
        print("MESSAGE PROCESSING DEBUGGING INFO:")
        print(f"Message ID: {message_id}")
        print(f"Thread ID: {thread_id}")
        print(f"All Senders: {', '.join(all_senders)}")
        print(f"All Recipients: {', '.join(all_recipients)}")
        print(f"All Subjects: {', '.join(all_subjects)}")
        print(f"Contents: {contents}")

class ContentProcessor:
    def __init__(self, content):
        self.content = content
        print("ContentProcessor initialized with content.")

    def remove_signatures(self):
        # Assuming signatures are separated by "--" or similar markers
        signature_pattern = re.compile(r'(--\s*\n.*$)', re.MULTILINE | re.DOTALL)
        self.content, _ = re.subn(signature_pattern, '', self.content)
        return self.content

    def normalize_content(self):
        # Normalize whitespace and line breaks
        self.content = re.sub(r'\r\n', '\n', self.content)  # Normalize line breaks
        self.content = re.sub(r'[ \t]+', ' ', self.content)  # Normalize spaces
        self.content = re.sub(r'\n{3,}', '\n\n', self.content)  # Normalize multiple line breaks
        return self.content

    def extract_reply_body(self):
        # Use the EmailParser's method to remove quoted content
        # Since ContentProcessor does not handle headers, we should not attempt to extract headers here
        # Instead, pass the content directly to the EmailParser
        email_parser = EmailParser({'body': {'data': self.content}})
        content_type = 'text/html' if '<html>' in self.content.lower() else 'text/plain'
        self.content = email_parser.remove_quoted_content(self.content, content_type)
        return self.content


def handler(pd: "pipedream"):
    try:
        # Step 1: Instantiate Classes
        token = f'{pd.inputs["gmail_custom_oauth"]["$auth"]["oauth_access_token"]}'
        authorization = f'Bearer {token}'
        headers = {"Authorization": authorization}
        gmail_api = GmailAPI(headers)

        # Step 2: Extract Email Details
        message_id = pd.steps["trigger"]["event"]["id"]
        thread_id = pd.steps["trigger"]["event"]["threadId"]
        payload = pd.steps["trigger"]["event"]["payload"]
        email_parser = EmailParser(payload)
        sender, recipients, subject, date = email_parser.extract_details()

        if None in (sender, recipients, subject, date):
            print("One or more essential details are missing from the email. Skipping this message.")
            return  # Skip to the next message

        # Step 3: Fetch Thread Messages
        messages = gmail_api.get_thread_messages(thread_id)

        # Step 4: Process Each Message
        contents = []
        for message_data in messages:
            message_id, _ = message_data
            message_info = gmail_api.get_message_data(message_id)
            if message_info is None:
                continue  # Skip this message and continue with the next one
            content_processor = ContentProcessor(message_info["content"])
            processed_content = content_processor.remove_signatures()
            processed_content = content_processor.normalize_content()
            reply_body = content_processor.extract_reply_body()
            formatted_message = gmail_api.format_email_information(
                sender, recipients, subject, date, reply_body
            )
            contents.append(formatted_message)

        # Step 5: Compile Results
        most_recent_sender = sender if sender else recipients[0]

        # Step 6: Export Results
        pd.export("most_recent_sender", most_recent_sender)
        pd.export("message_id", message_id)
        pd.export("thread_id", thread_id)
        pd.export("sender", sender)
        pd.export("recipient", recipients[0] if recipients else None)
        pd.export("subject", subject)
        pd.export("contents", contents)

    except KeyError as error:
        print(f"An error occurred: {error}")
        return pd.flow.exit(f"Error: {error}")
    
    except (ValueError, requests.HTTPError) as error:
        print(f"An error occurred: {error}")
        return pd.flow.exit(f"Error: {error}")