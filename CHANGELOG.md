# Changelog

## Unreleased

* New
    * Added stub for integrating with TicketMaster. Note this is incomplete.
* Bug fixes
    * Fixed not being able to retrieve event info from StubHub, [issue #5](https://bitbucket.org/andcho09/stubhubz/issues/5/fix-not-being-able-to-track-certain-event). This involved partially moving to StubHub's V3 (2019-era) API. Note we're still using some V2 (2017-era) APIs because the V3 API doesn't return pricing/zone summary info.
    * Fixed retrieving listings failing because StubHub deprecated their V2 API, [issue #10](https://bitbucket.org/andcho09/stubhubz/issues/10/stubhub-api-is-moving-from-v2-to-v3). This involved full migration to the V3 API which doesn't return average price for you and subsequently introduced a bug where average price is incorrect if there are more than 100 listings for a zone (see [issue #11](https://bitbucket.org/andcho09/stubhubz/issues/11))

## 0.9 (Jul 2019)

* New
    * Added ``backup-aws`` Ant task to version control AWS config

## 0.8 (Apr 2019)

* New
    * Added ``dump-events`` option to CLI to dump Events table.
    * Added ``update-event-manual`` option to the CLI to update the Event table manually (instead of using ``update-event`` which updates from StubHub). This works around StubHub 404'ing when retrieving an event (even though retrieving listings for the event works) causing a blank row to be inserted into the Events table.
* Performance fixes
    * Added gzip compression to ``favicon.ico`` saving >10KB
    * and YUI compressor to JavaScript files saving >2KB 
* Bug fixes
    * Fixed error handling of UI
    * Fixed display of dates in the UI to use the event's time zone for the event date but the browser's time zone for the last update time. Chart is still in browser's time zone though (bug [#8](https://bitbucket.org/andcho09/stubhubz/issues/8/change-time-zone-of-chart-to-events-time))

## 0.7 and older (Oct 2017)

* Lots of stuff
