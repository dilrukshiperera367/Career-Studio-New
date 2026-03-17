"""
Custom Objects — EAV-hybrid model for user-defined data types.
Allows tenants to create their own data objects with custom schemas.
"""

import uuid
from django.db import models
from django.conf import settings


class CustomObjectDefinition(models.Model):
    """Schema definition for a custom object type (e.g. 'Vehicle', 'Training Room')."""
    PROPERTY_TYPES = ['text', 'number', 'date', 'boolean', 'email', 'url',
                      'phone', 'currency', 'dropdown', 'multi_select',
                      'rich_text', 'file', 'user_reference', 'employee_reference']

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey('tenants.Tenant', on_delete=models.CASCADE, related_name='custom_objects')
    name = models.CharField(max_length=100, help_text="Display name e.g. 'Company Vehicle'")
    slug = models.SlugField(max_length=100, help_text="URL-safe identifier e.g. 'company_vehicle'")
    plural_name = models.CharField(max_length=100, blank=True)
    description = models.TextField(blank=True)
    icon = models.CharField(max_length=10, default='📦', help_text="Emoji icon for UI")

    # Schema: list of property definitions
    properties = models.JSONField(default=list, help_text="""
        [{"key":"plate_number","label":"Plate Number","type":"text","required":true},
         {"key":"assigned_to","label":"Assigned To","type":"employee_reference"},
         {"key":"purchase_date","label":"Purchase Date","type":"date"}]
    """)

    # Associations to other models
    associations = models.JSONField(default=list, help_text="""
        [{"type":"belongs_to","target":"employee","key":"assigned_employee_id"},
         {"type":"has_many","target":"custom_object","slug":"maintenance_log"}]
    """)

    # Display config
    display_properties = models.JSONField(default=list, help_text="Property keys to show in list view")
    title_property = models.CharField(max_length=100, default='name', help_text="Property used as record title")
    searchable_properties = models.JSONField(default=list, help_text="Property keys that are searchable")

    # Workflow integration
    enable_timeline = models.BooleanField(default=True, help_text="Show in employee timeline")
    enable_workflows = models.BooleanField(default=True, help_text="Can trigger workflow rules")

    # Status
    is_active = models.BooleanField(default=True)
    record_count = models.IntegerField(default=0)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='+')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'custom_object_definitions'
        unique_together = ['tenant', 'slug']
        ordering = ['name']

    def __str__(self):
        return f"{self.icon} {self.name}"

    def get_property_map(self):
        return {p['key']: p for p in (self.properties or [])}


class CustomObjectRecord(models.Model):
    """Instance/record of a custom object with dynamic JSONB data."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey('tenants.Tenant', on_delete=models.CASCADE, related_name='custom_records')
    definition = models.ForeignKey(CustomObjectDefinition, on_delete=models.CASCADE, related_name='records')

    # Dynamic data stored as JSONB
    data = models.JSONField(default=dict, help_text='{"plate_number":"CAR-1234","assigned_to":"emp-uuid"}')

    # Optional association to an employee for timeline
    employee = models.ForeignKey('core_hr.Employee', on_delete=models.SET_NULL,
                                  null=True, blank=True, related_name='custom_records')

    # Audit
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
                                    null=True, related_name='+')
    updated_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
                                    null=True, related_name='+')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'custom_object_records'
        ordering = ['-created_at']

    def __str__(self):
        title_key = self.definition.title_property if self.definition else 'name'
        return str(self.data.get(title_key, f'Record {str(self.id)[:8]}'))

    @property
    def title(self):
        title_key = self.definition.title_property if self.definition else 'name'
        return self.data.get(title_key, f'Record {str(self.id)[:8]}')
