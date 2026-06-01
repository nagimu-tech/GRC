from django.urls import path
from . import views

app_name = "calling"

urlpatterns = [
    path("events/", views.EventListView.as_view(), name="event_list"),
    path("events/new/", views.EventCreateView.as_view(), name="event_create"),
    path("events/<int:pk>/edit/", views.EventUpdateView.as_view(), name="event_update"),
    path("events/<int:pk>/delete/", views.EventDeleteView.as_view(), name="event_delete"),
    path("events/<int:pk>/session/", views.CallingSessionView.as_view(), name="session"),
    path("events/<int:pk>/init/", views.InitCallRecordsView.as_view(), name="init_records"),

    # HTMX endpoints
    path("records/<int:pk>/claim/", views.ClaimCallRecordView.as_view(), name="claim_record"),
    path("records/<int:pk>/update/", views.UpdateCallRecordView.as_view(), name="update_record"),
]
