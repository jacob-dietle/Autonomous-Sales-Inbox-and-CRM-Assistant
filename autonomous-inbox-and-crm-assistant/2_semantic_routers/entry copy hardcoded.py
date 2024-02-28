# packages for interacting with OpenAI API and token counting
from simpleaichat import AsyncAIChat, AIChat
from pydantic import BaseModel, Field
import asyncio
import tiktoken
# packages for interacting with Gmail API for edge case handling 
import requests
import base64
from email.message import EmailMessage

# High Level Context

common_context =  """
You are monitoring an Organization's primary sales, lead generation and general inbound email account. You have one task as a part of a larger system
which will be described below. For context the larger system designed to provide an automated, intelligent solution for managing emails at the Organization. It is comprised of:
1. Email Classification (is this email from a real person or a notification/spam?)
2. Email Scenario Identification (what is the nature of the email? Who is it from? What is it about?)
3. Funnel Stage Classification (what stage of the sales funnel does this email seem like?)
4. Sensitivity Determination and Stakeholder Notification (if the email is from a real person, should a stakeholder handle it?)

Do your best to address the task below in the context of the larger system. Prioritize accuracy, and think quietly to yourself before responding.

YOUR ACTIONS MUST STRICTLY FOLLOW THE PROVIDED RULESETS IN EACH FUNCTION. IF YOU GENERATE ANYTHING OUTSIDE OF THE RULESET, YOU FAIL THE TEST.

You are responsible for the below task: 
"""


# Classification Function Call and Ruleset. Solves for "from a real person vs spam"

class EmailClassification(BaseModel):
    """
    This class represents the classification of an email, determining whether it requires a response.
    """
    requiresResponse: int = Field(
        description="Can either be 0 or 1. 0 if the email is a notification, a billing reminder, a social media update, spam, or some other sort of email that a person would not generally respond to. 1 if the email is from a real person with a genuine inquiry that requires some sort of response. Specific notification exceptions for  [example@example.com], as [reasoning].",
        ge=0, le=1
    )

system_prompt_classification = common_context + """
Function: Email Classification
Analyze the email and determine whether it requires a response or not.

Ruleset: 
- Can either be 0 or 1. 
- 0 if the email is a notification, a billing reminder, a social media update, spam, cold sales email or some other sort of email that a person would not generally respond to. 
- 1 if the email is from a real person with a genuine inquiry that requires some sort of response. Specific notification exceptions for  [example@example.com], as [reasoning].
"""


# Sales & Lead Gen Relevancy Function Call and Ruleset. Solves for "would an sdr/sales team member be interested in replying to this email?"

class EmailRelevancy(BaseModel):
    """
    This class represents the relevancy of an email to the Organization inbox.
    """
    isRelevant: int = Field(
        description="Can either be 0, 1 or 2 . 0 if the email is not relevant to the Organization inbox, 1 if the email is relevant or 2 if the email is relevant but sensitive and requires stakeholder attention. The rulset for relevancy is any emails related to lead generation, service inquiries, sales call scheduling, inquries from current or potential clients or any sales and or Organizationanic inbound. Recruiting, inbound sales emails from other companies, or current client work or newsletters or literally anything not regarding prospecting is irrelevant. Emails that are relevant but sensitive would be any regarding pricing, contract negotiations, client complaints, or basically any email where an sdr would pass off the email chain to legal or high executives.",
        ge=0, le=1
    )

system_prompt_relevancy = common_context + """
Function: Email Relevancy Classification
Analyze the email and determine whether it is relevant to the Organization inbox.

Ruleset: 
- Can either be 0 or 1. 
- 0 if the email is not relevant to the Organization prospecting inbox. For example, if the email is part of an ongoing chain that the inbox was cc'd on but does not require a response or action, is an inbound cold sales email, related to a current ongoing project, or company operations. Even if the sender sends a personalized cold outreach message, they are not relevant to this outbound sales system.
- 1 if the email is relevant to the Organization's sales and lead generation inbox. For example, if the email is a direct inquiry, a sales question, a lead trying to schedule a call, or requires some sort of action from the Organization inbox.
"""

# Sensitivity Function Call and Ruleset. Solves for "ok this is from a real person and relevant to sales, but is this above my pay grade i.e does this require a stakeholder who has higher/broader context of this business than me as an sdr? "

class EmailSensitivity(BaseModel):
    """
    This class represents the sensitivity of an email to the Organization inbox.
    """
    isSensitive: int = Field(
        description="Can either be 0 or 1. 0 if the email is not sensitive, 1 if the email is sensitive and requires stakeholder attention. Sensitive emails include any regarding pricing, requests for a contract, contract negotiations, client complaints, project scoping, or basically any email where an SDR would pass off the email chain to legal or high executives.",
        ge=0, le=1
    )

