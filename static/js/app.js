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

    const KINDS_BY_TYPE = {
        income: ["account"],
        expense: ["account", "credit", "balance"],
    };

    function setupTransactionForm(form) {
        const transactionType = form.querySelector('[name="transaction_type"]');
        const source = form.querySelector('[name="source"]');
        if (!transactionType || !source) {
            return;
        }

        // Guarda as opcoes originais; a cada troca de Tipo o select e remontado
        // so com os grupos validos. Sem JS o servidor valida a combinacao.
        const originalChildren = Array.from(source.children).map((node) => node.cloneNode(true));
        const sourceLabel = fieldContainer(source).querySelector("span");
        const sourceLabelText = sourceLabel ? sourceLabel.textContent : "";

        function rebuildSource(kind) {
            const allowedKinds = KINDS_BY_TYPE[kind] || [];
            const selected = source.value;

            source.innerHTML = "";
            originalChildren.forEach((node) => {
                const copy = node.cloneNode(true);
                if (copy.tagName === "OPTGROUP") {
                    Array.from(copy.children).forEach((option) => {
                        if (!allowedKinds.includes(option.dataset.kind)) {
                            copy.removeChild(option);
                        }
                    });
                    if (copy.children.length) {
                        source.appendChild(copy);
                    }
                } else {
                    source.appendChild(copy);
                }
            });

            const stillAvailable = Array.from(source.options).some((option) => option.value === selected);
            source.value = stillAvailable ? selected : "";
        }

        const update = function (shouldRebuild) {
            const kind = transactionType.value;
            const isTransfer = kind === "transfer";

            if (shouldRebuild && !isTransfer) {
                rebuildSource(kind);
            }

            const selectedOption = source.options[source.selectedIndex];
            const isCredit = !isTransfer && selectedOption && selectedOption.dataset.kind === "credit";

            if (sourceLabel) {
                const labelText = source.dataset[kind === "income" ? "labelIncome" : "labelExpense"];
                sourceLabel.textContent = labelText || sourceLabelText;
            }

            fieldsFor(form, "payment-source").forEach((field) => {
                setFieldVisible(field, !isTransfer);
            });
            fieldsFor(form, "payment-installments").forEach((field) => {
                setFieldVisible(field, isCredit);
            });
            fieldsFor(form, "payment-transfer").forEach((field) => {
                setFieldVisible(field, isTransfer);
            });
        };

        transactionType.addEventListener("change", () => update(true));
        source.addEventListener("change", () => update(false));
        update(true);
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
