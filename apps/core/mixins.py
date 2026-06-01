from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404


class TenantScopedMixin(LoginRequiredMixin):
    """
    Миксин для всех CBV, работающих с тенант-моделями.
    Фильтрует queryset по request.company и проставляет company при создании.
    """

    def get_queryset(self):
        qs = super().get_queryset()
        if self.request.user.is_system_admin:
            return qs
        company = self.request.company
        if not company:
            raise PermissionDenied
        return qs.filter(company=company)

    def form_valid(self, form):
        instance = form.instance
        if hasattr(instance, "company_id") and not instance.company_id:
            if not self.request.company:
                raise PermissionDenied
            instance.company = self.request.company
        return super().form_valid(form)


class SystemAdminRequiredMixin(LoginRequiredMixin):
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        if not request.user.is_system_admin:
            raise PermissionDenied
        return super().dispatch(request, *args, **kwargs)


class CompanyAdminRequiredMixin(LoginRequiredMixin):
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        if not (request.user.is_system_admin or request.user.is_company_admin):
            raise PermissionDenied
        return super().dispatch(request, *args, **kwargs)


class TenantObjectMixin:
    """
    Для DetailView/UpdateView/DeleteView: проверяет, что объект принадлежит company.
    Возвращает 404 вместо 403, чтобы не раскрывать существование записи.
    """

    def get_object(self, queryset=None):
        obj = super().get_object(queryset)
        user = self.request.user
        if user.is_system_admin:
            return obj
        if hasattr(obj, "company_id") and obj.company_id != self.request.company.pk:
            from django.http import Http404
            raise Http404
        return obj
