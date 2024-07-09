from filemanager.utils import get_created_or_shared_folder
from rest_framework.permissions import BasePermission


class CanChat(BasePermission):
    def has_object_permission(self, request, view, obj):
        folder = get_created_or_shared_folder(request.user, obj.folder.id)
        return folder is not None
