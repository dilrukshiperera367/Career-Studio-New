"""
Unit tests for HRM backend modules (#216 — unit tests for core logic).
Covers: WorkflowConditionEvaluator, leave balance service, CSV export utils,
benefit enrollment validation, skill matrix, clamav integration.
"""
import pytest
from decimal import Decimal
from datetime import date, timedelta


# ─────────────────────────────────────────────────────────────────────────────
# WorkflowConditionEvaluator  (pure unit — no DB)
# ─────────────────────────────────────────────────────────────────────────────

class TestWorkflowConditionEvaluator:
    """Pure unit tests for the workflow condition evaluation engine."""

    def setup_method(self):
        from workflows.engine import WorkflowConditionEvaluator
        self.evaluator = WorkflowConditionEvaluator()

    def test_empty_conditions_always_true(self):
        assert self.evaluator.evaluate([], {}) is True

    def test_eq_operator_match(self):
        conditions = [{"field": "status", "operator": "eq", "value": "approved"}]
        assert self.evaluator.evaluate(conditions, {"status": "approved"}) is True

    def test_eq_operator_no_match(self):
        conditions = [{"field": "status", "operator": "eq", "value": "approved"}]
        assert self.evaluator.evaluate(conditions, {"status": "pending"}) is False

    def test_neq_operator(self):
        conditions = [{"field": "role", "operator": "neq", "value": "admin"}]
        assert self.evaluator.evaluate(conditions, {"role": "employee"}) is True
        assert self.evaluator.evaluate(conditions, {"role": "admin"}) is False

    def test_gt_operator(self):
        conditions = [{"field": "years_experience", "operator": "gt", "value": 3}]
        assert self.evaluator.evaluate(conditions, {"years_experience": 5}) is True
        assert self.evaluator.evaluate(conditions, {"years_experience": 2}) is False

    def test_gte_operator(self):
        conditions = [{"field": "salary", "operator": "gte", "value": 50000}]
        assert self.evaluator.evaluate(conditions, {"salary": 50000}) is True
        assert self.evaluator.evaluate(conditions, {"salary": 49999}) is False

    def test_lt_and_lte_operators(self):
        conditions_lt = [{"field": "age", "operator": "lt", "value": 30}]
        conditions_lte = [{"field": "age", "operator": "lte", "value": 30}]
        assert self.evaluator.evaluate(conditions_lt, {"age": 25}) is True
        assert self.evaluator.evaluate(conditions_lt, {"age": 30}) is False
        assert self.evaluator.evaluate(conditions_lte, {"age": 30}) is True

    def test_contains_operator(self):
        conditions = [{"field": "tags", "operator": "contains", "value": "python"}]
        assert self.evaluator.evaluate(conditions, {"tags": "python, django"}) is True
        assert self.evaluator.evaluate(conditions, {"tags": "java, spring"}) is False

    def test_starts_with_operator(self):
        conditions = [{"field": "department", "operator": "starts_with", "value": "eng"}]
        assert self.evaluator.evaluate(conditions, {"department": "Engineering"}) is True
        assert self.evaluator.evaluate(conditions, {"department": "Marketing"}) is False

    def test_in_operator_list(self):
        conditions = [{"field": "status", "operator": "in", "value": ["active", "on_leave"]}]
        assert self.evaluator.evaluate(conditions, {"status": "active"}) is True
        assert self.evaluator.evaluate(conditions, {"status": "inactive"}) is False

    def test_nested_field_access(self):
        conditions = [{"field": "employee.department.name", "operator": "eq", "value": "Finance"}]
        ctx = {"employee": {"department": {"name": "Finance"}}}
        assert self.evaluator.evaluate(conditions, ctx) is True

    def test_missing_field_returns_none(self):
        """Missing field should cause condition to fail gracefully."""
        conditions = [{"field": "nonexistent.field", "operator": "eq", "value": "x"}]
        assert self.evaluator.evaluate(conditions, {"other": "value"}) is False

    def test_unknown_operator_skipped(self):
        """Unknown operator should be skipped (logged warning), not crash."""
        conditions = [{"field": "status", "operator": "unknown_op", "value": "x"}]
        # Should not raise; unrecognized operators are skipped (continue)
        result = self.evaluator.evaluate(conditions, {"status": "x"})
        assert result is True  # condition skipped → all remaining conditions pass

    def test_multiple_conditions_and_logic(self):
        """All conditions must pass (AND semantics)."""
        conditions = [
            {"field": "status", "operator": "eq", "value": "active"},
            {"field": "salary", "operator": "gte", "value": 40000},
        ]
        assert self.evaluator.evaluate(conditions, {"status": "active", "salary": 50000}) is True
        assert self.evaluator.evaluate(conditions, {"status": "active", "salary": 30000}) is False
        assert self.evaluator.evaluate(conditions, {"status": "inactive", "salary": 50000}) is False

    def test_type_mismatch_returns_false(self):
        """Non-numeric strings in numeric comparison should return False gracefully."""
        conditions = [{"field": "salary", "operator": "gt", "value": 1000}]
        assert self.evaluator.evaluate(conditions, {"salary": "not-a-number"}) is False


