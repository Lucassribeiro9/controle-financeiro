(function () {
    function fieldContainer(field) {
        return field.closest(".form-field") || field.parentElement;
    }

    function setFieldVisible(field, isVisible) {
        const container = fieldContainer(field);
        if (!container) {
            return;
        }

        container.hidden = !isVisible;
        field.disabled = !isVisible;
    }

    function fieldsFor(form, groupName) {
        return Array.from(
            form.querySelectorAll(`[data-conditional-field="${groupName}"]`)
        );
    }

    function setupCardForm(form) {
        const cardType = form.querySelector('[name="card_type"]');
        if (!cardType) {
            return;
        }

        const update = function () {
            const isCredit = cardType.value === "credit";
            const isBalanceCard = ["benefit", "prepaid", "transport"].includes(cardType.value);

            fieldsFor(form, "card-credit").forEach((field) => {
                setFieldVisible(field, isCredit);
            });
            fieldsFor(form, "card-balance").forEach((field) => {
                setFieldVisible(field, isBalanceCard);
            });
        };

        cardType.addEventListener("change", update);
        update();
    }

    function setupTransactionForm(form) {
        const transactionType = form.querySelector('[name="transaction_type"]');
        if (!transactionType) {
            return;
        }

        const update = function () {
            const isCardPurchase = transactionType.value === "card_purchase";

            fieldsFor(form, "transaction-card").forEach((field) => {
                setFieldVisible(field, isCardPurchase);
            });
            fieldsFor(form, "transaction-account").forEach((field) => {
                setFieldVisible(field, !isCardPurchase);
            });
        };

        transactionType.addEventListener("change", update);
        update();
    }

    function setupConditionalForms() {
        document.querySelectorAll('[data-conditional-form="card"]').forEach(setupCardForm);
        document.querySelectorAll('[data-conditional-form="transaction"]').forEach(setupTransactionForm);
    }

    function setupMasks() {
        document.querySelectorAll('[data-mask="date"]').forEach((field) => {
            field.addEventListener("input", () => {
                const digits = field.value.replace(/\D/g, "").slice(0, 8);
                const parts = [digits.slice(0, 2), digits.slice(2, 4), digits.slice(4, 8)].filter(Boolean);
                field.value = parts.join("/");
            });
        });

        document.querySelectorAll('[data-mask="integer"]').forEach((field) => {
            field.addEventListener("input", () => {
                field.value = field.value.replace(/\D/g, "");
            });
        });

        document.querySelectorAll('[data-mask="decimal"]').forEach((field) => {
            field.addEventListener("blur", () => {
                if (field.value && !field.value.includes(",")) {
                    field.value = field.value.replace(".", ",");
                }
            });
        });
    }

    function setupBulkToggles() {
        document.querySelectorAll("[data-bulk-toggle]").forEach((toggle) => {
            const fieldName = toggle.dataset.bulkToggle;
            const checkboxes = Array.from(
                document.querySelectorAll(`input[type="checkbox"][name="${fieldName}"]`)
            );

            if (!checkboxes.length) {
                toggle.disabled = true;
                return;
            }

            const syncToggle = function () {
                const checkedCount = checkboxes.filter((checkbox) => checkbox.checked).length;
                toggle.checked = checkedCount === checkboxes.length;
                toggle.indeterminate = checkedCount > 0 && checkedCount < checkboxes.length;
            };

            toggle.addEventListener("change", () => {
                checkboxes.forEach((checkbox) => {
                    checkbox.checked = toggle.checked;
                });
                syncToggle();
            });

            checkboxes.forEach((checkbox) => {
                checkbox.addEventListener("change", syncToggle);
            });
            syncToggle();
        });
    }

    document.addEventListener("DOMContentLoaded", () => {
        setupConditionalForms();
        setupMasks();
        setupBulkToggles();
    });
}());
