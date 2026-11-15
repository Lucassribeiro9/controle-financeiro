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

    const hasValue = (value) => Number(value) !== 0;
    const pointRadius = (context) => (hasValue(context.raw) ? 3 : 0);
    const hoverRadius = (context) => (hasValue(context.raw) ? 6 : 0);

    const colors = chartColors();

    const chart = new Chart(canvas, {
        data: {
            labels: payload.labels,
            datasets: [
                {
                    type: "bar",
                    label: "Receitas",
                    data: payload.income,
                    backgroundColor: colors.income,
                    borderColor: colors.income,
                    borderRadius: 6,
                    borderSkipped: false,
                    maxBarThickness: 26,
                },
                {
                    type: "bar",
                    label: "Despesas",
                    data: payload.expenses,
                    backgroundColor: colors.expense,
                    borderColor: colors.expense,
                    borderRadius: 6,
                    borderSkipped: false,
                    maxBarThickness: 26,
                },
                {
                    type: "line",
                    label: "Saldo",
                    data: payload.balance,
                    borderColor: colors.balance,
                    backgroundColor: colors.balance,
                    fill: false,
                    pointBackgroundColor: colors.balance,
                    pointBorderColor: colors.surface,
                    pointBorderWidth: 2,
                    pointRadius,
                    pointHoverRadius: hoverRadius,
                    tension: 0.28,
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
                    align: "end",
                    labels: {
                        boxWidth: 10,
                        boxHeight: 10,
                        color: colors.text,
                        font: {
                            weight: "700",
                        },
                        useBorderRadius: true,
                    },
                },
                tooltip: {
                    callbacks: {
                        label(context) {
                            return `${context.dataset.label}: ${moneyFormatter.format(context.parsed.y || 0)}`;
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
        const [income, expense, balance] = chart.data.datasets;

        income.backgroundColor = next.income;
        income.borderColor = next.income;
        expense.backgroundColor = next.expense;
        expense.borderColor = next.expense;
        balance.borderColor = next.balance;
        balance.backgroundColor = next.balance;
        balance.pointBackgroundColor = next.balance;
        balance.pointBorderColor = next.surface;

        chart.options.plugins.legend.labels.color = next.text;
        chart.options.scales.x.ticks.color = next.text;
        chart.options.scales.y.ticks.color = next.text;
        chart.options.scales.y.grid.color = next.grid;
        chart.update();
    }

    document.addEventListener("themechange", applyTheme);
}());
