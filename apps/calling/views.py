from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.db.models import F, Max, Q
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.views.generic import ListView, CreateView, UpdateView, DeleteView, DetailView, View

from apps.core.mixins import (
    TenantScopedMixin, TenantObjectMixin,
    CompanyAdminRequiredMixin,
)
from .forms import EventForm, CallRecordPersonForm, CallRecordUpdateForm
from .models import Event, CallRecord


def can_manage_call_pool(user):
    return user.is_system_admin or user.is_company_admin


def get_event_for_pool_action(request, pk):
    event = get_object_or_404(Event, pk=pk)
    if not can_manage_call_pool(request.user):
        raise PermissionDenied
    if not request.user.is_system_admin and event.company_id != request.company.pk:
        raise Http404
    return event


class EventListView(TenantScopedMixin, LoginRequiredMixin, ListView):
    model = Event
    template_name = "calling/event_list.html"
    context_object_name = "events"

    def get_queryset(self):
        qs = super().get_queryset().select_related("course", "company")
        user = self.request.user
        if not user.is_system_admin and not user.is_company_admin:
            # Прозвонщик видит только назначенные ему встречи
            if not user.person_id:
                return qs.none()
            qs = qs.filter(assigned_callers__person=user.person).distinct()
        return qs


class EventCreateView(TenantScopedMixin, CompanyAdminRequiredMixin, CreateView):
    model = Event
    form_class = EventForm
    template_name = "calling/event_form.html"
    success_url = reverse_lazy("calling:event_list")

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["company"] = self.request.company
        return kwargs

    def form_valid(self, form):
        form.instance.company = self.request.company
        messages.success(self.request, "Встреча создана.")
        return super().form_valid(form)


class EventUpdateView(TenantScopedMixin, TenantObjectMixin, CompanyAdminRequiredMixin, UpdateView):
    model = Event
    form_class = EventForm
    template_name = "calling/event_form.html"
    success_url = reverse_lazy("calling:event_list")

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["company"] = self.request.company
        return kwargs

    def form_valid(self, form):
        messages.success(self.request, "Встреча обновлена.")
        return super().form_valid(form)


class EventDeleteView(TenantScopedMixin, TenantObjectMixin, CompanyAdminRequiredMixin, DeleteView):
    model = Event
    template_name = "calling/event_confirm_delete.html"
    success_url = reverse_lazy("calling:event_list")

    def form_valid(self, form):
        messages.success(self.request, "Встреча удалена.")
        return super().form_valid(form)


class CallingSessionView(LoginRequiredMixin, DetailView):
    """
    Главный экран прозвона (mobile-first).
    Доступен назначенным прозвонщикам и администратору компании.
    """
    model = Event
    template_name = "calling/calling_session.html"
    context_object_name = "event"

    def get_object(self):
        event = get_object_or_404(Event, pk=self.kwargs["pk"])
        user = self.request.user
        if not event.company == self.request.company and not user.is_system_admin:
            raise Http404
        if not (
            user.is_system_admin
            or user.is_company_admin
            or event.is_assigned_to_user(user)
        ):
            raise PermissionDenied
        return event

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        event = self.object
        user = self.request.user

        course_filter = self.request.GET.get("course")
        show_mine = self.request.GET.get("mine") == "1"
        search = self.request.GET.get("q", "").strip()

        from apps.catalog.models import Course
        available_courses = Course.objects.filter(
            company=event.company, is_active=True
        )

        records = (
            CallRecord.objects
            .filter(event=event)
            .select_related(
                "company_person__person",
                "called_by",
                "claimed_by",
            )
            .prefetch_related(
                "company_person__participations__session__course",
            )
        )

        if show_mine:
            records = records.filter(claimed_by=user)
        else:
            # Доступный пул + мои захваченные
            records = records.filter(
                Q(claimed_by__isnull=True, status=CallRecord.NOT_CALLED)
                | Q(claimed_by=user)
            )

        if course_filter:
            records = records.filter(
                company_person__participations__session__course_id=course_filter,
                company_person__participations__role="STUDENT",
            ).distinct()

        if search:
            records = records.filter(
                Q(company_person__person__last_name__icontains=search)
                | Q(company_person__person__first_name__icontains=search)
            )

        from apps.participation.models import Participation
        records = records.annotate(
            latest_course_end=Max(
                "company_person__participations__session__end_date",
                filter=Q(
                    company_person__participations__session__course=event.course,
                    company_person__participations__role=Participation.STUDENT,
                ),
            )
        )

        ctx["records"] = records.order_by(
            F("latest_course_end").desc(nulls_last=True),
            "status",
            "company_person__person__last_name",
        )
        ctx["available_courses"] = available_courses
        ctx["selected_course"] = course_filter
        ctx["show_mine"] = show_mine
        ctx["search_query"] = search
        ctx["statuses"] = CallRecord.STATUS_CHOICES
        ctx["update_form"] = CallRecordUpdateForm()
        ctx["can_manage_call_pool"] = can_manage_call_pool(user)
        ctx["add_record_form"] = CallRecordPersonForm(company=event.company, event=event)
        return ctx


