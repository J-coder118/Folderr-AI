from django.contrib.auth import get_user_model
from rest_framework import permissions
from rest_framework.permissions import BasePermission
from sunrun.models import Job

User = get_user_model()


class SunrunChecklistPermission(BasePermission):
    def has_permission(self, request, view):
        if request.user.user_type == User.NORMAL_USER_TYPE:
            return False

        if request.method in permissions.SAFE_METHODS:
            return True

        return request.user.user_type == User.SUNRUN_ADMIN_USER_TYPE


class IsChecklistOwnerOrReadonly(BasePermission):
    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        return obj.user == request.user


class IsSunrunEmployee(BasePermission):
    def has_permission(self, request, view):
        return request.user.user_type == User.SUNRUN_EMPLOYEE_USER_TYPE


class IsJobOwner(BasePermission):
    def has_object_permission(self, request, view, obj):
        return obj.user == request.user


class IsJobRelatedObjectOwner(BasePermission):
    def has_object_permission(self, request, view, obj):
        return obj.job.user == request.user


class CanAddPhoto(BasePermission):
    def has_permission(self, request, view):
        if request.method == "POST":
            job_id = request.data.get("job")
            job = Job.objects.get(id=job_id)
            return job.checklist.add_photo
        return True


class CanAddVideo(BasePermission):
    def has_permission(self, request, view):
        if request.method == "POST":
            job_id = request.data.get("job")
            job = Job.objects.get(id=job_id)
            return job.checklist.add_video
        return True


class CanAddNote(BasePermission):
    def has_permission(self, request, view):
        if request.method == "POST":
            job_id = request.data.get("job")
            job = Job.objects.get(id=job_id)
            return job.checklist.add_note
        return True
