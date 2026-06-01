from django.db import models


class TenantManager(models.Manager):
    def for_company(self, company):
        return self.get_queryset().filter(company=company)


class TenantModel(models.Model):
    """
    Абстрактная база для всех моделей с изоляцией по компании.
    Поле company дублируется на каждой дочерней модели (денормализация),
    чтобы любая выборка фильтровалась одним полем без джойнов.
    """
    company = models.ForeignKey(
        "accounts.Company",
        on_delete=models.CASCADE,
        verbose_name="Компания",
        db_index=True,
    )

    objects = TenantManager()

    class Meta:
        abstract = True
