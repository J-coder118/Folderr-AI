import logging

from core.models import User
from rest_framework import permissions
from rest_framework.request import Request

from .models import Folder, Share, ZippedFolder

log = logging.getLogger(__name__)


# params
# obj - file obj or folder
# user - requested user
# permission
# - 1 for Add
# - 2 for Update
# - 3 for Delete
# - 4 for view
def shared(obj, user, permission):
    result = False
    share_object_permissions = [1, 2, 3]

    if permission == 1:
        share_object_permissions = [1, 2]

    elif permission in [2, 3]:
        share_object_permissions = [1]
    else:
        share_object_permissions = [1, 2, 3]
    if Share.objects.filter(
        folder=obj, receiver=user, permission__in=share_object_permissions
    ).exists():
        result = True
    if (
        result is False
        and obj.parent
        and Share.objects.filter(
            folder=obj.parent,
            receiver=user,
            permission__in=share_object_permissions,
        ).exists()
    ):
        result = True
    return result


def delete_shared_assest(obj, user):
    result = False
    if Share.objects.filter(folder=obj, sender=user).exists():
        result = True
    if (
        result is False
        and obj.parent
        and Share.objects.filter(folder=obj.parent, sender=user).exists()
    ):
        result = True
    return result


class FileCreatePermission(permissions.BasePermission):
    def has_permission(self, request, view):
        selected_folder = request.data.get("folder")
        created_by = request.user
        if request.method == "POST":
            if selected_folder:
                try:
                    folder_obj = Folder.objects.get(id=int(selected_folder))
                except Folder.DoesNotExist:
                    folder_obj = None

                if created_by == folder_obj.created_by or shared(
                    folder_obj, request.user, 1
                ):
                    return True
            return False
        return True


class FileRetriveAuthenticate(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        if request.method == "PUT":
            folder = request.data.get("folder")
            if folder is not None:
                folder_object = Folder.objects.get(
                    id=request.data.get("folder")
                )
                return folder_object.created_by == request.user or shared(
                    obj.folder, request.user, 2
                )
            return obj.created_by == request.user or shared(
                obj.folder, request.user, 2
            )
        if request.method == "DELETE":
            return obj.created_by == request.user or delete_shared_assest(
                obj.folder, request.user
            )
            # return obj.created_by == request.user or shared(obj.folder, request.user, 3)
        return obj.created_by == request.user or shared(
            obj.folder, request.user, 4
        )


class FolderSubfolderPermission(permissions.BasePermission):
    def has_permission(self, request, view):
        parent = request.data.get("parent")
        if request.method == "POST":
            if parent:
                try:
                    folder = Folder.objects.get(id=parent)
                except Folder.DoesNotExist:
                    folder = None
                if folder:
                    if request.user == folder.created_by or shared(
                        folder, request.user, 1
                    ):
                        if not folder.parent:
                            return True
                    else:
                        return False
                else:
                    return False
            return True
        return True


class FolderRetriveAuthenticate(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        if request.method == "POST":
            parent_folder = Folder.objects.get(id=request.data.get("parent"))
            return (
                not obj.is_root
                and parent_folder.is_root
                and obj.created_by == request.user
            )

        if request.method == "PUT":
            new_parent_folder = request.data.get("parent")
            if new_parent_folder:
                if obj.parent:  # Get object must be have parent-folder
                    # get folder obj using submitted form parent Field
                    parent_folder = Folder.objects.get(id=new_parent_folder)
                    # select parent-folder must be root and created-user match with logged-in user
                    return (
                        parent_folder.is_root
                        and parent_folder.created_by == request.user
                        or shared(obj, request.user, 2)
                    )
                return False
            return obj.created_by == request.user or shared(
                obj, request.user, 2
            )
        if request.method == "DELETE":
            return obj.created_by == request.user or delete_shared_assest(
                obj, request.user
            )
            # return obj.created_by == request.user or shared(obj, request.user, 3)
        return obj.created_by == request.user or shared(obj, request.user, 4)


class StickyNotePermission(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        return obj.created_by == request.user


class SharePermission(permissions.BasePermission):
    def has_permission(self, request, view):
        if request.method == "POST":
            if not request.data.get("receiver_email"):
                try:
                    folder = Folder.objects.get(id=request.data.get("folder"))
                    receiver = User.objects.get(
                        id=request.data.get("receiver")
                    )
                    if receiver and folder:
                        if (
                            folder.created_by != request.user
                            or receiver == request.user
                        ):
                            return False
                    else:
                        if not folder or folder.created_by != request.user:
                            return False
                except Exception as e:
                    log.exception(e)
                    return False
        return True


class CanDownloadFolder(permissions.BasePermission):
    def has_object_permission(self, request: Request, view, obj: ZippedFolder):
        folder = obj.folder
        if folder in request.user.folder_set.all():
            return True
        try:
            request.user.receiver.get(folder__id=folder.id)
            return True
        except Share.DoesNotExist:
            return False


class TaskReminderFullAccess(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        return request.user == obj.task.created_by


class CanShareFile(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        return obj.folder.created_by == request.user


class PreventAIFolderUpdateDestroy(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        if obj.title == "AI":
            if request.method == "PATCH" or request.method == "DELETE":
                return False
        return True
