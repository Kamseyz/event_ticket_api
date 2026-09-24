from django.shortcuts import render
from .execption import InsufficientCapacityError, TierNotFoundError, InvalidQuantityError
from .service import create_booking
from .serializer import BookingCreationSerializer,DisplayBookingSerializer
from .models import Booking
from events.models import TicketTier
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
# Create your views here.


#create booking view
class CreatingBookingView(APIView):
    permission_classes= [IsAuthenticated]
    
    def post(self,request):
        #get the form from the serializer
        serializer=BookingCreationSerializer(data=request.data)
        #validate the form and make sure all expections are true
        serializer.is_valid(raise_exception=True)
        
        #make sure its validated
        validated_data=serializer.validated_data
        
        #create the booking
        booking = create_booking(
            user=request.user,
            tier_id=validated_data['tier_id'],
            quantity=validated_data['quantity'],
        )
        
        
        #return responses
        return Response(DisplayBookingSerializer(booking).data, status= status.HTTP_201_CREATED)
    
    
    