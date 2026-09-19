from rest_framework.exceptions import APIException
from rest_framework import status



class InsufficientCapacityError(APIException):
    status_code = status.HTTP_400_BAD_REQUEST
    message = "Insufficient Capacity"
    
    
    
class TierNotFoundError(APIException):
    status_code=status.HTTP_404_NOT_FOUND
    message="Ticket Tier Doesn't exist"
    
    
    
class InvalidQuantityError(APIException):
    status_code =status.HTTP_400_BAD_REQUEST
    message="Quantity can't be zero or less than zero"