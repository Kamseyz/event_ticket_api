from django.urls import path
from .views import CreatingBookingView
urlpatterns = [
   #creating booking url
   path("booking/", CreatingBookingView.as_view(), name='booking')
]