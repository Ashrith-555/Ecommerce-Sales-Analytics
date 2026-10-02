/**
 * Pulse — premium Chart.js theme (visual only, no data logic)
 */
window.PulseChartTheme = (function () {
    const C = {
        indigo: '#6366f1',
        indigoDark: '#4f46e5',
        purple: '#a855f7',
        cyan: '#06b6d4',
        cyanLight: '#22d3ee',
        emerald: '#10b981',
        emeraldLight: '#34d399',
        amber: '#f59e0b',
        rose: '#f43f5e',
        pink: '#ec4899',
        slate: '#64748b',
        grid: 'rgba(99, 102, 241, 0.07)',
        gridDash: 'rgba(148, 163, 184, 0.35)',
        tooltipBg: 'rgba(15, 23, 42, 0.92)',
        tooltipBorder: 'rgba(99, 102, 241, 0.35)',
        white: '#ffffff',
    };

    const PALETTE = [
        C.indigo,
        C.cyan,
        C.emerald,
        C.purple,
        C.amber,
        C.rose,
        C.pink,
        '#14b8a6',
    ];

    const PALETTE_SOFT = PALETTE.map((hex) => hex + '22');

    function applyDefaults() {
        if (typeof Chart === 'undefined') return;

        Chart.defaults.font.family = "'Plus Jakarta Sans', 'Inter', sans-serif";
        Chart.defaults.color = C.slate;
        Chart.defaults.font.size = 12;
        Chart.defaults.font.weight = '500';

        Chart.defaults.animation.duration = 900;
        Chart.defaults.animation.easing = 'easeInOutQuart';

        Chart.defaults.plugins.tooltip.backgroundColor = C.tooltipBg;
        Chart.defaults.plugins.tooltip.borderColor = C.tooltipBorder;
        Chart.defaults.plugins.tooltip.borderWidth = 1;
        Chart.defaults.plugins.tooltip.padding = 14;
        Chart.defaults.plugins.tooltip.cornerRadius = 12;
        Chart.defaults.plugins.tooltip.titleFont = { weight: '700', size: 13 };
        Chart.defaults.plugins.tooltip.bodyFont = { weight: '500', size: 12 };
        Chart.defaults.plugins.tooltip.displayColors = true;
        Chart.defaults.plugins.tooltip.boxPadding = 6;
        Chart.defaults.plugins.tooltip.usePointStyle = true;

        Chart.defaults.plugins.legend.labels.usePointStyle = true;
        Chart.defaults.plugins.legend.labels.pointStyle = 'circle';
        Chart.defaults.plugins.legend.labels.padding = 18;
        Chart.defaults.plugins.legend.labels.font = { size: 12, weight: '600' };
        Chart.defaults.plugins.legend.labels.color = '#475569';
    }

    function verticalGradient(ctx, topColor, bottomColor, height) {
        const h = height || 320;
        const g = ctx.createLinearGradient(0, 0, 0, h);
        g.addColorStop(0, topColor);
        g.addColorStop(1, bottomColor);
        return g;
    }

    function barGradient(ctx, from, to) {
        return verticalGradient(ctx, from, to, 400);
    }

    function getLegend(position) {
        return {
            display: true,
            position: position || 'bottom',
            labels: {
                usePointStyle: true,
                padding: 20,
                font: { size: 12, weight: '600' },
                color: '#475569',
            },
        };
    }

    function getScales(currencyFormatter) {
        const tickCb = currencyFormatter || function (v) { return v; };
        return {
            y: {
                beginAtZero: true,
                grid: {
                    color: C.grid,
                    borderDash: [4, 6],
                    drawBorder: false,
                },
                border: { display: false },
                ticks: {
                    padding: 10,
                    font: { size: 11, weight: '500' },
                    color: '#94a3b8',
                    callback: tickCb,
                },
            },
            x: {
                grid: { display: false, drawBorder: false },
                border: { display: false },
                ticks: {
                    padding: 8,
                    font: { size: 11, weight: '600' },
                    color: '#94a3b8',
                },
            },
        };
    }

    function inrTick(value) {
        if (value >= 100000) return '₹' + (value / 100000).toFixed(1) + 'L';
        if (value >= 1000) return '₹' + (value / 1000).toFixed(0) + 'K';
        return '₹' + value;
    }

    function inrTooltipLabel(context) {
        return ' ₹' + context.parsed.y.toLocaleString('en-IN');
    }

    function percentTooltipLabel(context) {
        const total = context.dataset.data.reduce((a, b) => a + b, 0);
        const pct = total ? ((context.parsed / total) * 100).toFixed(1) : 0;
        return ` ${context.label}: ${pct}%`;
    }

    function percentCurrencyTooltipLabel(context) {
        const total = context.dataset.data.reduce((a, b) => a + b, 0);
        const pct = total ? ((context.parsed / total) * 100).toFixed(1) : 0;
        return ` ${context.label}: ${pct}% (₹${context.parsed.toLocaleString('en-IN')})`;
    }

    function lineDataset(ctx, data, opts) {
        const o = opts || {};
        const lineColor = o.color || C.indigo;
        const fillTop = o.fillTop || 'rgba(99, 102, 241, 0.35)';
        const fillBottom = o.fillBottom || 'rgba(99, 102, 241, 0)';

        return {
            label: o.label || 'Value',
            data: data,
            borderColor: lineColor,
            backgroundColor: verticalGradient(ctx, fillTop, fillBottom, 400),
            borderWidth: 3,
            tension: 0.42,
            fill: true,
            pointBackgroundColor: C.white,
            pointBorderColor: lineColor,
            pointBorderWidth: 2.5,
            pointRadius: 4,
            pointHoverRadius: 7,
            pointHoverBackgroundColor: lineColor,
            pointHoverBorderColor: C.white,
            pointHoverBorderWidth: 2.5,
        };
    }

    const BAR_FILL_PAIRS = [
        ['#6366f1', '#a5b4fc'],
        ['#06b6d4', '#67e8f9'],
        ['#10b981', '#6ee7b7'],
        ['#a855f7', '#d8b4fe'],
        ['#f59e0b', '#fcd34d'],
        ['#f43f5e', '#fda4af'],
    ];

    const BAR_HOVER_PAIRS = [
        ['#4f46e5', '#818cf8'],
        ['#0891b2', '#22d3ee'],
        ['#059669', '#34d399'],
        ['#7c3aed', '#c084fc'],
        ['#d97706', '#fbbf24'],
        ['#e11d48', '#fb7185'],
    ];

    function multiBarColors(ctx, count, pairs) {
        const palette = pairs || BAR_FILL_PAIRS;
        return Array.from({ length: count }, (_, i) => {
            const [a, b] = palette[i % palette.length];
            return barGradient(ctx, a, b);
        });
    }

    function multiBarHoverColors(ctx, count) {
        return multiBarColors(ctx, count, BAR_HOVER_PAIRS);
    }

    function barDataset(ctx, data, opts) {
        const o = opts || {};
        const count = data.length;
        const fills = multiBarColors(ctx, count);
        const hovers = multiBarHoverColors(ctx, count);

        return {
            label: o.label || 'Value',
            data: data,
            backgroundColor: fills,
            hoverBackgroundColor: hovers,
            borderRadius: { topLeft: 14, topRight: 14, bottomLeft: 6, bottomRight: 6 },
            borderSkipped: false,
            barThickness: o.barThickness || 40,
            maxBarThickness: 52,
            borderWidth: 0,
            hoverBorderWidth: 2,
            hoverBorderColor: C.white,
        };
    }

    const ARC_HOVER = ['#4f46e5', '#0891b2', '#059669', '#7c3aed', '#d97706', '#e11d48', '#db2777', '#0d9488'];

    function arcDataset(data, opts) {
        const o = opts || {};
        const type = o.type || 'doughnut';
        const colors = o.colors || PALETTE;
        return {
            data: data,
            backgroundColor: colors,
            hoverBackgroundColor: colors.map((c, i) => ARC_HOVER[i % ARC_HOVER.length]),
            borderWidth: type === 'doughnut' ? 6 : 4,
            borderColor: C.white,
            hoverBorderColor: C.white,
            hoverOffset: type === 'pie' ? 16 : 12,
            spacing: type === 'doughnut' ? 3 : 1,
        };
    }

    const layoutPadding = { top: 10, right: 16, bottom: 6, left: 8 };

    function lineOptions(opts) {
        const o = opts || {};
        return {
            responsive: true,
            maintainAspectRatio: false,
            layout: { padding: layoutPadding },
            interaction: { intersect: false, mode: 'index' },
            plugins: {
                legend: o.legend || { display: false },
                tooltip: {
                    padding: 14,
                    displayColors: o.displayColors !== false,
                    callbacks: { label: o.tooltipLabel || inrTooltipLabel },
                },
            },
            scales: getScales(o.yTick || inrTick),
            animation: { duration: 900, easing: 'easeInOutQuart' },
        };
    }

    function barOptions(opts) {
        const o = opts || {};
        return {
            responsive: true,
            maintainAspectRatio: false,
            layout: { padding: layoutPadding },
            interaction: { intersect: false, mode: 'index' },
            plugins: {
                legend: { display: false },
                tooltip: {
                    padding: 14,
                    callbacks: {
                        label: o.tooltipLabel || function (context) {
                            return ' ' + (context.label || '') + ': ₹' + context.parsed.y.toLocaleString('en-IN');
                        },
                    },
                },
            },
            scales: getScales(o.yTick || inrTick),
            animation: { duration: 900, easing: 'easeInOutQuart' },
        };
    }

    function arcOptions(type, opts) {
        const o = opts || {};
        const options = {
            responsive: true,
            maintainAspectRatio: false,
            layout: { padding: { top: 8, bottom: 8, left: 12, right: 12 } },
            plugins: {
                legend: getLegend(o.legendPosition || 'bottom'),
                tooltip: {
                    padding: 14,
                    callbacks: { label: o.tooltipLabel || percentCurrencyTooltipLabel },
                },
            },
            animation: { animateRotate: true, animateScale: true, duration: 900, easing: 'easeInOutQuart' },
        };
        if (type === 'doughnut') options.cutout = o.cutout || '74%';
        return options;
    }

    function buildDynDataset(canvasEl, chartConfig, index) {
        const ctx = canvasEl.getContext('2d');
        const type = chartConfig.type;
        const ds = {
            label: chartConfig.title || 'Value',
            data: chartConfig.values,
        };

        if (type === 'bar') {
            Object.assign(ds, barDataset(ctx, chartConfig.values, { label: chartConfig.title }));
        } else if (type === 'line') {
            const accent = PALETTE[index % PALETTE.length];
            Object.assign(ds, lineDataset(ctx, chartConfig.values, {
                label: chartConfig.title,
                color: accent,
                fillTop: accent + '40',
                fillBottom: accent + '00',
            }));
        } else if (type === 'doughnut' || type === 'pie') {
            Object.assign(ds, arcDataset(chartConfig.values, { type: type }));
        }
        return ds;
    }

    function buildDynOptions(type) {
        if (type === 'bar') return barOptions();
        if (type === 'line') return lineOptions();
        if (type === 'doughnut' || type === 'pie') {
            return arcOptions(type, {
                tooltipLabel: type === 'pie' ? percentTooltipLabel : percentCurrencyTooltipLabel,
            });
        }
        return { responsive: true, maintainAspectRatio: false };
    }

    function initAnalyticsCharts() {
        const dataEl = document.getElementById('forecast-data');
        const lineEl = document.getElementById('lineChart');
        const doughnutEl = document.getElementById('trafficChart');
        if (!dataEl || !lineEl) return;

        const forecastData = {
            historicalLabels: JSON.parse(dataEl.getAttribute('data-historical-labels') || '[]'),
            historicalValues: JSON.parse(dataEl.getAttribute('data-historical-values') || '[]'),
            forecastLabels: JSON.parse(dataEl.getAttribute('data-forecast-labels') || '[]'),
            forecastValues: JSON.parse(dataEl.getAttribute('data-forecast-values') || '[]'),
        };

        const allLabels = forecastData.historicalLabels.concat(forecastData.forecastLabels);

        const histData = [...forecastData.historicalValues];
        while (histData.length < allLabels.length) histData.push(null);

        const foreData = [];
        for (let i = 0; i < forecastData.historicalValues.length - 1; i++) foreData.push(null);
        if (forecastData.historicalValues.length > 0) {
            foreData.push(forecastData.historicalValues[forecastData.historicalValues.length - 1]);
        }
        foreData.push(...forecastData.forecastValues);

        const lineCtx = lineEl.getContext('2d');

        const forecastTooltip = function (context) {
            if (context.parsed.y === null) return null;
            return ' ' + context.dataset.label.split(' (')[0] + ': ₹' + context.parsed.y.toLocaleString('en-IN');
        };

        new Chart(lineEl, {
            type: 'line',
            data: {
                labels: allLabels,
                datasets: [
                    Object.assign(lineDataset(lineCtx, histData, {
                        label: 'Historical Revenue (₹)',
                        color: C.indigo,
                        fillTop: 'rgba(99, 102, 241, 0.38)',
                        fillBottom: 'rgba(99, 102, 241, 0)',
                    }), { spanGaps: false }),
                    {
                        label: 'Forecasted Revenue (₹)',
                        data: foreData,
                        borderColor: C.emerald,
                        backgroundColor: 'rgba(16, 185, 129, 0.06)',
                        borderWidth: 3,
                        borderDash: [8, 6],
                        tension: 0.42,
                        fill: false,
                        pointRadius: 5,
                        pointBackgroundColor: C.emerald,
                        pointBorderColor: C.white,
                        pointBorderWidth: 2,
                        pointHoverRadius: 8,
                        pointHoverBackgroundColor: C.emeraldLight,
                        pointHoverBorderColor: C.white,
                    },
                ],
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                interaction: { intersect: false, mode: 'index' },
                plugins: {
                    legend: getLegend('top'),
                    tooltip: {
                        padding: 14,
                        callbacks: { label: forecastTooltip },
                    },
                },
                scales: getScales(inrTick),
            },
        });

        if (doughnutEl) {
            new Chart(doughnutEl, {
                type: 'doughnut',
                data: {
                    labels: ['Direct Sales', 'Online Store', 'Marketplace'],
                    datasets: [arcDataset([55, 30, 15], {
                        colors: [C.indigo, C.cyan, C.emerald],
                    })],
                },
                options: arcOptions('doughnut', {
                    cutout: '74%',
                    tooltipLabel: percentTooltipLabel,
                }),
            });
        }
    }

    return {
        C,
        PALETTE,
        PALETTE_SOFT,
        applyDefaults,
        verticalGradient,
        barGradient,
        getLegend,
        getScales,
        inrTick,
        inrTooltipLabel,
        percentTooltipLabel,
        percentCurrencyTooltipLabel,
        lineDataset,
        barDataset,
        multiBarColors,
        arcDataset,
        lineOptions,
        barOptions,
        arcOptions,
        buildDynDataset,
        buildDynOptions,
        initAnalyticsCharts,
    };
})();
