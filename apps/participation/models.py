from django.db import models
from apps.core.models import TenantModel


class Participation(TenantModel):
    """
    Участие человека в конкретном запуске курса.
    Роль определяет, кем он был: студентом, ассистентом или тренером.
    Тренер — не отдельная сущность, а роль участия.

    Структура спроектирована с расчётом на безболезненное добавление
    полей оплаты: payment_type, amount, currency, paid_at, payment_note.
    """
    STUDENT = "STUDENT"
    ASSISTANT = "ASSISTANT"
    TRAINER = "TRAINER"

    ROLE_CHOICES = [
        (STUDENT, "Студент"),
        (ASSISTANT, "Ассистент"),
        (TRAINER, "Тренер"),
    ]

    company_person = models.ForeignKey(
        "people.CompanyPerson",
        on_delete=models.CASCADE,
        related_name="participations",
        verbose_name="Человек в компании",
    )
    session = models.ForeignKey(
        "catalog.CourseSession",
        on_delete=models.CASCADE,
        related_name="participations",
        verbose_name="Запуск курса",
    )
    role = models.CharField(
        max_length=15,
        choices=ROLE_CHOICES,
        verbose_name="Роль",
    )
    chosen_position = models.ForeignKey(
        "catalog.Position",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="Должность",
    )
    notes = models.TextField(blank=True, verbose_name="Заметки")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Участие"
        verbose_name_plural = "Участия"
        unique_together = [("company_person", "session", "role")]
        ordering = ["-session__start_date", "role"]

    def __str__(self):
        return f"{self.company_person.full_name} — {self.get_role_display()} — {self.session}"

    @property
    def role_badge_class(self):
        mapping = {
            self.STUDENT: "bg-blue-100 text-blue-800",
            self.ASSISTANT: "bg-yellow-100 text-yellow-800",
            self.TRAINER: "bg-green-100 text-green-800",
        }
        return mapping.get(self.role, "bg-gray-100 text-gray-800")
