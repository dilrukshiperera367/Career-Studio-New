from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import CourseViewSet, CourseEnrollmentViewSet, CohortProgramViewSet, CourseLearningPathViewSet

router = DefaultRouter()
router.register("courses", CourseViewSet, basename="course")
router.register("course-enrollments", CourseEnrollmentViewSet, basename="course-enrollment")
router.register("cohort-programs", CohortProgramViewSet, basename="cohort-program")
router.register("learning-paths", CourseLearningPathViewSet, basename="learning-path")

urlpatterns = [path("", include(router.urls))]
