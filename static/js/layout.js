/*
 * JS da casca (spec 017, 3.2, ADR-019). Sem rede, sem cookie e sem gravacao no
 * servidor (ADR-012):
 * - revela o controle de tema e o mantem em sincronia com window.Theme (theme.js);
 * - folha "Mais" (popover nativo): aria-expanded no Mais, toque na camada fecha,
 *   foco volta ao Mais e a folha fecha ao passar de 768px.
 * Sem JS a navegacao continua inteira; so o controle de tema fica escondido.
 */
(function () {
    const SHEET_ID = "more-sheet";
    const desktopQuery = window.matchMedia("(min-width: 768px)");

    function setupThemeSwitches() {
        const switches = document.querySelectorAll(".theme-switch");
        if (!window.Theme || switches.length === 0) {
            return;
        }

        function sync() {
            const choice = window.Theme.choice();
            document.querySelectorAll("[data-theme-choice]").forEach((button) => {
                button.setAttribute(
                    "aria-pressed",
                    String(button.getAttribute("data-theme-choice") === choice)
                );
            });
        }

        switches.forEach((control) => {
            control.hidden = false;
            control.addEventListener("click", (event) => {
                const button = event.target.closest("[data-theme-choice]");
                if (button) {
                    window.Theme.set(button.getAttribute("data-theme-choice"));
                }
            });
        });

        document.addEventListener("themechange", sync);
        sync();
    }

    function setupMoreSheet() {
        const sheet = document.getElementById(SHEET_ID);
        if (!sheet || typeof sheet.hidePopover !== "function") {
            return;
        }

        const toggles = document.querySelectorAll('[popovertarget="' + SHEET_ID + '"]');

        sheet.addEventListener("toggle", (event) => {
            const isOpen = event.newState === "open";
            toggles.forEach((button) => {
                button.setAttribute("aria-expanded", String(isOpen));
            });

            // Fechou sem foco em outro controle (toque na camada): devolve ao Mais.
            const active = document.activeElement;
            if (!isOpen && toggles[0] && (active === document.body || sheet.contains(active))) {
                toggles[0].focus();
            }
        });

        // O proprio popover e a camada escurecida: clicar nela e tocar fora do painel.
        sheet.addEventListener("click", (event) => {
            if (event.target === sheet) {
                sheet.hidePopover();
            }
        });

        desktopQuery.addEventListener("change", (event) => {
            if (event.matches && sheet.matches(":popover-open")) {
                sheet.hidePopover();
            }
        });
    }

    setupThemeSwitches();
    setupMoreSheet();
}());
