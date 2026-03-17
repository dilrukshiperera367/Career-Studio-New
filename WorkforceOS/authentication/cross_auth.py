"""
Cross-system authentication utilities for ConnectOS platform (HRM side).

Both ATS and HRM share SHARED_JWT_SECRET so a user logged into either
system can switch to the other without re-authentication.

Usage:
    # In settings.py SIMPLE_JWT config:
    "TOKEN_OBTAIN_SERIALIZER": "authentication.cross_auth.CrossSystemTokenObtainPairSerializer"
"""

import logging
from typing import Optional
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.tokens import AccessToken, RefreshToken
from django.conf import settings

logger = logging.getLogger(__name__)

PRODUCT_ATS = "ats"
PRODUCT_HRM = "hrm"


class CrossSystemTokenObtainPairSerializer(TokenObtainPairSerializer):
    """
    JWT serializer that injects `active_product` = 'hrm' and the ATS URL
    into every token for cross-system navigation (module switcher).
    """

    @classmethod
    def get_token(cls, user) -> RefreshToken:
        token = super().get_token(user)

        product = getattr(settings, "HRM_PRODUCT_CLAIM", PRODUCT_HRM)
        token["active_product"] = product
        token["tenant_id"] = str(getattr(user, "tenant_id", ""))

        ats_url = getattr(settings, "ATS_BASE_URL_FRONTEND", "")
        token["ats_url"] = ats_url

        # Embed role names for frontend feature-gating
        try:
            roles = list(
                user.user_roles.select_related("role").values_list("role__name", flat=True)
            )
            token["roles"] = roles
        except Exception:
            token["roles"] = []

        return token

    def validate(self, attrs):
        data = super().validate(attrs)
        data["active_product"] = getattr(settings, "HRM_PRODUCT_CLAIM", PRODUCT_HRM)
        data["ats_url"] = getattr(settings, "ATS_BASE_URL_FRONTEND", "")
        return data


def build_module_switch_url(
    target_product: str,
    token: str,
    deep_path: str = "/dashboard",
) -> Optional[str]:
    """
    Build a cross-product deep-link with the current JWT embedded.
    The receiving app validates with the shared signing key.
    """
    if target_product == PRODUCT_ATS:
        base = getattr(settings, "ATS_BASE_URL_FRONTEND", "")
    else:
        base = getattr(settings, "HRM_BASE_URL", "http://localhost:5173")

    if not base:
        return None

    base = base.rstrip("/")
    return f"{base}/auth/switch?token={token}&redirect={deep_path}"


def validate_cross_system_token(token_str: str) -> Optional[AccessToken]:
    """
    Validate a JWT token from the ATS system.
    Works only if SHARED_JWT_SECRET is configured in both apps.
    """
    try:
        return AccessToken(token_str)
    except Exception as exc:
        logger.warning("Cross-system token validation failed: %s", exc)
        return None
