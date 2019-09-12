# StubHubz

Graphs ticket prices from StubHub which aims to provide guidance on when to purchase tickets.


# Usage

Assuming:

* Tables in DynamoDB have been set up
* StubHub credentials have been added to `keys.ini`
* AWS credentials have been configured

For help:

`py stubhubzcli.py --help`

To add a new event for tracking:

1. Go to [www.stubhub.com](https://www.stubhub.com/) and find an event you want to track
1. In the URL note the event ID (it appears after `/event/<event ID>/`)
1. `> py stubhubzcli.py track-event <event ID>`
1. StubHubz will now track this event
1. Go to [https://stubhubz.andrewcho.xyz/](https://stubhubz.andrewcho.xyz/) to see the price history


# Design

## DynamoDB Data Model
See [aws.dynamodb.py](aws.dynamodb.py) for exact details. Summary:
* `Event`: id, name (from description), dateTime (from eventDateLocal), eventStatus (from status.statusId), venue (from venue.name + venue.city), primaryPerformer (from performers.primaryPerformer.name), lastScraped, scapeStatus (on/off)
* ` PriceHistory`: eventid, dateTime, zonePrices (zoneId, zoneName, totalTickets, totalListings, averagePrice, minPrice)

## Workflows
The StubHubz has several workflows:

1. Admin adds events for tracking
    1. Administrator uses `py stubhubzcli.py track-event` to add StubHub events for tracking
1. Periodically AWS Lambda (triggered hourly by CloudWatch) scrapes for events to retrieve price history for
    1. Lambda inspects `Event` DynamoDB table for "Active" events (i.e. not historical or marked as "Inactive")
    1. For each Event:
        1. Lambda scrapes StubHub for price information of each event storing pricing info in DyanmoDB
            * pricing info is by zone (e.g. General Admission, Loge, Balcony)
            * does not exclude obstructed view seats as this appears difficult to do in StubHub's API
    1. If new price history was retrieved (i.e. there was at least one active event) publish a notification to a AWS SNS Topic
1. AWS SNS Topic dumps price history to AWS S3 in JSON
    1. SNS Topic triggers AWS Lambda passing the Event IDs where new price history was retrieved
    1. For each Event ID AWS Lambda:
        1. Retrieve the event's price history from DynamoDB
        1. Convert to JSON format that is suitable for [Chart.js](http://www.chartjs.org/)
        1. Store the result in AWS S3
1. Person navigates to UI in their browser
    1. Events table is rendered from data retrieved from CloudFront > API Gateway > which dumps DynamoDB's Event table
    1. Clicking an event invokes Chart.js to render the price history retrieved from S3


# Developer Guide

## Setting Up A Development Environment

1. First time setup
    1. Install [Java 6.x](http://www.oracle.com/technetwork/java/javase/downloads/index.html) or higher
    1. Install [Python 3](https://www.python.org/downloads/)
    1. Install Python dependencies `> pip install -r requirements.txt`
    1. (Optional) Install [Local DynamoDB](http://docs.aws.amazon.com/amazondynamodb/latest/developerguide/DynamoDBLocal.html) instance (note this requires  plus)
    1. Clone this git repository `> git clone git@bitbucket.org:andcho09/stubhubz.git` (assuming you have access to the repository)
    1. Sign up for [StubHub API](https://developer.stubhub.com/store/) 
        1. generate an API key for `Production`
        1. subscribe your application to all of the APIs
        1. copy `keys_template.ini` to `keys.ini` and populate your StubHub credentials and API key into it
    1. Deploy AWS DynamoDB tables
        1. sign up for [AWS](https://aws.amazon.com/)
        1. edit `aws.ini` and updated the endpoint to point to the DynamoDB instance you want to use
        1. configure your AWS access ID and secret key using one of the methods described [here](http://docs.aws.amazon.com/cli/latest/userguide/cli-chap-getting-started.html#config-settings-and-precedence)
        1. run `> py stubhubzcli.py dynamodb create`
1. Developing
    1. Start local DynamoDB instance (this step is not required if you're using the real DynamoDB instead of a local instance)
    1. Check your `aws.ini` and `keys.ini` and files
    1. Code it!
1. Packaging for AWS Lambda deployment
    1. Note, it might make sense to do this in a clean working copy
    1. Install python modules to the local directory, i.e. `> pip install -r requirements.txt -t .`
    1. Run `ant` to generate the .zip file for AWS upload
    1. New Python code is uploaded to Lambda
    1. New client-side JavaScript is uploaded to S3 (cache invalidation might be required here)

## Backing up AWS

> ant aws-backup

This exports AWS settings to the ``aws`` directory but has so gaps:
* CloudWatch trigger rule, IAM, and S3 configuration details are not exported
* Config can't actually be imported back into AWS. It's more of a snapshot than an restorable backup.


# Prior And Related Art

* [The Land Of Oz](http://ozzieliu.com/2016/06/21/scraping-ticket-data-with-stubhub-api/) - proof of concept to retrieve event info from StubHub
    * [GitHub Gist code](https://gist.github.com/ozzieliu/9fbbc83b354c568709dc4e6a30fea54f)