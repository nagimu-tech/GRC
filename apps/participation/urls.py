from django.urls import path
from . import views

app_name = "participation"

urlpatterns = [
    path("new/", views.ParticipationCreateView.as_view(), name="create"),
    path("<int:pk>/edit/", views.ParticipationUpdateView.as_view(), name="update"),
    path("<int:pk>/delete/", views.ParticipationDeleteView.as_view(), name="delete"),
]
