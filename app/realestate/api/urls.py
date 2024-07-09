from django.urls import path

from . import views

urlpatterns = [path("find-home/", views.find_home, name="find-home-api"),
               path("update-home/<int:pk>/", views.update_home, name='update-home-api')]
