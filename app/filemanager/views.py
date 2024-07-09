import datetime
import json
import logging
from datetime import timedelta

from backend.aws_setup import download, ocr
from celery.result import AsyncResult
from core.tasks import send_email
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.shortcuts import get_object_or_404
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from rest_framework import generics, permissions, status, viewsets
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.exceptions import (
    NotFound,
    PermissionDenied,
    ValidationError,
)
from rest_framework.generics import RetrieveAPIView
from rest_framework.mixins import (
    CreateModelMixin,
    DestroyModelMixin,
    ListModelMixin,
    RetrieveModelMixin,
    UpdateModelMixin,
)
from rest_framework.permissions import (
    IsAuthenticated,
    IsAuthenticatedOrReadOnly,
)
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import (
    AssetType,
    Comment,
    File,
    Folder,
    FolderTransfer,
    IgnoredSuggestedFolder,
    Share,
    SharedFile,
    SharedFileEmail,
    ShareNotification,
    StickyNote,
    Task,
    TaskReminder,
    VideoFile,
    ZippedFolder,
)
from .pagination import TaskPagination
from .permissions import (
    CanDownloadFolder,
    FileCreatePermission,
    FileRetriveAuthenticate,
    FolderRetriveAuthenticate,
    FolderSubfolderPermission,
    PreventAIFolderUpdateDestroy,
    SharePermission,
    StickyNotePermission,
    TaskReminderFullAccess,
)
from .serializers import (
    AssetTypeSerializer,
    CommentSerializer,
    FileSearchSerializer,
    FileSerializer,
    FolderCreateSerializer,
    FolderSearchSerializer,
    FolderSerializer,
    IgnoredSuggestedFolderSerializer,
    OnlyAssetTypeSerializer,
    PerformFolderTransferSerializer,
    SendShareFolderMailSerializer,
    SharedFileSerializer,
    ShareNotificationSerializer,
    ShareSerializer,
    StickyNoteSerializer,
    TaskReminderSerializer,
    TaskSerializer,
    TransferredFolderSerializer,
    VideoFileSerializer,
    ZippedFolderSerializer,
)
from .tasks import zip_folder_contents

log = logging.getLogger(__name__)

User = get_user_model()


class UserFolderViewSet(viewsets.ViewSet):
    def retrieve(self, request, pk=None):
        queryset = Folder.objects.filter(created_by=pk)
        if not queryset:
            return Response(status=status.HTTP_400_BAD_REQUEST)
        else:
            serializer = FolderSerializer(queryset, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)


