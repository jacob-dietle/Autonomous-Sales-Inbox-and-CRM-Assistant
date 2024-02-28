# pipedream add-package simplejson
# pipedream add-package delorean
# pipedream add-package hubspot-api-client

from hubspot.crm.contacts import SimplePublicObjectInput, ApiException as ContactsApiException, SimplePublicObjectInputForCreate
from hubspot.crm.deals import ApiException as DealsApiException, PublicObjectSearchRequest, SimplePublicObjectInputForCreate as SimplePublicObjectInputForCreateDeal, FilterGroup, Filter
from hubspot.crm.timeline import ApiException as TimelineApiException
import hubspot

class HubSpotManager:
    def __init__(self, pd):
        self.pd = pd
        self.access_token = pd.inputs["hubspot_developer_app"]["$auth"]["oauth_access_token"]
        self.client = hubspot.Client.create(access_token=self.access_token)

    def get_contact_by_email(self, email):
        print(f"Attempting to get contact by email: {email}")
        try:
            search_request = {
                "filterGroups": [{
                    "filters": [{
                        "propertyName": "email",
                        "operator": "EQ",
                        "value": email
                    }]
                }],
                "properties": ["email"],
                "limit": 1
            }
            response = self.client.crm.contacts.search_api.do_search(search_request)
            contacts = response.results
            if contacts:
                return contacts[0].id
            else:
                return None
        except ContactsApiException as e:
            print(f"Exception when searching for contact by email: {e}")
            return None

    def create_or_update_contact(self, email, contact_properties):
        contact_id = self.get_contact_by_email(email)
        if contact_id:
            self.update_contact(contact_id, contact_properties)
        else:
            self.create_contact(email, contact_properties)

    def create_contact(self, email, contact_properties):
        try:
            contact_properties["email"] = email
            simple_public_object_input_for_create = SimplePublicObjectInputForCreate(properties=contact_properties)
            api_response = self.client.crm.contacts.basic_api.create(simple_public_object_input_for_create=simple_public_object_input_for_create)
            print(f"Contact created with ID: {api_response.id}")
            return api_response.id
        except ContactsApiException as e:
            print(f"Exception when creating a new contact: {e}")
            return None

    def update_contact(self, contact_id, contact_properties):
        try:
            simple_public_object_input = SimplePublicObjectInput(properties=contact_properties)
            self.client.crm.contacts.basic_api.update(contact_id=contact_id, simple_public_object_input=simple_public_object_input)
            print(f"Contact {contact_id} updated with properties: {contact_properties}")
        except ContactsApiException as e:
            print(f"Exception when updating contact: {e}")

    def get_deal_by_contact_id(self, contact_id):
        print(f"Attempting to get deal by contact ID: {contact_id}")
        try:
            # Use the pseudo-property "associations.contact" to search for associated deals
            filter = Filter(
                property_name="associations.contact",
                operator="EQ",
                value=contact_id
            )
            filter_group = FilterGroup(filters=[filter])
            search_request = PublicObjectSearchRequest(filter_groups=[filter_group])
            
            # Execute the search request
            api_response = self.client.crm.deals.search_api.do_search(public_object_search_request=search_request)
            
            # Check if there are any associated deals
            if api_response.total > 0:
                # Return the first associated deal ID
                return api_response.results[0].id
            else:
                return None
        except ApiException as e:
            print(f"Exception when searching for associated deals: {e}")
            return None

    def create_deal(self, contact_id, deal_properties):
        print("Attempting to create a new deal with properties:", deal_properties)
        try:
            # Define the association to the contact
            associations = {
                "associations": [
                    {
                        "to": {"id": contact_id},
                        "types": [
                            {
                                "associationCategory": "HUBSPOT_DEFINED",
                                "associationTypeId": "3"
                            }
                        ]
                    }
                ]
            }
            # Include the associations in the deal creation request
            simple_public_object_input_for_create = SimplePublicObjectInputForCreateDeal(
                properties=deal_properties,
                **associations
            )
            api_response = self.client.crm.deals.basic_api.create(
                simple_public_object_input_for_create=simple_public_object_input_for_create
            )
            print(f"Deal created with ID: {api_response.id}")
            return api_response.id
        except DealsApiException as e:
            print(f"Exception when creating a new deal: {e}")
            return None

    def update_deal(self, deal_id, deal_properties):
        try:
            simple_public_object_input = SimplePublicObjectInput(properties=deal_properties)
            self.client.crm.deals.basic_api.update(deal_id=deal_id, simple_public_object_input=simple_public_object_input)
            print(f"Deal {deal_id} updated with properties: {deal_properties}")
        except DealsApiException as e:
            print(f"Exception when updating deal: {e}")

    def update_deal_stage(self, deal_id, stage_id):
        print(f"Attempting to update deal {deal_id} to stage {stage_id}")
        try:
            simple_public_object_input = SimplePublicObjectInput(properties={"dealstage": stage_id})
            self.client.crm.deals.basic_api.update(deal_id=deal_id, simple_public_object_input=simple_public_object_input)
            print(f"Deal stage updated for deal ID {deal_id}")
        except DealsApiException as e:
            print(f"Exception when updating deal stage: {e}")

    def create_timeline_event(self, contact_id, event_template_id, event_properties):
        print(f"Attempting to create timeline event for contact ID {contact_id}")
        try:
            timeline_event = {
                "eventTemplateId": event_template_id,
                "email": contact_id,
                "tokens": event_properties
            }
            self.client.crm.timeline.events_api.create(timeline_event=timeline_event)
            print(f"Timeline event created for contact ID {contact_id}")
        except TimelineApiException as e:
            print(f"Exception when creating timeline event: {e}")

def handler(pd: "pipedream"):
    print("Handler started")
    hubspot_manager = HubSpotManager(pd)
    email = pd.steps["parse_thread"]["most_recent_sender"]
    sentiment_and_funnel_stage_result = pd.steps["semantic_routers"]["Sentiment and Funnel Stage Result"]["label"]
    
    sentiment_and_funnel_stage_result = "appointment scheduled"

    print(f"sentiment_and_funnel_stage_result: {sentiment_and_funnel_stage_result}")

    # Map sentiment and funnel stage labels to HubSpot deal stages
    stage_mapping = {
        "appointment scheduled": "appointmentscheduled",
        "qualified to buy": "qualifiedtobuy",
        "presentation scheduled": "presentationscheduled",
        "decision maker bought in": "decisionmakerboughtin",
        "closed won": "closedwon",
        "closed lost": "closedlost"
    }

    if sentiment_and_funnel_stage_result.lower() in stage_mapping:
        stage_id = stage_mapping[sentiment_and_funnel_stage_result.lower()]
        contact_properties = {"email": email}  # Define contact properties based on your needs
        hubspot_manager.create_or_update_contact(email, contact_properties)

        contact_id = hubspot_manager.get_contact_by_email(email)
        if contact_id:
            print(f"Contact ID {contact_id} found, proceeding with deal checks")
            deal_id = hubspot_manager.get_deal_by_contact_id(contact_id)
            if deal_id:
                hubspot_manager.update_deal_stage(deal_id, stage_id)
            else:
                deal_properties = {
                    "dealname": "New Deal from Email",
                    "dealstage": stage_id,
                    "pipeline": "default"
                }
                deal_id = hubspot_manager.create_deal(contact_id, deal_properties)
        else:
            print("No contact ID found, exiting handler")
    else:
        print(f"The sentiment and funnel stage result '{sentiment_and_funnel_stage_result}' does not match any deal stage.")
