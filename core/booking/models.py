from django.db import models
from django.conf import settings
from events.models import TicketTier
import uuid
# Create your models here.
class Booking(models.Model):
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('CONFIRMED', 'Confirmed'),
        ('CANCELLED', 'Cancelled'),
    ]
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    ticket_tier = models.ForeignKey(TicketTier, on_delete=models.PROTECT)
    quantity = models.PositiveIntegerField(default=1)
    total_price = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='PENDING')
    booking_reference = models.CharField(max_length=32, editable=False, unique=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Booking {self.booking_reference} by {self.user}"
    
    #create uqiue uuid
    def generate_reference(self):
        while True:
            new_ref = f"PAIN_BOOKING{uuid.uuid4().hex[:12].upper()}"
            if not Booking.objects.filter(booking_reference=new_ref).exists():
                return new_ref

                
    def save(self, *args, **kwargs):
        #make sure the qunantity doesnt accept zero
        if self.quantity <=0:
            raise ValueError("Quantity must be at least 1")
        if not self.booking_reference:
            self.booking_reference=self.generate_reference
        super().save(*args, **kwargs)