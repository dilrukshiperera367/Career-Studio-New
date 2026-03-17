"""Custom Objects API views — dynamic schema + record CRUD."""

from rest_framework import viewsets, serializers, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.utils.text import slugify

from config.base_api import TenantViewSetMixin, TenantSerializerMixin, AuditMixin
from platform_core.services import emit_timeline_event
from .models import CustomObjectDefinition, CustomObjectRecord


# --- Serializers ---

class CustomObjectDefinitionSerializer(TenantSerializerMixin, serializers.ModelSerializer):
    class Meta:
        model = CustomObjectDefinition
        fields = '__all__'
        read_only_fields = ['id', 'tenant', 'slug', 'record_count', 'created_at', 'updated_at']


class CustomObjectRecordSerializer(TenantSerializerMixin, serializers.ModelSerializer):
    definition_name = serializers.CharField(source='definition.name', read_only=True)
    record_title = serializers.SerializerMethodField()

    class Meta:
        model = CustomObjectRecord
        fields = '__all__'
        read_only_fields = ['id', 'tenant', 'created_by', 'updated_by', 'created_at', 'updated_at']

    def get_record_title(self, obj):
        return obj.title


# --- Views ---

class CustomObjectDefinitionViewSet(TenantViewSetMixin, AuditMixin, viewsets.ModelViewSet):
    """CRUD for custom object schemas. Only admins should access this."""
    queryset = CustomObjectDefinition.objects.all()
    serializer_class = CustomObjectDefinitionSerializer
    filterset_fields = ['is_active']
    search_fields = ['name', 'description']

    def perform_create(self, serializer):
        name = serializer.validated_data.get('name', '')
        slug = slugify(name).replace('-', '_')
        # Ensure unique slug per tenant
        base_slug = slug
        counter = 1
        while CustomObjectDefinition.objects.filter(
            tenant_id=self.request.tenant_id, slug=slug
        ).exists():
            slug = f"{base_slug}_{counter}"
            counter += 1
        plural = serializer.validated_data.get('plural_name', '') or f"{name}s"
        serializer.save(
            tenant_id=self.request.tenant_id,
            slug=slug,
            plural_name=plural,
            created_by=self.request.user,
        )

    @action(detail=True, methods=['get'], url_path='definition-schema', url_name='definition-schema')
    def definition_schema(self, request, pk=None):
        """Get the full schema for building dynamic forms."""
        defn = self.get_object()
        return Response({
            'data': {
                'id': str(defn.id),
                'name': defn.name,
                'slug': defn.slug,
                'icon': defn.icon,
                'properties': defn.properties,
                'associations': defn.associations,
                'display_properties': defn.display_properties,
                'title_property': defn.title_property,
                'searchable_properties': defn.searchable_properties,
            }
        })

    @action(detail=True, methods=['get'])
    def records(self, request, pk=None):
        """List all records for this definition."""
        defn = self.get_object()
        records = CustomObjectRecord.objects.filter(
            tenant_id=request.tenant_id, definition=defn
        ).order_by('-created_at')

        # Search
        q = request.query_params.get('q')
        if q:
            from django.db.models import Q
            searchable = defn.searchable_properties or [defn.title_property]
            filters = Q()
            for prop in searchable:
                filters |= Q(**{f'data__{prop}__icontains': q})
            records = records.filter(filters)

        data = CustomObjectRecordSerializer(records, many=True).data
        return Response({'data': data, 'meta': {'total': len(data)}})


class CustomObjectRecordViewSet(TenantViewSetMixin, AuditMixin, viewsets.ModelViewSet):
    """CRUD for custom object records with dynamic validation."""
    queryset = CustomObjectRecord.objects.select_related('definition', 'employee').all()
    serializer_class = CustomObjectRecordSerializer
    filterset_fields = ['definition', 'employee']

    def perform_create(self, serializer):
        defn = serializer.validated_data.get('definition')
        data = serializer.validated_data.get('data', {})

        # Validate required properties
        prop_map = defn.get_property_map()
        errors = []
        for key, prop in prop_map.items():
            if prop.get('required') and not data.get(key):
                errors.append(f"Property '{prop.get('label', key)}' is required")
        if errors:
            from rest_framework.exceptions import ValidationError
            raise ValidationError({'data': errors})

        record = serializer.save(
            tenant_id=self.request.tenant_id,
            created_by=self.request.user,
            updated_by=self.request.user,
        )

        # Update record count
        defn.record_count = defn.records.count()
        defn.save(update_fields=['record_count'])

        # Emit timeline event if linked to employee
        if record.employee and defn.enable_timeline:
            emit_timeline_event(
                tenant_id=self.request.tenant_id,
                employee=record.employee,
                event_type=f'custom_object.{defn.slug}.created',
                category='custom_object',
                title=f'{defn.icon} {defn.name}: {record.title}',
                actor=self.request.user,
                source_object_type='CustomObjectRecord',
                source_object_id=record.id,
            )

    def perform_update(self, serializer):
        serializer.save(updated_by=self.request.user)

    def perform_destroy(self, instance):
        defn = instance.definition
        instance.delete()
        defn.record_count = defn.records.count()
        defn.save(update_fields=['record_count'])

    @action(detail=False, methods=['get'], url_path='by-type/(?P<slug>[^/.]+)')
    def by_type(self, request, slug=None):
        """Get records filtered by custom object slug."""
        try:
            defn = CustomObjectDefinition.objects.get(
                tenant_id=request.tenant_id, slug=slug
            )
        except CustomObjectDefinition.DoesNotExist:
            return Response({'error': {'message': 'Custom object type not found'}}, status=404)

        records = CustomObjectRecord.objects.filter(
            tenant_id=request.tenant_id, definition=defn
        ).order_by('-created_at')
        return Response({
            'data': CustomObjectRecordSerializer(records, many=True).data,
            'meta': {'definition': CustomObjectDefinitionSerializer(defn).data}
        })
