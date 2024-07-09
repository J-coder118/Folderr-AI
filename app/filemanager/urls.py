from django.urls import include, path
from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register("files", views.FileViewSet, basename="files"),
# router.register("filter-files", views.FilterFileViewSet, basename="filter-files"),
# router.register("folder-files", views.FolderFileViewSet, basename="folder-file"),
router.register("folders", views.FolderViewSet, basename="folders"),
# router.register("subfolders/folder", views.RetriveSubfolderViewSet, basename="subfolders"),
router.register("assets", views.AssetTypeViewSet, basename="assests"),
# router.register("newsfeed", views.NewsfeedViewSet, basename="newsfeed"),
router.register(
    "sticky-notes", views.StickyNoteViewSet, basename="sticky-notes"
),
router.register("comments", views.CommentViewSet, basename="comments"),
router.register("shared-with-me", views.ShareViewSet, basename="shares")
router.register("tasks", views.TaskViewSet, basename="tasks")
router.register("task-reminders", views.TaskReminderViewSet)
router.register(
    "ignored-suggested-folders",
    views.IgnoredSuggestedFolderViewSet,
    basename="ignored-suggested-folders",
)
router.register(
    "share-notifications",
    views.ShareNotificationViewSet,
    basename="share-notifications",
)
router.register("videos", views.VideoFileViewSet, basename="videos")

urlpatterns = [
    path("", include(router.urls)),
    path(
        "files/<str:file_id>/get_url",
        views.CreatePreSignedURL.as_view(),
        name="files_get_url",
    ),
    path(
        "files/<str:file_id>/analyze-expense",
        views.OCR.as_view(),
        name="analyze-expense",
    ),
    path("global-serch/", views.GlobalSearch.as_view(), name="global-serch"),
    # path("send-share-folder-mail/", views.sendShareFolderMail.as_view(), name="global-serch")
    path(
        "zipped-folder/<int:pk>/",
        views.RetrieveZippedFolder.as_view(),
        name="retrieve-zipped-folder",
    ),
    path(
        "share-file/<str:file_pk>/<str:file_type>/",
        views.share_file,
        name="share-file",
    ),
    path(
        "shared-file-emails/<str:file_pk>/<str:file_type>/",
        views.get_shared_file_emails,
        name="shared-file-emails",
    ),
    path(
        "unshare-file/<str:shared_file_pk>/",
        views.unshare_file,
        name="unshare-file",
    ),
    path("shared-files/", views.list_shared_files, name="shared-file-list"),
    path(
        "shared-files/<str:shared_file_pk>/",
        views.get_shared_file,
        name="shared-file-detail",
    ),
    path(
        "received-folders/",
        views.list_received_folders,
        name="rceived-folders",
    ),
    path(
        "transferred-folders/",
        views.list_transferred_folders,
        name="transferred-folders",
    ),
    path(
        "cancel-folder-transfer/<int:transfer_pk>/",
        views.cancel_folder_transfer,
        name="cancel-folder-transfer",
    ),
]
