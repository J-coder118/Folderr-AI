from rest_framework.pagination import PageNumberPagination


class NewsfeedPagination(PageNumberPagination):
    page_size_query_param = "paginate"
    page_size = 5


class TaskPagination(PageNumberPagination):
    page_size = 20
    page_query_param = "task-page"
