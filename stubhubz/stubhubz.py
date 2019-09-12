import botocore.session
import datetime
import gzip
import json

# The business logic of StubHubz
class StubHubz:
    def __init__(self, stubhub, ticketmaster, dynamo, region, debug):
        self.stubhub = stubhub
        self.ticketmaster = ticketmaster
        self.dynamo = dynamo
        self.region = region
        self.debug = debug

    def get_ticketsource_event(self, event_id, ticket_source):
        """Return info about an event from a TicketSource"""
        return ticket_source.get_event_info(event_id)

    def search_events(self, name, city, country, ticket_source):
        """Search for events from a TicketSource by name, city, and country"""
        return ticket_source.search_events(name, city, country)

    def get_stubhub_listing(self, event_id):
        """Get listings from StubHub for an event"""
        _zones = self.stubhub.get_section_zones(event_id)
        _listings_by_zone = {}
        for _zone in _zones:
            _listings = self.stubhub.find_listings(event_id, _zone['id'], 1)
            _listings['zone_name'] = _zone['name']
            _listings['zone_id'] = _zone['id']
            _listings_by_zone[_zone['name']] = _listings
        return _listings_by_zone

    def track_event(self, event_id):
        """Add a StubHub event for tracking in StubHubz"""
        if self.dynamo.has_event(event_id):
            pass
        else:
            self.dynamo.add_event(event_id)

    def get_event(self, event_id):
        """Retrieves an event from AWS DynamoDB"""
        return self.dynamo.get_event(event_id)

    def update_event(self, event_id):
        """Updates a AWS DynamoDB Event with info from StubHub"""
        dynamo_event = self.dynamo.get_event(event_id)
        if dynamo_event is None:
            raise RuntimeError('Cannot update event {} as it does not exist. You need to add it first using the "add-event" action.'.format(event_id))
        ticketsource_event = self.get_ticketsource_event(event_id, self.stubhub)
        print('Retrieved event from StubHub: {}'.format(ticketsource_event))
        if ticketsource_event.id == event_id:
            if ticketsource_event.event_status == 'Active' or ticketsource_event.event_status == 'Contingent' or ticketsource_event.event_status == 'Postponed'  or ticketsource_event.event_status == 'Scheduled':
                ticketsource_event.scrape_status = 'Active'
            else:
                ticketsource_event.scrape_status = 'Inactive'
            ticketsource_event.last_scraped_date_time = datetime.datetime.utcnow()
            ticketsource_event.save()
        else:
            raise RuntimeError('OK something weird went on, we requested event {} but StubHub API returned something else. Response was: {}'.format(event_id, ticketsource_event))

    def update_event_manual(self, event_id, primary_performer, name, venue_city, venue_name, date_time, event_status, scrape_status):
        """Updates a AWS DynamoDB Event with info manually entered by the user"""
        dynamo_event = self.dynamo.get_event(event_id)
        if dynamo_event is None:
            raise RuntimeError('Cannot update event {} as it does not exist. You need to add it first using the "add-event" action.'.format(event_id))
        dynamo_event.primary_performer = primary_performer
        dynamo_event.name = name
        dynamo_event.venue_city = venue_city
        dynamo_event.venue_name = venue_name
        dynamo_event.date_time = date_time
        dynamo_event.event_status = event_status
        dynamo_event.scrape_status = scrape_status
        dynamo_event.save()

    def scrape(self, event_id=None):
        _scraped_events = []
        if event_id is None:
            events = self.dynamo.get_events()
            for event in events:
                if self._scrape(event):
                    _scraped_events.append(event.id)
        else:
            event = self.dynamo.get_event(event_id)
            if event is None:
                print(' No such event {} in DynamoDB. Maybe add it to DynamoDB first?'.format(event_id))
            else:
                if self._scrape(event):
                    _scraped_events.append(event.id)
        return _scraped_events

    # Scrapes an Event (i.e. query StubHub for price info and store in DynamoDB) and updates the
    # Event's last scrape time. Returns True if the event was scraped or False (e.g. Event has
    # expired, is no longer active)
    def _scrape(self, event):
        print('Scarping event \'{}\' ({})...'.format(event.name, event.id))
        if event.scrape_status != 'Active':
            print(' Skipping event because it is no longer active')
            return False
        if self._date_check(event.date_time, 120):
            print(' Skipping event because it has expired. Event was scheduled for {}'.format(event.date_time))
            event.update({
                    'last_scraped_date_time': {'action': 'put', 'value': datetime.datetime.utcnow()},
                    'scrape_status': {'action': 'put', 'value': 'Inactive'}
            })
            return False
        zone_prices = [] # array of avg_price, max_ticket_quantity, min_price, total_listings, total_tickets, zone_id, zone_name
        listings_by_zone = self.get_stubhub_listing(event.id)
        if self.debug:
            print(' Retrieved listings for event {} from StubHub. Listings: {}'.format(event.id, listings_by_zone))
        for zone_name, zone_listings in listings_by_zone.items():
            min_price = 9999999
            max_quantity = 0
            tickets_seen = 0
            total_price = 0
            for listing in zone_listings['listings']:
                quantity = listing['quantity']
                if quantity > max_quantity:
                    max_quantity = quantity
                tickets_seen += quantity
                price = listing['pricePerProduct']['amount']
                if price < min_price:
                    min_price = price
                total_price += price * quantity
            avg_price_accurate = True if tickets_seen == zone_listings['totalTickets'] else False
            zone_prices.append(self._build_zone_price(zone_listings['zone_id'], zone_name, min_price, total_price/tickets_seen, None,
                    zone_listings['totalTickets'], zone_listings['totalListings'], avg_price_accurate))
        self.dynamo.add_price_history(event.id, datetime.datetime.utcnow(), zone_prices)
        event.update({'last_scraped_date_time': {'action': 'put', 'value': datetime.datetime.utcnow()}})
        print(' Scraped event')
        return True

    def get_events(self):
        return self.dynamo.get_events()

    def get_price_history(self, event_id):
        return self.dynamo.get_price_history(event_id)

    # Retrieves price history for an event of DynamoDB in a specified 'format' (text or json).
    # Stores the result if s3_bucket and s3_key_prefix are specified and the format is json
    def get_price_history_formatted(self, event_id, format, s3_bucket, s3_key_prefix):
        print('Retrieving price history from DynamoDB for event ID {}...', event_id)
        _price_history = self.dynamo.get_price_history(event_id)
        print(' Price history retrieved. Formatting...', event_id)
        _result = ""
        if format == 'json':
            _price_histories = [] # array of zone -> date, price
            _data_by_zone = dict()
            for _price_history in self.get_price_history(event_id): # array of date -> zones, prices
                for _zone_price in _price_history.zone_prices:
                    _zone_name = _zone_price['zone_name']
                    _data_zone_prices = None
                    if _zone_name in _data_by_zone:
                        _data_zone_prices = _data_by_zone[_zone_name]
                        _data_zone_prices.append(self._build_price_history(_price_history, _zone_price))
                    else:
                        _data_by_zone[_zone_name] = [self._build_price_history(_price_history, _zone_price)]
                        _price_histories.append({'zone': _zone_name, 'data': _data_by_zone[_zone_name]})
            _price_histories = sorted(_price_histories, key=lambda k: k['zone'])
            _json_text = json.dumps(_price_histories)
            if s3_bucket is not None and s3_key_prefix is not None:
                print(' Saving price history JSON to S3...', event_id)
                _aws_session = botocore.session.get_session()
                _aws_client = _aws_session.create_client('s3', self.region)
                _aws_client.put_object(ACL='private', Body=gzip.compress(_json_text.encode('utf-8')), Bucket=s3_bucket, ContentEncoding='gzip',
                    ContentType='application/javascript', Key=s3_key_prefix + '/' + str(event_id) + '.js')
            return _json_text
        else:
            for _price_history in self.get_price_history(event_id):
                _result += str(_price_history) + '\n'
        return _result

    def _date_check(self, event_date, grace_min):
        delta = datetime.datetime.utcnow().replace(tzinfo=datetime.timezone.utc) - event_date
        return delta.total_seconds() / 60 > grace_min

    """Builds a single price history of an event's zone for storage in S3 JSON file."""
    def _build_price_history(self, price_history, zone_price):
        result = {
            'x': price_history.date_time.isoformat(),
            'y': round(float(zone_price['min_price']), 2),
            'avgPrice': round(float(zone_price['avg_price']), 2),
            'totalTickets': zone_price['total_tickets'],
            'totalListings': zone_price['total_listings']
        }
        if 'avg_price_accurate' in zone_price:
            result['avgPriceAccurate'] = zone_price['avg_price_accurate']
        return result

    def notify_new_price_history(self, sns_topic, event_ids):
        if len(event_ids) == 0:
            return
        _aws_session = botocore.session.get_session()
        _aws_client = _aws_session.create_client('sns', self.region)
        _aws_client.publish(TopicArn=sns_topic, MessageStructure='json',
            Message=json.dumps({'default': json.dumps({'action': 'dump_price_history', 'event_ids': event_ids})})
        )

    """
    Builds a dictionary representing a single event's single zone's price summary for storage in DynamoDB. 'avg_price_accurate' means 
    whether we saw all the listings or not.
    """
    def _build_zone_price(self, zone_id, zone_name, min_price, avg_price, max_ticket_quantity, total_tickets, total_listings, avg_price_accurate):
        return {
            'zone_id': zone_id,
            'zone_name': zone_name,
            'min_price': min_price,
            'avg_price': avg_price,
            'avg_price_accurate': avg_price_accurate,
            'max_ticket_quantity': max_ticket_quantity,
            'total_tickets': total_tickets,
            'total_listings': total_listings
        }