# ─────────────────────────────────────────────────────────────────────────────
# WorkflowActionDispatcher — template rendering
# ─────────────────────────────────────────────────────────────────────────────

class TestWorkflowActionDispatcher:
    """Unit tests for WorkflowActionDispatcher template rendering."""

    def setup_method(self):
        from workflows.engine import WorkflowActionDispatcher
        self.dispatcher = WorkflowActionDispatcher()

    def test_render_template_substitution(self):
        tpl = "Hello {{name}}, your leave {{leave_type}} has been approved."
        ctx = {"name": "Alice", "leave_type": "Annual"}
        result = self.dispatcher._render_template(tpl, ctx)
        assert result == "Hello Alice, your leave Annual has been approved."

    def test_render_template_missing_key(self):
        tpl = "Hello {{name}}, {{missing}} field."
        ctx = {"name": "Bob"}
        result = self.dispatcher._render_template(tpl, ctx)
        assert "Bob" in result
        assert "{{missing}}" in result  # not substituted

    def test_dispatch_unknown_action_returns_false(self):
        ok = self.dispatcher.dispatch({"type": "nonsense_action"}, {})
        assert ok is False


# ─────────────────────────────────────────────────────────────────────────────
# Leave balance calculations  (pure unit)
# ─────────────────────────────────────────────────────────────────────────────

class TestLeaveBalanceCalculation:
    """Unit tests for leave balance helper functions."""

    def test_working_days_between_same_day(self):
        """A leave starting and ending on the same weekday = 1 day."""
        from leave_attendance.utils import working_days_between
        monday = date(2025, 1, 6)  # Monday
        assert working_days_between(monday, monday) == 1

    def test_working_days_between_full_week(self):
        from leave_attendance.utils import working_days_between
        mon = date(2025, 1, 6)
        fri = date(2025, 1, 10)
        assert working_days_between(mon, fri) == 5

    def test_working_days_excludes_weekends(self):
        from leave_attendance.utils import working_days_between
        fri = date(2025, 1, 10)
        mon = date(2025, 1, 13)
        # fri, (sat, sun), mon = 2 working days
        assert working_days_between(fri, mon) == 2

    def test_working_days_inverted_returns_zero(self):
        from leave_attendance.utils import working_days_between
        result = working_days_between(date(2025, 1, 10), date(2025, 1, 6))
        assert result == 0


# ─────────────────────────────────────────────────────────────────────────────
# ClamAV module  (unit — no socket required)
# ─────────────────────────────────────────────────────────────────────────────

