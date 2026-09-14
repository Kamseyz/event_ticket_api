from .models import Event, TicketTier
from rest_framework import serializers



#pov make sure the ticket_tiers matches with your related name


#ticker serializer(just like a form the users will fill)
class TicketTierSerializers(serializers.ModelSerializer):
    class Meta:
        model= TicketTier
        fields= ['id', 'name', 'price', 'capacity']
        
        

#event serializer(show the users the different type of events)
class EventSerializers(serializers.ModelSerializer):
    
    #if take note i passed many=true cause i have nested serializer repesentation
    ticket_tiers= TicketTierSerializers(many=True, read_only=True)
    
    class Meta:
        model= Event
        fields=['id', 'title', 'description', 'location', 'start_time', 'end_time','ticket_tiers']
    
    

#create event(admin only)
class CreateEventSerializer(serializers.ModelSerializer):
    
    #tire must be sent in by only the client
    ticket_tiers= TicketTierSerializers(many=True)
    
    class Meta:
        model= Event
        fields=['title', 'description', 'location' , 'start_time', 'end_time', 'ticket_tiers']


#update event(admin only)
class UpdateEventSerializer(serializers.ModelSerializer):
    
    class Meta:
        model= Event
        fields=['title', 'description', 'location' , 'start_time', 'end_time']
        extra_kwargs = {field: {'required': False} for field in fields}
