# packages for interacting with OpenAI API and token counting
from simpleaichat import AsyncAIChat, AIChat
from pydantic import BaseModel, Field
import asyncio
import tiktoken
# packages for interacting with Gmail API for edge case handling 
import requests
import base64
from email.message import EmailMessage


# Classification Function Call and Ruleset. Solves for "from a real person vs spam"

class EmailClassification(BaseModel):
    """
    This class represents the classification of an email, determining whether it requires a response.
    """
    requiresResponse: int = Field(
        description="Can either be 0 or 1. 0 if the email is a notification, a billing reminder, a social media update, spam, or some other sort of email that a person would not generally respond to. 1 if the email is from a real person with a genuine inquiry that requires some sort of response. Specific notification exceptions for  [example@example.com], as [reasoning].",
        ge=0, le=1
    )

# Sales & Lead Gen Relevancy Function Call and Ruleset. Solves for "would an sdr/sales team member be interested in replying to this email?"

class EmailRelevancy(BaseModel):
    """
    This class represents the relevancy of an email to the Organization inbox.
    """
    isRelevant: int = Field(
        description="Can either be 0, 1 or 2 . 0 if the email is not relevant to the Organization inbox, 1 if the email is relevant or 2 if the email is relevant but sensitive and requires stakeholder attention. The rulset for relevancy is any emails related to lead generation, service inquiries, sales call scheduling, inquries from current or potential clients or any sales and or Organizationanic inbound. Recruiting, inbound sales emails from other companies, or current client work or newsletters or literally anything not regarding prospecting is irrelevant. Emails that are relevant but sensitive would be any regarding pricing, contract negotiations, client complaints, or basically any email where an sdr would pass off the email chain to legal or high executives.",
        ge=0, le=1
    )

# Sensitivity Function Call and Ruleset. Solves for "ok this is from a real person and relevant to sales, but is this above my pay grade i.e does this require a stakeholder who has higher/broader context of this business than me as an sdr? "

class EmailSensitivity(BaseModel):
    """
    This class represents the sensitivity of an email to the Organization inbox.
    """
    isSensitive: int = Field(
        description="Can either be 0 or 1. 0 if the email is not sensitive, 1 if the email is sensitive and requires stakeholder attention. Sensitive emails include any regarding pricing, requests for a contract, contract negotiations, client complaints, project scoping, or basically any email where an SDR would pass off the email chain to legal or high executives.",
        ge=0, le=1
    )

# Sentiment and Funnel Classification. Solves for "how does this person sound and at what point of the funnel is being reflected in the emails. Set to match deal funnel stages in crm to move leads along automatically but not irregularly."

class EmailSentimentAndFunnelStage(BaseModel):
    """
    This class represents the combined sentiment and funnel stage labeling of an email.
    """
    label: str = Field(
        description="The label assigned to the email based on sentiment and funnel stage. Can be: not interested, interested, lead, appointment scheduled, qualified to buy, presentation scheduled, decision maker bought in, contract sent, closed won."
    )

# Thread Scenario and ICP Category Function Call and Ruleset. Solves for light attribution and pattern matching ICP based on content of thread.

class EmailScenario(BaseModel):
    """
    This class represents the scenario or context of the email, categorizing it based on the inquiry type,
    sender category, and specific inquiry details.
    """
    inquiry_type: str = Field(description="Type of inquiry. Can include: Organizationanic inbound, cold email outbound reply, warm intro reply.")
    sender_category: str = Field(description="Category of sender. Can include: ICP 1: Silent Giant, ICP 2: High Growth Innovation, Other ICP Type.", default=None)


class TokenCounter:
    def __init__(self, pd):
        self.pd = pd
        self.encoding = tiktoken.get_encoding("cl100k_base")

    def count_tokens(self, text):
        return len(self.encoding.encode(text))

    def count_and_export_tokens(self, input_text, output_result, export_name):
        # Count tokens in the input and output
        input_token_count = self.count_tokens(input_text)
        output_token_count = self.count_tokens(str(output_result))
        total_tokens = input_token_count + output_token_count

        # Export the total token count
        self.pd.export(export_name, total_tokens)

        # Return the total token count
        return total_tokens


