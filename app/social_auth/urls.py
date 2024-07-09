from django.urls import path

from . import views

urlpatterns = [
    path("google/", views.GoogleSocialAuthView.as_view()),
    path("facebook/", views.FacebookSocialAuthView.as_view()),
    path("apple/", views.siwa, name="siwa"),
]
