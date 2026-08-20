from django.db import models
from django.core.exceptions import ValidationError

# Create your models here.

#event model
class Event(models.Model):
    title = models.CharField(max_length=200)
    description = models.TextField(max_length=500)
    location = models.CharField(max_length=255)
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title
    
    #make sure the end time is not more than the start time 
    def clean(self):
        if self.end_time <= self.start_time:
            raise ValidationError("End time must be after start time.")
        super().clean()
    
    
    
#ticket tier(e.g like vip, regular, vvip etc)
class TicketTier(models.Model):
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name="ticket_tiers")
    name = models.CharField(max_length=50, help_text="e.g., Regular, VIP, VVIP")
    price = models.DecimalField(max_digits=10, decimal_places=2)
    capacity = models.PositiveIntegerField(help_text="Total tickets available for this specific tier")
    tickets_sold = models.PositiveIntegerField(default=0, help_text="Track sales to prevent overselling")


    @property
    def remaining_tickets(self):
        if self.capacity is None:
            return 0
        return max(0, self.capacity - self.tickets_sold)
    
    
    def __str__(self):
        return f"{self.event.title} - {self.name} (₦{self.price})"