class EmailHandler:
    def __init__(self, pd, config, assembled_prompts):
        self.pd = pd
        self.config = config
        self.assembled_prompts = assembled_prompts
        self.token_counter = TokenCounter(pd)
        self.token = f'{pd.inputs["openai"]["$auth"]["api_key"]}'
        self.authorization = f'Bearer {self.token}'
        self.headers = {"Authorization": self.authorization}
        self.ai_sync = AIChat(api_key=self.token, console=False, model="gpt-4-0125-preview", headers=self.headers, temperature=0.0)
        self.ai_async = AsyncAIChat(api_key=self.token, console=False, model="gpt-4-0125-preview", headers=self.headers, temperature=0.0)
        self.sender = pd.steps["parse_thread"]["sender"]
        self.recipient = pd.steps["parse_thread"]["recipient"]
        self.subject = pd.steps["parse_thread"]["subject"]
        self.content = pd.steps["parse_thread"]["contents"]
        self.input_data = f"Sender: {self.sender}. Recipient: {self.recipient}. Subject: {self.subject}. Content: {self.content}."

    def classify_email(self):
        print("Classifying email...")
        result = self.ai_sync(self.input_data, system=self.assembled_prompts["email_classification"], output_schema=EmailClassification)
        print(f"Email classified. Result: {result}")
        self.token_counter.count_and_export_tokens(self.input_data, str(result), "classify_email_tokens")
        return result


    def check_relevancy(self):
        print("Checking relevancy...")
        result = self.ai_sync(self.input_data, system=self.assembled_prompts["email_relevancy"], output_schema=EmailRelevancy)
        print(f"Email Relevancy Result: {result}")
        self.token_counter.count_and_export_tokens(self.input_data, str(result), "check_relevancy_tokens")
        return result 
    
    def check_sensitivity(self, classification_result, relevancy_result):
        # Generate the sensitivity prompt
        system_prompt_sensitivity = self.assembled_prompts["email_sensitivity"]
        print("Checking sensitivity...")
        self.sensitivity_result = self.ai_sync(
            self.input_data, system=system_prompt_sensitivity, output_schema=EmailSensitivity
        )
        print(f"Email Sensitivity Result: {self.sensitivity_result}")
        self.token_counter.count_and_export_tokens(
            self.input_data, str(self.sensitivity_result), "check_sensitivity_tokens"
        )
        return self.sensitivity_result

    def classify_sentiment_and_funnel_stage(self):
        # Now use the prompt to classify the sentiment and funnel stage
        result = self.ai_sync(self.input_data, system=self.assembled_prompts["email_sentiment_and_funnel_stage"], output_schema=EmailSentimentAndFunnelStage)
        print(f"Sentiment and funnel stage classified. Result: {result}")
        self.token_counter.count_and_export_tokens(self.input_data, str(result), "classify_sentiment_and_funnel_stage_tokens")
        return result

    def apply_label(self, label_category, label_name, thread_id):
        # Access the specific category from the email_labels configuration
        category_labels = self.config["email_labels"].get(label_category, {})
        
        # Fetch the label ID using the label name. Since label_id is directly the string we need, no further .get("id") is required.
        label_id = category_labels.get(label_name.upper())  # Removed the erroneous .get("id")
        
        if label_id:
            apply_label_instance = ApplyLabel(self.pd, [label_id])
            apply_label_instance.apply_labels(thread_id)
        else:            
            print(f"Label ID for {label_name} in category {label_category} not found. Skipping label application.")

    def handle_async_tasks(self):
        # Lazy initialization of the scenario prompt
        system_prompt_scenario = self.assembled_prompts["email_scenario"]
        system_prompt_sentiment_and_funnel_stage = self.assembled_prompts["email_sentiment_and_funnel_stage"]
        async def async_function():
            tasks = [
                self.ai_async(self.input_data, system=system_prompt_scenario, output_schema=EmailScenario),
                self.ai_async(self.input_data, system=system_prompt_sentiment_and_funnel_stage, output_schema=EmailSentimentAndFunnelStage)
            ]
            results = await asyncio.gather(*tasks)

            # Count and export tokens for each task
            for i, result in enumerate(results):
                self.token_counter.count_and_export_tokens(self.input_data, str(result), f"handle_async_tasks_tokens_{i}")

            return results

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        return loop.run_until_complete(async_function())


class ApplyLabel:
    def __init__(self, pd, label_ids):
        self.pd = pd
        self.label_ids = label_ids
        self.headers = {
            "Authorization": f'Bearer {self.pd.inputs["gmail_custom_oauth"]["$auth"]["oauth_access_token"]}',
            "Content-Type": "application/json"
        }

    def get_current_labels(self, thread_id):
        url = f'https://gmail.googleapis.com/gmail/v1/users/me/threads/{thread_id}'
        response = requests.get(url, headers=self.headers)
        if response.status_code == 200:
            thread_data = response.json()
            current_labels = [message['labelIds'] for message in thread_data['messages']]
            # Flatten the list of label IDs and remove duplicates
            return set([label for sublist in current_labels for label in sublist])
        else:
            print(f"Error fetching current labels: {response.text}")
            raise Exception(f"Error fetching current labels: {response.text}")    

    def apply_labels(self, thread_id):
        # Fetch current labels on the thread
        current_labels = self.get_current_labels(thread_id)
        print(f"current_labels: {current_labels}")

        # Filter out labels that already exist on the thread
        new_labels_to_add = [label_id for label_id in self.label_ids if label_id not in current_labels]

        # If there are no new labels to add, skip the API call
        if not new_labels_to_add:
            print("No new labels to add. Skipping label application.")
            return

        # Prepare the payload with the new labels to add
        payload = {
            "addLabelIds": new_labels_to_add
        }

        # Make the API call to modify the labels
        url = f'https://gmail.googleapis.com/gmail/v1/users/me/threads/{thread_id}/modify'
        response = requests.post(url, headers=self.headers, json=payload)
        if response.status_code == 200:
            print(f"Labels successfully applied to thread {thread_id}")
        else:
            print(f"Error applying labels: {response.text}")
            raise Exception(f"Error applying labels: {response.text}")


