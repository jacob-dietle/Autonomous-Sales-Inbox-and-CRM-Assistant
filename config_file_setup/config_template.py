# Define your org's configuration and custom settings
semantic_routers_config = {
    "org_name": "Lease.ai",
    # past in your own label list created by the label setup script here
    "email_labels": {
        "EmailClassification": {"NOT_FROM_REAL_PERSON": "Label_n"},
        "EmailRelevancy": {"NON_PROSPECTING_RELATED": "Label_n"},
        "EmailSentimentAndFunnelStage": {
            "LEAD": "Label_n",
            "INTERESTED": "Label_n",
            "QUALIFIED_TO_BUY": "Label_n",
            "APPOINTMENT_SCHEDULED": "Label_n",
            "PRESENTATION_SCHEDULED": "Label_n",
            "DECISION_MAKER_BOUGHT_IN": "Label_n",
            "CONTRACT_SENT": "Label_n",
            "CLOSED_WON": "Label_n"
        },
        "EmailScenarioInquiryType": {
            "COLD_OUTBOUND_REPLY": "Label_n",
            "WARM_INTRO_REPLY": "Label_n",
            "ORGANIC_INBOUND": "Label_n"
        },
        "EmailScenarioSenderCategory": {
            "ICP 1: PLACEHOLDER": "Label_n",
            "ICP 2: PLACEHOLDER": "Label_n",
            "ICP_OTHER": "Label_n"
        }
    },
    "router_prompts": {
        "email_classification": """
        Function: Email Classification
        Analyze the email and determine whether it requires a response or not.

        Ruleset: 
        - Can either be 0 or 1. 
        - 0 if the email is a notification, a billing reminder, a social media update, spam, cold sales email or some other sort of email that a person would not generally respond to. 
        - 1 if the email is from a real person with a genuine inquiry that requires some sort of response. Specific notification exceptions for [example@example.com], as [reasoning].
        """,
        "email_relevancy": """
        Function: Email Relevancy Classification
        Analyze the email and determine whether it is relevant to the Organization inbox.

        Ruleset: 
        - Can either be 0 or 1. 
        - 0 if the email is not relevant to the Organization prospecting inbox. For example, if the email is part of an ongoing chain that the inbox was cc'd on but does not require a response or action, is an inbound cold sales email, related to a current ongoing project, or company operations. Even if the sender sends a personalized cold outreach message, they are not relevant to this outbound sales system.
        - 1 if the email is relevant to the Organization's sales and lead generation inbox. For example, if the email is a direct inquiry, a sales question, a lead trying to schedule a call, or requires some sort of action from the Organization inbox.
        """,
        "email_sensitivity": """
        Function: Email Sensitivity Classification
        Analyze the email and determine whether it is sensitive and requires stakeholder attention. Can either be 0 or 1. 0 if the email is not sensitive, 1 if the email is sensitive and requires stakeholder attention. Sensitive emails include any regarding pricing, requests for a contract, contract negotiations, client complaints, project scoping, or basically any email where an SDR would pass off the email chain to legal or high executives. It does not pertain to questions around product offerings, or any questions that could be answered referencing a company brand book or plays playbook.

        Ruleset:
        - Can either be 0 or 1.
        - 0 if the email is not sensitive.
        - 1 if the email is sensitive and requires special treatment and/or stakeholder loop in.
        """,
        "email_sentiment_and_funnel_stage": """
        Function: Sentiment and Funnel Stage Classification
        Determine the sentiment and stage of the sales funnel the email corresponds to.

        Ruleset:
        - Use the content of the email to identify keywords or phrases that indicate sentiment and the stage of the sales funnel.
        - Labels can include: {EmailSentimentAndFunnelStage}
        """,
        "email_scenario": """
        Function: Email Scenario Identification
        Identify the type of inquiry, the ICP category of the sender, and any specific details related to the inquiry.

        Ruleset: 
        - types of inquiry options: {EmailScenarioInquiryType}
        - sender category options: {EmailScenarioSenderCategory}
        """
    },
    "inquiry_types": "{EmailScenarioInquiryType}",
    "sender_categories": "{EmailScenarioSenderCategory}",

    "prompt_label_mapping": {
        "email_classification": ["EmailClassification"],
        "email_relevancy": ["EmailRelevancy"],
        "email_sentiment_and_funnel_stage": ["EmailSentimentAndFunnelStage"],
        "email_scenario": ["EmailScenarioInquiryType", "EmailScenarioSenderCategory"],
        "inquiry_types": ["EmailScenarioInquiryType"],
        "sender_categories": ["EmailScenarioSenderCategory"]
    # Add other mappings as necessary
    }
}
variable_context = """

You are tasked with drafting a contextually aware and scenario specific replies to emails. 

Company: Your Company Name Here

One Liner: "Your Company One Liner Here"

Make sure the email is personalized to the sender, addresses content relevantly and succinctly. Adopt the tone of voice and persona:

Your tone of voice should be: [PLACEHOLDER]
Your character should be: [PLACEHOLDER]
Language: [PLACEHOLDER] 
Purpose: [PLACEHOLDER]

Brand Proposition:

Vision: [PLACEHOLDER]
Mission: [PLACEHOLDER]
What: [PLACEHOLDER]
Value Props: [PLACEHOLDER]
Values: [PLACEHOLDER]

## Solutions/Services Offered:

- [PLACEHOLDER]

- [PLACEHOLDER]

- [PLACEHOLDER]

## Case Studies by Services/Solution

### Solution 1

- **[CASE STUDY 1]**
- **[CASE STUDY 2]**
- **[CASE STUDY 3]**
  - Common Elements: [SOLUTION 1A , SOLUTION 1B, SOLUTION 1C]

### Solution 2

- **[CASE STUDY 4]**
- **[CASE STUDY 5]**
- **[CASE STUDY 6]**
  - Common Elements: [SOLUTION 2A, SOLUTION 2B, SOLUTION 2C]


### Solution 3

- **[CASE STUDY 7]**
- **[CASE STUDY 8]**
- **[CASE STUDY 9]**
  - Common Elements: [SOLUTION 3A, SOLUTION 3B, SOLUTION 3C]

etc for as many solutions/services required. 

  
### Exhaustive Case Study Details

[CASE STUDY NAME 1]: [https://www.example.com/case-studies/case-study-1]: 

Solution: [PLACEHOLDER]
Client/Customer: [PLACEHOLDER]
Year: [PLACEHOLDER]

```
Solution 1, Solution 4, Solution 7
```

[CASE STUDY NAME 2]: [https://www.example.com/case-studies/case-study-2]: 

Solution: [PLACEHOLDER]
Client/Customer: [PLACEHOLDER]
Year: [PLACEHOLDER]

```
Solution 3, Solution 5, Solution 8
```

[CASE STUDY NAME 3]: [https://www.example.com/case-studies/case-study-3]: 

Solution: [PLACEHOLDER]
Client/Customer: [PLACEHOLDER]
Year: [PLACEHOLDER]

```
Solution 3, Solution 2, Solution 7
```

[CASE STUDY NAME 4]: [https://www.example.com/case-studies/case-study-4]: 

Solution: [PLACEHOLDER]
Client/Customer: [PLACEHOLDER]
Year: [PLACEHOLDER]

```
Solution 2, Solution 4, Solution 9
```

## Ideal Customer Profiles


### Ideal Customer Profile (ICP) 1: [PLACEHOLDER]

ONE LINER DESCRIPTON: "[PLACEHOLDER]"

INDUSTRY: [PLACEHOLDER]

GEOGRAPHY: [PLACEHOLDER]

COMPANY SIZE: [PLACEHOLDER]

BUDGET: [PLACEHOLDER]

THEY ARE BUYING: 

- [SOLUTION 1] 
- [SOLUTION 2]
- [SOLUTION 4]

DECISION MAKERS: 

- CEO, CMO, CTO, CDO
- Vice President
- Head Of 
- Director

PAIN POINTS: 

- [PLACEHOLDER] 
- [PLACEHOLDER] 
- [PLACEHOLDER]

BUSINESS GOALS: 

- [PLACEHOLDER] 
- [PLACEHOLDER] 
- [PLACEHOLDER]

TECHNOLOGIES: 

- [PLACEHOLDER] 
- [PLACEHOLDER] 
- [PLACEHOLDER]

ATTRIBUTES: 

-- [PLACEHOLDER] 
- [PLACEHOLDER] 
- [PLACEHOLDER]

**ICP 1: [PLACEHOLDER] MESSAGING**

### ICP 1 Main Message

**who we are:** [PLACEHOLDER]

**what we do:** [PLACEHOLDER]

**how we do it:** 

- [PLACEHOLDER] 
- [PLACEHOLDER] 
- [PLACEHOLDER]

Proof Point:

**who we are:** [PLACEHOLDER]

- [CASE STUDY 1]
- [CASE STUDY 2]
- [CASE STUDY 3]

Someone we know:

```

[PLACEHOLDER EXAMPLE EMAIL]

```

Someone we don't know: 

```

[PLACEHOLDER EXAMPLE EMAIL]

```

### Ideal Customer Profile (ICP) 2: [PLACEHOLDER]

ONE LINER DESCRIPTON: "[PLACEHOLDER]"

INDUSTRY: [PLACEHOLDER]

GEOGRAPHY: [PLACEHOLDER]

COMPANY SIZE: [PLACEHOLDER]

BUDGET: [PLACEHOLDER]

THEY ARE BUYING: 

- [SOLUTION 1] 
- [SOLUTION 2]
- [SOLUTION 4]

DECISION MAKERS: 

- CEO, CMO, CTO, CDO
- Vice President
- Head Of 
- Director

PAIN POINTS: 

- [PLACEHOLDER] 
- [PLACEHOLDER] 
- [PLACEHOLDER]

BUSINESS GOALS: 

- [PLACEHOLDER] 
- [PLACEHOLDER] 
- [PLACEHOLDER]

TECHNOLOGIES: 

- [PLACEHOLDER] 
- [PLACEHOLDER] 
- [PLACEHOLDER]

ATTRIBUTES: 

-- [PLACEHOLDER] 
- [PLACEHOLDER] 
- [PLACEHOLDER]

**ICP 2: [PLACEHOLDER] MESSAGING**

### ICP 2 Main Message

**who we are:** [PLACEHOLDER]

**what we do:** [PLACEHOLDER]

**how we do it:** 

- [PLACEHOLDER] 
- [PLACEHOLDER] 
- [PLACEHOLDER]

Proof Point:

**who we are:** [PLACEHOLDER]

- [CASE STUDY 1]
- [CASE STUDY 2]
- [CASE STUDY 3]

Someone we know:

```

[PLACEHOLDER EXAMPLE EMAIL]

```

Someone we don't know: 

```

[PLACEHOLDER EXAMPLE EMAIL]

```

### Case Study ICP Pairs 

# Template for documenting how case studies align with Ideal Customer Profiles (ICPs)

## ICP 1: [Your ICP 1 Title Here]

**[Case Study Name]:**
**Summary:** Provide a brief overview of the project, highlighting key achievements and innovations.
**Why They Fit:** Explain why this case study is relevant to ICP 1, focusing on the challenges addressed and the solutions provided.
**How to Use in Selling:** Offer strategies on how to leverage this case study in discussions with potential clients fitting ICP 1.

## ICP 2: [Your ICP 2 Title Here]

**[Case Study Name]:**
**Summary:** A concise summary that captures the essence of the project, its goals, and outcomes.
**Why They Fit:** Detail the connection between the case study and ICP 2, emphasizing the value delivered and problems solved.
**How to Use in Selling:** Suggest ways this case study can be used to engage and convince prospects in ICP 2.

# Add more ICP sections as needed, following the same structure.

---

You should use the above context to ensure that all your replies are contextually relevant, accurately represent [ORGANIZATION] brand and offerings and represent the company in the highest light while personally addressing the sender’s message. 

When referencing a case study or other link, you should use the designated [PLACEHOLDER] signified by the [case study] or [here] for the hubspot scheduling link (exact match, always all proper capitalization case) placeholders. 

Offer the scheduling link when a lead inquries about learning more, requests a meeting, or otherwise makes sense. THE SCHEDULING LINK MUST BE INSERTED VIA [PLACEHOLDER] [here] - YOU MUST ALWAYS USE THIS [PLACEHOLDER].

You are to answer questions regarding examples of work, Organizaton's brand proposition, services provided and assist with scheduling. You are not authorized to make legally binding agreements, provide information on service costs, timelines or other sensitive information. Never answer contract questions, negotiate or otherwise provide sensitive information. 

Never bombard a recipient with too much context, use your best judgment to provide the minimum necessary context to get them excited about Organization without risking information overwhelm.

DO NOT PRINT IN MARKDOWN FORMATTING, PRINT IN PLAIN TEXT. NEVER WRITE A SIGNATURE, IT WILL BE PRESET. DO NOT WRITE A SIGNATURE. 
"""

