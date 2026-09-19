from django.urls import path
from .views import DeleteEventsView, UpdateEventsView,CreateEventsView,GetAnEventView,ShowAllEventsView

urlpatterns = [
    # 1. Public Endpoints
    
    #show all events to the user
    path('events/', ShowAllEventsView.as_view(), name='list-events'),
    
    #get a particular event
    path('events/<int:pk>/', GetAnEventView.as_view(), name='get-event'),
    
    # 2. Admin Endpoints
    path('events/create/', CreateEventsView.as_view(), name='create-event'),
    path('events/<int:pk>/update/', UpdateEventsView.as_view(), name='update-event'),
    path('events/<int:pk>/delete/', DeleteEventsView.as_view(), name='delete-event'),
]