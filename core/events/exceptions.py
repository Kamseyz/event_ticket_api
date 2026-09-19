from rest_framework.exceptions import APIException
from rest_framework import status

#if events is not found

class EventNotFoundError(APIException):
    status_code = status.HTTP_404_NOT_FOUND
    default_detail = "Event not found."
    
    
#for unauthorized user
class EventUnauthorizedError(APIException):
    status_code = status.HTTP_403_FORBIDDEN
    default_detail = "Unauthorized action."