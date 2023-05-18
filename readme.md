# Generative Email Assistant

## A proof of concept email batching and drafting assistant. 

This is a Pipedream workflow that integrates GPT-3.5 (or GPT-4) with Gmail to automatically generate email drafts based on the context of email threads and user instructions all from their gmail interface. This workflow ingests and cleans full threads and treats any drafts as user instructions to the LLM.  The workflow is triggered by applying a specific label to an email thread, and it generates a context-rich draft using OpenAI's GPT-3.5. The generated draft is then added to the email thread, and the workflow is marked as complete by applying an "Autodrafted Response" label (or any label you desire really).

I created this workflow as a proof of concept for an LLM-agent email assistant idea I've been scoping out. My goal was to both build something immediately useful, and develop a better understanding of the Gmail API and email infrastructure in general for future use. Working on this project was a lot of fun (and I learned a lot about the idiosyncrasies of the Gmail API). Please feel free to call out any bugs you experience using it or suggest any improvements you'd like to see. 


## Features:

- ***In-Gmail OpenAI Model Prompting and Messsage Drafting for Ease of Use***: The workflow is triggered by gmail labels, meaning you can call it both from your regular gmail web UI and mobile app. Existing Drafts serve as user instructions, so you can write a few bullet points in a draft of what you want to say, followed with a prompt like "expand on x part" or "revise to be more y" and the model will use it as instructions. I found the mobile experience of using this to be the most fun as you just label the email and ~20 seconds, and a refresh later, its in your literal hands. 

- ***Context Rich Drafting and Customizable Tone of Voice for Better Emails***: Included in this repo is the System and User Prompts I created. The user prompt takes in the full thread context and makes sure the model understands the scenario, such as if we're replying to someone or drafting a new message, so it can generate a meaningfully relevant message. In the system prompt you'll find a series of branding and tone of voice variables. The intent is to make sure we're always writing messages in the tone we want and give to the model the abilty to answer repeitive questions like "what does your company do?" without user provided context. The extra context from the full thread and the brand/TOV variables ***really** help improve the quality of the message and prevent the model from outputting the basic ProfessionalSpeak<sup>TM</sup> I feel like everyone can tell is straight from a "write this email for me" prompt in ChatGPT now. 

- ***Bulk concurrent drafting for faster email batching***: the workflow can generate multiple drafts concurrently thanks to Pipedreams concurrency features, allowing for faster email batching. I've used this to write out a few bullet points in each email I need to respond to, label them, go get a glass of water and come back to all them them drafted up. The number of concurrent draft generations is only limited by the user's OpenAI rate limits (you'll probably run into the tokens per min limit first if you've working with mulitple threads longer that 15+ messages) which varies from user to user. I used both GPT-3.5 and GPT-4 for this. Since GPT-4 has a much bigger token limit you'll get much farther using it. 


## Workflow Logic Overview

`Trigger`: The workflow starts when a new label specific to "needs new autodraft" is added to an email.

`parse_and_filter_new_email`: This step determines the email scenario (thread_and_draft, thread_no_draft, or standalone_draft) and extracts and exports relevant information, such as   message_id, thread_id, sender, recipient, subject, contents, user_instructions, email_type, most_recent_message_id, most_recent_date, and draft_id.

`draft_response`: This step makes an OpenAI call to generate a response to the message using the message contents and other context.

`message_draft_logic`: Handles creating or updating a draft in a thread depending on the scenario. It calls the appropriate helper functions based on the email_type (thread_no_draft, standalone_draft, or thread_and_draft) to create or update the draft.

`remove_needs_autodrafting_label`: This step removes the trigger label from all messages in the thread.

`add_autodrafted_label`: This step adds the "autodrafted response" label to the generated or updated thread.

There are three scenarios this workflow handles:
 • `thread_no_draft`: any thread with no drafts at the end of the thread. In this scenario, the workflow will prompt GPT-3.5 to generate a response using just the tone of voice set in the system prompt with no further context.
 • `thread_and_draft`: Any thread where the last message in thread is a draft. In this scenario, the workflow will extract the contents of the draft and provide it in the API call, effectively allowing the user to prompt GPT-3.5 from their inbox both on desktop and mobile.
 • `standalone_draft`: Any thread where there is only one message in the thread and it is labeled "DRAFT." In this scenario, the workflow will use the draft contents as user instructions for the API call and generate a new draft that contains the new content.

The workflow can be triggered as many times as desired. All that needs to be done to retrigger is to remove the "Autodrafted Response" label and reapply the set trigger label.


## Setup

1. Create a Pipedream account here -> https://pipedream.com/auth/signup

    You can create a free account that includes 100 free credits a day. In the context of this workflow, that is 100 email drafts a day. 

2. Create your trigger labels in Gmail.  

    You can name them whatever you want, as Gmail assigns user created labels a name like "Label_7116554950162008534" internally. 

3. Create a workflow and select Gmail (Developer App) for your source and select "New Labeled Email" as the trigger.

4. Authorize Pipedream to access your Gmail Account via API and select your labels after it succesfully connects.
    
    Pipedream has in depth instructions on how to authorize access to the Gmail API. Follow the on-screen instructions. After it is complete, it will allow you select the label (the name you assigned it). Select the label you want to serve as the workflow trigger, then create a test event (label an email in Gmail) to ensure it is working properly

5. Create code blocks, paste in and configure each block step by step. 

    After you've ensured the trigger is working, begin creating python code blocks pasting in the code in order. You should test each code block before adding the next one to ensure the next block has data to use. 

    After setting up the parse_and_filter_new_email block, you'll want to create the OpenAI API step, rather than use a code block here, I opted to use Pipedream's step for simplicity. Select the Chat option and configure using the user and system prompt template included and adjust to fit your desired tone, style and end result. You will need an OpenAI API key, if you don't have one, you can signup for an account here: 
    
    https://platform.openai.com/ 

    After you test the OpenAI test, continue creating code blocks and pasting in the respective code. This should be fairly straightforward except for the last two blocks, remove_trigger_label_from_thread and add_autodrafted_label_to_draft, as in each of these you'll need to find the internal Gmail name for your custom labels. 
    
    You can find the custom lable names using the Gmail API explorer here 
    
    https://developers.google.com/gmail/api/reference/rest/v1/users.labels/list 
    
    For user ID you can input "me." This will retrieve all your labels, find your trigger and completion label. 

    In the `remove_trigger_label_from_thread` code block: 

    set the trigger label = `to_remove_label_id` 

    And in the `add_autodrafted_label_to_draft`:

    Set your completion label = `to_add_label_id` 
    
     Please note, if you change the name of the blocks, you will need to reconfigure the export paths in each step to match the renamed block. 


6. Deploy and test using your trigger labels. 
    
    Deploy the workflow. Test to ensure it works, Pipedream is good about telling you where something goes wrong but I've also included tracebacks in both the parse_and_filter_new_email and message_draft_logic blocks for easier debugging if something goes wrong. 
    
    Select any email thread or standalone draft in your desktop or mobile gmail and label it your trigger label. This will trigger the workflow. Monitor the workflow execution, and once you see the little green check mark you'll know you've got an email drafting assitant inside your gmail :) 


## Troubleshooting

If you encounter any issues during the setup or usage of this workflow, please refer to the debugging information provided in the code blocks in the logs during workflow executions. Additionally, you can consult Pipedream's documentation and support resources for further assistance. 