#if events is not found

class EventNotFoundError(Exception):
    pass

#for unauthorized user
class EventUnauthorizedError(Exception):
    pass