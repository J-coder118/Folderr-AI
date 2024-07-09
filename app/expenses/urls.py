from django.urls import include, path

app_name = "expenses"

urlpatterns = [
    path("api/", include("expenses.api.urls")),
]
