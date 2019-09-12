# Retrieves data from the StubHub API. This is intended to be invoked by the command-line
#
# Requirements
# - AWS credentials configured with one of these methods http://docs.aws.amazon.com/cli/latest/userguide/cli-chap-getting-started.html#config-settings-and-precedence
# - 'aws.ini' file with the AWS details
# - 'keys.ini' file with the StubHub generated API keys and credentials

import argparse
import configparser
import datetime

from stubhubz.dynamodb import StubHubzDynamoDb
from stubhubz.ticketmaster import TicketMasterApi
from stubhubz.stubhub import StubHubApi
from stubhubz.stubhubz import StubHubz

# =====================
# Functions and Classes
# =====================

# Get config from .ini file
def load_config(file_name):
    _config = configparser.ConfigParser()
    _config.read(file_name)
    return _config

# Ask for date when updating an event manually
def ask_date(default_date_time):
    _result = None
    _date_time_format = '%Y-%m-%dT%H:%M:%S%z'
    _default_date_time_str = '' if not default_date_time else default_date_time.strftime(_date_time_format)
    while _result == None:
        _candidate = input('Date time (default is \'{}\'. Warning issue #9, date is stored as UTC): '.format(_default_date_time_str))
        if not _candidate:
            _candidate = _default_date_time_str
        try:
            _result = datetime.datetime.strptime(_candidate, _date_time_format)
        except Exception as err:
            print('Error: {}. The date time \'{}\' is invalid. Format should be \'{}\''.format(err, _candidate, _date_time_format))
    return _result

# Ask for generic parameter when updating an event manually
def ask_generic_input(prompt_name, default_value):
    _result = input('{} (default is \'{}\'): '.format(prompt_name, default_value))
    if not _result:
        _result = default_value
    return _result

# Ask for status when updating an event manually
def ask_status(status_name, default_value):
    _result = None
    while not _result == 'Active' and not _result == 'Inactive':
        _result = input('{} status (Valid values: \'Active\', \'Inactive\'. Default is \'{}\'): '.format(status_name, default_value))
        if not _result:
            _result = default_value
    return _result

# ====
# Main
# ====

# Parse arguments
parser = argparse.ArgumentParser(description='Query StubHub/TicketMaster API and track within StubHubz. Event IDs are 7 digit numbers in the URL for the event, e.g. 104128143 is Liverpool FC at Fenway Jul 21 2019')
subparsers = parser.add_subparsers(dest='target', help='List of possible domains to retrieve')
parser_event = subparsers.add_parser('event', help='Retrieve event information from StubHub/TicketMaster')
parser_event.add_argument('id', help='The ID of the event')
parser_event_search = subparsers.add_parser('event-search', help='Search for an event on StubHub/TicketMaster')
parser_listings = subparsers.add_parser('listings', help='Retrieve listing information for an event from StubHub')
parser_listings.add_argument('id', type=int, help='The ID of the event')
parser_track_event = subparsers.add_parser('track-event', help='Adds an event to the Events table for tracking')
parser_track_event.add_argument('id', type=int, help='The ID of the event')
parser_update_event = subparsers.add_parser('update-event', help='Updates an event\'s metadata info within the Events table from StubHub')
parser_update_event.add_argument('id', type=int, help='The ID of the event')
parser_update_event_manual = subparsers.add_parser('update-event-manual', help='Updates an event\'s metadata info within the Events table from command line input')
parser_scrape = subparsers.add_parser('scrape', help='Checks StubHub prices for events in the Events table')
parser_scrape.add_argument('id', type=int, nargs='?', default=None, help='The ID of the event')
parser_scrape.add_argument('--sns', action='store_true', help='Whether to trigger a new price history event to the SNS topic in \'aws.ini\'')
parser_dump_events = subparsers.add_parser('dump-events', help='Dumps events out of Event table')
parser_price_history = subparsers.add_parser('dump-price-history', help='Dumps price history out of the PriceHistory table for an event')
parser_price_history.add_argument('ids', type=int, nargs='+', help='The IDs of the event separated by spaces')
parser_price_history.add_argument('--format', dest='format', choices=['text', 'json'], default='text')
parser_price_history.add_argument('--s3', action='store_true', help='Whether to store the result to the S3 bucket in \'aws.ini\'. Only if format=\'json\'')
parser_publish_sns = subparsers.add_parser('publish-sns', help='Publishes event IDs to AWS SNS topic to trigger generation of price history to S3')
parser_publish_sns.add_argument('ids', type=int, nargs='+', help='The ID of the events separated by spaces')
parser_dynamodb = subparsers.add_parser('dynamodb', help='Create or drop AWS DynamoDB tables')
parser_dynamodb.add_argument('action', choices=['create', 'drop'])
parser.add_argument('-tm', '--ticketmaster', action='store_true', help='Source info from TicketMaster (default is StubHub)')
parser.add_argument('--debug', action='store_true', help='print debug messages')
args = parser.parse_args()
DEBUG = args.debug
if args.target == None:
    parser.print_help()
    exit()

