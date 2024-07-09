from rest_framework.permissions import IsAuthenticated
from rest_framework.viewsets import ModelViewSet
from sunrun.models import Checklist, Job, JobNote, JobPhoto, JobVideo
from sunrun.permissions import (
    CanAddNote,
    CanAddPhoto,
    CanAddVideo,
    IsChecklistOwnerOrReadonly,
    IsJobOwner,
    IsJobRelatedObjectOwner,
    IsSunrunEmployee,
    SunrunChecklistPermission,
)
from sunrun.serializers import (
    ChecklistSerializer,
    JobNoteSerializer,
    JobPhotoSerializer,
    JobSerializer,
    JobVideoSerializer,
)


class ChecklistViewset(ModelViewSet):
    serializer_class = ChecklistSerializer
    permission_classes = [
        IsAuthenticated,
        SunrunChecklistPermission,
        IsChecklistOwnerOrReadonly,
    ]
    queryset = Checklist.objects.all()

    def perform_create(self, serializer):
        instance = serializer.save(user=self.request.user)
        return instance


class JobViewset(ModelViewSet):
    serializer_class = JobSerializer
    permission_classes = [IsAuthenticated, IsSunrunEmployee, IsJobOwner]
    queryset = Job.objects.all()

    def get_queryset(self):
        return self.queryset.filter(user=self.request.user)

    def perform_create(self, serializer):
        instance = serializer.save(user=self.request.user)
        return instance


class JobPhotoViewset(ModelViewSet):
    serializer_class = JobPhotoSerializer
    permission_classes = [
        IsAuthenticated,
        IsSunrunEmployee,
        IsJobRelatedObjectOwner,
        CanAddPhoto,
    ]
    queryset = JobPhoto.objects.all()

    def get_queryset(self):
        return self.queryset.filter(job__user=self.request.user)


class JobVideoViewset(ModelViewSet):
    serializer_class = JobVideoSerializer
    permission_classes = [
        IsAuthenticated,
        IsSunrunEmployee,
        IsJobRelatedObjectOwner,
        CanAddVideo,
    ]
    queryset = JobVideo.objects.all()

    def get_queryset(self):
        return self.queryset.filter(job__user=self.request.user)


class JobNoteViewset(ModelViewSet):
    serializer_class = JobNoteSerializer
    permission_classes = [
        IsAuthenticated,
        IsSunrunEmployee,
        IsJobRelatedObjectOwner,
        CanAddNote,
    ]
    queryset = JobNote.objects.all()

    def get_queryset(self):
        return self.queryset.filter(job__user=self.request.user)
