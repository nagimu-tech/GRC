from django.urls import path
from . import views

app_name = "catalog"

urlpatterns = [
    # Должности
    path("positions/", views.PositionListView.as_view(), name="position_list"),
    path("positions/new/", views.PositionCreateView.as_view(), name="position_create"),
    path("positions/<int:pk>/edit/", views.PositionUpdateView.as_view(), name="position_update"),
    path("positions/<int:pk>/delete/", views.PositionDeleteView.as_view(), name="position_delete"),

    # Курсы
    path("courses/", views.CourseListView.as_view(), name="course_list"),
    path("courses/new/", views.CourseCreateView.as_view(), name="course_create"),
    path("courses/<int:pk>/", views.CourseDetailView.as_view(), name="course_detail"),
    path("courses/<int:pk>/edit/", views.CourseUpdateView.as_view(), name="course_update"),

    # Запуски курсов
    path("sessions/new/", views.SessionCreateView.as_view(), name="session_create"),
    path("sessions/<int:pk>/", views.SessionDetailView.as_view(), name="session_detail"),
    path("sessions/<int:pk>/edit/", views.SessionUpdateView.as_view(), name="session_update"),
    path("sessions/<int:pk>/delete/", views.SessionDeleteView.as_view(), name="session_delete"),
    path("sessions/<int:pk>/photos/add/", views.SessionPhotoAddView.as_view(), name="session_photo_add"),
    path("session-photos/<int:pk>/delete/", views.SessionPhotoDeleteView.as_view(), name="session_photo_delete"),
]
