# Autonomous Sales Inbox & CRM Assistant

This app leverages generative AI to intelligently manage your sales inbox and CRM, auto-draft replies using your sales playbook & company branding, and more. 


## Demo: 

https://www.loom.com/share/92dcb751ba6f4a16a54ffccf92a4178e?sid=88f35317-6cea-4a68-9582-49f254c3d860

## Features:

**Auto-drafted Responses that Match How You Already Sell:** Generative AI systems deployed without relevant context are useless for problem solving. Inbox Assistant can be configured to match your existing sales process, drafting style, commonly used case studies, and even your scheduling links. By inserting your company branding, sales playbooks, case studies and other context inbox assistant will draft contextually-coherent, one-review-and-send replies; and is specifically excellent at answering those repeat questions and lead objections that your templates don't handle but are still the same question, over and over again. 

**Autonomous Message Classification & Inbox Management:** To successfully achieve the level of accuracy needed for auto-drafting, Inbox Assistant parses every new message that lands in your inbox and semantically classifies it, this has the added benefit of enabling a completely customizable inbox management and triage feature. Out of the inbox, it will filter high signal prospecting emails out from the noise of your inbox and surface them using labels such as:

- ICP Type (custom to your company)
- Deal stage (APPOINTMENT SCHEDULED, QUALIFIED TO BUY, etc.)
- Sentiment  (INTERESTED, NOT INTERESTED, LEAD, etc.)
- ***Any Custom Label Group You Configure***

Once labeled, it easy to search and group by any label in your inbox, allowing for easy discovery and trend spotting, saving you time and hopefully easing the pain of context switching across deals.

**Semantic CRM Automation:** Integrating with HubSpot, CRM assistant will create and update contacts, update and create deals, and automatically move deals through your funnel accordingly. This feature improves data quality inside HubSpot, as it only creates contacts for prospects, unlike the native HubSpot Gmail integration, which will create contacts for every single message that lands in your inbox. This feature is still in testing, and further functionality is planned.

## How it Works: 

**GPT-4-based Semantic Routing:** This app uses a series of layered semantic classifications to filter out spam, non-prospecting emails and other such noise so that only high signal emails are processed for auto-drafting. This is done by making use of GPT-4 function calling. It is extremely simple, making it deceivingly effective. [Diagram here](https://www.figma.com/file/VQslgQjpVLrJ8KNVrPl6vQ/Digital-Leverage-Inbox-Assistant-Semantic-Routing?type=whiteboard&node-id=0-1&t=IaGMYaFv8cMN3d04-0).

**Full Thread Context + Natural Language Programming + Python:** Throughout the entire workflow, the full thread is processed to ensure accurate classification and contextually-correct responses, with GPT-4-turbo, the 128k context window is almost never capped out. The natural language instructions represented in prompts, in the semantic routers and drafting logic are integrated with regular python, enabling handling of nuanced, squishy problems like "how to respond to this email correctly" to be processed as structured data by a series of processor classes that orchestrate the Gmail and OpenAI APIs. 

**Easy Config File Customization:** This app makes use of a configuration file that can be easily changed to meet your specific company details, sales process and other nuances. In the config file you can update the organization information, the semantic routing logic, your drafting logic and more.

### How to Setup: 

Pipedream has workflow sharing functionality. You can clone a version of this app by clicking the link here. For those unfamiliar, Pipedream is a great workflow automation platform for devs that allows you to run code blocks sequentially and use pre-made triggers. In this case, Pipedream monitors the Gmail Inbox and triggers the workflow whenever a new message is received. 

If you are self-deploying and setting up this workflow, this does require some ability to understand basic technical concepts (API key, what a function does, json structure, etc.) but you're reading a README, so I am going to assume this understanding (if you don't have such understanding or would prefer a managed version, you can reach out to me [here](jacobdietle@generateleverage.com) to discuss implementation)

**Step by Step Setup:**

1. **Clone Workflow to Pipedream using this [link](https://pipedream.com/new?h=tch_5ofXeg&via=digital-leverage).**


2. **Setup GCP Secrets according to this Pipedream [guide](https://pipedream.com/apps/gmail-custom-oauth).**


3. **Context sourcing: Find your brand book and other company context for use in config file**

4. **Config File Setup:**
    - **Mapping your company information into the config format:**
        - Review the Lease.ai config file for example of how to setup correctly
        - Use provided template to insert your company context into the template. Using an LLM to do this for you is a good idea ;)
    - **Label Setup:**
        - The first thing you will notice in the config file is a nested list of labels. Go to the last python step in the workflow called `label_setup_script_disable_after_setup`. 
            - This script takes a list of labels of user set labels, creates each one in the Gmail API, and returns a nested list of labels by category with their corresponding Gmail API `label_id`.
            - This nested list corresponds to the semantic router layers, which you can customize as well (I do not recommend changing the `EmailClassification` and `EmailRelevancy` classes as their logic is generic)
            - Customize the label list to fit your sales process, run the script, and copy and paste the complete `label_name` and `label _id` list into the config.
    - **Set link injection and signature settings:** Any links you want the Inbox Assistant to use (case studies, scheduling links, etc.) are set here. You can also setup your signature as emails created via the API do not automatically use your signature set in the Gmail UI.
    - **Set Auto-reply or Auto-draft settings:** 0 for auto-draft and 1 for auto-reply. Use auto-reply at your own risk. 
    - **Set Whitelist settings:** This allows you to safely test the auto-reply functionality with guardrails, when turned on, Inbox assistant will only be able to send replies to whitelisted domains, allowing you leave the auto-reply setting on without concern if set to only your company domain. 0 for off, 1 for on.

5. **Hubspot Private App Setup (Optional)**

- You just need to create a Hubspot developer account, create a test app and configure the Pipedream Hubspot dev app accordingly (set scopes for app to allow all CRM permissions). Get started [here](https://developers.hubspot.com/get-started).

6. **Testing & Deployment**
    - Test the config file to make sure it runs and exports correctly. 
        - We recommend starting with the auto-reply setting turned on with the whitelist setting active. This allows you to test a deployed version that will autoreply but is limited to autoreplying to approved email addresses.
    - Test each code step individually. (You will likely need to test the drafting step several times to find the drafting tone of voice and style that you want)
    - Deploy the workflow and begin sending test emails to the inbox to measure end to end functionality. 
    - Swap the reply settings from auto-reply to auto-draft (or not, again up to you) and turn off the whitelist setting. You now have a Gen AI Sales Inbox & CRM Assistant. 


### License

This app is ***source-available for noncommercial use***. I previously open-sourced the proof of concept of this project (check out the legacy branch) and am considering alternative licensing options.

If you are interested in a commercial license, I'd love to hear from you, please reach out to me [here](https://ihb0ndabs87.typeform.com/to/Eo8FHOYh#comapany_name=xxxxx). To be transparent, I actively testing and exploring pricing models to find what works for me and my (assumed) target audiences.

I am currently offering one time license purchase for self setup and hosting; I also offer managed deployments as a service. This is subject to change as I test and validate assumptions.

### Feedback & Testing:

**All feedback is welcome (especially constructive criticism)** - I am still exploring where to take this application. Feel free to open an issue in this repo.

If you are interested in testing new features, I am open to granting more permissive licenses as a part of a product feedback and testing.

For any feedback or inquiries, you can reach me at jacobdietle@generateleverage.com 
