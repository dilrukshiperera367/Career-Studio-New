"""CampusOS — Alumni Mentors serializers."""

from rest_framework import serializers
from .models import AlumniProfile, AlumniJobShare, CircleEnrollment, GroupMentoringCircle, MentorRequest, MentorSession, MentorshipGoal


class AlumniProfileListSerializer(serializers.ModelSerializer):
    full_name = serializers.SerializerMethodField()

    class Meta:
        model = AlumniProfile
        fields = [
            "id", "full_name", "graduation_year", "current_employer", "current_designation",
            "current_industry", "mentoring_areas", "mentor_rating", "total_sessions_completed",
            "is_mentor", "preferred_meeting_mode",
        ]

    def get_full_name(self, obj):
        return obj.user.get_full_name()


class AlumniProfileDetailSerializer(serializers.ModelSerializer):
    full_name = serializers.SerializerMethodField()
    avatar_url = serializers.SerializerMethodField()

    class Meta:
        model = AlumniProfile
        fields = "__all__"
        read_only_fields = ["id", "user", "campus", "is_verified", "mentor_rating", "total_sessions_completed"]

    def get_full_name(self, obj):
        return obj.user.get_full_name()

    def get_avatar_url(self, obj):
        return getattr(obj.user, "avatar_url", None)


class MentorRequestSerializer(serializers.ModelSerializer):
    mentor_name = serializers.SerializerMethodField()
    student_name = serializers.SerializerMethodField()

    class Meta:
        model = MentorRequest
        fields = "__all__"
        read_only_fields = ["id", "student", "status", "accepted_at", "completed_at"]

    def get_mentor_name(self, obj):
        return obj.mentor.user.get_full_name()

    def get_student_name(self, obj):
        return obj.student.get_full_name()


class MentorSessionSerializer(serializers.ModelSerializer):
    class Meta:
        model = MentorSession
        fields = "__all__"
        read_only_fields = ["id"]


class MentorshipGoalSerializer(serializers.ModelSerializer):
    class Meta:
        model = MentorshipGoal
        fields = "__all__"
        read_only_fields = ["id"]


class GroupMentoringCircleSerializer(serializers.ModelSerializer):
    host_name = serializers.SerializerMethodField()
    enrolled_count = serializers.SerializerMethodField()

    class Meta:
        model = GroupMentoringCircle
        fields = "__all__"
        read_only_fields = ["id", "campus", "host"]

    def get_host_name(self, obj):
        return obj.host.user.get_full_name()

    def get_enrolled_count(self, obj):
        return obj.enrollments.count()


class AlumniJobShareSerializer(serializers.ModelSerializer):
    class Meta:
        model = AlumniJobShare
        fields = "__all__"
        read_only_fields = ["id", "campus", "shared_by", "view_count"]
