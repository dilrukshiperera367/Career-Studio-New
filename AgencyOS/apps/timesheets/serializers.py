"""Timesheets serializers."""
from rest_framework import serializers
from .models import TimesheetPeriod, Timesheet, TimesheetEntry, ExpenseReport, ExpenseLineItem


class TimesheetPeriodSerializer(serializers.ModelSerializer):
    class Meta:
        model = TimesheetPeriod
        fields = "__all__"
        read_only_fields = ["id", "agency", "created_at"]


class TimesheetEntrySerializer(serializers.ModelSerializer):
    class Meta:
        model = TimesheetEntry
        fields = "__all__"
        read_only_fields = ["id"]


class ExpenseLineItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = ExpenseLineItem
        fields = "__all__"
        read_only_fields = ["id"]


class ExpenseReportSerializer(serializers.ModelSerializer):
    line_items = ExpenseLineItemSerializer(many=True, read_only=True)

    class Meta:
        model = ExpenseReport
        fields = "__all__"
        read_only_fields = ["id", "agency", "created_at", "updated_at"]


class TimesheetSerializer(serializers.ModelSerializer):
    entries = TimesheetEntrySerializer(many=True, read_only=True)
    expenses = ExpenseReportSerializer(many=True, read_only=True)

    class Meta:
        model = Timesheet
        fields = "__all__"
        read_only_fields = ["id", "agency", "gross_pay", "gross_bill", "gross_margin", "created_at", "updated_at"]


class TimesheetListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Timesheet
        fields = [
            "id", "assignment", "period", "status", "total_hours",
            "gross_pay", "gross_bill", "currency", "submitted_at",
        ]
