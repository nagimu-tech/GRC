from django.urls import path
from . import views

app_name = "people"

urlpatterns = [
    # Люди в компании
    path("", views.CompanyPersonListView.as_view(), name="companyperson_list"),
    path("new/", views.CompanyPersonCreateView.as_view(), name="companyperson_create"),
    path("<int:pk>/", views.CompanyPersonDetailView.as_view(), name="companyperson_detail"),
    path("<int:pk>/edit/", views.CompanyPersonUpdateView.as_view(), name="companyperson_update"),
    path("<int:pk>/delete/", views.CompanyPersonDeleteView.as_view(), name="companyperson_delete"),
    path("<int:pk>/merge/", views.CompanyPersonMergeView.as_view(), name="companyperson_merge"),
    path("<int:pk>/photos/add/", views.CompanyPersonPhotoAddView.as_view(), name="companyperson_photo_add"),
    path("photos/<int:pk>/delete/", views.CompanyPersonPhotoDeleteView.as_view(), name="companyperson_photo_delete"),

    # Только для системного администратора
    path("global/", views.GlobalPersonListView.as_view(), name="person_list"),
    path("global/<int:pk>/edit/", views.PersonUpdateView.as_view(), name="person_update"),
    path("merge-candidates/", views.MergeCandidatesView.as_view(), name="merge_candidates"),
]
