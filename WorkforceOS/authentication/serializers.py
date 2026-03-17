"""Authentication serializers — login, register, token, user profile."""

from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from django.contrib.auth import get_user_model
from tenants.models import Tenant

User = get_user_model()


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    """Adds tenant_id and role info to JWT claims."""
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token['active_product'] = 'hrm'
        token['tenant_id'] = str(user.tenant_id) if user.tenant_id else None
        token['email'] = user.email
        token['full_name'] = user.full_name
        # Add roles
        roles = list(user.user_roles.values_list('role__name', flat=True))
        token['roles'] = roles
        return token


class UserRegistrationSerializer(serializers.Serializer):
    """Register a new tenant + admin user. Starts 14-day free trial."""
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, min_length=10)
    first_name = serializers.CharField(max_length=100)
    last_name = serializers.CharField(max_length=100)
    company_name = serializers.CharField(max_length=255)
    company_slug = serializers.SlugField(max_length=100)

    def validate_company_slug(self, value):
        if Tenant.objects.filter(slug=value).exists():
            raise serializers.ValidationError("This company identifier is already taken.")
        return value

    def validate_email(self, value):
        return value.lower()

    def create(self, validated_data):
        from datetime import timedelta
        from django.db import transaction
        from django.utils import timezone
        from tenants.enterprise import Subscription

        trial_end = timezone.now() + timedelta(days=14)

        with transaction.atomic():
            # Create tenant with 14-day trial
            tenant = Tenant.objects.create(
                name=validated_data['company_name'],
                slug=validated_data['company_slug'],
                plan='starter',
                status='trial',
                trial_ends_at=trial_end,
                max_employees=25,
            )

            # Create subscription record
            Subscription.objects.create(
                tenant=tenant,
                plan='starter',
                status='trial',
                trial_ends_at=trial_end,
                max_users=25,
                current_users=1,
            )

            # Create user
            user = User.objects.create_user(
                email=validated_data['email'],
                password=validated_data['password'],
                first_name=validated_data['first_name'],
                last_name=validated_data['last_name'],
                tenant_id=tenant.id,
            )

            # Assign Super Admin role
            from authentication.models import Role, UserRole
            admin_role, _ = Role.objects.get_or_create(
                name='Super Admin',
                defaults={'is_system_role': True, 'description': 'Full access to all features'}
            )
            UserRole.objects.create(user=user, role=admin_role)

        return user


class UserProfileSerializer(serializers.ModelSerializer):
    """Read-only user profile with roles."""
    roles = serializers.SerializerMethodField()
    tenant_name = serializers.CharField(source='tenant.name', read_only=True)

    class Meta:
        model = User
        fields = ['id', 'email', 'first_name', 'last_name', 'avatar_url',
                  'status', 'roles', 'tenant_name', 'date_joined', 'last_login_at']

    def get_roles(self, obj):
        return list(obj.user_roles.values_list('role__name', flat=True))
