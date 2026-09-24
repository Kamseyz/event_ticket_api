from rest_framework.exceptions import APIException
from rest_framework import status


#insufficent capactiy error
class InsufficientCapacityError(APIException):
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = "Insufficient Capacity"
    
    
#events/tier not found error    
class TierNotFoundError(APIException):
    status_code=status.HTTP_404_NOT_FOUND
    default_detail="Ticket Tier Doesn't exist"
    
    
#invalid quantity error    
class InvalidQuantityError(APIException):
    status_code =status.HTTP_400_BAD_REQUEST
    default_detail="Quantity can't be zero or less than zero"