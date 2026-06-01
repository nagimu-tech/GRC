// HTMX: добавляем CSRF-токен в заголовки всех AJAX-запросов
document.addEventListener("DOMContentLoaded", function () {
    document.body.addEventListener("htmx:configRequest", function (e) {
        const token = document.cookie.match(/csrftoken=([^;]+)/);
        if (token) {
            e.detail.headers["X-CSRFToken"] = token[1];
        }
    });
});
