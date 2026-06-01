from django import forms
from .models import Event, CallRecord
from apps.catalog.models import Course
from apps.accounts.models import User


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
            self.fields["assigned_callers"].queryset = User.objects.filter(
                company=company, is_active=True, role=User.CALLER
            )
        self.fields["course"].required = False


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
