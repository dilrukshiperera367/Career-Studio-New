"""Serializers for accounts app."""

from django.utils.text import slugify
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from apps.accounts.models import User, Role, UserRole
from apps.tenants.models import Tenant


class UserSerializer(serializers.ModelSerializer):
    roles = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            "id", "email", "first_name", "last_name",
            "user_type", "tenant_id", "is_active", "roles", "created_at",
        ]
        read_only_fields = ["id", "created_at"]

    def get_roles(self, obj):
        return list(obj.user_roles.values_list("role__name", flat=True))


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------

class CompanyRegisterSerializer(serializers.Serializer):
    """Register a company (tenant) + its first admin user. Starts 14-day trial."""

    company_name = serializers.CharField(max_length=255)
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, min_length=8)
    first_name = serializers.CharField(max_length=150)
    last_name = serializers.CharField(max_length=150)

    def validate_email(self, value):
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("Email already registered.")
        return value

    def validate_company_name(self, value):
        slug = slugify(value)
        if Tenant.objects.filter(slug=slug).exists():
            raise serializers.ValidationError("Company name already taken.")
        return value

    def create(self, validated_data):
        from datetime import timedelta
        from django.db import transaction
        from django.utils import timezone
        from apps.tenants.models import Subscription

        trial_end = timezone.now() + timedelta(days=14)

        with transaction.atomic():
            # Create tenant with 14-day trial
            tenant = Tenant.objects.create(
                name=validated_data["company_name"],
                slug=slugify(validated_data["company_name"]),
                status="trial",
                plan="free",
                trial_ends_at=trial_end,
            )

            # Create subscription record
            Subscription.objects.create(
                tenant=tenant,
                plan="starter",
                status="trial",
                trial_ends_at=trial_end,
                max_users=5,
                current_users=1,
            )

            # Create admin user
            user = User.objects.create_user(
                email=validated_data["email"],
                password=validated_data["password"],
                first_name=validated_data["first_name"],
                last_name=validated_data["last_name"],
                tenant=tenant,
                user_type="company_admin",
            )
        return user


class CandidateRegisterSerializer(serializers.Serializer):
    """Register a candidate user (no tenant)."""

    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, min_length=8)
    first_name = serializers.CharField(max_length=150)
    last_name = serializers.CharField(max_length=150)

    def validate_email(self, value):
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("Email already registered.")
        return value

    def create(self, validated_data):
        return User.objects.create_user(
            email=validated_data["email"],
            password=validated_data["password"],
            first_name=validated_data["first_name"],
            last_name=validated_data["last_name"],
            user_type="candidate",
            tenant=None,
        )


# Legacy serializer kept for backward compat
class UserCreateSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)

    class Meta:
        model = User
        fields = ["email", "password", "first_name", "last_name", "tenant_id"]

    def create(self, validated_data):
        return User.objects.create_user(**validated_data)


class TokenObtainSerializer(TokenObtainPairSerializer):
    """Custom token with tenant_id + user_type claims."""

    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token["active_product"] = "ats"
        token["tenant_id"] = str(user.tenant_id) if user.tenant_id else None
        token["user_type"] = user.user_type
        token["email"] = user.email
        token["first_name"] = user.first_name
        return token


class RoleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Role
        fields = ["id", "name", "permissions", "created_at"]
        read_only_fields = ["id", "created_at"]


class UserRoleSerializer(serializers.ModelSerializer):
    role_name = serializers.CharField(source="role.name", read_only=True)

    class Meta:
        model = UserRole
        fields = ["id", "user", "role", "role_name", "assigned_at"]
        read_only_fields = ["id", "assigned_at"]
