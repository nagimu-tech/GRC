from django.db import models
from apps.core.models import TenantModel


class Position(models.Model):
    """
    Должность — глобальный справочник, общий для всех компаний.
    Не тенант-модель: не имеет company, редактируется только сисадмином.
    """
    name = models.CharField(max_length=200, unique=True, verbose_name="Название")
    description = models.TextField(blank=True, verbose_name="Описание")
    is_active = models.BooleanField(default=True, verbose_name="Активна")
    order = models.PositiveSmallIntegerField(default=0, verbose_name="Порядок")

    class Meta:
        verbose_name = "Должность"
        verbose_name_plural = "Должности"
        ordering = ["order", "name"]

    def __str__(self):
        return self.name


class Course(TenantModel):
    """Программа курса. Один курс имеет много запусков (CourseSession)."""
    name = models.CharField(max_length=255, verbose_name="Название")
    description = models.TextField(blank=True, verbose_name="Описание")
    is_active = models.BooleanField(default=True, verbose_name="Активен")

    class Meta:
        verbose_name = "Курс"
        verbose_name_plural = "Курсы"
        ordering = ["name"]

    def __str__(self):
        return self.name


class CourseSession(TenantModel):
    """Конкретный запуск (поток) курса."""
    ONLINE = "ONLINE"
    OFFLINE = "OFFLINE"
    HYBRID = "HYBRID"

    FORMAT_CHOICES = [
        (ONLINE, "Онлайн"),
        (OFFLINE, "Офлайн"),
        (HYBRID, "Смешанный"),
    ]

    course = models.ForeignKey(
        Course,
        on_delete=models.CASCADE,
        related_name="sessions",
        verbose_name="Курс",
    )
    label = models.CharField(max_length=255, verbose_name="Название потока")
    start_date = models.DateField(null=True, blank=True, verbose_name="Дата начала")
    end_date = models.DateField(null=True, blank=True, verbose_name="Дата окончания")
    location_format = models.CharField(
        max_length=10,
        choices=FORMAT_CHOICES,
        default=OFFLINE,
        verbose_name="Формат",
    )
    notes = models.TextField(blank=True, verbose_name="Заметки")

    class Meta:
        verbose_name = "Запуск курса"
        verbose_name_plural = "Запуски курсов"
        ordering = ["-start_date", "label"]

    def __str__(self):
        return f"{self.course.name} — {self.label}"

    @property
    def date_range(self):
        if self.start_date and self.end_date:
            return f"{self.start_date.strftime('%d.%m.%Y')} — {self.end_date.strftime('%d.%m.%Y')}"
        if self.start_date:
            return self.start_date.strftime("%d.%m.%Y")
        return "—"


class CourseSessionPhoto(models.Model):
    """Фото потока курса: хранится во внешнем хранилище, в БД только ссылка."""
    session = models.ForeignKey(
        CourseSession,
        on_delete=models.CASCADE,
        related_name="photos",
        verbose_name="Поток курса",
    )
    image_url = models.URLField(max_length=1000, verbose_name="Ссылка на фото")
    caption = models.CharField(max_length=255, blank=True, verbose_name="Подпись")
    order = models.PositiveSmallIntegerField(default=0, verbose_name="Порядок")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Добавлено")

    class Meta:
        verbose_name = "Фото потока курса"
        verbose_name_plural = "Фото потоков курсов"
        ordering = ["order", "created_at"]

    def __str__(self):
        return self.caption or f"Фото {self.session}"
