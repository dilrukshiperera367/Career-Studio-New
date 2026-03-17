from django.apps import AppConfig


class LeaveAttendanceConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'leave_attendance'

    def ready(self):
        import leave_attendance.signals  # noqa