# Function to create the sensitivity prompt. Had to convert static string into function to pass in previous results 
def create_sensitivity_prompt(common_context, classification_result, relevancy_result):
    return f"""
    {common_context}
    The email has been classified with a response requirement of {classification_result['requiresResponse']}
    and a relevancy determination of {relevancy_result['isRelevant']}.
    
    Function: Email Sensitivity Classification
    Analyze the email and determine whether it is sensitive and requires stakeholder attention. Can either be 0 or 1. 0 if the email is not sensitive, 1 if the email is sensitive and requires stakeholder attention. Sensitive emails include any regarding pricing, requests for a contract, contract negotiations, client complaints, project scoping, or basically any email where an SDR would pass off the email chain to legal or high executives.

    Ruleset:
    - Can either be 0 or 1.
    - 0 if the email is not sensitive.
    - 1 if the email is sensitive and requires special treatment and/or stakeholder loop in.
    """

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
    def __init__(self, pd, config):
        self.pd = pd
        self.config = config
        self.token_counter = TokenCounter(pd)
        self.token = f'{pd.inputs["openai"]["$auth"]["api_key"]}'
        self.authorization = f'Bearer {self.token}'
        self.headers = {"Authorization": self.authorization}
        self.ai_sync = AIChat(api_key=self.token, console=False, model="gpt-4-0613", headers=self.headers, temperature=0.0)
        self.ai_async = AsyncAIChat(api_key=self.token, console=False, model="gpt-4-0613", headers=self.headers, temperature=0.0)
        self.sender = pd.steps["parse_thread"]["sender"]
        self.recipient = pd.steps["parse_thread"]["recipient"]
        self.subject = pd.steps["parse_thread"]["subject"]
        self.content = pd.steps["parse_thread"]["contents"]
        self.input_data = f"Sender: {self.sender}. Recipient: {self.recipient}. Subject: {self.subject}. Content: {self.content}."

    def classify_email(self):
        print("Classifying email...")
        result = self.ai_sync(self.input_data, system=system_prompt_classification, output_schema=EmailClassification)
        print(f"Email classified. Result: {result}")
        self.token_counter.count_and_export_tokens(self.input_data, str(result), "classify_email_tokens")
        return result

    def check_relevancy(self):
        print("Checking relevancy...")
        result = self.ai_sync(self.input_data, system=system_prompt_relevancy, output_schema=EmailRelevancy)
        print(f"Email Relevancy Result: {result}")
        self.token_counter.count_and_export_tokens(self.input_data, str(result), "check_relevancy_tokens")
        return result 
    
    def check_sensitivity(self, classification_result, relevancy_result):
        # Generate the sensitivity prompt
        system_prompt_sensitivity = create_sensitivity_prompt(
            common_context,
            classification_result,
            relevancy_result
        )
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
        # Lazy initialization of the prompt
        system_prompt_sentiment_and_funnel_stage = self.config["email_prompts"]["sentiment_and_funnel_stage"].format(
            labels=", ".join(self.config["email_labels"].keys())
        )
        # Now use the prompt to classify the sentiment and funnel stage
        result = self.ai_sync(self.input_data, system=system_prompt_sentiment_and_funnel_stage, output_schema=EmailSentimentAndFunnelStage)
        print(f"Sentiment and funnel stage classified. Result: {result}")
        self.token_counter.count_and_export_tokens(self.input_data, str(result), "classify_sentiment_and_funnel_stage_tokens")
        return result

    def apply_label(self, label, thread_id):
        # Use the config to map the label to a Gmail label ID
        label_id_mapping = self.config["email_labels"]
        print(f"label_id_mapping: {label_id_mapping}")
        label_ids = [label_id_mapping.get(label.upper())]

        # Call the Gmail API to apply the label
        apply_label = ApplyLabel(self.pd, [label_id_mapping.get(label.upper())])
        apply_label.apply_labels(thread_id)

    def handle_async_tasks(self):
        # Lazy initialization of the scenario prompt
        system_prompt_scenario = self.config["email_prompts"]["scenario"].format(
            inquiry_types=", ".join(self.config["inquiry_types"]),
            sender_categories=", ".join(self.config["sender_categories"])
        )
        system_prompt_sentiment_and_funnel_stage = self.config["email_prompts"]["sentiment_and_funnel_stage"].format(
            labels=", ".join(self.config["email_labels"].keys())
        )
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
    #setup handler and token count
    email_handler = EmailHandler(pd, semantic_routers_config)
    inquiry_type = None
    total_tokens = 0 

    # Perform the EmailClassification task and count tokens
    print("Starting Email Classification...")
    classification_result = email_handler.classify_email()
    pd.export("classification result:", classification_result)
    classify_email_tokens = email_handler.token_counter.count_and_export_tokens(email_handler.input_data, classification_result, "classify_email_tokens")
    total_tokens += classify_email_tokens  # Accumulate total tokens

    # If the email does not require a response, apply label and exit the workflow early
    if classification_result['requiresResponse'] == 0:
        print("Applying 'not from person' label and exiting workflow...")
        email_handler.apply_label("not from person", pd.steps["trigger"]["event"]["threadId"])
        pd.export("total_tokens", total_tokens)  # Export total tokens before exiting
        return pd.flow.exit('Email does not require a response. Exiting workflow.')

    # Perform the EmailRelevancy task and count tokens
    print("Starting Email Relevancy Check...")
    relevancy_result = email_handler.check_relevancy()
    pd.export("relevancy result:", relevancy_result)
    relevancy_tokens = email_handler.token_counter.count_and_export_tokens(email_handler.input_data, relevancy_result, "check_relevancy_tokens")
    total_tokens += relevancy_tokens  # Accumulate total tokens

    # If the email is not relevant, apply label and exit the workflow
    if relevancy_result['isRelevant'] == 0:
        print("Applying 'non-relevant' label and exiting workflow...")
        email_handler.apply_label("non-relevant", pd.steps["trigger"]["event"]["threadId"])
        pd.export("total_tokens", total_tokens)  # Export total tokens before exiting
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
        email_handler.apply_label(scenario_result['inquiry_type'], pd.steps["trigger"]["event"]["threadId"])
    if scenario_result['sender_category']:
        email_handler.apply_label(scenario_result['sender_category'], pd.steps["trigger"]["event"]["threadId"])
    if sentiment_and_funnel_stage_result['label']:
        email_handler.apply_label(sentiment_and_funnel_stage_result['label'], pd.steps["trigger"]["event"]["threadId"])

    # Sum the total tokens used in each step
    print(f"Total Tokens Used: {total_tokens}")

    # Export the results for use in the next step
    pd.export("total_tokens", total_tokens)
