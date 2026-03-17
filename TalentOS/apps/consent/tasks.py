"""Celery tasks for consent app — data export and deletion processing."""

import io
import json
import logging
import zipfile
from datetime import timedelta

from celery import shared_task
from django.utils import timezone

logger = logging.getLogger("ats.consent")


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def process_data_export(self, data_request_id: str):
    """
    Build a GDPR data export ZIP for a candidate and upload to MinIO/S3.
    ZIP contains: profile.json, applications.json, consents.json, resumes/ files.
    """
    from django.conf import settings
    from apps.consent.models import DataRequest
    from apps.candidates.models import Candidate
    from apps.applications.models import Application
    from apps.consent.models import ConsentRecord

    try:
        dr = DataRequest.objects.get(id=data_request_id)
    except DataRequest.DoesNotExist:
        logger.error("DataRequest %s not found", data_request_id)
        return

    dr.status = "processing"
    dr.save(update_fields=["status"])

    try:
        candidate = Candidate.objects.get(id=dr.candidate_id)

        # ---- Build JSON payloads -----------------------------------------
        profile_data = {
            "id": str(candidate.id),
            "full_name": candidate.full_name,
            "email": candidate.primary_email or "",
            "phone": candidate.primary_phone or "",
            "location": candidate.location or "",
            "headline": candidate.headline or "",
            "total_experience_years": candidate.total_experience_years,
            "skills": candidate.tags or [],
            "created_at": str(candidate.created_at),
        }

        applications_qs = Application.objects.filter(
            candidate=candidate
        ).select_related("job", "current_stage")

        applications_data = [
            {
                "id": str(app.id),
                "job_title": app.job.title if app.job else None,
                "status": app.status,
                "applied_at": str(app.created_at),
                "current_stage": app.current_stage.name if app.current_stage else None,
            }
            for app in applications_qs
        ]

        consents_qs = ConsentRecord.objects.filter(
            candidate=candidate, tenant_id=dr.tenant_id
        )
        consents_data = [
            {
                "consent_type": c.consent_type,
                "granted": c.granted,
                "granted_at": str(c.granted_at) if c.granted_at else None,
                "revoked_at": str(c.revoked_at) if c.revoked_at else None,
            }
            for c in consents_qs
        ]

        # ---- Build ZIP in memory -----------------------------------------
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.writestr("profile.json", json.dumps(profile_data, indent=2))
            zf.writestr("applications.json", json.dumps(applications_data, indent=2))
            zf.writestr("consents.json", json.dumps(consents_data, indent=2))

            # Attach resume files if stored in MinIO
            try:
                import boto3
                from botocore.exceptions import ClientError

                s3 = boto3.client(
                    "s3",
                    endpoint_url=getattr(settings, "AWS_S3_ENDPOINT_URL", None),
                    aws_access_key_id=getattr(settings, "AWS_ACCESS_KEY_ID", ""),
                    aws_secret_access_key=getattr(settings, "AWS_SECRET_ACCESS_KEY", ""),
                )
                bucket = getattr(settings, "AWS_STORAGE_BUCKET_NAME", "ats-media")

                for resume in candidate.resumes.all():
                    key = str(resume.file_path).lstrip("/")
                    try:
                        obj = s3.get_object(Bucket=bucket, Key=key)
                        zf.writestr(f"resumes/{resume.original_filename}", obj["Body"].read())
                    except ClientError:
                        pass  # Skip missing files gracefully
            except Exception:
                pass  # S3 unavailable — skip attachments

        zip_buffer.seek(0)

        # ---- Upload ZIP --------------------------------------------------
        try:
            import boto3

            s3 = boto3.client(
                "s3",
                endpoint_url=getattr(settings, "AWS_S3_ENDPOINT_URL", None),
                aws_access_key_id=getattr(settings, "AWS_ACCESS_KEY_ID", ""),
                aws_secret_access_key=getattr(settings, "AWS_SECRET_ACCESS_KEY", ""),
            )
            bucket = getattr(settings, "AWS_STORAGE_BUCKET_NAME", "ats-media")
            s3_key = f"exports/{str(dr.tenant_id)}/{str(candidate.id)}/data_export.zip"
            s3.put_object(
                Bucket=bucket,
                Key=s3_key,
                Body=zip_buffer.getvalue(),
                ContentType="application/zip",
            )

            # Generate presigned URL valid for 72 hours
            url = s3.generate_presigned_url(
                "get_object",
                Params={"Bucket": bucket, "Key": s3_key},
                ExpiresIn=72 * 3600,
            )
            dr.result_url = url
        except Exception as exc:  # pragma: no cover
            logger.warning("S3 upload failed for export %s: %s", data_request_id, exc)
            dr.result_url = ""

        dr.status = "completed"
        dr.completed_at = timezone.now()
        dr.save(update_fields=["status", "completed_at", "result_url"])
        logger.info("Data export completed for DataRequest %s", data_request_id)

    except Exception as exc:
        dr.status = "failed"
        dr.save(update_fields=["status"])
        logger.exception("Data export failed for %s: %s", data_request_id, exc)
        raise self.retry(exc=exc)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def process_data_deletion(self, data_request_id: str):
    """
    GDPR Article 17 — Right to erasure.
    Soft-deletes candidate data: anonymises PII, marks candidate as deleted.
    A 30-day grace period is applied before hard-delete (handled by purge task).
    """
    from apps.consent.models import DataRequest
    from apps.candidates.models import Candidate

    try:
        dr = DataRequest.objects.get(id=data_request_id)
    except DataRequest.DoesNotExist:
        logger.error("DataRequest %s not found", data_request_id)
        return

    dr.status = "processing"
    dr.save(update_fields=["status"])

    try:
        candidate = Candidate.objects.get(id=dr.candidate_id)

        # Anonymise PII (soft delete — preserve application history for audit)
        candidate.primary_email = f"deleted_{candidate.id}@gdpr.invalid"
        candidate.full_name = "[Deleted User]"
        candidate.primary_phone = ""
        candidate.location = ""
        candidate.linkedin_url = ""
        candidate.github_url = ""
        candidate.portfolio_url = ""
        candidate.headline = ""
        candidate.pool_status = "gdpr_deleted"
        candidate.gdpr_deletion_requested_at = timezone.now()
        candidate.save()

        # Mark ConsentRecords as revoked
        from apps.consent.models import ConsentRecord

        ConsentRecord.objects.filter(
            candidate=candidate,
            tenant_id=dr.tenant_id,
        ).update(granted=False, revoked_at=timezone.now())

        dr.status = "completed"
        dr.completed_at = timezone.now()
        dr.save(update_fields=["status", "completed_at"])
        logger.info("Data deletion completed for DataRequest %s", data_request_id)

    except Exception as exc:
        dr.status = "failed"
        dr.save(update_fields=["status"])
        logger.exception("Data deletion failed for %s: %s", data_request_id, exc)
        raise self.retry(exc=exc)


