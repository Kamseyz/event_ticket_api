from rest_framework import serializers
from .models import Booking


#creating booking 
class BookingCreationSerializer(serializers.Serializer):
    tier_id= serializers.IntegerField()
    quantity=serializers.IntegerField(min_value=1)



#display the booking
class DisplayBookingSerializer(serializers.ModelSerializer):
    
    class Meta:
        model= Booking
        fields= [
            "id",
            "ticket_tier",
            "user",
            "quantity",
            "total_price",
            "status",
            "booking_reference"
        ]