import json
import requests
from datetime import datetime
from stubhubz.dynamodb import Event
from stubhubz.model import TicketSource

class TicketMasterApi(TicketSource):
    """Represents the TicketMaster API"""

    def __init__(self, api_key):
        self.api_key = api_key

    def __str__(self):
        return "TicketMaster API"

    def get_event_info(self, event_id):
        """Retrieves basic info about an event as a dynamodb.Event or None if not found."""
        _url = 'https://app.ticketmaster.com/discovery/v2/events/' + str(event_id) + '.json'
        _params = {'apikey': str(self.api_key)}
        _response = requests.get(_url, params=_params)
        if _response.status_code == 404:
            return None
        elif _response.status_code != 200:
            raise RuntimeError('Could not get Event {} from TicketMaster. Status: {}. Text: {}'.format(event_id, _response.status_code, _response.text))
        _event_json = json.loads(_response.text)
        _event = Event(_event_json['id'])
        _event.name = _event_json['name']
        _event.date_time = datetime.strptime(_event_json['dates']['start']['dateTime'], '%Y-%m-%dT%H:%M:%S%z')
        _event.event_status = self._map_status(_event_json['dates']['status']['code'])
        _event.venue_name = _event_json['_embedded']['venues'][0]['name']
        _event.venue_city = _event_json['_embedded']['venues'][0]['city']['name']
        performers = []
        for performer in _event_json['_embedded']['attractions']:
            performers.append(performer['name'])
        _event.primary_performer = ', '.join(performers)
        return _event

    def search_events(self, name, city, country):
        """Search for events returning (as text) given the search criteria."""
        _url = 'https://app.ticketmaster.com/discovery/v2/events.json'
        _params = {'apikey': str(self.api_key), 'keyword': name, 'city': city, 'countryCode': country.lower(), 'locale': 'en'}
        _response = requests.get(_url, params=_params)
        if _response.status_code != 200:
            raise RuntimeError('Could not get search for events from TicketMaster. Status: {}. Text: {}'.format(_response.status_code, _response.text))
        _search_results = json.loads(_response.text)
        _result = "Number of events found: " + str(_search_results['page']['totalElements']) + "\n"
        for _event in _search_results['_embedded']['events']:
            _result += "ID: {}, Name: {}, Performer: {}, Venue: {} ({}), Date: {}\n".format(
                _event['id'], _event['name'], _event['_embedded']['attractions'][0]['name'], _event['_embedded']['venues'][0]['name'],
                _event['_embedded']['venues'][0]['city']['name'], _event['dates']['start']['dateTime']
            )
        return _result

    def _map_status(self, ticketmaster_status):
        """Maps TicketMaster status to StubHubz status"""
        if ticketmaster_status == "onsale":
            return "Active"
        else:
            return "Inactive"
