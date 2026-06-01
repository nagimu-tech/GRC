from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.db.models import Q
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.views.generic import ListView, CreateView, UpdateView, DeleteView, DetailView, FormView, View

from apps.core.mixins import (
    TenantScopedMixin, TenantObjectMixin,
    SystemAdminRequiredMixin, CompanyAdminRequiredMixin,
)
from .forms import (
    PersonForm, CompanyPersonCreateForm,
    CompanyPersonEditForm, CompanyPersonPhotoForm, PersonMergeForm,
)
from .models import Person, CompanyPerson, CompanyPersonPhoto


class CompanyPersonListView(TenantScopedMixin, CompanyAdminRequiredMixin, ListView):
    model = CompanyPerson
    template_name = "people/companyperson_list.html"
    context_object_name = "people"
    paginate_by = 30

    def get_queryset(self):
        qs = super().get_queryset().select_related("person", "company")
        search = self.request.GET.get("q", "").strip()
        if search:
            qs = qs.filter(
                Q(person__last_name__icontains=search)
                | Q(person__first_name__icontains=search)
                | Q(person__middle_name__icontains=search)
                | Q(person__phone__icontains=search)
                | Q(person__email__icontains=search)
            )
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["search_query"] = self.request.GET.get("q", "")
        return ctx


class CompanyPersonDetailView(TenantScopedMixin, TenantObjectMixin, CompanyAdminRequiredMixin, DetailView):
    model = CompanyPerson
    template_name = "people/companyperson_detail.html"
    context_object_name = "cp"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        from apps.participation.models import Participation
        participations = (
            Participation.objects
            .filter(company_person=self.object)
            .select_related("session__course", "chosen_position")
            .order_by("-session__start_date")
        )
        ctx["participations"] = participations
        ctx["photos"] = self.object.photos.all()
        ctx["photo_form"] = CompanyPersonPhotoForm()
        ctx["photo_limit"] = 5
        return ctx


class CompanyPersonCreateView(CompanyAdminRequiredMixin, CreateView):
    """Создание человека в компании через единую форму (Person + CompanyPerson)."""
    template_name = "people/companyperson_form.html"
    form_class = CompanyPersonCreateForm

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        if not request.company:
            raise PermissionDenied
        return super().dispatch(request, *args, **kwargs)

    def get_form(self, form_class=None):
        return CompanyPersonCreateForm(**self.get_form_kwargs())

    def get_form_kwargs(self):
        kwargs = {"initial": self.get_initial()}
        if self.request.method in ("POST", "PUT"):
            kwargs["data"] = self.request.POST
        return kwargs

    def form_valid(self, form):
        warnings = form.get_duplicate_warnings(self.request.company)
        for warning in warnings:
            messages.warning(self.request, warning)
        cp = form.save(self.request.company)
        messages.success(self.request, "Человек добавлен в компанию.")
        return redirect("people:companyperson_detail", pk=cp.pk)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["title"] = "Добавить человека"
        return ctx


class CompanyPersonUpdateView(TenantObjectMixin, CompanyAdminRequiredMixin, UpdateView):
    model = CompanyPerson
    form_class = CompanyPersonEditForm
    template_name = "people/companyperson_form.html"

    def get_queryset(self):
        if self.request.user.is_system_admin:
            return CompanyPerson.objects.all()
        return CompanyPerson.objects.filter(company=self.request.company)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        kwargs["current_company"] = self.request.company
        return kwargs

    def form_valid(self, form):
        messages.success(self.request, "Карточка обновлена.")
        return super().form_valid(form)

    def get_success_url(self):
        if self.object.company_id is None and not self.request.user.is_system_admin:
            return reverse_lazy("people:companyperson_list")
        return reverse_lazy("people:companyperson_detail", kwargs={"pk": self.object.pk})

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["title"] = "Редактировать карточку"
        ctx["can_edit_person"] = self.request.user.is_system_admin
        return ctx


class CompanyPersonDeleteView(TenantObjectMixin, CompanyAdminRequiredMixin, DeleteView):
    model = CompanyPerson
    template_name = "people/companyperson_confirm_delete.html"
    success_url = reverse_lazy("people:companyperson_list")

    def get_queryset(self):
        if self.request.user.is_system_admin:
            return CompanyPerson.objects.all()
        return CompanyPerson.objects.filter(company=self.request.company)

    def form_valid(self, form):
        messages.success(self.request, "Человек удалён из компании.")
        return super().form_valid(form)


