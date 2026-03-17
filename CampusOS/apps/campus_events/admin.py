from django.contrib import admin
from .models import CampusEvent, EventFeedback, EventRegistration, EventSpeaker


@admin.register(CampusEvent)
class CampusEventAdmin(admin.ModelAdmin):
    list_display = ["title", "event_type", "campus", "start_datetime", "mode", "status"]
    list_filter = ["event_type", "mode", "status"]
    search_fields = ["title"]
    raw_id_fields = ["campus", "organizer", "employer"]


@admin.register(EventRegistration)
class EventRegistrationAdmin(admin.ModelAdmin):
    list_display = ["event", "student", "registration_number", "attended", "waitlisted"]
    list_filter = ["attended", "waitlisted"]
    search_fields = ["student__email", "registration_number"]


@admin.register(EventFeedback)
class EventFeedbackAdmin(admin.ModelAdmin):
    list_display = ["registration", "overall_rating", "would_recommend"]
    list_filter = ["overall_rating"]


@admin.register(EventSpeaker)
class EventSpeakerAdmin(admin.ModelAdmin):
    list_display = ["name", "event", "company", "designation", "is_alumni"]
    list_filter = ["is_alumni"]
