(function () {
    const root = document.documentElement;
    const savedMode = localStorage.getItem("grc-mode");
    if (savedMode === "light" || savedMode === "dark") {
        root.setAttribute("data-mode", savedMode);
    }

    function syncButtons() {
        const mode = root.getAttribute("data-mode") || "dark";
        document.querySelectorAll("[data-theme-toggle]").forEach((button) => {
            button.setAttribute("aria-label", mode === "dark" ? "Включить светлую тему" : "Включить тёмную тему");
            button.querySelectorAll("[data-theme-icon]").forEach((icon) => {
                icon.hidden = icon.getAttribute("data-theme-icon") !== mode;
            });
        });
    }

    document.addEventListener("click", function (event) {
        const button = event.target.closest("[data-theme-toggle]");
        if (!button) return;
        const next = (root.getAttribute("data-mode") || "dark") === "dark" ? "light" : "dark";
        root.setAttribute("data-mode", next);
        localStorage.setItem("grc-mode", next);
        syncButtons();
    });

    document.addEventListener("DOMContentLoaded", syncButtons);
})();
