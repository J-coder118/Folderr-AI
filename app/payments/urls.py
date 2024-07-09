from django.urls import include, path

app_name = "payments"

urlpatterns = [path("api/", include("payments.api.urls"))]
