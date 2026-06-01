def company_context(request):
    return {
        "active_company": getattr(request, "company", None),
    }