# Load config
keys_config = load_config('keys.ini')
aws_config = load_config('aws.ini')

# Init business logic class
dynamodb = StubHubzDynamoDb(aws_config['General']['Region'], aws_config['DynamoDB']['Endpoint'])
stubhub_api = StubHubApi(keys_config['StubHubV2']['ConsumerKey'], keys_config['StubHubV2']['ConsumerSecret'], keys_config['StubHubV2']['Scope'],
                         keys_config['StubHubV3']['ConsumerKey'], keys_config['StubHubV3']['ConsumerSecret'],
                         keys_config['Credentials']['User'], keys_config['Credentials']['Password'])
ticketmaster_api = TicketMasterApi(keys_config['TicketMaster']['ApiKey'])
stubhubz = StubHubz(stubhub_api, ticketmaster_api, dynamodb, aws_config['General']['Region'], DEBUG)

ticket_source = ticketmaster_api if args.ticketmaster else stubhub_api

if args.target == 'event':
    print('Getting event info for event {} from {}'.format(args.id, ticket_source))
    _event = stubhubz.get_ticketsource_event(args.id, ticket_source)
    print(_event)
elif args.target == 'event-search':
    print("StubHub event search tips:")
    print(" AND terms:       name=San Francisco Giants")
    print(" Specific phrase: name=\"San Francisco\" Giants")
    print(" Exclude terms:   name=\"San Francisco\" -Giants")
    print(" Union terms:     city=\"San Francisco\"|\"New York\"|Seattle")
    print()
    _name = input("Enter name of the event: ")
    _city = input("Enter city of the event (or blank for 'Boston'): ")
    if _city == "":
        _city = "Boston"
    _country = input("Enter country of the event (or blank for 'US'): ")
    if _country =="":
        _country = "US"
    if DEBUG:
        print("Search for event name='{}' in city='{}' and country='{}'".format(_name, _city, _country))
    print(stubhubz.search_events(_name, _city, _country, ticket_source))
elif args.target == 'listings':
    print('Getting listings for event {}'.format(args.id))
    _listings_by_zone = stubhubz.get_stubhub_listing(args.id)
    for _zone in sorted(_listings_by_zone.keys()):
        _listing = _listings_by_zone[_zone]
        print('Zone: {}, zone ID: {}, total listings: {}, total tickets: {}. Listings: \n{}'.format(_zone, _listing['zone_id'], _listing['totalListings'], _listing['totalTickets'], _listing['listings']))
elif args.target == 'track-event':
    print('Adding event {} for tracking'.format(args.id))
    stubhubz.track_event(args.id)
    print('Updating event {} for tracking'.format(args.id))
    stubhubz.update_event(args.id)
