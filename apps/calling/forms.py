from django import forms
from .models import Event, CallRecord
from apps.catalog.models import Course
from apps.people.models import CompanyPerson


class EventForm(forms.ModelForm):
    class Meta:
        model = Event
        fields = ["title", "course", "date", "location", "is_active", "notes", "assigned_callers"]
        labels = {
            "title": "Название встречи",
            "course": "Курс",
            "date": "Дата",
            "location": "Место проведения",
            "is_active": "Активна (прозвон идёт)",
            "notes": "Заметки",
            "assigned_callers": "Назначенные прозвонщики",
        }
        widgets = {
            "date": forms.DateInput(attrs={"type": "date"}),
            "notes": forms.Textarea(attrs={"rows": 3}),
            "assigned_callers": forms.CheckboxSelectMultiple(),
        }

    def __init__(self, *args, company=None, **kwargs):
        super().__init__(*args, **kwargs)
        if company:
            self.fields["course"].queryset = Course.objects.filter(
                company=company, is_active=True
            )
            selected_course_id = self.data.get("course") or getattr(self.instance, "course_id", None)
            callers = CompanyPerson.objects.filter(
                company=company,
                is_active=True,
                participations__role="ASSISTANT",
            )
            if selected_course_id:
                callers = callers.filter(participations__session__course_id=selected_course_id)
            if self.instance and self.instance.pk:
                callers = callers | self.instance.assigned_callers.all()
            self.fields["assigned_callers"].queryset = (
                callers.select_related("person").distinct().order_by("person__last_name", "person__first_name")
            )
        self.fields["course"].required = False


class CallRecordPersonForm(forms.Form):
    company_person = forms.ModelChoiceField(
        label="Добавить человека",
        queryset=CompanyPerson.objects.none(),
    )

    def __init__(self, *args, company=None, event=None, **kwargs):
        super().__init__(*args, **kwargs)
        queryset = CompanyPerson.objects.none()
        if company and event:
            existing_ids = event.call_records.values_list("company_person_id", flat=True)
            queryset = (
                CompanyPerson.objects
                .filter(company=company, is_active=True)
                .exclude(pk__in=existing_ids)
                .select_related("person")
                .order_by("person__last_name", "person__first_name")
            )
        self.fields["company_person"].queryset = queryset


class CallRecordUpdateForm(forms.ModelForm):
    """Форма обновления статуса и комментария (для HTMX-обновлений в прозвоне)."""
    class Meta:
        model = CallRecord
        fields = ["status", "comment"]
        labels = {
            "status": "Статус",
            "comment": "Комментарий",
        }
        widgets = {
            "comment": forms.Textarea(attrs={"rows": 2, "placeholder": "Комментарий..."}),
        }
