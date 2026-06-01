class CompanyMiddleware:
    """
    Резолвит request.company из пользователя.
    Системный администратор может переключить активную компанию через сессию.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request.company = None
        if request.user.is_authenticated:
            if request.user.is_system_admin:
                active_id = request.session.get("active_company_id")
                if active_id:
                    from apps.accounts.models import Company
                    try:
                        request.company = Company.objects.get(pk=active_id, is_active=True)
                    except Company.DoesNotExist:
                        request.session.pop("active_company_id", None)
            elif request.user.company_id:
                request.company = request.user.company
        return self.get_response(request)
