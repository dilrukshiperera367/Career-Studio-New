"""CampusOS — Accounts serializers."""

from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from .models import User


class UserRegistrationSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, validators=[validate_password])
    password_confirm = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = [
            "email", "first_name", "last_name", "role", "phone",
            "password", "password_confirm",
        ]

    def validate(self, attrs):
        if attrs["password"] != attrs.pop("password_confirm"):
            raise serializers.ValidationError({"password": "Passwords do not match."})
        return attrs

    def create(self, validated_data):
        return User.objects.create_user(**validated_data)


class UserProfileSerializer(serializers.ModelSerializer):
    full_name = serializers.SerializerMethodField()
    campus_name = serializers.CharField(source="campus.name", read_only=True, default=None)

    class Meta:
        model = User
        fields = [
            "id", "email", "first_name", "last_name", "full_name",
            "role", "campus", "campus_name", "phone", "profile_photo",
            "is_verified", "email_verified", "phone_verified",
            "profile_visibility", "notify_email", "notify_sms",
            "notify_whatsapp", "notify_push",
            "data_processing_consent", "marketing_consent",
            "date_joined", "last_login",
        ]
        read_only_fields = [
            "id", "email", "role", "is_verified", "email_verified",
            "phone_verified", "date_joined", "last_login",
        ]

    def get_full_name(self, obj):
        return obj.get_full_name()


class UserMiniSerializer(serializers.ModelSerializer):
    """Compact user representation for nested usage."""

    full_name = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ["id", "email", "full_name", "role", "profile_photo"]

    def get_full_name(self, obj):
        return obj.get_full_name()


class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True, validators=[validate_password])
    new_password_confirm = serializers.CharField(write_only=True)

    def validate(self, attrs):
        if attrs["new_password"] != attrs["new_password_confirm"]:
            raise serializers.ValidationError({"new_password": "Passwords do not match."})
        return attrs


class CampusJWTSerializer(TokenObtainPairSerializer):
    """Extend JWT payload with CampusOS role and campus context."""

    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token["email"] = user.email
        token["role"] = user.role
        token["campus_id"] = str(user.campus_id) if user.campus_id else None
        token["full_name"] = user.get_full_name()
        return token
