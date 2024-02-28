# packages for interacting with Gmail API 
import base64
from email.message import EmailMessage
from email.headerregistry import Address
from email.utils import make_msgid
# packages for interacting with OpenAI API 
from simpleaichat import AIChat
import tiktoken
import markdown


# Drafting setup prompt. Will produce high quality context-aware responses that are succinct and use links to case studies and other resources
common_context =  """
# Cold Email & Reply Drafting Prompt

You are monitoring [ORGANIZATION]'s primary sales, lead generation and general inbound email account. You have one task as a part of a larger system
which will be described below. For context the larger system designed to provide an automated, intelligent solution for managing emails at the [ORGANIZATION]. It is comprised of:

1. Email Classification (is this email from a real person or a notification/spam?)
2. Email Scenario Identification (what is the nature of the email? Who is it from? What is it about?)
3. Funnel Stage Classification (what stage of the sales funnel does this email seem like?)
4. Stakeholder Notification (if the email is from a real person, is there a member of [ORGANIZATION] is best suited to address the inquiry or not?)
5. Contextually Aware & Scenario Specific Generative AI drafting and reply  (Using the email's classification, scenario, and stakeholder notification, along with specific instructions for each scenario and a general tone of voice and SOPs generate a contextually aware and scenario specific reply to the email)

YOUR ACTIONS MUST STRICTLY FOLLOW THE PROVIDED RULESETS IN EACH FUNCTION. IF YOU GENERATE ANYTHING OUTSIDE OF THE RULESET, YOU FAIL THE TEST.

You are responsible for the below task: 

You are handling step 5. You are to act as the intelligent email drafting AI assistant for [ORGANIZATION]. You are tasked with drafting a contextually aware and scenario specific replies to emails. You are drafting replies for [NAME], the founder of [ORGANIZATION] to review and send himself, keep this in mind. 

Make sure the email is personalized to the sender, addresses content relevantly and succinctly.Adopt the tone of voice and persona:

Balance excitment with professionalism. Messages that only necessitate a sort reply should have a short reply. Never be overly verbose or fluffy in your replies, almost spartan. Above, all limit corny phrases and euphemisms.

Your signature will be included, YOU DO NOT NEED TO WRITE YOUR SIGNATURE. NEVER INCLUDE A SIGNATURE. IF YOU INCLUDE A SIGNATURE YOU FAIL THE TEST.

NEVER PRINT THE EMAIL OR SUBJECT IN YOUR RESPONSE. ONLY PRINT THE RELEVANT CONTENT AS IF YOU WERE RESPONDING TO THE EMAIL.

Your responses should be succinct. Your primary objective is to write a response to the message that addresses their primary inquiry, and anticipates follow-up questions and addresses them, in as few sentences as possible. Think of it is a game - "how can I use as few words as possible to write the best, most actionable information-dense helpful response possible?" (hint: links to case studies can be a good way to optimize density) is how you should approach the problem. 

When someone inquires with a question about a case study, scheduling a call/meeting with someone at [ORGANIZATION], you should provide a link to the Hubspot scheduling link, using the below mentioned placeholder, for that person or the case study that most cleary demonstrates [ORGANIZATION]'s ability to address their problem and create value specific to them. 

When referring to links, only use "here" for scheduling links. YOU MUST FOLLOW MARKDOWN FORMATTING FOR REFERENCING CASE STUDIES. NEVER USE "here" for case study links. When you reference a case study you must used a [Case Study] placeholder.

When referencing a case study or other link, you should use the designated placeholder signified by the [case study] or [here] for the hubspot scheduling link (exact match, always all proper capitalization case) placeholders. For example if you want to reference Helix, you would write [Helix].


Outline:
- Intro (Company, Tone of voice, Brand Proposition)
- Case studies
    - Case Studies by discipline
    - Exhaustive case study list
- Ideal Customer Profiles
    - ICP Messaging
    - Case Study ICP Pairs
- Services 
    - ICP Services Pairs

## Intro

"""


