from django.conf import settings
from django.db import models, transaction
from django.utils import timezone
from simple_history.models import HistoricalRecords
from apps.core.models import TenantModel


class Event(TenantModel):
    """Встреча выпускников / прозвон. Против него ведётся обзвон."""
    course = models.ForeignKey(
        "catalog.Course",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="events",
        verbose_name="Курс",
    )
    title = models.CharField(max_length=255, verbose_name="Название")
    date = models.DateField(null=True, blank=True, verbose_name="Дата")
    location = models.CharField(max_length=255, blank=True, verbose_name="Место")
    is_active = models.BooleanField(default=True, verbose_name="Активна")
    notes = models.TextField(blank=True, verbose_name="Заметки")
    assigned_callers = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        blank=True,
        related_name="assigned_events",
        verbose_name="Назначенные прозвонщики",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Встреча / прозвон"
        verbose_name_plural = "Встречи / прозвоны"
        ordering = ["-date", "-created_at"]

    def __str__(self):
        return self.title


class CallRecord(TenantModel):
    """
    Отметка прозвона для конкретного человека в рамках конкретной встречи.
    Атомарный захват предотвращает двойной обзвон при конкурентном доступе.
    """
    NOT_CALLED = "NOT_CALLED"
    WILL_COME = "WILL_COME"
    WONT_COME = "WONT_COME"
    MAYBE = "MAYBE"
    NO_ANSWER = "NO_ANSWER"

    STATUS_CHOICES = [
        (NOT_CALLED, "Не звонили"),
        (WILL_COME, "Придёт"),
        (WONT_COME, "Не придёт"),
        (MAYBE, "Возможно придёт"),
        (NO_ANSWER, "Не берёт трубку"),
    ]

    STATUS_BADGE = {
        NOT_CALLED: "bg-gray-100 text-gray-600",
        WILL_COME: "bg-green-100 text-green-800",
        WONT_COME: "bg-red-100 text-red-800",
        MAYBE: "bg-yellow-100 text-yellow-800",
        NO_ANSWER: "bg-orange-100 text-orange-800",
    }

    event = models.ForeignKey(
        Event,
        on_delete=models.CASCADE,
        related_name="call_records",
        verbose_name="Встреча",
    )
    company_person = models.ForeignKey(
        "people.CompanyPerson",
        on_delete=models.CASCADE,
        related_name="call_records",
        verbose_name="Человек в компании",
    )
    status = models.CharField(
        max_length=15,
        choices=STATUS_CHOICES,
        default=NOT_CALLED,
        verbose_name="Статус",
    )
    comment = models.TextField(blank=True, verbose_name="Комментарий")
    called_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="called_records",
        verbose_name="Позвонил",
    )
    claimed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="claimed_records",
        verbose_name="Взял в работу",
    )
    claimed_at = models.DateTimeField(null=True, blank=True, verbose_name="Время захвата")
    updated_at = models.DateTimeField(auto_now=True)

    history = HistoricalRecords()

    class Meta:
        verbose_name = "Отметка прозвона"
        verbose_name_plural = "Отметки прозвона"
        unique_together = [("event", "company_person")]

    def __str__(self):
        return f"{self.company_person.full_name} — {self.event.title} — {self.get_status_display()}"

    @property
    def is_available(self):
        """Доступен ли для захвата: не взят и не обзвонен."""
        return self.claimed_by_id is None and self.status == self.NOT_CALLED

    @property
    def status_badge_class(self):
        return self.STATUS_BADGE.get(self.status, "bg-gray-100 text-gray-600")

    @classmethod
    @transaction.atomic
    def claim(cls, event, company_person, user):
        """
        Атомарный захват записи. Возвращает запись если захват успешен, иначе None.
        Использует SELECT FOR UPDATE с SKIP LOCKED для честной конкуренции.
        """
        try:
            record = cls.objects.select_for_update(skip_locked=True).get(
                event=event,
                company_person=company_person,
                claimed_by__isnull=True,
                status=cls.NOT_CALLED,
            )
            record.claimed_by = user
            record.claimed_at = timezone.now()
            record.save(update_fields=["claimed_by", "claimed_at"])
            return record
        except cls.DoesNotExist:
            return None

    @classmethod
    def get_or_create_for_event(cls, event):
        """
        Инициализация CallRecord для всех подходящих людей события.
        Создаёт записи с дефолтным статусом NOT_CALLED для всех студентов курса.
        """
        from apps.participation.models import Participation
        from apps.people.models import CompanyPerson

        course = event.course
        if not course:
            return

        student_persons = (
            CompanyPerson.objects
            .filter(
                company=event.company,
                participations__session__course=course,
                participations__role=Participation.STUDENT,
                is_active=True,
            )
            .distinct()
        )

        existing_ids = set(
            cls.objects.filter(event=event).values_list("company_person_id", flat=True)
        )

        new_records = [
            cls(
                event=event,
                company_person=cp,
                company=event.company,
                status=cls.NOT_CALLED,
            )
            for cp in student_persons
            if cp.pk not in existing_ids
        ]
        if new_records:
            cls.objects.bulk_create(new_records, ignore_conflicts=True)
