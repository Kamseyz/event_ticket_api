from .exceptions import EventNotFoundError, EventUnauthorizedError
from .models import Event,TicketTier
from django.shortcuts import get_object_or_404


#create event(admin only)
def create_event(user,validate_data,tiers_data):
    #check if the user is a staff
    if not user.is_staff:
        raise EventUnauthorizedError("Only admin can perform such actions")
    
    event = Event.objects.create(**validate_data)
    
    for tiers in tiers_data:
        TicketTier.objects.create(event=event, **tiers)
        
    return event


#updating event(admin only)
def update_event(user,event_id, validate_data):
    if not user.is_staff:
        raise EventUnauthorizedError("Update action can only be performed by the admin")

    try:
        events = Event.objects.get(id=event_id)
    except Event.DoesNotExist:
        raise EventNotFoundError(f"Event with the {id} couldn't be found")
    
    for field, value in validate_data.items():
        setattr(events, field, value)
    events.save()

    return events

#delete events(admin only)
def delete_events(user, event_id, validate_data=None):
    if not user.is_staff:
        return EventUnauthorizedError("Invalid action, must only be performed by the admin only")
    
    try:
        events = Event.objects.get(id=event_id)
    except Event.DoesNotExist:
        raise EventNotFoundError(f"Events with the {id} couldn't be found")
    
    
    events.delete()
    return {"message": f"Event {event_id} successfully deleted"}
        
        
#get a particular event
def get_event(event_id):
    try:
        event = Event.objects.get(id=event_id)
    except Event.DoesNotExist:
        raise EventNotFoundError(f"Event with the {id} doesn't exist")
    
    return event


#list event
def list_event():
    return Event.objects.all().order_by('-created_at')