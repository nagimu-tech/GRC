from django import forms
from .models import Participation
from apps.catalog.models import Position, CourseSession
from apps.people.models import CompanyPerson


class ParticipationForm(forms.ModelForm):
    class Meta:
        model = Participation
        fields = ["company_person", "session", "role", "chosen_position", "notes"]
        labels = {
            "company_person": "Человек",
            "session": "Запуск курса",
            "role": "Роль",
            "chosen_position": "Должность",
            "notes": "Заметки",
        }
        widgets = {
            "notes": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, company=None, initial_person=None, initial_session=None, **kwargs):
        super().__init__(*args, **kwargs)
        if company:
            self.fields["company_person"].queryset = CompanyPerson.objects.filter(
                company=company, is_active=True
            ).select_related("person").order_by("person__last_name")
            self.fields["session"].queryset = CourseSession.objects.filter(
                company=company
            ).select_related("course").order_by("-start_date")
        self.fields["chosen_position"].queryset = Position.objects.filter(is_active=True)
        self.fields["chosen_position"].required = False

        if initial_person:
            self.fields["company_person"].initial = initial_person
        if initial_session:
            self.fields["session"].initial = initial_session
