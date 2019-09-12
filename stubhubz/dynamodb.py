import configparser

from pynamodb.attributes import ListAttribute
from pynamodb.attributes import NumberAttribute
from pynamodb.attributes import UnicodeAttribute
from pynamodb.attributes import UTCDateTimeAttribute

from pynamodb.models import Model

REGION_NAME = None
ENDPOINT_URL = None

class Event(Model):
    class Meta:
        table_name = 'Event'
        region = REGION_NAME
        host = ENDPOINT_URL
        write_capacity_units = 1
        read_capacity_units = 1
    id = NumberAttribute(hash_key=True)
    name = UnicodeAttribute(null=True)
    date_time = UTCDateTimeAttribute(null=True)
    event_status = UnicodeAttribute(null=True)
    venue_name = UnicodeAttribute(null=True)
    venue_city = UnicodeAttribute(null=True)
    primary_performer = UnicodeAttribute(null=True)
    last_scraped_date_time = UTCDateTimeAttribute(null=True)
    scrape_status = UnicodeAttribute(null=True)

    def __str__(self):
        return 'Event id={}, name={}, date_time={}, event_status={}, venue_name={}, venue_city={}, primary_performer={}, last_scraped_date_time={}, scrape_status={}'.format(
            self.id, self.name, self.date_time, self.event_status, self.venue_name, self.venue_city, self.primary_performer, self.last_scraped_date_time, self.scrape_status)

class PriceHistory(Model):
    class Meta:
        table_name = 'PriceHistory'
        region = REGION_NAME
        host = ENDPOINT_URL
        write_capacity_units = 1
        read_capacity_units = 1
    event_id = NumberAttribute(hash_key=True)
    date_time = UTCDateTimeAttribute(range_key=True)
    zone_prices = ListAttribute()

    def __str__(self):
        result = 'PriceHistory event_id={}, date_time={}, zone_prices='.format(self.event_id, self.date_time)
        for z in sorted(self.zone_prices, key=lambda k: k['zone_name']):
            result += '\n zone_id={}, zone_name={:10} min_price={:.2f}, avg_price={:.3f}, max_ticket_quantity={:2}, total_tickets={:3}, total_listings={:2}'.format(
                z['zone_id'], z['zone_name'] + ',', z['min_price'], z['avg_price'], z['max_ticket_quantity'], z['total_tickets'], z['total_listings'])
        return result

class StubHubzDynamoDb:

    def __init__(self, region, endpoint):
        REGION_NAME = region
        ENDPOINT_URL = endpoint

    # Creates the tables
    def create_tables(self):
        if not Event.exists():
            Event.create_table(wait = True)
            print('Created Event table')
        if not PriceHistory.exists():
            PriceHistory.create_table(wait = True)
            print('Created PriceHistory table')

    # Drops the tables
    def drop_tables(self):
        if Event.exists():
            Event.delete_table()
        else:
            print('Can\'t drop Event table because it does not exist')
        if PriceHistory.exists():
            PriceHistory.delete_table()
            print('Dropped PriceHistory table')
        else:
            print('Can\'t drop PriceHistory table because it does not exist')
    
    # Adds an event to the Event table
    def add_event(self, event_id):
        event_item = Event(event_id)
        event_item.save()

    # Returns True if an event exists, otherwise False
    def has_event(self, event_id):
        if self.get_event(event_id) is None:
            return False
        else:
            return True

    # Retrieves an Event or None if it doesn't exist
    def get_event(self, event_id):
        try:
            return Event.get(event_id)
        except Event.DoesNotExist:
            return None

    # Retrieves all events
    def get_events(self):
        return Event.scan()

    def add_price_history(self, event_id, date_time, zone_prices):
        price_history_item = PriceHistory(event_id, date_time, zone_prices=zone_prices)
        price_history_item.save()

    def get_price_history(self, event_id):
        return PriceHistory.query(event_id)