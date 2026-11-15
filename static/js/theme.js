/*
 * Troca de tema (Claro, Escuro, Sistema). Dono: item 3.1 (spec 017, D2).
 * A escolha vive so no localStorage do navegador: sem requisicao, sem cookie e
 * sem gravacao no servidor (ADR-012). O script inline do <head> aplica a escolha
 * salva antes da primeira pintura; este arquivo cuida da troca depois.
 */
(function () {
    const STORAGE_KEY = "theme";
    const root = document.documentElement;
    const systemQuery = window.matchMedia("(prefers-color-scheme: dark)");

    function storedChoice() {
        try {
            const value = window.localStorage.getItem(STORAGE_KEY);
            return value === "light" || value === "dark" ? value : "system";
        } catch (error) {
            return "system";
        }
    }

    function resolvedTheme() {
        const attribute = root.getAttribute("data-theme");
        if (attribute === "light" || attribute === "dark") {
            return attribute;
        }
        return systemQuery.matches ? "dark" : "light";
    }

    function syncThemeColor() {
        const canvas = getComputedStyle(root).getPropertyValue("--color-bg-canvas").trim();
        if (!canvas) {
            return;
        }
        document.querySelectorAll('meta[name="theme-color"]').forEach((meta) => {
            meta.setAttribute("content", canvas);
        });
    }

    function announce() {
        syncThemeColor();
        document.dispatchEvent(
            new CustomEvent("themechange", {
                detail: { choice: storedChoice(), theme: resolvedTheme() },
            })
        );
    }

    function setChoice(choice) {
        const next = choice === "light" || choice === "dark" ? choice : "system";

        try {
            if (next === "system") {
                window.localStorage.removeItem(STORAGE_KEY);
            } else {
                window.localStorage.setItem(STORAGE_KEY, next);
            }
        } catch (error) {
            // Sem localStorage a troca vale so ate recarregar a pagina.
        }

        if (next === "system") {
            root.removeAttribute("data-theme");
        } else {
            root.setAttribute("data-theme", next);
        }
        announce();
    }

    systemQuery.addEventListener("change", () => {
        if (storedChoice() === "system") {
            announce();
        }
    });

    window.addEventListener("storage", (event) => {
        if (event.key !== STORAGE_KEY && event.key !== null) {
            return;
        }
        const choice = storedChoice();
        if (choice === "system") {
            root.removeAttribute("data-theme");
        } else {
            root.setAttribute("data-theme", choice);
        }
        announce();
    });

    window.Theme = {
        choice: storedChoice,
        current: resolvedTheme,
        set: setChoice,
    };

    syncThemeColor();
}());