class ClaimCallRecordView(LoginRequiredMixin, View):
    """HTMX POST — атомарный захват записи прозвона."""

    def post(self, request, pk):
        if request.user.is_system_admin:
            record = get_object_or_404(CallRecord, pk=pk)
        else:
            record = get_object_or_404(
                CallRecord,
                pk=pk,
                event__company=request.company,
            )
        event = record.event
        user = request.user

        if not (
            user.is_system_admin
            or user.is_company_admin
            or event.is_assigned_to_user(user)
        ):
            raise PermissionDenied

        claimed = CallRecord.claim(event, record.company_person, user)
        if claimed is None:
            record.refresh_from_db()

        return render(request, "calling/_call_record_row.html", {
            "record": record if claimed is None else claimed,
            "update_form": CallRecordUpdateForm(instance=record),
            "can_manage_call_pool": can_manage_call_pool(user),
        })


class UpdateCallRecordView(LoginRequiredMixin, View):
    """HTMX POST — обновление статуса и комментария."""

    def post(self, request, pk):
        if request.user.is_system_admin:
            record = get_object_or_404(CallRecord, pk=pk)
        else:
            record = get_object_or_404(
                CallRecord,
                pk=pk,
                event__company=request.company,
            )
        event = record.event
        user = request.user

        # Только тот, кто захватил, или администратор
        if not (
            user.is_system_admin
            or user.is_company_admin
            or record.claimed_by == user
        ):
            raise PermissionDenied

        form = CallRecordUpdateForm(request.POST, instance=record)
        if form.is_valid():
            updated = form.save(commit=False)
            updated.called_by = user
            updated.save(update_fields=["status", "comment", "called_by", "updated_at"])

        record.refresh_from_db()
        return render(request, "calling/_call_record_row.html", {
            "record": record,
            "update_form": CallRecordUpdateForm(instance=record),
            "can_manage_call_pool": can_manage_call_pool(user),
        })


class InitCallRecordsView(CompanyAdminRequiredMixin, View):
    """Заполнение пула прозвона выпускниками выбранного курса."""

    def post(self, request, pk):
        event = get_event_for_pool_action(request, pk)
        if not event.course_id:
            messages.error(request, "Сначала выберите курс для прозвона.")
            return redirect("calling:session", pk=pk)
        added = CallRecord.fill_from_course(event)
        messages.success(request, f"Пул прозвона заполнен. Добавлено записей: {added}.")
        return redirect("calling:session", pk=pk)


class AddCallRecordView(LoginRequiredMixin, View):
    """Ручное добавление человека в пул прозвона."""

    def post(self, request, pk):
        event = get_event_for_pool_action(request, pk)
        form = CallRecordPersonForm(request.POST, company=event.company, event=event)
        if form.is_valid():
            cp = form.cleaned_data["company_person"]
            CallRecord.objects.get_or_create(
                event=event,
                company_person=cp,
                defaults={
                    "company": event.company,
                    "status": CallRecord.NOT_CALLED,
                },
            )
            messages.success(request, f"{cp.full_name} добавлен в прозвон.")
        else:
            messages.error(request, "Не удалось добавить человека в прозвон.")
        return redirect("calling:session", pk=pk)


class DeleteCallRecordView(LoginRequiredMixin, View):
    """Ручное удаление человека из пула прозвона."""

    def post(self, request, pk):
        record = get_object_or_404(CallRecord.objects.select_related("event"), pk=pk)
        event = record.event
        if not can_manage_call_pool(request.user):
            raise PermissionDenied
        if not request.user.is_system_admin and event.company_id != request.company.pk:
            raise Http404
        person_name = record.company_person.full_name
        record.delete()
        messages.success(request, f"{person_name} удалён из прозвона.")
        return redirect("calling:session", pk=event.pk)
