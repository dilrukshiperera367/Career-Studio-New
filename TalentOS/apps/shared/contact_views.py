"""Contact form submission endpoint."""
from django.core.mail import send_mail
from django.conf import settings
from rest_framework.decorators import api_view, permission_classes, throttle_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle
from rest_framework import serializers, status
import logging

logger = logging.getLogger(__name__)


class ContactThrottle(AnonRateThrottle):
    rate = '5/hour'


class ContactSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=120)
    email = serializers.EmailField()
    company = serializers.CharField(max_length=120, required=False, allow_blank=True)
    message = serializers.CharField(max_length=4000)


@api_view(['POST'])
@permission_classes([AllowAny])
@throttle_classes([ContactThrottle])
def contact_submit(request):
    """
    Public endpoint that accepts contact-form submissions.
    Validates the payload, optionally emails the team, and returns 201.
    """
    ser = ContactSerializer(data=request.data)
    if not ser.is_valid():
        return Response(ser.errors, status=status.HTTP_422_UNPROCESSABLE_ENTITY)

    data = ser.validated_data
    subject = f"[ConnectOS Contact] {data['name']} — {data.get('company', 'n/a')}"
    body = (
        f"Name: {data['name']}\n"
        f"Email: {data['email']}\n"
        f"Company: {data.get('company', '—')}\n\n"
        f"{data['message']}"
    )

    try:
        recipient = getattr(settings, 'CONTACT_EMAIL', 'hello@connectos.io')
        send_mail(
            subject=subject,
            message=body,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[recipient],
            fail_silently=True,
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning("Contact form email delivery failed: %s", exc)

    return Response({'detail': 'Message received. We will be in touch soon.'}, status=status.HTTP_201_CREATED)