def handler(pd: "pipedream"):
    # import config
    semantic_routers_config = pd.steps["workflow_config"]["semantic_routers_config"]
    email_labels = semantic_routers_config["email_labels"]
    print("semantic_router_config", semantic_routers_config)
    assembled_prompts = pd.steps["workflow_config"]["assembled_prompts"]
    #setup handler and token count
    email_handler = EmailHandler(pd, semantic_routers_config, assembled_prompts)
    total_tokens = 0 

    # Perform the EmailClassification task and count tokens
    print("Starting Email Classification...")
    classification_result = email_handler.classify_email()
    pd.export("classification result:", classification_result)
    classify_email_tokens = email_handler.token_counter.count_and_export_tokens(email_handler.input_data, classification_result, "classify_email_tokens")
    total_tokens += classify_email_tokens

    # Dynamically determine the label for EmailClassification
    classification_label = "NOT_FROM_REAL_PERSON" if classification_result['requiresResponse'] == 0 else None
    if classification_label:
        print(f"Applying '{classification_label}' label and exiting workflow...")
        email_handler.apply_label("EmailClassification", classification_label, pd.steps["trigger"]["event"]["threadId"])
        pd.export("total_tokens", total_tokens)
        return pd.flow.exit('Email does not require a response. Exiting workflow.')

    # Perform the EmailRelevancy task and count tokens
    print("Starting Email Relevancy Check...")
    relevancy_result = email_handler.check_relevancy()
    pd.export("relevancy result:", relevancy_result)
    relevancy_tokens = email_handler.token_counter.count_and_export_tokens(email_handler.input_data, relevancy_result, "check_relevancy_tokens")
    total_tokens += relevancy_tokens

    # Dynamically determine the label for EmailRelevancy
    relevancy_label = "NON_PROSPECTING_RELATED" if relevancy_result['isRelevant'] == 0 else None
    if relevancy_label:
        print(f"Applying '{relevancy_label}' label and exiting workflow...")
        email_handler.apply_label("EmailRelevancy", relevancy_label, pd.steps["trigger"]["event"]["threadId"])
        pd.export("total_tokens", total_tokens)
        return pd.flow.exit('Email is not relevant. Exiting workflow.')

    # Perform the EmailSensitivity task using the results of the previous steps and count tokens
    print("Starting Email Sensitivity Check...")
    sensitivity_result = email_handler.check_sensitivity(classification_result, relevancy_result)
    pd.export("sensitivity result:", sensitivity_result)
    sensitivity_tokens = email_handler.token_counter.count_and_export_tokens(email_handler.input_data, sensitivity_result, "check_sensitivity_tokens")
    total_tokens += sensitivity_tokens  # Accumulate total tokens

    # Conditional logic based on sensitivity result
    if sensitivity_result['isSensitive'] == 1:
        # If email is sensitive then export result, which will be used in sending to just send notification to relevant stakeholder rather than generate a reply
        print("Email is sensitive. Skipping further classification.")
        pd.export("total_tokens", total_tokens)  # Export total tokens before exiting
        return 
    else:
        # Proceed with asynchronous tasks for non-sensitive emails
        print("Starting Asynchronous Tasks for Scenario and Sentiment & Funnel Stage...")
        scenario_result, sentiment_and_funnel_stage_result = email_handler.handle_async_tasks()

        # Count tokens for scenario and sentiment/funnel stage classification
        scenario_tokens = email_handler.token_counter.count_and_export_tokens(email_handler.input_data, scenario_result, "scenario_tokens")
        sentiment_and_funnel_stage_tokens = email_handler.token_counter.count_and_export_tokens(email_handler.input_data, sentiment_and_funnel_stage_result, "sentiment_and_funnel_stage_tokens")
        total_tokens += scenario_tokens + sentiment_and_funnel_stage_tokens  # Accumulate total tokens

        pd.export("Sentiment and Funnel Stage Result", sentiment_and_funnel_stage_result)
        pd.export("email_scenario_result", scenario_result)

    
    # Apply labels based on the scenario and sentiment/funnel stage results
    print("Applying labels based on Scenario and Sentiment & Funnel Stage results...")
    if scenario_result['inquiry_type']:
        email_handler.apply_label("EmailScenario", scenario_result['inquiry_type'], pd.steps["trigger"]["event"]["threadId"])
    if scenario_result['sender_category']:
        email_handler.apply_label("EmailScenario", scenario_result['sender_category'], pd.steps["trigger"]["event"]["threadId"])
    if sentiment_and_funnel_stage_result['label']:
        email_handler.apply_label("EmailSentimentAndFunnelStage", sentiment_and_funnel_stage_result['label'], pd.steps["trigger"]["event"]["threadId"])

    # Sum the total tokens used in each step
    print(f"Total Tokens Used: {total_tokens}")

    # Export the results for use in the next step
    pd.export("total_tokens", total_tokens)
