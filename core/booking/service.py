from .models import Booking
from .execption import(
    TierNotFoundError,
    InsufficientCapacityError,
    InvalidQuantityError
)
from events.models import TicketTier
from django.contrib.auth import get_user_model




#create booking logic layer
def create_booking(user, tier_id: int, quantity: int)-> dict: 
    #check the quantity first if its less than zero or zero
    if quantity <= 0:
        raise InvalidQuantityError("Quantity cannot be zero or less than zero")
    
    
    #check if the event exist
    try:
        tier = TicketTier.objects.get(id=tier_id)
    except TicketTier.DoesNotExist:
        raise TierNotFoundError(f"Event with this id {tier_id} doesn't exist")
    
    
    #check for insufficient capacity
    remainder= tier.capacity - tier.tickets_sold
    if quantity > remainder:
        raise InsufficientCapacityError(f"Insufficient capacity only {tier.capacity} is avaiable")
    
    
    #create the booking and save 
    book = Booking.objects.create(
        user=user,
        ticket_tier=tier,
        quantity=quantity,
        total_price=tier.price * quantity,
        status="PENDING",
    )

    
    #update the db 
    tier.tickets_sold += quantity
    tier.save()
    
    #return 
    return book
    