class EmailAssembler:
    def __init__(self, response, original_email, drafting_config):
        self.response = response
        self.original_email = original_email
        self.variable_context = drafting_config["variable_context"]
        self.signature_block = drafting_config["signature_block"]
        self.links_for_insertion = drafting_config["links_for_insertion"]
        self.formatted_message = self.format_original_message(original_email['content'])
        self.response = self.inject_links()  # Call inject_links here
        self.context_block = self.create_context_block()

    def format_original_message(self, original_message):
        # Join the list of strings into a single string
        original_message = ' '.join(original_message)
        lines = original_message.split('\n')
        headers = lines[:4]
        content = lines[4:]
        formatted_headers = [f"> {line}  " for line in headers if line.strip() != '']
        formatted_content = [f"> {line}  " for line in content if line.strip() != '']
        return '\n'.join(formatted_headers + [''] + formatted_content)

    def create_context_block(self):
        # Use the signature_block from the config
        context_block = f"""
{self.response}

{self.signature_block}
"""
        return '\n'.join(line.lstrip() for line in context_block.split('\n'))

    def inject_links(self) -> str:
        # Replace the placeholders with the actual links from the config
        for placeholder, link in self.links_for_insertion.items():
            markdown_link = f"[{placeholder.strip('[]')}]({link})"
            self.response = self.response.replace(placeholder, markdown_link)
        return self.response

    def assemble_email(self):
        # Convert markdown to HTML for each part of the context block
        parts = self.context_block.split('---')
        html_parts = [markdown.markdown(part) for part in parts]
        return '---'.join(html_parts)

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

def handler(pd: "pipedream"):
    try:
        sensitivity_result = pd.steps["semantic_routers"]["sensitivity result:"]["isSensitive"]

        variable_context = pd.steps["workflow_config"]["drafting_config"]["variable_context"]

        # Check if 'requiresResponse' is 1 and set the forwarding instruction
        if sensitivity_result == 1:
            # Set the forwarding instruction
            forwarding_instruction = "Please forward this email to stakeholder@example.com for further review."
            pd.export("forwarding_instruction", forwarding_instruction)
            print("Forwarding instruction set. Exiting handler.")
            return  # Exit the handler early
        else:
            # Instantiate the TokenCounter
            token_counter = TokenCounter(pd)
            # Extract original email details
            sender = pd.steps["parse_thread"]["sender"]
            recipient = pd.steps["parse_thread"]["recipient"]
            subject = pd.steps["parse_thread"]["subject"]
            content = pd.steps["parse_thread"]["contents"]

            print(f"Original email details - Sender: {sender}, Recipient: {recipient}, Subject: {subject}, Content: {content}")

            # Extract scenario details
            inquiry_type = pd.steps["semantic_routers"]["email_scenario_result"]

            full_drafting_context = common_context + variable_context
            
            # Determine system prompt based on inquiry type
            system_prompt = full_drafting_context + "ALWAYS GENERATE YOUR RESPONSE IN MARKDOWN. Please use markdown."

            # Generate response using simpleaichat
            token = f'{pd.inputs["openai"]["$auth"]["api_key"]}'
            authorization = f'Bearer {token}'
            headers = {"Authorization": authorization}
            ai = AIChat(console=False, save_messages=False, model="gpt-4-0125-preview", headers=headers, api_key=token, temperature=0.0)
            input_data = f"Subject: {subject}. Content: {content}. Inquiry Type: {inquiry_type}."
            print("Input data for AIChat: ", input_data)
            # Generate response using simpleaichat
            output = ai(input_data, system=system_prompt)
            print("Output from AIChat: ", output)

            # Count and export tokens for draft response
            draft_response_tokens = token_counter.count_and_export_tokens(input_data, output, "draft_response_tokens")

            # Assemble the email using EmailAssembler Class
            assembler = EmailAssembler(output, {"sender": sender, "recipient": recipient, "subject": subject, "content": content}, pd.steps["workflow_config"]["drafting_config"])
            context_block = assembler.assemble_email()
            print("Context Block Email: ", context_block)
            
            total_tokens = draft_response_tokens

            # Export the results for visibility
            pd.export("Context Block Email: ", context_block)
            pd.export("draft_response_tokens", draft_response_tokens)
            pd.export("total tokens", total_tokens)

    except Exception as e:
        print(f"An error occurred: {str(e)}")
        pd.export("error", str(e))
