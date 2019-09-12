# AWS Lambda function for StubHubz

import json
import os

from stubhubz.dynamodb import StubHubzDynamoDb
from stubhubz.stubhub import StubHubApi
from stubhubz.stubhubz import StubHubz

DEBUG = False

def handler(event, context):
    global DEBUG
    if os.environ['STUBHUBZ_DEBUG'] == 'True':
        DEBUG = True
    stubhubz = initStubHubz()
    if 'Records' in event: # This is an SNS topic
        for record in event['Records']:
            handleEvent(stubhubz, json.loads(record['Sns']['Message']))
    else:
        handleEvent(stubhubz, event)
    return None

def handleEvent(stubhubz, event):
    print('Handling action: {}'.format(event['action']))
    if event['action'] == 'scrape':
        _scraped_events = []
        if 'event_id' in event:
            _scraped_events.append(stubhubz.scrape(event['event_id']))
        else:
            _scraped_events = stubhubz.scrape()
        if 'STUBHUBZ_SNS_TOPIC' in os.environ:
            _s3_topic = os.environ['STUBHUBZ_SNS_TOPIC']
            stubhubz.notify_new_price_history(_s3_topic, _scraped_events)
    elif event['action'] == 'dump_price_history':
        _event_ids = event['event_ids']
        if len(_event_ids) > 0:
            _s3_bucket = os.environ['STUBHUBZ_S3_BUCKET']
            _s3_key_prefix = os.environ['STUBHUBZ_S3_KEY_PREFIX']
            for _event_id in _event_ids:
                stubhubz.get_price_history_formatted(_event_id, 'json', _s3_bucket, _s3_key_prefix)

def initStubHubz():
    _region = os.environ['STUBHUBZ_REGION']
    _dynamodb_url = None
    _stubhub_v2_consumer_key = os.environ['STUBHUBZ_STUBHUB_V2_CONSUMER_KEY']
    _stubhub_v2_consumer_secret = os.environ['STUBHUBZ_STUBHUB_V2_CONSUMER_SECRET']
    _stubhub_v2_scope = os.environ['STUBHUBZ_STUBHUB_V2_SCOPE']
    _stubhub_v3_consumer_key = os.environ['STUBHUBZ_STUBHUB_V3_CONSUMER_KEY']
    _stubhub_v3_consumer_secret = os.environ['STUBHUBZ_STUBHUB_V3_CONSUMER_SECRET']
    _stubhub_user = os.environ['STUBHUBZ_STUBHUB_USER']
    _stubhub_password = os.environ['STUBHUBZ_STUBHUB_PASSWORD']
    return StubHubz(StubHubApi(_stubhub_v2_consumer_key, _stubhub_v2_consumer_secret, _stubhub_v2_scope, 
            _stubhub_v3_consumer_key, _stubhub_v3_consumer_secret, _stubhub_user, _stubhub_password), 
            None, StubHubzDynamoDb(_region, _dynamodb_url), _region, DEBUG)
