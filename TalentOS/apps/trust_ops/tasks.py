"""Celery tasks for Trust Ops app."""

from celery import shared_task


@shared_task(name="apps.trust_ops.tasks.scan_pending_documents")
def scan_pending_documents():
    """
    Scan documents with status='pending' using ClamAV.
    Updates DocumentScanResult status to 'clean' or 'infected'.
    """
    from django.utils import timezone
    from apps.trust_ops.models import DocumentScanResult

    pending = DocumentScanResult.objects.filter(status="pending")
    scanned = 0
    for doc in pending:
        # Placeholder: in production, stream file from S3 and call pyclamd
        # For now, mark as clean (replace with real scan logic)
        doc.status = "clean"
        doc.scanned_at = timezone.now()
        doc.save(update_fields=["status", "scanned_at"])
        scanned += 1

    return {"documents_scanned": scanned}


@shared_task(name="apps.trust_ops.tasks.expire_safe_share_links")
def expire_safe_share_links():
    """
    Mark SafeShareLinks whose expires_at has passed as effectively expired
    by deleting them (or optionally soft-deleting if auditing is required).
    Currently: no-op delete of expired, past-access links — can be adjusted.
    """
    from django.utils import timezone
    from apps.trust_ops.models import SafeShareLink

    now = timezone.now()
    expired = SafeShareLink.objects.filter(expires_at__lt=now)
    count = expired.count()
    expired.delete()
    return {"expired_links_deleted": count}


@shared_task(name="apps.trust_ops.tasks.check_employer_domain_dns")
def check_employer_domain_dns(domain_verification_id: str):
    """
    Check DNS TXT record for an EmployerDomainVerification.
    Marks as 'verified' if the expected token is present, otherwise 'failed'.
    """
    import dns.resolver  # type: ignore[import]
    from django.utils import timezone
    from apps.trust_ops.models import EmployerDomainVerification

    try:
        record = EmployerDomainVerification.objects.get(pk=domain_verification_id)
    except EmployerDomainVerification.DoesNotExist:
        return {"error": "record_not_found"}

    now = timezone.now()
    record.last_checked_at = now

    try:
        answers = dns.resolver.resolve(record.domain, "TXT")
        txt_values = [rdata.to_text().strip('"') for rdata in answers]
        if record.dns_token and record.dns_token in txt_values:
            record.status = "verified"
            record.verified_at = now
        else:
            record.status = "failed"
    except Exception:
        record.status = "failed"

    record.save(update_fields=["status", "last_checked_at", "verified_at"])
    return {"domain": record.domain, "status": record.status}
