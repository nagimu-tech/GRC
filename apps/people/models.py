from django.db import models
from django.db.models import Q
from django.urls import reverse
from simple_history.models import HistoricalRecords
from apps.core.models import TenantModel


class Person(models.Model):
    """
    Глобальная запись личности — без company.
    Прямой доступ запрещён для администраторов компаний и прозвонщиков.
    Редактирование идентифицирующих полей только системным администратором.
    """
    last_name = models.CharField(max_length=100, verbose_name="Фамилия")
    first_name = models.CharField(max_length=100, verbose_name="Имя")
    middle_name = models.CharField(max_length=100, blank=True, verbose_name="Отчество")
    birth_date = models.DateField(null=True, blank=True, verbose_name="Дата рождения")
    phone = models.CharField(max_length=30, blank=True, verbose_name="Телефон")
    email = models.EmailField(blank=True, verbose_name="Email")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    history = HistoricalRecords()

    class Meta:
        verbose_name = "Человек (глобальный)"
        verbose_name_plural = "Люди (глобальные)"
        ordering = ["last_name", "first_name", "middle_name"]

    @property
    def full_name(self):
        parts = [self.last_name, self.first_name]
        if self.middle_name:
            parts.append(self.middle_name)
        return " ".join(parts)

    def __str__(self):
        return self.full_name


class CompanyPerson(TenantModel):
    """
    Карточка человека в конкретной компании (company-scoped).
    Все рабочие экраны компании работают через CompanyPerson, не через Person напрямую.
    """
    company = models.ForeignKey(
        "accounts.Company",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="Компания",
        db_index=True,
    )
    person = models.ForeignKey(
        Person,
        on_delete=models.PROTECT,
        related_name="company_persons",
        verbose_name="Человек",
    )
    notes = models.TextField(blank=True, verbose_name="Заметки")
    consent_stored = models.BooleanField(default=False, verbose_name="Согласие на хранение ПДн")
    consent_contact = models.BooleanField(default=False, verbose_name="Согласие на обзвон")
    is_active = models.BooleanField(default=True, verbose_name="Активен")
    created_at = models.DateTimeField(auto_now_add=True)

    history = HistoricalRecords()

    class Meta:
        verbose_name = "Человек в компании"
        verbose_name_plural = "Люди в компании"
        constraints = [
            models.UniqueConstraint(
                fields=["company", "person"],
                condition=Q(company__isnull=False),
                name="uniq_company_person_when_company_set",
            )
        ]
        ordering = ["person__last_name", "person__first_name"]

    def __str__(self):
        company_name = self.company.name if self.company else "без компании"
        return f"{self.person.full_name} ({company_name})"

    def get_absolute_url(self):
        return reverse("people:companyperson_detail", kwargs={"pk": self.pk})

    @property
    def full_name(self):
        return self.person.full_name

    @property
    def phone(self):
        return self.person.phone

    @property
    def birth_date(self):
        return self.person.birth_date
