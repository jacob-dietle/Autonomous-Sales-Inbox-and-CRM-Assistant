import requests
import json


def create_label(pd, label_name, parent_label_id=None):
    headers_gmail = {
        "Authorization": f'Bearer {pd.inputs["gmail_custom_oauth"]["$auth"]["oauth_access_token"]}',
        "Content-Type": "application/json"
    }
    payload_create_label = {
        "name": label_name,
        "labelListVisibility": "labelShow",
        "messageListVisibility": "show",
        "parent": parent_label_id
    }
    url_gmail = 'https://gmail.googleapis.com/gmail/v1/users/me/labels'
    create_response = requests.post(url_gmail, headers=headers_gmail, data=json.dumps(payload_create_label))
    if create_response.status_code == 200:
        label_info = create_response.json()
        print(f'Created label with name "{label_name}" and ID "{label_info.get('id')}".')
        return label_info
    else:
        print(f'An error occurred while creating the label "{label_name}".')
        print(f'Status code: {create_response.status_code}')
        print(f'Error message: {create_response.text}')
        return None
    
def create_parent_labels(pd, label_categories):
    parent_labels = {}
    for category in label_categories:
        parent_label_info = create_label(pd, category)
        if parent_label_info:
            parent_labels[category] = parent_label_info['id']
        else:
            print(f"Failed to create parent label for category '{category}'")
    return parent_labels

def create_and_organize_labels(pd, label_categories, parent_labels):
    organized_labels = {category: {} for category in label_categories}

    for category, sub_labels in label_categories.items():
        parent_label_id = parent_labels.get(category)
        for sub_label_name in sub_labels:
            label_info = create_label(pd, sub_label_name, parent_label_id)
            if label_info:
                organized_labels[category][sub_label_name] = label_info['id']
            else:
                print(f"Failed to create sub label '{sub_label_name}' under parent label '{category}'")

    return organized_labels

def handler(pd: "pipedream"):
    label_categories = {
        "EmailClassification": ["NOT_FROM_REAL_PERSON"],
        "EmailRelevancy": ["NON_PROSPECTING_RELATED"],
        "EmailSentimentAndFunnelStage": ["LEAD", "INTERESTED", "QUALIFIED_TO_BUY", "APPOINTMENT_SCHEDULED", "PRESENTATION_SCHEDULED", "DECISION_MAKER_BOUGHT_IN", "CONTRACT_SENT", "CLOSED_WON"],
        "EmailScenario": ["COLD_OUTBOUND_REPLY", "WARM_INTRO_REPLY", "ORGANIC_INBOUND", "ICP 1: Large Commercial Real Estate Firms:", "ICP 2: Property Management Companies", "ICP_OTHER"]
    }

    # Create parent labels
    parent_labels = create_parent_labels(pd, label_categories)

    # Create sub labels and organize them
    organized_labels = create_and_organize_labels(pd, label_categories, parent_labels)

    # Export the organized labels as a JSON object
    pd.export("organized_labels", organized_labels)

