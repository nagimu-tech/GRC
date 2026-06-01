from django import forms
from django.contrib.auth.forms import AuthenticationForm
from .models import Company, User


class LoginForm(AuthenticationForm):
    username = forms.CharField(
        label="Логин",
        widget=forms.TextInput(attrs={"class": "form-input", "autofocus": True}),
    )
    password = forms.CharField(
        label="Пароль",
        widget=forms.PasswordInput(attrs={"class": "form-input"}),
    )


class CompanyForm(forms.ModelForm):
    class Meta:
        model = Company
        fields = ["name", "is_active", "phone", "email", "notes"]
        labels = {
            "name": "Название",
            "is_active": "Активна",
            "phone": "Телефон",
            "email": "Email",
            "notes": "Заметки",
        }
        widgets = {
            "notes": forms.Textarea(attrs={"rows": 3}),
        }


class UserCreateForm(forms.ModelForm):
    password = forms.CharField(
        label="Пароль",
        widget=forms.PasswordInput(),
        min_length=8,
    )

    class Meta:
        model = User
        fields = ["username", "first_name", "last_name", "email", "person", "role", "company"]
        labels = {
            "username": "Логин",
            "first_name": "Имя",
            "last_name": "Фамилия",
            "email": "Email",
            "person": "Связанный человек",
            "role": "Роль",
            "company": "Компания",
        }

    def __init__(self, *args, company=None, **kwargs):
        super().__init__(*args, **kwargs)
        from apps.people.models import Person

        persons = Person.objects.select_related("user_account").order_by("last_name", "first_name")
        if company:
            persons = persons.filter(company_persons__company=company).distinct()
        self.fields["person"].queryset = persons
        self.fields["person"].required = False

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password"])
        if commit:
            user.save()
        return user


class UserUpdateForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ["username", "first_name", "last_name", "email", "person", "role", "is_active"]
        labels = {
            "username": "Логин",
            "first_name": "Имя",
            "last_name": "Фамилия",
            "email": "Email",
            "person": "Связанный человек",
            "role": "Роль",
            "is_active": "Активен",
        }

    def __init__(self, *args, company=None, **kwargs):
        super().__init__(*args, **kwargs)
        from apps.people.models import Person

        persons = Person.objects.order_by("last_name", "first_name")
        if company:
            persons = persons.filter(company_persons__company=company).distinct()
        self.fields["person"].queryset = persons
        self.fields["person"].required = False


class CompanyUserCreateForm(forms.ModelForm):
    """Форма создания прозвонщика администратором компании."""
    password = forms.CharField(
        label="Пароль",
        widget=forms.PasswordInput(),
        min_length=8,
    )

    class Meta:
        model = User
        fields = ["username", "first_name", "last_name", "email", "person"]
        labels = {
            "username": "Логин",
            "first_name": "Имя",
            "last_name": "Фамилия",
            "email": "Email",
            "person": "Связанный человек",
        }

    def __init__(self, *args, company=None, **kwargs):
        super().__init__(*args, **kwargs)
        from apps.people.models import Person

        self.fields["person"].queryset = (
            Person.objects
            .filter(company_persons__company=company)
            .distinct()
            .order_by("last_name", "first_name")
            if company
            else Person.objects.none()
        )
        self.fields["person"].required = False

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password"])
        user.role = User.CALLER
        if commit:
            user.save()
        return user


class SwitchCompanyForm(forms.Form):
    """Форма переключения активной компании для системного администратора."""
    from apps.accounts.models import Company  # noqa: F401 — local import to avoid circular

    company = forms.ModelChoiceField(
        queryset=Company.objects.filter(is_active=True),
        label="Активная компания",
        empty_label="— Все компании —",
        required=False,
    )
