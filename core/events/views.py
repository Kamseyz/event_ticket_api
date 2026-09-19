from django.shortcuts import render
from .serializer import TicketTierSerializers, EventSerializers, CreateEventSerializer, UpdateEventSerializer
from .services import create_event, update_event, delete_events, get_event, list_event
from rest_framework.permissions import AllowAny, IsAuthenticated, IsAdminUser
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import status

#show all events to users
class ShowAllEventsView(APIView):
    permission_classes = [AllowAny]
    
    def get(self,request):
        
        #get event from serivce layer
        events= list_event()
        
        serializers= EventSerializers(events, many=True)
        
        #return the data
        return Response(serializers.data, status=status.HTTP_200_OK)
        
        

#get a particular event
class GetAnEventView(APIView):
    permission_classes = [AllowAny]
    
    def get(self,request, pk):
        event = get_event(
            event_id=pk
        )
        
        
        #return a new json output
        new_output = EventSerializers(event)
        #return a response
        
        return Response(new_output.data, status=status.HTTP_200_OK)


#create events(admin only)
class CreateEventsView(APIView):
    permission_classes = [IsAdminUser]
    
    def post(self,request):
        
        #get the serializer
        serializer= CreateEventSerializer(data=request.data)
        
        #check if its valid and raise expection
        serializer.is_valid(raise_exception=True)
        
        #remove tickettire
        validate_data = serializer.validated_data
        tiers_data = validate_data.pop('ticket_tiers', [])
        
        #send to your service layer
        new_data = create_event(
            user= request.user,
            validate_data=validate_data, 
            tiers_data=tiers_data
        )
        
        #return the new serializer to display
        new_output = EventSerializers(new_data)
        #return response
        
        return Response(new_output.data, status=status.HTTP_201_CREATED)


#update events(admin only)
class UpdateEventsView(APIView):
    permission_classes = [IsAdminUser]
    
    def patch(self,request, pk):
        
        #get the exisiting form
        event = get_event(event_id=pk)
        
        #update the form
        serializer=UpdateEventSerializer(instance =event, data=request.data, partial=True)
        
        #check if the form is valid and raise expection
        serializer.is_valid(raise_exception=True)
        
        #validate serializer
        new_data= serializer.validated_data
        
        #send to service layer
        results= update_event(
            user=request.user,
            event_id=pk,
            validate_data=new_data,
        )
        
        #return a new json output to the user
        new_results = EventSerializers(results)
        
        
        #return responses
        return Response(new_results.data, status=status.HTTP_200_OK)


#delete events(admin only)
class DeleteEventsView(APIView):
    permission_classes = [IsAdminUser]
    
    def delete(self,request, pk):
        #send to the service
        
        result = delete_events(
            user=request.user,
            event_id=pk,
            
        )
        
        
        #give a response
        
        return Response(result, status=status.HTTP_200_OK)
                