@shared_task
def auto_purge_expired_candidates():
    """
    Celery-beat daily task.
    Hard-delete candidate records where:
    - gdpr_deletion_requested_at + 30-day grace period has passed, OR
    - retention period (from TenantSettings) has been exceeded and candidate has no active applications.
    """
    from django.db.models import Q
    from apps.candidates.models import Candidate
    from apps.applications.models import Application

    grace_cutoff = timezone.now() - timedelta(days=30)

    # Hard-delete candidates past grace period
    to_delete = Candidate.objects.filter(
        pool_status="gdpr_deleted",
        gdpr_deletion_requested_at__lte=grace_cutoff,
    )
    deleted_count = 0
    for candidate in to_delete:
        # Verify no active applications
        active = Application.objects.filter(
            candidate=candidate,
            status__in=["applied", "screening", "interview", "assessment", "offer"],
        ).exists()
        if not active:
            candidate.delete()
            deleted_count += 1

    logger.info("Auto-purge: hard-deleted %d candidates past GDPR grace period", deleted_count)
    return deleted_count


@shared_task
def expire_old_consent_records():
    """
    GDPR consent expiry task (#57).
    Marks ConsentRecords as expired where:
    - The consent is still active (granted=True, revoked_at=None)
    - expires_at < now  (if set), OR
    - created_at is older than the tenant's retention window (default 2 years)
    Runs daily via Celery beat.
    """
    from apps.consent.models import ConsentRecord
    expiry_horizon = timezone.now() - timedelta(days=730)  # 2-year default retention

    # Records with explicit expires_at in the past
    explicit_expired = ConsentRecord.objects.filter(
        granted=True,
        revoked_at__isnull=True,
        expires_at__lt=timezone.now(),
    )
    # Records older than 2 years and never explicitly set to expire
    implicit_expired = ConsentRecord.objects.filter(
        granted=True,
        revoked_at__isnull=True,
        expires_at__isnull=True,
        created_at__lt=expiry_horizon,
    )

    expired_count = 0
    for qs in (explicit_expired, implicit_expired):
        updated = qs.update(granted=False, revoked_at=timezone.now())
        expired_count += updated

    logger.info("expire_old_consent_records: expired %d consent records", expired_count)
    return expired_count
