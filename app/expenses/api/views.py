from django.db.models import QuerySet
from rest_framework import status
from rest_framework.generics import get_object_or_404
from rest_framework.mixins import CreateModelMixin, DestroyModelMixin, ListModelMixin, \
    RetrieveModelMixin
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from expenses.api.serializers import ExpenseSerializer
from expenses.models import Expense
from filemanager.models import File

CREATED_AT_OLDEST_PARAM = "created_at-oldest"


class ExpenseSetPagination(PageNumberPagination):
    page_size = 5


class ExpenseViewSet(ListModelMixin, RetrieveModelMixin, CreateModelMixin,
                     DestroyModelMixin,
                     GenericViewSet):
    serializer_class = ExpenseSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = ExpenseSetPagination

    def get_ordered_queryset(self, qs: QuerySet[Expense]):
        order_by = self.request.query_params.get("order_by")
        ordered_qs = qs.order_by("-created_at")
        if order_by is not None:
            if order_by == CREATED_AT_OLDEST_PARAM:
                ordered_qs = qs.order_by("created_at")
        return ordered_qs

    def get_queryset(self):
        qs = self.get_ordered_queryset(
            Expense.objects.all().filter(file__created_by=self.request.user)
        )
        folder_id = self.request.query_params.get('folder')
        if folder_id is not None:
            folder = get_object_or_404(self.request.user.folder_set.all(), pk=folder_id)
            folder_expenses = qs.filter(file__folder=folder)
            if folder.is_root:
                subfolder_expenses = Expense.objects.none()
                for subfolder in folder.subfolders.all():
                    subfolder_expenses = subfolder_expenses | qs.filter(
                        file__folder=subfolder)
                folder_expenses = folder_expenses | subfolder_expenses
            qs = folder_expenses
        return qs

    def create(self, request: Request, *args, **kwargs):
        file_id = request.query_params.get('file_id')
        if file_id is None:
            return Response({"errors": ["Please supply a file id."]},
                            status=status.HTTP_400_BAD_REQUEST)
        file: File = get_object_or_404(request.user.file_set.all(), pk=file_id)
        success, errors, expense = file.save_ocr_data(request.data)
        if success is False:
            return Response({"errors": errors}, status=status.HTTP_400_BAD_REQUEST)
        serializer = self.serializer_class(expense)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
