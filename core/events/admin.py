from django.contrib import admin
from .models import Event, TicketTier

# 1. Inline setup: This displays Ticket Tiers directly inside the Event page
class TicketTierInline(admin.TabularInline):
    model = TicketTier
    extra = 1 # Provides one blank row by default to quickly add a tier
    fields = ('name', 'price', 'capacity', 'tickets_sold', 'display_remaining_tickets')
    readonly_fields = ('display_remaining_tickets',)
    
    # Expose the remaining_tickets property inside the inline view
    def display_remaining_tickets(self, obj):
        if obj.id: # Check if the object is saved in the database
            return obj.remaining_tickets
        return "-"
    display_remaining_tickets.short_description = "Remaining"


# 2. Event Configuration
@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    # What columns show up on the main list page
    list_display = ('title', 'location', 'start_time', 'end_time', 'created_at', 'total_tiers_count')
    
    # Sidebar filters for quick navigation
    list_filter = ('start_time', 'created_at', 'location')
    
    # Real-time search bar
    search_fields = ('title', 'location', 'description')
    
    # Combines the inline setup so ticket tiers (VIP, Regular) live under the event details
    inlines = [TicketTierInline]

    # Custom column to show how many variations of tickets an event has
    def total_tiers_count(self, obj):
        return obj.ticket_tiers.count()
    total_tiers_count.short_description = "Active Tiers"


# 3. Ticket Tier Configuration (For independent monitoring)
@admin.register(TicketTier)
class TicketTierAdmin(admin.ModelAdmin):
    list_display = ('name', 'event', 'price', 'capacity', 'tickets_sold', 'display_remaining_tickets', 'is_sold_out')
    list_filter = ('name', 'event')
    search_fields = ('name', 'event__title')
    
    # Keeps ticket metrics read-only on this screen to prevent accidental manipulation
    readonly_fields = ('tickets_sold', 'display_remaining_tickets')

    def display_remaining_tickets(self, obj):
        return obj.remaining_tickets
    display_remaining_tickets.short_description = "Remaining Tickets"

    # A cool status indicator flag for your dashboard
    def is_sold_out(self, obj):
        return obj.remaining_tickets <= 0
    is_sold_out.boolean = True # Turns True/False into nice green checkmarks or red X's
    is_sold_out.short_description = "Sold Out?"
