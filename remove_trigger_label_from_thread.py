import requests
import json

def handler(pd: "pipedream"):
    # Get the thread_id from the trigger
    thread_id = pd.steps["trigger"]["event"]["messages"][0]["threadId"]
    
    # Set the label ID to remove
    to_remove_label_id = "Label_#####################" # You'll need to go find the label ID in Gmail and replace this value. You can use the Gmail API Explore to do so easily https://developers.google.com/gmail/api/reference/rest/v1/users.labels/get

    # Set up the Gmail API request headers and payload for removing the label
    headers_gmail = {
        "Authorization": f'Bearer {pd.inputs["gmail_custom_oauth"]["$auth"]["oauth_access_token"]}',
        "Content-Type": "application/json"
    }

    payload_remove_gmail = {
        "removeLabelIds": [to_remove_label_id]
    }

    # Get all messages in the thread
    url_thread = f'https://gmail.googleapis.com/gmail/v1/users/me/threads/{thread_id}'
    thread_response = requests.get(url_thread, headers=headers_gmail)
    messages = thread_response.json()["messages"]

    # Modify the messages in Gmail by removing the old label
    for message in messages:
        message_id = message['id']
        url_gmail = f'https://gmail.googleapis.com/gmail/v1/users/me/messages/{message_id}/modify'
        remove_response = requests.post(url_gmail, headers=headers_gmail, data=json.dumps(payload_remove_gmail))

        # Log the response from the Gmail API
        if remove_response.status_code == 200:
            print(f'Removed label with ID "{to_remove_label_id}" from message "{message_id}".')
            print(f'Gmail API response: {remove_response.json()}')
        else:
            print(f'An error occurred while removing the label for message "{message_id}".')
            print(f'Status code: {remove_response.status_code}')
            print(f'Error message: {remove_response.text}')