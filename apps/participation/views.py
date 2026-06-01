from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.views.generic import CreateView, UpdateView, DeleteView

from apps.core.mixins import TenantScopedMixin, TenantObjectMixin, CompanyAdminRequiredMixin
from .forms import ParticipationForm
from .models import Participation


class ParticipationCreateView(TenantScopedMixin, CompanyAdminRequiredMixin, CreateView):
    model = Participation
    form_class = ParticipationForm
    template_name = "participation/participation_form.html"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["company"] = self.request.company
        kwargs["initial_person"] = self.request.GET.get("person")
        kwargs["initial_session"] = self.request.GET.get("session")
        kwargs["initial_role"] = self.request.GET.get("role")
        return kwargs

    def form_valid(self, form):
        form.instance.company = self.request.company
        messages.success(self.request, "Участие добавлено.")
        return super().form_valid(form)

    def get_success_url(self):
        if self.request.GET.get("session"):
            return reverse_lazy("catalog:session_detail", kwargs={"pk": self.object.session_id})
        return reverse_lazy("people:companyperson_detail", kwargs={"pk": self.object.company_person_id})


class ParticipationUpdateView(TenantObjectMixin, CompanyAdminRequiredMixin, UpdateView):
    model = Participation
    form_class = ParticipationForm
    template_name = "participation/participation_form.html"

    def get_queryset(self):
        if self.request.user.is_system_admin:
            return Participation.objects.all()
        return Participation.objects.filter(company=self.request.company)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["company"] = self.request.company
        return kwargs

    def form_valid(self, form):
        messages.success(self.request, "Участие обновлено.")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy("people:companyperson_detail", kwargs={"pk": self.object.company_person_id})


class ParticipationDeleteView(TenantObjectMixin, CompanyAdminRequiredMixin, DeleteView):
    model = Participation
    template_name = "participation/participation_confirm_delete.html"

    def get_queryset(self):
        if self.request.user.is_system_admin:
            return Participation.objects.all()
        return Participation.objects.filter(company=self.request.company)

    def form_valid(self, form):
        cp_id = self.object.company_person_id
        messages.success(self.request, "Участие удалено.")
        super().form_valid(form)
        return redirect("people:companyperson_detail", pk=cp_id)
