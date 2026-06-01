from django.contrib.auth import views as auth_views, login
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.db.models import Count
from django.shortcuts import redirect, get_object_or_404
from django.urls import reverse_lazy
from django.views.generic import (
    TemplateView, ListView, CreateView, UpdateView, DeleteView
)

from apps.core.mixins import SystemAdminRequiredMixin, CompanyAdminRequiredMixin
from .forms import (
    LoginForm, CompanyForm, UserCreateForm, UserUpdateForm,
    CompanyUserCreateForm, SwitchCompanyForm,
)
from .models import Company, User


class LoginView(auth_views.LoginView):
    template_name = "registration/login.html"
    authentication_form = LoginForm
    redirect_authenticated_user = True


class LogoutView(auth_views.LogoutView):
    pass


class DashboardView(LoginRequiredMixin, TemplateView):
    template_name = "accounts/dashboard.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        company = self.request.company
        if company:
            from apps.people.models import CompanyPerson
            from apps.catalog.models import Course, CourseSession
            from apps.calling.models import Event
            ctx["people_count"] = CompanyPerson.objects.filter(company=company, is_active=True).count()
            ctx["courses_count"] = Course.objects.filter(company=company, is_active=True).count()
            ctx["sessions_count"] = CourseSession.objects.filter(company=company).count()
            ctx["active_events"] = Event.objects.filter(company=company, is_active=True).select_related("course")[:5]
        return ctx


# --- Компании (только для системного администратора) ---

class CompanyListView(SystemAdminRequiredMixin, ListView):
    model = Company
    template_name = "accounts/company_list.html"
    context_object_name = "companies"

    def get_queryset(self):
        return Company.objects.annotate(users_count=Count("users")).order_by("name")


class CompanyCreateView(SystemAdminRequiredMixin, CreateView):
    model = Company
    form_class = CompanyForm
    template_name = "accounts/company_form.html"
    success_url = reverse_lazy("accounts:company_list")

    def form_valid(self, form):
        messages.success(self.request, "Компания создана.")
        return super().form_valid(form)


class CompanyUpdateView(SystemAdminRequiredMixin, UpdateView):
    model = Company
    form_class = CompanyForm
    template_name = "accounts/company_form.html"
    success_url = reverse_lazy("accounts:company_list")

    def form_valid(self, form):
        messages.success(self.request, "Компания обновлена.")
        return super().form_valid(form)


# --- Пользователи ---

class UserListView(CompanyAdminRequiredMixin, ListView):
    model = User
    template_name = "accounts/user_list.html"
    context_object_name = "users"

    def get_queryset(self):
        qs = User.objects.select_related("company", "person").order_by("last_name", "first_name")
        if not self.request.user.is_system_admin:
            qs = qs.filter(company=self.request.company)
        return qs


class UserCreateView(CompanyAdminRequiredMixin, CreateView):
    model = User
    template_name = "accounts/user_form.html"
    success_url = reverse_lazy("accounts:user_list")

    def get_form_class(self):
        if self.request.user.is_system_admin:
            return UserCreateForm
        return CompanyUserCreateForm

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        if not self.request.user.is_system_admin:
            kwargs["company"] = self.request.company
        return kwargs

    def form_valid(self, form):
        user = form.save(commit=False)
        if not self.request.user.is_system_admin:
            user.company = self.request.company
            user.role = User.CALLER
        user.save()
        messages.success(self.request, "Пользователь создан.")
        return redirect(self.success_url)


class UserUpdateView(CompanyAdminRequiredMixin, UpdateView):
    model = User
    template_name = "accounts/user_form.html"
    success_url = reverse_lazy("accounts:user_list")

    def get_form_class(self):
        return UserUpdateForm

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        if not self.request.user.is_system_admin:
            kwargs["company"] = self.request.company
        return kwargs

    def get_object(self):
        obj = get_object_or_404(User, pk=self.kwargs["pk"])
        if not self.request.user.is_system_admin:
            if obj.company != self.request.company:
                raise PermissionDenied
        return obj

    def form_valid(self, form):
        messages.success(self.request, "Пользователь обновлён.")
        return super().form_valid(form)


class UserToggleActiveView(CompanyAdminRequiredMixin, TemplateView):
    """Блокировка/разблокировка пользователя."""
    template_name = "accounts/user_list.html"

    def post(self, request, pk):
        user = get_object_or_404(User, pk=pk)
        if not request.user.is_system_admin:
            if user.company != request.company:
                raise PermissionDenied
        if user == request.user:
            messages.error(request, "Нельзя заблокировать себя.")
        else:
            user.is_active = not user.is_active
            user.save(update_fields=["is_active"])
            status = "активирован" if user.is_active else "заблокирован"
            messages.success(request, f"Пользователь {user} {status}.")
        return redirect("accounts:user_list")


# --- Переключение компании для системного администратора ---

class SwitchCompanyView(LoginRequiredMixin, TemplateView):
    template_name = "accounts/switch_company.html"

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_system_admin:
            raise PermissionDenied
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["form"] = SwitchCompanyForm(
            initial={"company": self.request.session.get("active_company_id")}
        )
        ctx["current_company"] = self.request.company
        return ctx

    def post(self, request, *args, **kwargs):
        form = SwitchCompanyForm(request.POST)
        if form.is_valid():
            company = form.cleaned_data["company"]
            if company:
                request.session["active_company_id"] = company.pk
                messages.success(request, f"Активная компания: {company.name}")
            else:
                request.session.pop("active_company_id", None)
                messages.success(request, "Просмотр всех компаний.")
        return redirect("accounts:dashboard")