class FolderViewSet(viewsets.ModelViewSet):
    queryset = Folder.objects.filter(visible=True)
    serializer_class = FolderSerializer
    permission_classes = [
        permissions.IsAuthenticated,
        FolderSubfolderPermission,
        FolderRetriveAuthenticate,
        PreventAIFolderUpdateDestroy,
    ]

    def get_queryset(self):
        order_by = self.request.query_params.get("order-by")
        if order_by is not None:
            log.debug("Ordering Folder queryset by %s.", order_by)
            if order_by == "latest":
                return self.queryset.order_by("-updated")
            else:
                return self.queryset.order_by("updated")
        log.debug("Using default ordering for Folder queryset.")
        return self.queryset

    def perform_create(self, serializer):
        if (
            self.request.user.can_create_asset
            or serializer.validated_data.get("parent") is not None
        ):
            serializer.save(created_by=self.request.user)
        else:
            raise PermissionDenied("Asset creation limit reached.")

        if serializer.validated_data.get("title") == "AI":
            raise ValidationError(
                detail="You can't have more than one AI folder."
            )

    def list(self, request, *args, **kwargs):
        user = self.request.user
        queryset = self.get_queryset().filter(created_by=user.id)
        parent = request.GET.get("parent")
        if parent is not None:
            queryset = queryset.filter(parent=int(parent))
        else:
            queryset = queryset.filter(is_root=True)
        serializer = self.serializer_class(queryset, many=True)
        return Response(serializer.data)

    def update(self, request, *args, **kwargs):
        current_folder = self.get_object()
        serializer = self.serializer_class(
            current_folder, data=request.data, partial=True
        )
        self.check_object_permissions(request, current_folder)
        if serializer.is_valid():
            serializer.save()
            return Response({"status": "success", "data": serializer.data})
        else:
            return Response({"status": "error", "message": serializer.errors})

    def destroy(self, request, pk=None, *args, **kwargs):
        try:
            current_obj = get_object_or_404(Folder, id=pk)
            self.check_object_permissions(request, current_obj)
            current_obj.delete()
            return Response(
                {"status": "success", "message": "delete folder successfully"}
            )
        except Exception as e:
            return Response({"status": "error", "message": str(e)})

    @action(detail=True, methods=["get"], url_path="download")
    def download(self, request, pk: int):
        try:
            folder = request.user.folder_set.get(pk=pk)
        except Folder.DoesNotExist:
            try:
                share = request.user.receiver.get(folder__id=pk)
            except Share.DoesNotExist:
                raise NotFound()
            folder = share.folder
        task_result = zip_folder_contents.delay(folder.pk)
        return Response({"taskId": task_result.id})

    @action(detail=False, methods=["get"], url_path="zip-result")
    def get_zip_result(self, request):
        task_id = request.GET.get("task_id")
        if task_id is None:
            raise NotFound()
        result = AsyncResult(id=task_id)
        if result.state == "SUCCESS":
            value = result.get()
            return Response({"zipId": value})
        elif result.state == "FAILURE":
            return Response({"failed": True})
        return Response({"pending": True})

    @action(detail=True, methods=["delete"], url_path="delete-media")
    def delete_media(self, request, pk=None):
        folders = request.data.get("folder")
        files = request.data.get("file")
        success = {"folder": [], "file": []}
        failed = {"folder": [], "file": []}
        if folders:
            for folder in folders:
                try:
                    current_obj = Folder.objects.get(id=int(folder))
                    self.check_object_permissions(self.request, current_obj)
                    current_obj.delete()
                    success["folder"].append(folder)
                except Exception:
                    failed["folder"].append(folder)

        if files:
            for file in files:
                try:
                    current_obj = File.objects.get(id=file)
                    self.check_object_permissions(self.request, current_obj)
                    current_obj.delete()
                    success["file"].append(file)
                except Exception:
                    failed["file"].append(file)
        return Response({"success": success, "failed": failed})

    @action(detail=False, methods=["get"], url_path="share")
    def share(self, request, *args, **kwargs):
        print(request.query_params)

        id = request.query_params.get("id")
        id = int(urlsafe_base64_decode(id).decode())
        folder = Folder.objects.filter(id=id)
        serializer = self.serializer_class(folder, many=True)

        print(args)
        print(kwargs)
        return Response({"hello": serializer.data})

    @action(detail=True, methods=["GET"], permission_classes=[IsAuthenticated])
    def transfer_detail(self, request, pk):
        folder_transfer = get_object_or_404(
            FolderTransfer, folder_id=pk, to_email=request.user.email
        )
        return Response(
            {
                "folderTitle": folder_transfer.folder.title,
                "senderFirstName": folder_transfer.folder.created_by.first_name,
                "senderLastName": folder_transfer.folder.created_by.last_name,
                "senderEmail": folder_transfer.folder.created_by.email,
            }
        )

    @action(
        methods=["POST"], detail=True, permission_classes=[IsAuthenticated]
    )
    def transfer(self, request, pk):
        folder = get_object_or_404(
            request.user.folder_set.all(), visible=True, pk=pk
        )
        if not folder.is_root:
            raise ValidationError("Can't transfer a subfolder.")
        serializer = PerformFolderTransferSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        transfer = folder.transfer_to_email(
            serializer.validated_data["to_email"]
        )
        transfer_serializer = TransferredFolderSerializer(instance=transfer)
        return Response(
            transfer_serializer.data, status=status.HTTP_201_CREATED
        )

    @action(
        methods=["POST"], detail=True, permission_classes=[IsAuthenticated]
    )
    def claim_transfer(self, request, pk):
        folder_transfer = get_object_or_404(
            FolderTransfer, folder_id=pk, to_email=request.user.email
        )
        folder_transfer.claim()
        return Response()


