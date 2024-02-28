# Define your org's configuration and custom settings
semantic_routers_config = {
    "org_name": "Bttr",
    "email_labels": {
        # Set to apply gmail labels that map to below custom set sentiment and funnel stage rules and scenario rules. 
        # See label setup script to get started.
        "NOT FROM PERSON": "Label_18",
        "NON-RELEVANT": "Label_19",
        "NOT INTERESTED": "Label_20",
        "INTERESTED": "Label_21",
        "LEAD": "Label_22",
        "APPOINTMENT SCHEDULED": "Label_23",
        "QUALIFIED TO BUY": "Label_24",
        "PRESENTATION SCHEDULED": "Label_25",
        "DECISION MAKER BOUGHT IN": "Label_26",
        "CONTRACT SENT": "Label_27",
        "CLOSED WON": "Label_28",
        "ORGANIC INBOUND": "Label_29",
        "COLD EMAIL OUTBOUND REPLY": "Label_30",
        "WARM INTRO REPLY": "Label_31",
        "ICP 1: SILENT GIANT": "Label_32",
        "ICP 2: HIGH GROWTH INNOVATION": "Label_33",
        "OTHER ICP TYPE": "Label_34",
        "OTHER": "Label_35",
        "AUTOMATED/SPAM": "Label_36",
        # ... add all labels here
    },
    "email_prompts": {
        # Used to set your custom funnel stages and classify sentiment speciifc to your use case. 
        # See semnatic_router. 
        "sentiment_and_funnel_stage": """
            Function: Sentiment and Funnel Stage Classification
            Determine the sentiment and stage of the sales funnel the email corresponds to.

            Ruleset:
            - Use the content of the email to identify keywords or phrases that indicate sentiment and the stage of the sales funnel.
            - Labels can include: {labels}.
        """,
        "scenario": """
            Function: Email Scenario Identification
            Identify the type of inquiry, the ICP category of the sender, and any specific details related to the inquiry.

            Ruleset: 
            - types of inquiry options: {inquiry_types}
            - sender category options: {sender_categories}
        """
    },
    "inquiry_types": ["organic inbound", "cold email outbound reply", "warm intro reply"],
    "sender_categories": ["ICP 1: Silent Giant", "ICP 2: High Growth Innovation", "Other ICP Type", "other", "automated/spam"]
}

def handler(pd: "pipedream"):
    # Export the configuration for use in downstream steps
    print("Config Exported.")
    pd.export("config", semantic_routers_config)
    # Continue with the rest of your logic


reply_drafter_config = {drafting_prompt, signature_name,links_for_insertion}

sending_manager_config = {}
- inbox email (used as sending email)
- whitelisted domains for auto reply, (if the list is empty all allowed)
- draft reply or auto send reply (0 or 1)

hubspot_crm_config = {}
- deal stage mappings: 
    stage_mapping = {
        "appointment scheduled": "appointmentscheduled",
        "qualified to buy": "qualifiedtobuy",
        "presentation scheduled": "presentationscheduled",
        "decision maker bought in": "decisionmakerboughtin",
        "closed won": "closedwon",
        "closed lost": "closedlost"
    }




