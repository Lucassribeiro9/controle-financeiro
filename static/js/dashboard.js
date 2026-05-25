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

    const hasValue = (value) => Number(value) !== 0;
    const pointRadius = (context) => (hasValue(context.raw) ? 3 : 0);
    const hoverRadius = (context) => (hasValue(context.raw) ? 6 : 0);

    new Chart(canvas, {
        data: {
            labels: payload.labels,
            datasets: [
                {
                    type: "bar",
                    label: "Receitas",
                    data: payload.income,
                    backgroundColor: "rgba(22, 101, 52, 0.72)",
                    borderColor: "#166534",
                    borderRadius: 6,
                    borderSkipped: false,
                    maxBarThickness: 26,
                },
                {
                    type: "bar",
                    label: "Despesas",
                    data: payload.expenses,
                    backgroundColor: "rgba(180, 35, 24, 0.68)",
                    borderColor: "#b42318",
                    borderRadius: 6,
                    borderSkipped: false,
                    maxBarThickness: 26,
                },
                {
                    type: "line",
                    label: "Saldo",
                    data: payload.balance,
                    borderColor: "#0f5fa8",
                    backgroundColor: "rgba(15, 95, 168, 0.12)",
                    fill: false,
                    pointBackgroundColor: "#0f5fa8",
                    pointBorderColor: "#ffffff",
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
                        color: "#1f2937",
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
                        color: "#526071",
                        maxRotation: 0,
                    },
                },
                y: {
                    beginAtZero: true,
                    grid: {
                        color: "rgba(82, 96, 113, 0.16)",
                    },
                    ticks: {
                        color: "#526071",
                        callback(value) {
                            return moneyFormatter.format(value);
                        },
                    },
                },
            },
        },
    });
}());