class TestClamAVModule:
    """Unit tests for the ClamAV integration helper."""

    def test_scan_returns_clean_when_disabled(self, settings):
        """When CLAMAV_ENABLED=False the scan always returns is_clean=True."""
        settings.CLAMAV_ENABLED = False
        from platform_core.clamav import scan_file, ScanResult
        import io
        result = scan_file(io.BytesIO(b"hello"), filename="test.pdf")
        assert result.is_clean is True
        assert result.threat is None

    def test_scan_result_is_error_property(self):
        """ScanResult.is_error is True when error field is set."""
        from platform_core.clamav import ScanResult
        ok = ScanResult(is_clean=True)
        err = ScanResult(is_clean=False, error="connection refused")
        assert ok.is_error is False
        assert err.is_error is True

    def test_scan_connection_error_strict_mode(self, settings):
        """Connection error in strict mode should return is_clean=False."""
        settings.CLAMAV_ENABLED = True
        settings.CLAMAV_STRICT_MODE = True
        settings.CLAMAV_HOST = "127.0.0.99"   # non-routable → connection error
        settings.CLAMAV_PORT = 9999
        settings.CLAMAV_TIMEOUT = 1
        from platform_core.clamav import scan_file
        import io
        result = scan_file(io.BytesIO(b"test"), filename="test.pdf")
        assert result.is_clean is False
        assert result.error is not None

    def test_scan_connection_error_non_strict(self, settings):
        """Connection error in non-strict mode should return is_clean=True (fail-open)."""
        settings.CLAMAV_ENABLED = True
        settings.CLAMAV_STRICT_MODE = False
        settings.CLAMAV_HOST = "127.0.0.99"
        settings.CLAMAV_PORT = 9999
        settings.CLAMAV_TIMEOUT = 1
        from platform_core.clamav import scan_file
        import io
        result = scan_file(io.BytesIO(b"test"), filename="test.pdf")
        assert result.is_clean is True
        assert result.error is not None


# ─────────────────────────────────────────────────────────────────────────────
# File validators
# ─────────────────────────────────────────────────────────────────────────────

class TestFileValidators:
    """Unit tests for document upload validation."""

    def test_valid_pdf_extension(self):
        from platform_core.file_validators import validate_document_upload
        from django.core.files.uploadedfile import SimpleUploadedFile
        # Minimal PDF header
        pdf_content = b"%PDF-1.4 minimal"
        f = SimpleUploadedFile("resume.pdf", pdf_content, content_type="application/pdf")
        # ClamAV disabled in test settings; should pass extension + magic
        f.name = "resume.pdf"
        f.size = len(pdf_content)
        # Should not raise
        validate_document_upload(f)

    def test_invalid_extension_raises(self):
        from platform_core.file_validators import validate_document_upload
        from django.core.files.uploadedfile import SimpleUploadedFile
        from rest_framework.exceptions import ValidationError
        f = SimpleUploadedFile("malware.exe", b"MZ\x90\x00", content_type="application/octet-stream")
        f.name = "malware.exe"
        f.size = 4
        with pytest.raises(ValidationError):
            validate_document_upload(f)

    def test_oversized_file_raises(self):
        from platform_core.file_validators import validate_document_upload
        from django.core.files.uploadedfile import SimpleUploadedFile
        from rest_framework.exceptions import ValidationError
        big_content = b"%PDF" + b"0" * (21 * 1024 * 1024)
        f = SimpleUploadedFile("big.pdf", big_content, content_type="application/pdf")
        f.name = "big.pdf"
        f.size = len(big_content)
        with pytest.raises(ValidationError):
            validate_document_upload(f)

    def test_wrong_magic_bytes_raises(self):
        """PDF extension but ZIP magic should be rejected."""
        from platform_core.file_validators import validate_document_upload
        from django.core.files.uploadedfile import SimpleUploadedFile
        from rest_framework.exceptions import ValidationError
        f = SimpleUploadedFile("fake.pdf", b"PK\x03\x04rest", content_type="application/pdf")
        f.name = "fake.pdf"
        f.size = 8
        with pytest.raises(ValidationError):
            validate_document_upload(f)