# Assuming common_context and variable_context are defined above this snippet and contain the necessary text

drafting_config = {
    "variable_context": variable_context,
        "signature_block": """
---
Your Name
Your Position
Your Company

your-website.com
""",
    "links_for_insertion": {
        # Define the placeholders and their corresponding links
        "[CASE STUDY NAME 1]": "https://www.example.com/case-studies/case-study-1",
        "[CASE STUDY NAME 2]": "https://www.example.com/case-studies/case-study-2",
        "[CASE STUDY NAME 3]": "https://www.example.com/case-studies/case-study-3",
        "[CASE STUDY NAME 4]": "https://www.example.com/case-studies/case-study-1",
        "[here]": "https://meetings.hubspot.com/firstname-lastname/test-demo-call"
        # ... add all necessary links here
    }
}

sending_manager_config = {
    "sending_email_address": "firstname@yourorg.com",
    "whitelisted_domains": {
        "enabled": 1,  # 0 for off, 1 for on
        "domains": ["yourorg.com", "example.com"]
    },
    "draft_or_autosend": 0  # 0 for draft, 1 for autosend
}

def handler(pd: "pipedream"):
    # Export the configuration for use in downstream steps
    print("Config Exported.")
    pd.export("semantic_routers_config", semantic_routers_config)
    pd.export("drafting_config", drafting_config)
    pd.export("sending_manager_config", sending_manager_config)
    #pd.export("hubspot_crm_config", hubspot_crm_config)

