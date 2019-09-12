import base64
import requests
import json
from datetime import datetime
from stubhubz.dynamodb import Event
from stubhubz.model import TicketSource

class AuthToken:
    """Reprents a logged in session for either the V2 or V3 API, i.e. has the bear/access token"""
    def __init__(self, response):
        if response.status_code != 200:
            raise RuntimeError('Login failed. Response status code: ' + str(response.status_code) + '. Text: ' + str(response.text))
        self.access_token = response.json()['access_token']
        self.refresh_token = response.json()['refresh_token']

class StubHubApi(TicketSource):
    """Represents the StubHub API"""

    def __init__(self, v2_consumer_key, v2_consumer_secret, v2_scope, v3_consumer_key, v3_consumer_secret, user, password):
        self.v2_consumer_key = v2_consumer_key
        self.v2_consumer_secret = v2_consumer_secret
        self.v2_scope = v2_scope
        self.v3_consumer_key = v3_consumer_key
        self.v3_consumer_secret = v3_consumer_secret
        self.user = user
        self.password = password
        self.v2_auth_token = None
        self.v3_auth_token = None

    def __str__(self):
        return "StubHub API"

    def authenticate(self, is_v3):
        """Returns StubHub access token. Should be called before StubHub API calls. Can be called multiple times."""
        if is_v3:
            if self.v3_auth_token is None:
                consumer_token = base64.b64encode((self.v3_consumer_key + ':' + self.v3_consumer_secret).encode('utf-8'))
                url = 'https://api.stubhub.com/sellers/oauth/accesstoken'
                headers = {
                    'Authorization': 'Basic ' + consumer_token.decode('utf-8'),
                    'Content-Type': 'application/json'
                }
                params = {'grant_type': 'client_credentials'}
                payload = {
                    'username': self.user,
                    'password': self.password
                }
                auth_response = requests.post(url, headers=headers, params=params, json=payload)
                self.v3_auth_token = AuthToken(auth_response)
                self.v3_consumer_key = None
                self.v3_consumer_secret = None
            return self.v3_auth_token.access_token
        else:
            if self.v2_auth_token is None:
                consumer_token = base64.b64encode((self.v2_consumer_key + ':' + self.v2_consumer_secret).encode('utf-8'))
                url = 'https://api.stubhub.com/login'
                headers = {
                    'Content-Type': 'application/x-www-form-urlencoded',
                    'Authorization': 'Basic ' + consumer_token.decode('utf-8')}
                body = {
                    'grant_type': 'password',
                    'username': self.user,
                    'password': self.password,
                    'scope': self.v2_scope}
                auth_response = requests.post(url, headers=headers, data=body)
                self.v2_auth_token = AuthToken(auth_response)
                self.v2_consumer_key = None
                self.v2_consumer_secret = None
                self.v2_scope = None
            return self.v2_auth_token.access_token

    def get_event_info(self, event_id):
        """Retrieves basic info about an event as a dynamodb.Event or None if not found."""
        #TODO not sure which ID to use for NZ events
        url = 'https://api.stubhub.com/sellers/search/events/v3'
        headers = {
            'Authorization': 'Bearer ' + self.authenticate(True),
            'Accept': 'application/json',
            'Accept-Encoding': 'application/json'
        }
        params = {'id': str(event_id)}
        response = requests.get(url, headers=headers, params=params)
        if response.status_code != 200:
            raise RuntimeError('Could not get Event {} from StubHub. Status: {}. Text: {}'.format(event_id, response.status_code, response.text))
        jsonResponse = json.loads(response.text)
        if 'numFound' in jsonResponse:
            if jsonResponse['numFound'] != 1:
                raise RuntimeError('Search for Event {} returned more than one result. Results: {}'.format(event_id, jsonResponse))
            eventJson = jsonResponse['events'][0]
            event = Event(eventJson['id'])
            event.name = eventJson['description']
            event.date_time = datetime.strptime(eventJson['eventDateLocal'], '%Y-%m-%dT%H:%M:%S%z')
            event.event_status = eventJson['status']
            event.venue_name = eventJson['venue']['name']
            event.venue_city = eventJson['venue']['city']
            performers = []
            for performer in eventJson['performers']:
                performers.append(performer['name'])
            event.primary_performer = ', '.join(performers)
            return event
        return None

    def search_events(self, name, city, country):
        """Search for events returning (as text) given the search criteria."""
        #TODO doesn't return hits for NZ
        url = 'https://api.stubhub.com/sellers/search/events/v3'
        headers = {
            'Authorization': 'Bearer ' + self.authenticate(True),
            'Accept': 'application/json',
            'Accept-Encoding': 'application/json'
        }
        params = {
            'name': name,
            'city': city,
            'country': country,
            'parking': 'false',
            'rows': 50
        }
        search_results = json.loads(requests.get(url, headers=headers, params=params).text)

        result = "Number of events found: " + (str(search_results['numFound']) if 'numFound' in search_results else "0") + "\n"
        for event in search_results['events']:
            result += "ID: {}, Name: {}, Performer: {}, Venue: {} ({}), Date: {}\n".format(
                event['id'], event['name'], event['performers'][0]['name'], event['venue']['name'], event['venue']['city'], event['eventDateLocal']
            )
        return result

    # Retrieves the available zones for an event. Array of zone dictionary objects ('id', 'name', section dictionary objects)
    def get_section_zones(self, event_id):
        url = 'https://api.stubhub.com/partners/catalog/events/v3/{}/sectionZones'.format(event_id)
        headers = {
            'Authorization': 'Bearer ' + self.authenticate(True),
            'Accept': 'application/json',
            'Accept-Encoding': 'application/json'
        }
        response = requests.get(url, headers=headers)
        if response.status_code != 200:
            raise RuntimeError('Could not get Section Zones for Event {} from StubHub. Status: {}. Text: {}'.format(event_id, response.status_code, response.text))
        jsonResponse = json.loads(response.text)
        return jsonResponse['zones']

    # Find listings for an event by zone ID
    def find_listings(self, event_id, zone_id_list, quantity):
        url = 'https://api.stubhub.com/sellers/find/listings/v3/'
        headers = {
            'Authorization': 'Bearer ' + self.authenticate(True),
            'Accept': 'application/json',
            'Accept-Encoding': 'application/json'
        }
        params = {
            'eventid': event_id,
            'sort': 'currentprice asc',
            'zoneIdList': str(zone_id_list),
            'quantity': str(quantity)
        }
        response = requests.get(url, headers=headers, params=params)
        if response.status_code != 200:
            raise RuntimeError('Could not get Listings for Event {} from StubHub. Status: {}. Text: {}'.format(event_id, response.status_code, response.text))
        return json.loads(response.text)