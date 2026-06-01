from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path("django-admin/", admin.site.urls),
    path("", include("apps.accounts.urls", namespace="accounts")),
    path("catalog/", include("apps.catalog.urls", namespace="catalog")),
    path("people/", include("apps.people.urls", namespace="people")),
    path("participation/", include("apps.participation.urls", namespace="participation")),
    path("calling/", include("apps.calling.urls", namespace="calling")),
]