elif args.target == 'update-event':
    print('Updating event {} for tracking'.format(args.id))
    stubhubz.update_event(args.id)
elif args.target == 'update-event-manual':
    _event_id = None
    while _event_id == None:
        try:
            _event_id = int(input('Which event do you want to update? '))
        except:
            print('Error. Please enter valid event ID (it''s an intger)')
    _event = stubhubz.get_event(_event_id)
    if _event == None:
        print('Event \'{}\' does not exist in Events table'.format(_event_id))
    else:
        _new_primary_performer = ask_generic_input('Primary performer', _event.primary_performer)
        _default_name = ''
        if _new_primary_performer:
            _default_name = _new_primary_performer + ' Tickets'
        elif _event.name:
            _default_name = _event.name
        _new_name = ask_generic_input('Name', _default_name)
        _new_venue_city = ask_generic_input('Venue city', _event.venue_city)
        _new_venue_name = ask_generic_input('Venue name', _event.venue_name)
        _new_date_time = ask_date(_event.date_time)
        _new_event_status = ask_status('Event', _event.event_status)
        _new_scrape_status = ask_status('Scrape', _event.scrape_status)
    print('Update event {} with the following? '.format(_event_id))
    print(' Primary performer: {}'.format(_new_primary_performer))
    print(' Name:              {}'.format(_new_name))
    print(' Venue city:        {}'.format(_new_venue_city))
    print(' Venue name:        {}'.format(_new_venue_name))
    print(' Date time:         {}'.format(_new_date_time))
    print(' Event status:      {}'.format(_new_event_status))
    print(' Scrape status:     {}'.format(_new_scrape_status))
    _confirmation = input('Type \'Y\' to update (anything else will exit): ')
    if _confirmation == 'Y' or _confirmation == 'y':
        stubhubz.update_event_manual(_event_id, _new_primary_performer, _new_name, _new_venue_city, _new_venue_name, _new_date_time, _new_event_status, _new_scrape_status)
        print('Event updated')
elif args.target == 'scrape':
    _scraped_events = []
    if args.id is None:
        print('Scraping events...')
        _scraped_events = stubhubz.scrape()
    else:
        print('Scraping event {}'.format(args.id))
        _scraped_events = stubhubz.scrape(args.id)
    if args.sns:
        _topic = aws_config['SNS']['NewPriceHistoryTopic']
        print('Publishing scraped events to SNS topic {}'.format(_topic))
        stubhubz.notify_new_price_history(_topic, _scraped_events)
elif args.target == 'dump-events':
    print('Dumping Event table...')
    _events = sorted(stubhubz.get_events(), key=lambda event: event.date_time)
    for event in _events:
        print(str(event) + '\n')
elif args.target == 'dump-price-history':
    if args.s3 and args.format != 'json':
        print('Aborting. Publishing to S3 can only be done if the format is \'json\'.')
    else:
        _s3_bucket = aws_config['S3']['Bucket'] if args.s3 else None
        _s3_key_prefix = aws_config['S3']['KeyPrefix'] if args.s3 else None
        for _event_id in args.ids:
            print(stubhubz.get_price_history_formatted(_event_id, args.format, _s3_bucket, _s3_key_prefix))
elif args.target == 'publish-sns':
    print('Publishing SNS topic')
    _topic = aws_config['SNS']['NewPriceHistoryTopic']
    stubhubz.notify_new_price_history(_topic, args.ids)
elif args.target == 'dynamodb':
    _confirmation = input("Are you sure you want to '" + args.action + "' for endpoint '" + aws_config['Endpoint'] + "'? Type 'YES' to proceed: ")
    if _confirmation != 'YES':
        print('Aborting...')
    else:
        if args.action == 'create':
            print('Creating DynamoDB tables...')
            dynamodb.create_tables()
        elif args.action == 'drop':
            print('Dropping DynamoDB tables...')
            dynamodb.drop_tables()