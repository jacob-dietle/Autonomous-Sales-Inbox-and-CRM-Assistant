import requests
import json

def handler(pd: "pipedream"):
    # Get the message_id from the previous step
    message_id = pd.steps["trigger"]["event"]["messages"][0]["id"]
    
    # Set the label ID to add
    to_add_label_id = "Label_###################" # You'll need to go configure this yourself.You can find the label ID in Gmail and replace this value. You can use the Gmail API Explore to do so easily https://developers.google.com/gmail/api/reference/rest/v1/users.labels/get


    # Set up the Gmail API request headers and payload for adding the label
    headers_gmail = {
        "Authorization": f'Bearer {pd.inputs["gmail_custom_oauth"]["$auth"]["oauth_access_token"]}',
        "Content-Type": "application/json"
    }

    payload_add_gmail = {
        "addLabelIds": [to_add_label_id]
    }

    # Modify the message in Gmail by adding the new label
    url_gmail = f'https://gmail.googleapis.com/gmail/v1/users/me/messages/{message_id}/modify'
    add_response = requests.post(url_gmail, headers=headers_gmail, data=json.dumps(payload_add_gmail))

    # Log the response from the Gmail API
    if add_response.status_code == 200:
        print(f'Added label with ID "{to_add_label_id}" to message "{message_id}".')
        print(f'Gmail API response: {add_response.json()}')
    else:
        print(f'An error occurred while adding the label for message "{message_id}".')
        print(f'Status code: {add_response.status_code}')
        print(f'Error message: {add_response.text}')