"""Accounts serializers — registration, login, profile, OAuth, 2FA, account management."""
from datetime import date
from rest_framework import serializers
from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from .models import User, UserSession, TwoFactorSecret, PushToken


# ── Registration ──────────────────────────────────────────────────────────

class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8, validators=[validate_password])
    password_confirm = serializers.CharField(write_only=True)
    date_of_birth = serializers.DateField(required=False)

    class Meta:
        model = User
        fields = ["email", "phone", "password", "password_confirm", "user_type", "preferred_lang", "date_of_birth"]

    def validate(self, data):
        if data["password"] != data.pop("password_confirm"):
            raise serializers.ValidationError({"password_confirm": "Passwords do not match."})
        return data

    def validate_date_of_birth(self, value):
        """Age verification — must be 16+ to register (#34)."""
        if value:
            today = date.today()
            age = today.year - value.year - ((today.month, today.day) < (value.month, value.day))
            if age < 16:
                raise serializers.ValidationError("You must be at least 16 years old to register.")
        return value

    def create(self, validated_data):
        validated_data.pop("date_of_birth", None)  # stored on seeker profile, not user
        return User.objects.create_user(**validated_data)


class PhoneRegisterSerializer(serializers.Serializer):
    phone = serializers.CharField(max_length=15)
    user_type = serializers.ChoiceField(choices=User.UserType.choices, default="seeker")
    preferred_lang = serializers.ChoiceField(choices=User.Language.choices, default="en")


# ── Login ─────────────────────────────────────────────────────────────────

class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField()

    def validate(self, data):
        user = authenticate(email=data["email"], password=data["password"])
        if not user:
            raise serializers.ValidationError("Invalid email or password.")
        if not user.is_active:
            raise serializers.ValidationError("Account is disabled.")
        data["user"] = user
        return data


class PhoneOTPRequestSerializer(serializers.Serializer):
    phone = serializers.CharField(max_length=15)


class PhoneOTPVerifySerializer(serializers.Serializer):
    phone = serializers.CharField(max_length=15)
    otp = serializers.CharField(max_length=6)


class MagicLinkRequestSerializer(serializers.Serializer):
    email = serializers.EmailField()


class MagicLinkVerifySerializer(serializers.Serializer):
    token = serializers.UUIDField()


# ── Social OAuth ──────────────────────────────────────────────────────────

class SocialAuthSerializer(serializers.Serializer):
    access_token = serializers.CharField()
    user_type = serializers.ChoiceField(choices=User.UserType.choices, default="seeker")


# ── Password ──────────────────────────────────────────────────────────────

class PasswordResetRequestSerializer(serializers.Serializer):
    email = serializers.EmailField()


class PasswordResetConfirmSerializer(serializers.Serializer):
    token = serializers.CharField()
    new_password = serializers.CharField(min_length=8, validators=[validate_password])


class PasswordChangeSerializer(serializers.Serializer):
    old_password = serializers.CharField()
    new_password = serializers.CharField(min_length=8, validators=[validate_password])

    def validate_old_password(self, value):
        if not self.context["request"].user.check_password(value):
            raise serializers.ValidationError("Current password is incorrect.")
        return value


# ── Email Verification ────────────────────────────────────────────────────

class EmailVerifySerializer(serializers.Serializer):
    token = serializers.CharField(max_length=6)


class ResendVerificationSerializer(serializers.Serializer):
    email = serializers.EmailField()


# ── 2FA / TOTP ────────────────────────────────────────────────────────────

class TwoFactorSetupSerializer(serializers.Serializer):
    """Returns TOTP secret + QR URI on GET; accepts first code on POST."""
    code = serializers.CharField(max_length=6, required=False)


class TwoFactorVerifySerializer(serializers.Serializer):
    code = serializers.CharField(max_length=6)


# ── Profile ───────────────────────────────────────────────────────────────

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
            "id", "email", "phone", "user_type", "preferred_lang",
            "is_verified", "avatar_url", "date_joined", "last_login",
            "login_method",
        ]
        read_only_fields = ["id", "email", "is_verified", "date_joined", "last_login"]


class UserUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["phone", "preferred_lang", "avatar_url"]


# ── Sessions ──────────────────────────────────────────────────────────────

class UserSessionSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserSession
        fields = ["id", "device_info", "ip_address", "location", "is_trusted", "created_at", "last_active_at"]
        read_only_fields = fields


# ── Push Tokens ───────────────────────────────────────────────────────────

class PushTokenSerializer(serializers.ModelSerializer):
    class Meta:
        model = PushToken
        fields = ["id", "token", "platform", "is_active", "created_at"]
        read_only_fields = ["id", "created_at"]


# ── ToS ───────────────────────────────────────────────────────────────────

class AcceptTosSerializer(serializers.Serializer):
    version = serializers.CharField(max_length=20)


# ── Password Reset via SMS (#13) ─────────────────────────────────────────

class PasswordResetSMSRequestSerializer(serializers.Serializer):
    phone = serializers.CharField(max_length=15)


# ── Email Change (#19) ───────────────────────────────────────────────────

class EmailChangeSerializer(serializers.Serializer):
    new_email = serializers.EmailField()
    password = serializers.CharField()


# ── Phone Change (#20) ───────────────────────────────────────────────────

class PhoneChangeSerializer(serializers.Serializer):
    new_phone = serializers.CharField(max_length=15)


# ── Social Linking (#21–22) ──────────────────────────────────────────────

SOCIAL_PROVIDERS = [("google", "Google"), ("facebook", "Facebook"), ("linkedin", "LinkedIn"), ("apple", "Apple")]


class SocialLinkSerializer(serializers.Serializer):
    provider = serializers.ChoiceField(choices=SOCIAL_PROVIDERS)
    social_id = serializers.CharField(max_length=100)
    access_token = serializers.CharField(required=False)  # For verification


class SocialUnlinkSerializer(serializers.Serializer):
    provider = serializers.ChoiceField(choices=SOCIAL_PROVIDERS)


# ── Account Management (#14–15) ──────────────────────────────────────────

class AccountDeactivateSerializer(serializers.Serializer):
    password = serializers.CharField()


class AccountDeleteSerializer(serializers.Serializer):
    password = serializers.CharField()
    confirm_text = serializers.CharField()  # User types "DELETE"

    def validate_confirm_text(self, value):
        if value != "DELETE":
            raise serializers.ValidationError("Type DELETE to confirm.")
        return value


# ── NIC Recovery (#26) ───────────────────────────────────────────────────

class NICRecoverySerializer(serializers.Serializer):
    nic_number = serializers.CharField(max_length=12)


# ── Employer Verification (#35) ──────────────────────────────────────────

class EmployerVerificationSerializer(serializers.Serializer):
    registration_no = serializers.CharField(max_length=50, required=False)
    tax_id = serializers.CharField(max_length=50, required=False)
    address = serializers.CharField(max_length=500, required=False)