# --- Системный администратор: глобальные Person и сопоставление ---

class GlobalPersonListView(SystemAdminRequiredMixin, ListView):
    model = Person
    template_name = "people/person_list.html"
    context_object_name = "persons"
    paginate_by = 30

    def get_queryset(self):
        qs = Person.objects.prefetch_related("company_persons__company")
        search = self.request.GET.get("q", "").strip()
        if search:
            qs = qs.filter(
                Q(last_name__icontains=search)
                | Q(first_name__icontains=search)
                | Q(phone__icontains=search)
            )
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["search_query"] = self.request.GET.get("q", "")
        return ctx


class PersonUpdateView(SystemAdminRequiredMixin, UpdateView):
    model = Person
    form_class = PersonForm
    template_name = "people/person_form.html"
    success_url = reverse_lazy("people:person_list")

    def form_valid(self, form):
        messages.success(self.request, "Данные человека обновлены.")
        return super().form_valid(form)


class MergeCandidatesView(SystemAdminRequiredMixin, ListView):
    """
    Список кандидатов на межкомпанийное сопоставление.
    Находит Person, которые привязаны к нескольким CompanyPerson в разных компаниях,
    а также потенциальные дубли по ФИО/телефону.
    """
    template_name = "people/merge_candidates.html"
    context_object_name = "candidates"

    def get_queryset(self):
        from django.db.models import Count
        return (
            Person.objects
            .annotate(companies_count=Count("company_persons__company", distinct=True))
            .filter(companies_count__gte=2)
            .prefetch_related("company_persons__company")
        )


class CompanyPersonMergeView(SystemAdminRequiredMixin, FormView):
    """Перепривязка CompanyPerson к существующему Person."""
    form_class = PersonMergeForm
    template_name = "people/companyperson_merge.html"

    def get_object(self):
        return get_object_or_404(CompanyPerson, pk=self.kwargs["pk"])

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["cp"] = self.get_object()
        return ctx

    def form_valid(self, form):
        cp = self.get_object()
        target_person = form.cleaned_data["target_person"]
        old_person = cp.person

        if CompanyPerson.objects.filter(company=cp.company, person=target_person).exists():
            messages.error(
                self.request,
                "В этой компании уже есть карточка для выбранного человека."
            )
            return self.form_invalid(form)

        cp.person = target_person
        cp.save(update_fields=["person"])
        messages.success(
            self.request,
            f"Карточка перепривязана с «{old_person}» на «{target_person}»."
        )
        return redirect("people:merge_candidates")


class CompanyPersonPhotoAddView(TenantObjectMixin, CompanyAdminRequiredMixin, View):
    limit = 5

    def get_queryset(self):
        if self.request.user.is_system_admin:
            return CompanyPerson.objects.all()
        return CompanyPerson.objects.filter(company=self.request.company)

    def get_object(self):
        return get_object_or_404(self.get_queryset(), pk=self.kwargs["pk"])

    def post(self, request, pk):
        company_person = self.get_object()
        if company_person.photos.count() >= self.limit:
            messages.error(request, f"Для человека можно добавить не больше {self.limit} фото.")
            return redirect("people:companyperson_detail", pk=company_person.pk)

        form = CompanyPersonPhotoForm(request.POST)
        if form.is_valid():
            photo = form.save(commit=False)
            photo.company_person = company_person
            photo.save()
            messages.success(request, "Фото добавлено.")
        else:
            messages.error(request, "Не удалось добавить фото. Проверьте ссылку.")
        return redirect("people:companyperson_detail", pk=company_person.pk)


class CompanyPersonPhotoDeleteView(CompanyAdminRequiredMixin, View):
    def post(self, request, pk):
        photo = get_object_or_404(
            CompanyPersonPhoto.objects.select_related("company_person"),
            pk=pk,
        )
        company_person = photo.company_person
        if not request.user.is_system_admin and company_person.company_id != request.company.pk:
            raise Http404
        photo.delete()
        messages.success(request, "Фото удалено.")
        return redirect("people:companyperson_detail", pk=company_person.pk)
