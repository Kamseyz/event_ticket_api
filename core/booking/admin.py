from django.contrib import admin
from .models import Booking

@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    # 1. Main Dashboard Grid Columns
    list_display = (
        'booking_reference', 
        'get_customer', 
        'get_event', 
        'ticket_tier', 
        'quantity', 
        'total_price', 
        'status', 
        'created_at'
    )

    # 2. Sidebar Filters
    list_filter = ('status', 'created_at', 'ticket_tier__event', 'ticket_tier')

    # 3. Supercharged Search Bar
    # Use '__username' or '__email' depending on your custom user model fields
    search_fields = (
        'booking_reference', 
        'user__username', 
        'user__email', 
        'ticket_tier__name', 
        'ticket_tier__event__title'
    )

    # 4. Form Rules (When clicking inside a booking record)
    readonly_fields = ('booking_reference', 'created_at', 'total_price')
    
    # Organizes details cleanly into drop-down sections inside the record view
    fieldsets = (
        ('Reference Info', {
            'fields': ('booking_reference', 'status', 'created_at')
        }),
        ('Customer & Ticket Details', {
            'fields': ('user', 'ticket_tier', 'quantity', 'total_price')
        }),
    )

    # 5. Bulk Admin Actions (Update multiple bookings at once)
    actions = ['mark_as_confirmed', 'mark_as_cancelled']

    # Custom methods to fetch related data across your foreign keys cleanly
    def get_customer(self, obj):
        return obj.user.email if obj.user.email else obj.user.username
    get_customer.short_description = 'Customer'
    get_customer.admin_order_field = 'user'

    def get_event(self, obj):
        return obj.ticket_tier.event.title
    get_event.short_description = 'Event'
    get_event.admin_order_field = 'ticket_tier__event'

    # Admin Action logic for instant bulk confirmations
    @admin.action(description='Confirm selected bookings')
    def mark_as_confirmed(self, request, queryset):
        updated = queryset.update(status='CONFIRMED')
        self.message_user(request, f'{updated} bookings were successfully confirmed.')

    # Admin Action logic for instant bulk cancellations
    @admin.action(description='Cancel selected bookings')
    def mark_as_cancelled(self, request, queryset):
        updated = queryset.update(status='CANCELLED')
        self.message_user(request, f'{updated} bookings were successfully cancelled.')
