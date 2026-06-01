from django.contrib.auth.models import AbstractUser
from django.db import models


class Company(models.Model):
    name = models.CharField(max_length=255, verbose_name="Название")
    is_active = models.BooleanField(default=True, verbose_name="Активна")
    phone = models.CharField(max_length=50, blank=True, verbose_name="Телефон")
    email = models.EmailField(blank=True, verbose_name="Email")
    notes = models.TextField(blank=True, verbose_name="Заметки")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Создана")

    class Meta:
        verbose_name = "Компания"
        verbose_name_plural = "Компании"
        ordering = ["name"]

    def __str__(self):
        return self.name


class User(AbstractUser):
    SYSTEM_ADMIN = "SYSTEM_ADMIN"
    COMPANY_ADMIN = "COMPANY_ADMIN"
    CALLER = "CALLER"

    ROLE_CHOICES = [
        (SYSTEM_ADMIN, "Системный администратор"),
        (COMPANY_ADMIN, "Администратор компании"),
        (CALLER, "Прозвонщик"),
    ]

    company = models.ForeignKey(
        Company,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="users",
        verbose_name="Компания",
    )
    role = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES,
        default=COMPANY_ADMIN,
        verbose_name="Роль",
    )

    class Meta:
        verbose_name = "Пользователь"
        verbose_name_plural = "Пользователи"

    @property
    def is_system_admin(self):
        return self.role == self.SYSTEM_ADMIN

    @property
    def is_company_admin(self):
        return self.role == self.COMPANY_ADMIN

    @property
    def is_caller(self):
        return self.role == self.CALLER

    @property
    def display_role(self):
        return dict(self.ROLE_CHOICES).get(self.role, self.role)

    def __str__(self):
        full = self.get_full_name()
        return full if full else self.username
