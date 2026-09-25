from .models import Booking
from .execption import(
    TierNotFoundError,
    InsufficientCapacityError,
    InvalidQuantityError
)
from events.models import TicketTier
from django.db import transaction




#create booking logic layer
def create_booking(user, tier_id: int, quantity: int)-> dict: 
    #check the quantity first if its less than zero or zero
    if quantity <= 0:
        raise InvalidQuantityError("Quantity cannot be zero or less than zero")
    
     #check if the event exist
    with transaction.atomic():
        try:
            tier= TicketTier.objects.select_for_update().get(id=tier_id)
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
            total_price =tier.price * quantity,
            status="PENDING"
        )
        
        #update the db
        tier.tickets_sold += quantity
        tier.save()
        
        #return booking
        return book
    