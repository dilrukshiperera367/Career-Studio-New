from django.urls import path
from apps.shared import bulk_api, advanced_api
from apps.shared.contact_views import contact_submit

urlpatterns = [
    path("contact/", contact_submit, name="contact-submit"),
    path("bulk/stage/", bulk_api.bulk_stage_transition, name="bulk-stage"),
    path("bulk/reject/", bulk_api.bulk_reject, name="bulk-reject"),
    path("bulk/tag/", bulk_api.bulk_tag, name="bulk-tag"),
    path("export/candidates/", bulk_api.export_candidates_csv, name="export-candidates"),
    path("export/jobs/", bulk_api.export_jobs_csv, name="export-jobs"),
    path("import/candidates/", bulk_api.import_candidates_csv, name="import-candidates"),
    path("candidates/merge/", bulk_api.merge_candidates, name="merge-candidates"),
    path("jobs/<uuid:job_id>/clone/", bulk_api.clone_job, name="clone-job"),
    # Advanced APIs
    path("activity/", advanced_api.activity_feed, name="activity-feed"),
    path("candidates/compare/", advanced_api.compare_candidates, name="compare-candidates"),
    path("talent-pools/", advanced_api.talent_pools, name="talent-pools"),
]