class ListFolder(APIView):
    """
    View to list all folders in the system.

    * Requires token authentication to post
    """

    permission_classes = [IsAuthenticatedOrReadOnly]

    def get(self, request, post_id=None):
        if post_id:
            item = Folder.objects.get(id=post_id)
            serializer = FolderSerializer(item)
            return Response(
                {"status": "success", "data": serializer.data},
                status=status.HTTP_200_OK,
            )
        isPublic = request.GET.get("isPublic", False)
        if isPublic is False:
            if request.user.is_authenticated:
                items = Folder.objects.filter(user=request.user)
            else:
                return Response(
                    {"status": "success", "data": []},
                    status=status.HTTP_200_OK,
                )
        else:
            items = Folder.objects.filter(isPublic=isPublic)
        serializer = FolderSerializer(items, many=True)
        return Response(
            {"status": "success", "data": serializer.data},
            status=status.HTTP_200_OK,
        )

    def post(self, request):
        data = {
            "title": request.data.get("title"),
            "public": True if request.data.get("public") == "true" else False,
            "user": request.user.id if request.user.is_authenticated else 1,
            "parent": request.data.get("parent"),
        }
        serializer = FolderCreateSerializer(data=data)
        if serializer.is_valid():
            obj = serializer.save()
            return Response(
                {"status": "success", "data": FolderSerializer(obj).data},
                status=status.HTTP_200_OK,
            )
        else:
            return Response(
                {"status": "error", "message": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )

    def patch(self, request, id=None):
        item = Folder.objects.get(id=id)
        serializer = FolderSerializer(item, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response({"status": "success", "data": serializer.data})
        else:
            return Response({"status": "error", "message": serializer.errors})

    def delete(self, request, id=None):
        item = get_object_or_404(Folder, id=id)
        item.delete()
        return Response({"status": "success", "data": "Item Deleted"})


"""
    This View Set return list of file on list action,
    on create action  create file object,
    on retrive method to get any one file with pk and also do
    update and delete
    and add extra action for retuen list of file with latest craeted file.
"""


class FileViewSet(viewsets.ModelViewSet):
    queryset = File.objects.all()
    serializer_class = FileSerializer
    permission_classes = [
        IsAuthenticated,
        FileCreatePermission,
        FileRetriveAuthenticate,
    ]

    def get_queryset(self):
        qs = self.queryset.filter(created_by=self.request.user)
        folder = self.request.GET.get("folder")
        if folder is not None:
            qs = qs.filter(folder_id=int(folder))
        return qs

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    def destroy(self, request, pk=None, *args, **kwargs):
        try:
            current_obj = get_object_or_404(File, id=pk)
            self.check_object_permissions(self.request, current_obj)
            current_obj.delete()
            return Response(
                {"status": "success", "data": "delete file successfully"}
            )
        except Exception as e:
            return Response({"status": "error", "message": str(e)})

    @action(detail=False)
    def recent_files(self, request):
        limit = request.GET.get("limit")
        if limit is None:
            limit = 10
        else:
            limit = int(limit)
        recent_files = request.user.file_set.all().order_by("-created")[:limit]
        serializers = self.get_serializer(recent_files, many=True)
        return Response(serializers.data)

    @action(detail=True, methods=["get", "post"], url_path="copy-file")
    def copy_file(self, request, pk=None):
        copy_file = File.objects.get(id=pk)
        data = {
            "file_name": copy_file.file_name,
            "file": copy_file.file,
            "folder": request.data["folder"],
        }
        serializer = FileSerializer(data=data, context={"request": request})

        if serializer.is_valid():
            serializer.save()
            return Response({"status": "success", "data": serializer.data})
        else:
            return Response({"status": "error", "message": serializer.errors})

    @action(detail=True, methods=["get"])
    def check_quality_score(self, request, pk):
        file = get_object_or_404(request.user.file_set.all(), pk=pk)
        success = file.update_quality_score()
        if success:
            file.refresh_from_db()
            return Response({"score": file.quality_score})
        return Response(
            {"detail": "Failed to check score."},
            status=status.HTTP_400_BAD_REQUEST,
        )


"""
    This Folder return files from particular folder
"""


class FolderFileViewSet(viewsets.ModelViewSet):
    queryset = File.objects.all()
    serializer_class = FileSerializer

    def retrieve(self, request, pk=None, *args, **kwargs):
        folder_file = File.objects.filter(folder=pk)
        serializer = self.get_serializer(folder_file, many=True)
        return Response(serializer.data)


"""
    Defult this viewset return Response all folders and when pass any root folder ID
    Then return subfolder of root folder
"""


class RetriveSubfolderViewSet(viewsets.ModelViewSet):
    queryset = Folder.objects.all()
    serializer_class = FolderSerializer

    def retrieve(self, request, pk=None):
        subFolder = Folder.objects.filter(parent=int(pk))
        serializer = FolderSerializer(subFolder, many=True)
        return Response(serializer.data)


"""
    This View Set return list of files as descending order
"""


class FilterFileViewSet(viewsets.ModelViewSet):
    serializer_class = FileSerializer

    def get_queryset(self):
        files_obj = File.objects.order_by("-created")
        return files_obj


class CreatePreSignedURL(APIView):
    permission_classes = [
        IsAuthenticated,
    ]

    def get(self, request, file_id):
        if file_id:
            try:
                allow_download = False
                params = request.query_params
                if params.get("download"):
                    allow_download = params.get("download")
                file = File.objects.get(id=file_id)
                url = ""
                if (
                    params.get("thumbnail") is not None
                    and json.loads(params.get("thumbnail")) is True
                ):
                    url = download(f"{file.thumbnail}", allow_download)
                else:
                    url = download(f"{file.file.name}", allow_download)
                # Generate PreSigned URL
                print(f"PRE SIGNED URL: {url}")

                return Response(
                    {"pre_signed_url": url}, status=status.HTTP_200_OK
                )
            except Exception as e:
                return Response(
                    {"error": str(e)}, status=status.HTTP_404_NOT_FOUND
                )


class OCR(APIView):
    permission_classes = [
        IsAuthenticated,
    ]

    def get(self, request, file_id):
        if request.user.can_scan_receipt:
            request.user.record_receipt_scan()
            file: File = get_object_or_404(
                request.user.file_set.all(), pk=file_id
            )
            expense_data = ocr(file.file.name)
            return Response(expense_data)
        raise PermissionDenied("Receipt scanning limit reached.")


class AssetTypeViewSet(
    viewsets.GenericViewSet, ListModelMixin, RetrieveModelMixin
):
    queryset = AssetType.objects.filter(hidden=False)
    serializer_class = AssetTypeSerializer
    permission_classes = [permissions.IsAuthenticated]

    def list(self, request, *args, **kwargs):
        try:
            assest = self.get_queryset()
            serializer = self.serializer_class(assest, many=True)
            return Response({"status": "success", "data": serializer.data})
        except Exception as e:
            return Response({"status": "error", "message": str(e)})

    @action(detail=False, methods=["get"], url_path="assets-list")
    def assets_list(self, request):
        try:
            assest = self.get_queryset()
            serializer = OnlyAssetTypeSerializer(assest, many=True)
            return Response({"status": "success", "data": serializer.data})
        except Exception as e:
            return Response({"status": "error", "message": str(e)})


# class NewsfeedViewSet(viewsets.ModelViewSet):
#     queryset = UserActivity.objects.all()
#     serializer_class = UserActivitySerializer
#     pagination_class = NewsfeedPagination
#     permission_classes = [permissions.IsAuthenticated]
#
#     def get_queryset(self):
#         order_by = self.request.query_params.get("order-by")
#         if order_by:
#             if order_by == "latest":
#                 return self.queryset.order_by("-created_at")
#             else:
#                 return self.queryset.order_by("created_at")
#         return self.queryset.order_by("-created_at")
#
#     def list(self, request, file=None, folder=None, *args, **kwargs):
#         params = request.query_params
#         action = (
#             params.get("actions").split(",") if params.get("actions") else []
#         )
#         folder = (
#             params.get("folder").split(",") if params.get("folder") else []
#         )
#         file = params.get("file").split(",") if params.get("file") else []
#         user = self.request.user
#         qs = self.get_queryset()
#         activities = qs.filter(user=user.id)
#         if action:
#             activities = activities.filter(action__in=action)
#
#         if folder:
#             activities = activities.filter(folder__in=folder)
#
#         if file:
#             activities = activities.filter(file__in=file)
#         queryset = self.paginate_queryset(activities)
#         serializer = self.serializer_class(queryset, many=True)
#
#         data = self.get_paginated_response(serializer.data)
#         return data
#
#     @action(detail=False)
#     def newest(self, request):
#         recent_activty = UserActivity.objects.filter(
#             user=self.request.user
#         ).order_by("-created_at")
#         serializers = self.get_serializer(recent_activty, many=True)
#         return Response(serializers.data)


class GlobalSearch(APIView):
    def get(self, request, *args, **kwargs):
        user = request.user
        params = request.query_params
        search_keyword = params.get("search")
        data = {"file": [], "folder": []}
        if len(search_keyword) >= 3:
            files = File.objects.filter(
                created_by=user.id, file_name__icontains=search_keyword
            )
            file_serialzier = FileSearchSerializer(files, many=True)
            data["file"] = file_serialzier.data
            folder = Folder.objects.filter(
                created_by=user.id, title__icontains=search_keyword
            )
            folder_serializer = FolderSearchSerializer(folder, many=True)
            data["folder"] = folder_serializer.data
        return Response(data)


class StickyNoteViewSet(viewsets.ModelViewSet):
    queryset = StickyNote.objects.all()
    serializer_class = StickyNoteSerializer
    permission_classes = [permissions.IsAuthenticated, StickyNotePermission]

    def get_queryset(self):
        qs = self.queryset.filter(created_by=self.request.user).order_by(
            "-updated"
        )
        folder_id = self.request.GET.get("folder")
        if folder_id is not None:
            qs = qs.filter(folder_id=int(folder_id))
        return qs

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    @action(detail=True, methods=["post"], url_path="copy-sticky-note")
    def copy_sticky_note(self, request, pk=None):
        try:
            object = StickyNote.objects.get(id=pk)
            if StickyNote.objects.filter(
                folder=request.data.get("folder"), title=object.title
            ).exists():
                title = {"title": f"{object.title} - copy"}
            else:
                title = {"title": object.title}
            data = {
                **title,
                "discription": object.discription,
                "pin": object.pin,
                "color": object.color,
                "folder": request.data.get("folder"),
            }
            self.check_object_permissions(self.request, object)
            serializer = self.serializer_class(
                data=data, context={"request": request}
            )
            if serializer.is_valid():
                serializer.save()
                return Response({"status": "success", "data": serializer.data})
            else:
                return Response(
                    {"status": "error", "message": serializer.errors}
                )
        except Exception as e:
            return Response({"status": "error", "message": str(e)})


class CommentViewSet(viewsets.ModelViewSet):
    queryset = Comment.objects.all()
    serializer_class = CommentSerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class sendShareFolderMail(generics.GenericAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = SendShareFolderMailSerializer

    def post(self, request):
        serializer = self.serializer_class(
            data=request.data, context={"request": request}
        )
        try:
            if serializer.is_valid():
                folder = Folder.objects.get(id=request.data.get("folder"))
                permission = request.data.get("permission")
                receiver_email = request.data.get("email")
                email_body = f"""Hello,\n{self.request.user.first_name} {self.request.user.last_name} ({self.request.user.email}) invited you to view the folder "{folder.title}"\n\nhttps://folderr.com/share-with-me/folders?s={urlsafe_base64_encode(str(self.request.user.id).encode())}&r={urlsafe_base64_encode(str(receiver_email).encode())}&f={urlsafe_base64_encode(str(folder.id).encode())}&p={urlsafe_base64_encode(str(permission).encode())}\n\nEnjoy!\nThe Folderr team"""
                send_email.delay(
                    subject="A folder was shared with you!",
                    body=email_body,
                    sender=settings.DEFAULT_FROM_EMAIL,
                    recipients=[receiver_email],
                    fail_silently=False,
                )
            return Response(
                {
                    "status": "success",
                    "data": "delete sticky-note successfully",
                }
            )
        except Exception as e:
            return Response({"status": "error", "message": str(e)})


class ShareViewSet(viewsets.ModelViewSet):
    queryset = Share.objects.all()
    serializer_class = ShareSerializer
    permission_classes = [SharePermission, permissions.IsAuthenticated]

    def get_queryset(self):
        order_by = self.request.query_params.get("order-by")
        if order_by is not None:
            if order_by == "latest":
                return self.queryset.order_by("-created")
            else:
                return self.queryset.order_by("created")

        return self.queryset

    def list(self, request, *args, **kwargs):
        user = self.request.user
        queryset = Share.objects.filter(sender=user.id)
        serializer = self.serializer_class(queryset, many=True)
        return Response(serializer.data)

    def create(self, request, *args, **kwargs):
        try:
            serializer = self.serializer_class(
                data=request.data, context={"request": request}
            )
            if serializer.is_valid():
                email = None
                save = False
                folder = Folder.objects.get(id=request.data.get("folder"))
                share_object = None
                receiver = request.data.get("receiver")
                receiver_email = request.data.get("receiver_email")
                if receiver:
                    share_object = Share.objects.filter(
                        folder=folder, receiver=receiver
                    )
                    save = True if share_object.exists() else False
                    if save:
                        email = share_object[0].receiver.email
                    else:
                        email = User.objects.filter(id=receiver)[0].email
                elif receiver_email:
                    email = receiver_email
                    share_object = Share.objects.filter(
                        folder=folder, receiver_email=email
                    )
                    save = True if share_object.exists() else False
                email_body = f"""Hello,\n{self.request.user.first_name} {self.request.user.last_name} ({self.request.user.email}) invited you to view the folder "{folder.title}"\n\nhttps://folderr.com/share-with-me/folders\n\nEnjoy!\nThe Folderr team"""
                html_body = f'''{self.request.user.first_name} {self.request.user.last_name} ({self.request.user.email}) invited you to view the folder "{folder.title}"'''
                button_link = (
                    f"https://folderr.com/share-with-me/folders/{folder.id}"
                )
                send_email.delay(
                    subject="A folder was shared with you!",
                    body=email_body,
                    sender=settings.DEFAULT_FROM_EMAIL,
                    recipients=[email],
                    fail_silently=False,
                    html_body=html_body,
                    button_link=button_link,
                )
                if not save:
                    serializer.save()
                else:
                    share_record = Share.objects.get(id=share_object[0].id)
                    serializer = self.serializer_class(
                        share_record, data=request.data, partial=True
                    )
                    if serializer.is_valid():
                        serializer.save()
                        return Response(
                            {"status": "success", "data": serializer.data}
                        )

                return Response({"status": "success", "data": serializer.data})
            else:
                return Response(
                    {"status": "error", "message": serializer.errors}
                )
        except Exception as e:
            log.exception(e)
            return Response(
                {"status": "error", "message": "Something went wrong"}
            )

    @action(detail=False, url_path="receiver")
    def receive(self, request, pk=None):
        kwargs = {"receiver": self.request.user}

        if (share_id := self.request.query_params.get("id")) is not None:
            kwargs["id"] = share_id
        received_data = self.get_queryset().filter(**kwargs)

        serializer = self.serializer_class(received_data, many=True)

        return Response(serializer.data)

    @action(detail=True, url_path="received")
    def received(self, request, pk: int):
        """
        Received share detail.
        """
        received_share = get_object_or_404(
            self.request.user.receiver.all(), folder__pk=pk
        )
        serializer = self.serializer_class(received_share)
        return Response(serializer.data)

    def destroy(self, request, *args, **kwargs):
        try:
            object = self.get_object()
            Share.objects.filter(id=object.id).delete()
            return Response(
                {
                    "status": "success",
                    "data": "delete shared-folder successfully",
                }
            )
        except Exception as e:
            return Response({"status": "error", "message": str(e)})


class TaskViewSet(viewsets.ModelViewSet):
    queryset = Task.objects.all()
    serializer_class = TaskSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = TaskPagination

    def get_queryset(self):
        qs = self.request.user.task_set.order_by("due_at")
        folder_pk = self.request.query_params.get("folder")
        if folder_pk is not None and folder_pk != "":
            return qs.filter(folder_id=folder_pk)
        return qs

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    @action(detail=True, methods=["get"])
    def next_recurrence(self, request, pk):
        task = get_object_or_404(self.get_queryset(), pk=pk)
        next_recurrence = task.recurrences.after(datetime.datetime.now())
        return Response(next_recurrence)

    @action(detail=True, methods=["post"])
    def snooze(self, request, pk):
        task = get_object_or_404(self.get_queryset(), pk=pk)
        next_recurrence = task.recurrences.after(datetime.datetime.now())
        task.start_at = next_recurrence
        task.remind_at = next_recurrence - timedelta(days=1)
        task.save()
        serializer = self.serializer_class(instance=task)
        return Response(serializer.data)


class TaskReminderViewSet(
    RetrieveModelMixin,
    ListModelMixin,
    DestroyModelMixin,
    viewsets.GenericViewSet,
):
    serializer_class = TaskReminderSerializer
    queryset = TaskReminder.objects.all()
    permission_classes = [IsAuthenticated, TaskReminderFullAccess]

    def get_queryset(self):
        return self.queryset.filter(task__created_by=self.request.user)


class IgnoredSuggestedFolderViewSet(
    ListModelMixin, CreateModelMixin, viewsets.GenericViewSet
):
    serializer_class = IgnoredSuggestedFolderSerializer
    model = IgnoredSuggestedFolder
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return self.model.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class ShareNotificationViewSet(
    ListModelMixin, UpdateModelMixin, viewsets.GenericViewSet
):
    serializer_class = ShareNotificationSerializer
    permission_classes = [IsAuthenticated]
    model = ShareNotification

    def get_queryset(self):
        return self.model.objects.filter(share__receiver=self.request.user)


class VideoFileViewSet(viewsets.ModelViewSet):
    serializer_class = VideoFileSerializer
    permission_classes = [IsAuthenticated]
    model = VideoFile

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(
            data=request.data, context={"request": request}
        )

        try:
            serializer.is_valid(raise_exception=True)
        except Exception as e:
            log.debug("Could not create new video file because: %s", e)
            raise e
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(
            serializer.data, status=status.HTTP_201_CREATED, headers=headers
        )

    def get_queryset(self):
        qs = self.model.objects.filter(folder__created_by=self.request.user)
        folder = self.request.GET.get("folder")
        if folder is not None:
            qs = qs.filter(folder_id=int(folder))
        return qs


class RetrieveZippedFolder(RetrieveAPIView):
    queryset = ZippedFolder.objects.filter()
    serializer_class = ZippedFolderSerializer
    permission_classes = [IsAuthenticated, CanDownloadFolder]


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def share_file(request, file_pk, file_type):
    emails = request.data.get("emails")
    if emails is None or len(emails) == 0:
        return Response(
            {"detail": "Please provide some email addresses to share with."},
            status=status.HTTP_400_BAD_REQUEST,
        )
    if file_type == "file":
        file = get_object_or_404(File.objects.all(), pk=file_pk)
    elif file_type == "videofile":
        file = get_object_or_404(VideoFile.objects.all(), pk=int(file_pk))
    else:
        return Response(
            {"detail": "Unknown file type."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if file.folder.created_by != request.user:
        raise PermissionDenied(detail="You're not allowed to share this file.")

    try:
        shared_file = SharedFile.objects.get(
            content_type__model=file_type, object_id=file_pk
        )
    except SharedFile.DoesNotExist:
        shared_file = SharedFile(content_object=file)
        try:
            shared_file.full_clean()
        except ValidationError as e:
            log.exception(e)
            return Response(
                {"detail": "Failed to share file."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        try:
            shared_file.save()
        except Exception as e:
            log.exception(e)
            return Response(
                {"detail": "Failed to share file."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
    for email in emails:
        shared_file_email = SharedFileEmail(
            shared_file=shared_file, email=email
        )

        try:
            shared_file_email.full_clean()
        except ValidationError as e:
            log.exception(e)
            return Response(
                {"detail": "Failed to share file."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        try:
            shared_file_email.save()
        except Exception as e:
            log.exception(e)
            return Response(
                {"detail": "Failed to share file."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
    serializer = SharedFileSerializer(instance=shared_file)
    return Response(serializer.data, status=status.HTTP_201_CREATED)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_shared_file_emails(request, file_pk, file_type):
    if file_type == "file":
        content_type = ContentType.objects.get_for_model(File)
    elif file_type == "videofile":
        content_type = ContentType.objects.get_for_model(VideoFile)
    else:
        return Response(
            {"detail": "Unknown file type."},
            status=status.HTTP_400_BAD_REQUEST,
        )
    shared_file = get_object_or_404(
        SharedFile.objects.all(),
        content_type__pk=content_type.id,
        object_id=file_pk,
    )
    if shared_file.content_object.folder.created_by != request.user:
        raise PermissionDenied(
            detail="You're not allowed to access this file."
        )

    shared_file_emails = SharedFileEmail.objects.filter(
        shared_file=shared_file
    )
    return Response(
        {
            "shared_file_id": shared_file.id,
            "emails": [
                shared_file_email.email
                for shared_file_email in shared_file_emails
            ],
        }
    )


@api_view(["DELETE"])
@permission_classes([IsAuthenticated])
def unshare_file(request, shared_file_pk):
    shared_file = get_object_or_404(
        SharedFile.objects.all(), pk=shared_file_pk
    )
    if shared_file.content_object.folder.created_by != request.user:
        raise PermissionDenied(
            "You don't have permission to unshare this file."
        )
    email = request.data.get("email")
    if email is None:
        return Response(
            {"detail": "Please provide the email address to unshare with."},
            status=status.HTTP_400_BAD_REQUEST,
        )
    shared_file_email = get_object_or_404(
        shared_file.emails.all(), email=email
    )
    shared_file_email.delete()
    return Response()


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_shared_file(request, shared_file_pk):
    shared_file = get_object_or_404(SharedFile, pk=shared_file_pk)
    emails_allowed = [
        shared_email.email for shared_email in shared_file.emails.all()
    ]
    if request.user.email not in emails_allowed:
        if request.user != shared_file.content_object.folder.created_by:
            raise PermissionDenied(
                "You don't have permission to access this file."
            )
    serializer = SharedFileSerializer(instance=shared_file)
    return Response(serializer.data)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def list_shared_files(request):
    shared_file_emails = SharedFileEmail.objects.filter(
        email=request.user.email
    ).select_related("shared_file")
    shared_files = [email.shared_file for email in shared_file_emails]
    serializer = SharedFileSerializer(shared_files, many=True)
    return Response(serializer.data)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def list_received_folders(request):
    return Response([])


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def list_transferred_folders(request):
    folder_transfers = FolderTransfer.objects.filter(
        from_user=request.user, claimed=False
    )
    serializer = TransferredFolderSerializer(folder_transfers, many=True)
    return Response(serializer.data)


@api_view(["DELETE"])
@permission_classes([IsAuthenticated])
def cancel_folder_transfer(request, transfer_pk):
    transfer = get_object_or_404(
        FolderTransfer, from_user=request.user, claimed=False
    )
    serializer = FolderSerializer(instance=transfer.folder)
    transfer.folder.cancel_transfer()
    return Response(serializer.data)
