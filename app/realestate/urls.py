from django.urls import include, path

app_name = "realestate"

urlpatterns = [
    path("api/", include("realestate.api.urls")),
]
