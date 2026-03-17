"""
Cross-system authentication utilities for ConnectOS platform.

Provides:
  - Token serializer that embeds `active_product` claim in every JWT
  - Token validator that accepts tokens from the other system (ATS ↔ HRM)
  - Module switcher URL builder

Both ATS and HRM must share the same SHARED_JWT_SECRET environment variable
for cross-system token acceptance to work.

Usage:
    # In settings.py SIMPLE_JWT config:
    "TOKEN_OBTAIN_SERIALIZER": "apps.accounts.cross_auth.TokenObtainSerializer"
"""

import logging
from typing import Optional
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.tokens import AccessToken, RefreshToken
from django.conf import settings

logger = logging.getLogger(__name__)

# ─── Product identifier constants ────────────────────────────────────────────

PRODUCT_ATS = "ats"
PRODUCT_HRM = "hrm"


# ─── Token serializer with active_product claim ──────────────────────────────

class CrossSystemTokenObtainPairSerializer(TokenObtainPairSerializer):
    """
    JWT serializer that injects the `active_product` claim and platform-level
    nav hints into every access token.

    The claim tells the frontend which product issued the token and which
    product URLs are available via the module switcher.
    """

    @classmethod
    def get_token(cls, user) -> RefreshToken:
        token = super().get_token(user)

        # Inject product claim
        product = getattr(settings, "ATS_PRODUCT_CLAIM", PRODUCT_ATS)
        token["active_product"] = product
        token["tenant_id"] = str(getattr(user, "tenant_id", ""))

        # Cross-link to the counterpart system
        hrm_url = getattr(settings, "HRM_BASE_URL", "")
        ats_url = getattr(settings, "ATS_BASE_URL", "")

        if product == PRODUCT_ATS:
            token["hrm_url"] = hrm_url
        else:
            token["ats_url"] = ats_url

        # Embed user roles for frontend feature-gating
        try:
            roles = list(user.user_roles.values_list("role__name", flat=True))
            token["roles"] = roles
        except Exception:
            token["roles"] = []

        return token

    def validate(self, attrs):
        data = super().validate(attrs)

        # Append product + switch URL to the login response
        product = getattr(settings, "ATS_PRODUCT_CLAIM", PRODUCT_ATS)
        data["active_product"] = product
        data["hrm_url"] = getattr(settings, "HRM_BASE_URL", "")

        return data


def build_module_switch_url(
    target_product: str,
    token: str,
    deep_path: str = "/dashboard",
) -> Optional[str]:
    """
    Build a cross-system deep-link URL that pre-authenticates the user in the
    target product.

    The target product validates the token using the shared signing key
    (SHARED_JWT_SECRET), so the user lands on `deep_path` without a separate
    login prompt.

    Args:
        target_product: "ats" or "hrm"
        token: The user's current access token (issued by either product)
        deep_path: Path to redirect to after validation (default: /dashboard)

    Returns:
        Full URL string, or None if the base URL is not configured.
    """
    if target_product == PRODUCT_HRM:
        base = getattr(settings, "HRM_BASE_URL", "")
    else:
        base = getattr(settings, "ATS_BASE_URL", "")

    if not base:
        logger.warning("Module switch URL could not be built — %s base URL not configured", target_product)
        return None

    base = base.rstrip("/")
    return f"{base}/auth/switch?token={token}&redirect={deep_path}"


def validate_cross_system_token(token_str: str) -> Optional[AccessToken]:
    """
    Validate a JWT token from the counterpart system.
    Both systems must share the same SHARED_JWT_SECRET for this to work.

    Returns the AccessToken if valid, None otherwise.
    """
    try:
        token = AccessToken(token_str)
        return token
    except Exception as exc:
        logger.warning("Cross-system token validation failed: %s", exc)
        return None
