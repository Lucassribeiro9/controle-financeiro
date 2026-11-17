(function () {
    const dataElement = document.getElementById("dashboard-chart-data");
    const canvas = document.getElementById("cashflow-chart");

    if (!dataElement || !canvas || !window.Chart) {
        return;
    }

    const payload = JSON.parse(dataElement.textContent);
    const moneyFormatter = new Intl.NumberFormat("pt-BR", {
        style: "currency",
        currency: payload.currency || "BRL",
    });

    // Cores vem dos tokens (--chart-*) do tema ativo; nenhuma cor fixa aqui (spec 017, D3).
    function chartColors() {
        const styles = getComputedStyle(document.documentElement);
        const read = (name) => styles.getPropertyValue(name).trim();

        return {
            income: read("--chart-income"),
            expense: read("--chart-expense"),
            balance: read("--chart-balance"),
            grid: read("--chart-grid"),
            text: read("--chart-text"),
            surface: read("--chart-surface"),
        };
    }

    const colors = chartColors();

    // Saldo do mes nao e uma serie: aparece so no tooltip, com as cores do tema.
    const tooltipStyle = (palette) => ({
        backgroundColor: palette.surface,
        titleColor: palette.text,
        bodyColor: palette.text,
        borderColor: palette.grid,
        borderWidth: 1,
        footerColor: palette.balance,
    });

    const chart = new Chart(canvas, {
        type: "bar",
        data: {
            labels: payload.labels,
            datasets: [
                {
                    label: "Receitas",
                    data: payload.income,
                    backgroundColor: colors.income,
                    borderColor: colors.income,
                    borderRadius: 6,
                    borderSkipped: false,
                    maxBarThickness: 20,
                },
                {
                    label: "Despesas",
                    data: payload.expenses,
                    backgroundColor: colors.expense,
                    borderColor: colors.expense,
                    borderRadius: 6,
                    borderSkipped: false,
                    maxBarThickness: 20,
                },
            ],
        },
        options: {
            maintainAspectRatio: false,
            interaction: {
                intersect: false,
                mode: "index",
            },
            plugins: {
                legend: {
                    align: "start",
                    position: "bottom",
                    labels: {
                        boxWidth: 10,
                        boxHeight: 10,
                        color: colors.text,
                        font: {
                            weight: "600",
                        },
                        useBorderRadius: true,
                        borderRadius: 2,
                    },
                },
                tooltip: {
                    ...tooltipStyle(colors),
                    callbacks: {
                        label(context) {
                            return `${context.dataset.label}: ${moneyFormatter.format(context.parsed.y || 0)}`;
                        },
                        footer(items) {
                            const balance = payload.balance[items[0].dataIndex] || 0;
                            return `Saldo: ${moneyFormatter.format(balance)}`;
                        },
                    },
                },
            },
            scales: {
                x: {
                    grid: {
                        display: false,
                    },
                    ticks: {
                        color: colors.text,
                        maxRotation: 0,
                    },
                },
                y: {
                    beginAtZero: true,
                    grid: {
                        color: colors.grid,
                    },
                    ticks: {
                        color: colors.text,
                        callback(value) {
                            return moneyFormatter.format(value);
                        },
                    },
                },
            },
        },
    });

    function applyTheme() {
        const next = chartColors();
        const [income, expense] = chart.data.datasets;

        income.backgroundColor = next.income;
        income.borderColor = next.income;
        expense.backgroundColor = next.expense;
        expense.borderColor = next.expense;

        Object.assign(chart.options.plugins.tooltip, tooltipStyle(next));
        chart.options.plugins.legend.labels.color = next.text;
        chart.options.scales.x.ticks.color = next.text;
        chart.options.scales.y.ticks.color = next.text;
        chart.options.scales.y.grid.color = next.grid;
        chart.update();
    }

    document.addEventListener("themechange", applyTheme);
}());
