from django.urls import path

from . import views

app_name = "help"

urlpatterns = [
    path("", views.GetHelpTopics.as_view(), name='get-help-topics')
]
