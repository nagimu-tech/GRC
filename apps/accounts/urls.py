from django.urls import path
from . import views

app_name = "accounts"

urlpatterns = [
    path("", views.DashboardView.as_view(), name="dashboard"),
    path("login/", views.LoginView.as_view(), name="login"),
    path("logout/", views.LogoutView.as_view(), name="logout"),

    # Компании
    path("companies/", views.CompanyListView.as_view(), name="company_list"),
    path("companies/new/", views.CompanyCreateView.as_view(), name="company_create"),
    path("companies/<int:pk>/edit/", views.CompanyUpdateView.as_view(), name="company_update"),

    # Пользователи
    path("users/", views.UserListView.as_view(), name="user_list"),
    path("users/new/", views.UserCreateView.as_view(), name="user_create"),
    path("users/<int:pk>/edit/", views.UserUpdateView.as_view(), name="user_update"),
    path("users/<int:pk>/toggle/", views.UserToggleActiveView.as_view(), name="user_toggle"),

    # Переключение компании (только для сисадмина)
    path("switch-company/", views.SwitchCompanyView.as_view(), name="switch_company"),
]
