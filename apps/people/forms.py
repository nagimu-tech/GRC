from django import forms
from django.core.exceptions import ValidationError
from django.db.models import Q
from apps.accounts.models import Company
from .models import Person, CompanyPerson


class PersonForm(forms.ModelForm):
    """Форма создания/редактирования глобальной личности (только сисадмин)."""
    class Meta:
        model = Person
        fields = ["last_name", "first_name", "middle_name", "birth_date", "phone", "email"]
        labels = {
            "last_name": "Фамилия",
            "first_name": "Имя",
            "middle_name": "Отчество",
            "birth_date": "Дата рождения",
            "phone": "Телефон",
            "email": "Email",
        }
        widgets = {
            "birth_date": forms.DateInput(attrs={"type": "date"}),
        }


class CompanyPersonCreateForm(forms.Form):
    """
    Форма создания человека в компании.
    Создаёт Person + CompanyPerson.
    Администратор компании не редактирует глобальный Person напрямую.
    """
    last_name = forms.CharField(label="Фамилия", max_length=100)
    first_name = forms.CharField(label="Имя", max_length=100)
    middle_name = forms.CharField(label="Отчество", max_length=100, required=False)
    birth_date = forms.DateField(
        label="Дата рождения",
        required=False,
        widget=forms.DateInput(attrs={"type": "date"}),
    )
    phone = forms.CharField(label="Телефон", max_length=30, required=False)
    email = forms.EmailField(label="Email", required=False)
    notes = forms.CharField(
        label="Заметки",
        required=False,
        widget=forms.Textarea(attrs={"rows": 3}),
    )
    consent_stored = forms.BooleanField(label="Согласие на хранение ПДн", required=False)
    consent_contact = forms.BooleanField(label="Согласие на обзвон", required=False)

    def save(self, company):
        data = self.cleaned_data
        person = Person.objects.create(
            last_name=data["last_name"],
            first_name=data["first_name"],
            middle_name=data.get("middle_name", ""),
            birth_date=data.get("birth_date"),
            phone=data.get("phone", ""),
            email=data.get("email", ""),
        )
        company_person = CompanyPerson.objects.create(
            person=person,
            company=company,
            notes=data.get("notes", ""),
            consent_stored=data.get("consent_stored", False),
            consent_contact=data.get("consent_contact", False),
        )
        return company_person

    def get_duplicate_warnings(self, company):
        """Возвращает список предупреждений о дублях внутри компании."""
        warnings = []
        data = self.cleaned_data
        qs = CompanyPerson.objects.filter(company=company).select_related("person")

        full_name_match = qs.filter(
            person__last_name__iexact=data["last_name"],
            person__first_name__iexact=data["first_name"],
        )
        if full_name_match.exists():
            names = ", ".join(str(cp) for cp in full_name_match[:3])
            warnings.append(f"Найдены люди с таким же именем: {names}")

        phone = data.get("phone", "").strip()
        if phone:
            phone_match = qs.filter(person__phone=phone)
            if phone_match.exists():
                names = ", ".join(str(cp) for cp in phone_match[:3])
                warnings.append(f"Найдены люди с таким же телефоном: {names}")

        return warnings


class CompanyPersonEditForm(forms.ModelForm):
    """
    Форма редактирования карточки человека в компании.
    Администратор компании может менять только notes/consents/is_active.
    ФИО редактируется отдельно и только сисадмином.
    """
    class Meta:
        model = CompanyPerson
        fields = ["company", "notes", "consent_stored", "consent_contact", "is_active"]
        labels = {
            "company": "Компания",
            "notes": "Заметки",
            "consent_stored": "Согласие на хранение ПДн",
            "consent_contact": "Согласие на обзвон",
            "is_active": "Активен",
        }
        widgets = {
            "notes": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, user=None, current_company=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["company"].required = False
        self.fields["company"].empty_label = "— Без компании —"
        if user and user.is_system_admin:
            self.fields["company"].queryset = Company.objects.filter(is_active=True)
        elif current_company:
            self.fields["company"].queryset = Company.objects.filter(pk=current_company.pk)
        else:
            self.fields["company"].queryset = Company.objects.none()

    def clean_company(self):
        company = self.cleaned_data["company"]
        if company and CompanyPerson.objects.filter(
            company=company,
            person=self.instance.person,
        ).exclude(pk=self.instance.pk).exists():
            raise ValidationError("В этой компании уже есть карточка для этого человека.")
        return company


class PersonMergeForm(forms.Form):
    """Форма перепривязки CompanyPerson к существующему Person (только сисадмин)."""
    target_person = forms.ModelChoiceField(
        queryset=Person.objects.all(),
        label="Привязать к существующему человеку",
        help_text="CompanyPerson будет перепривязан к выбранному Person.",
    )
