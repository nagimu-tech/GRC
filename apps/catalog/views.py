from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.views.generic import ListView, CreateView, UpdateView, DeleteView, DetailView

from apps.core.mixins import (
    TenantScopedMixin, TenantObjectMixin,
    SystemAdminRequiredMixin, CompanyAdminRequiredMixin,
)
from .forms import PositionForm, CourseForm, CourseSessionForm
from .models import Position, Course, CourseSession


# --- Должности (глобальный справочник, управляет сисадмин) ---

class PositionListView(CompanyAdminRequiredMixin, ListView):
    model = Position
    template_name = "catalog/position_list.html"
    context_object_name = "positions"


class PositionCreateView(SystemAdminRequiredMixin, CreateView):
    model = Position
    form_class = PositionForm
    template_name = "catalog/position_form.html"
    success_url = reverse_lazy("catalog:position_list")

    def form_valid(self, form):
        messages.success(self.request, "Должность создана.")
        return super().form_valid(form)


class PositionUpdateView(SystemAdminRequiredMixin, UpdateView):
    model = Position
    form_class = PositionForm
    template_name = "catalog/position_form.html"
    success_url = reverse_lazy("catalog:position_list")

    def form_valid(self, form):
        messages.success(self.request, "Должность обновлена.")
        return super().form_valid(form)


class PositionDeleteView(SystemAdminRequiredMixin, DeleteView):
    model = Position
    template_name = "catalog/position_confirm_delete.html"
    success_url = reverse_lazy("catalog:position_list")

    def form_valid(self, form):
        messages.success(self.request, "Должность удалена.")
        return super().form_valid(form)


# --- Курсы ---

class CourseListView(TenantScopedMixin, CompanyAdminRequiredMixin, ListView):
    model = Course
    template_name = "catalog/course_list.html"
    context_object_name = "courses"


class CourseDetailView(TenantScopedMixin, TenantObjectMixin, CompanyAdminRequiredMixin, DetailView):
    model = Course
    template_name = "catalog/course_detail.html"
    context_object_name = "course"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["sessions"] = self.object.sessions.select_related("course").order_by("-start_date")
        return ctx


class CourseCreateView(TenantScopedMixin, CompanyAdminRequiredMixin, CreateView):
    model = Course
    form_class = CourseForm
    template_name = "catalog/course_form.html"

    def get_success_url(self):
        return reverse_lazy("catalog:course_detail", kwargs={"pk": self.object.pk})

    def form_valid(self, form):
        messages.success(self.request, "Курс создан.")
        return super().form_valid(form)


class CourseUpdateView(TenantScopedMixin, TenantObjectMixin, CompanyAdminRequiredMixin, UpdateView):
    model = Course
    form_class = CourseForm
    template_name = "catalog/course_form.html"

    def get_success_url(self):
        return reverse_lazy("catalog:course_detail", kwargs={"pk": self.object.pk})

    def form_valid(self, form):
        messages.success(self.request, "Курс обновлён.")
        return super().form_valid(form)


# --- Запуски курсов ---

class SessionDetailView(TenantScopedMixin, TenantObjectMixin, CompanyAdminRequiredMixin, DetailView):
    model = CourseSession
    template_name = "catalog/session_detail.html"
    context_object_name = "session"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        from apps.participation.models import Participation
        participations = (
            Participation.objects
            .filter(session=self.object)
            .select_related("company_person__person", "chosen_position")
            .order_by("role", "company_person__person__last_name")
        )
        ctx["participations"] = participations
        return ctx


class SessionCreateView(TenantScopedMixin, CompanyAdminRequiredMixin, CreateView):
    model = CourseSession
    form_class = CourseSessionForm
    template_name = "catalog/session_form.html"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["company"] = self.request.company
        return kwargs

    def form_valid(self, form):
        form.instance.company = self.request.company
        messages.success(self.request, "Запуск создан.")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy("catalog:session_detail", kwargs={"pk": self.object.pk})


class SessionUpdateView(TenantScopedMixin, TenantObjectMixin, CompanyAdminRequiredMixin, UpdateView):
    model = CourseSession
    form_class = CourseSessionForm
    template_name = "catalog/session_form.html"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["company"] = self.request.company
        return kwargs

    def get_success_url(self):
        return reverse_lazy("catalog:session_detail", kwargs={"pk": self.object.pk})

    def form_valid(self, form):
        messages.success(self.request, "Запуск обновлён.")
        return super().form_valid(form)


class SessionDeleteView(TenantScopedMixin, TenantObjectMixin, CompanyAdminRequiredMixin, DeleteView):
    model = CourseSession
    template_name = "catalog/session_confirm_delete.html"

    def get_success_url(self):
        return reverse_lazy("catalog:course_detail", kwargs={"pk": self.object.course_id})

    def form_valid(self, form):
        messages.success(self.request, "Запуск удалён.")
        return super().form_valid(form)
