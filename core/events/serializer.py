from .models import Event, TicketTier
from rest_framework import serializers



#pov make sure the ticket_tiers matches with your related name


#ticker serializer(just like a form the users will fill)
class TicketTierSerializers(serializers.ModelSerializer):
    class Meta:
        model= TicketTier
        fields= ['id', 'name', 'price', 'capacity']
        
        

#event serializer (Converts Event records into complete JSON data to show the user)
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
    
    #to make sure the end time doesnt begin before the start time
    def validate(self, attrs):
        start_time = attrs.get('start_time')
        end_time = attrs.get('end_time')
        
        if start_time and end_time and end_time <= start_time:
            raise serializers.ValidationError("End time must be after start time")
        return attrs
    


#update event(admin only)
class UpdateEventSerializer(serializers.ModelSerializer):
    
    class Meta:
        model= Event
        fields=['title', 'description', 'location' , 'start_time', 'end_time']
        extra_kwargs = {field: {'required': False} for field in fields}
        
    #to make sure the end time doesnt begin before the start time
    def validate(self, attrs):
        start_time = attrs.get('start_time', getattr(self.instance, 'start_time', None))
        end_time = attrs.get('end_time', getattr(self.instance, 'end_time', None))
        if start_time and end_time and end_time <= start_time:
            raise serializers.ValidationError("End time must be after start time")
        return attrs
