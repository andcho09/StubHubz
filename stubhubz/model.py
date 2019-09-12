from abc import ABCMeta, abstractmethod

class TicketSource(metaclass=ABCMeta):

    @abstractmethod
    def get_event_info(self, event_id):
        """Return info for the given event as a stubhubz.dynamodb.Event from the source or None if not found."""
        raise NotImplementedError

    @abstractmethod
    def search_events(self, name, city, country):
        """Return event search results (as text) given the search criteria."""
        raise NotImplementedError