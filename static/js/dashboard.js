document.addEventListener("DOMContentLoaded", function () {

    // ANIMATION FOR CARDS
    const cards = document.querySelectorAll(".kpi-card, .chart-card, .table-card");

    cards.forEach((card, index) => {
        card.style.opacity = "0";
        card.style.transform = "translateY(20px)";

        setTimeout(() => {
            card.style.transition = "all 0.6s cubic-bezier(0.4, 0, 0.2, 1)";
            card.style.opacity = "1";
            card.style.transform = "translateY(0)";
        }, index * 100);
    });

    // SEARCH BAR EFFECT
    const searchInput = document.querySelector(".search-box input");
    if (searchInput) {
        searchInput.addEventListener("focus", function () {
            this.parentElement.style.borderColor = "var(--primary)";
            this.parentElement.style.boxShadow = "0 0 0 3px var(--primary-light)";
        });
        searchInput.addEventListener("blur", function () {
            this.parentElement.style.borderColor = "transparent";
            this.parentElement.style.boxShadow = "none";
        });
    }

    // Premium chart theme defaults
    if (window.PulseChartTheme) {
        PulseChartTheme.applyDefaults();
    }


    // ==========================================
    // SYSTEM 1: FIXED ECOMMERCE CHARTS
    // ==========================================
    // ==========================================
    // SYSTEM 1: FIXED ECOMMERCE CHARTS
    // ==========================================
    window.pulseCharts = {};

    if (typeof chartData !== 'undefined') {

        const T = window.PulseChartTheme;

        // 1. Monthly Sales Trend (Line Chart)
        const monthlyCtx = document.getElementById('monthlyChart');
        if (monthlyCtx && T) {
            const ctx = monthlyCtx.getContext('2d');
            window.pulseCharts.monthly = new Chart(monthlyCtx, {
                type: 'line',
                data: {
                    labels: chartData.months.labels,
                    datasets: [Object.assign(T.lineDataset(ctx, chartData.months.values, {
                        label: 'Sales (₹)',
                        color: T.C.indigo,
                        fillTop: 'rgba(99, 102, 241, 0.38)',
                        fillBottom: 'rgba(99, 102, 241, 0)',
                    }))],
                },
                options: T.lineOptions({
                    tooltipLabel: function (context) {
                        return ' ₹' + context.parsed.y.toLocaleString('en-IN');
                    },
                }),
            });
        }

        // 2. Region Sales (Bar Chart) — unique gradient per bar
        const regionCtx = document.getElementById('regionChart');
        if (regionCtx && T) {
            const ctx = regionCtx.getContext('2d');
            window.pulseCharts.region = new Chart(regionCtx, {
                type: 'bar',
                data: {
                    labels: chartData.regions.labels,
                    datasets: [T.barDataset(ctx, chartData.regions.values, {
                        label: 'Sales (₹)',
                    })],
                },
                options: T.barOptions(),
            });
        }

        // 3. Category Distribution (Doughnut Chart)
        const categoryCtx = document.getElementById('categoryChart');
        if (categoryCtx && T) {
            window.pulseCharts.category = new Chart(categoryCtx, {
                type: 'doughnut',
                data: {
                    labels: chartData.categories.labels,
                    datasets: [T.arcDataset(chartData.categories.values, { type: 'doughnut' })],
                },
                options: T.arcOptions('doughnut'),
            });
        }

        // 4. Segment Analysis (Pie Chart)
        const segmentCtx = document.getElementById('segmentChart');
        if (segmentCtx && T) {
            window.pulseCharts.segment = new Chart(segmentCtx, {
                type: 'pie',
                data: {
                    labels: chartData.segments.labels,
                    datasets: [T.arcDataset(chartData.segments.values, {
                        type: 'pie',
                        colors: [T.C.indigo, T.C.purple, T.C.pink],
                    })],
                },
                options: T.arcOptions('pie', { tooltipLabel: T.percentTooltipLabel }),
            });
        }

        // Dynamic Filtering Core Logic
        function updateDashboardData() {
            const year = document.getElementById("yearFilter")?.value || "All";
            const region = document.getElementById("regionFilter")?.value || "All";
            const category = document.getElementById("categoryFilter")?.value || "All";
            const search = document.querySelector(".search-box input")?.value || "";

            const container = document.querySelector(".main-content");
            if (container) container.classList.add("loading-overlay");

            fetch(`/api/dashboard-data?year=${year}&region=${region}&category=${category}&search=${encodeURIComponent(search)}`)
                .then(res => res.json())
                .then(data => {
                    if (container) container.classList.remove("loading-overlay");

                    // 1. Update KPI metrics
                    document.getElementById("totalSalesVal").innerText = data.total_sales;
                    document.getElementById("totalOrdersVal").innerText = data.total_orders;
                    document.getElementById("totalProfitVal").innerText = data.total_profit;
                    document.getElementById("avgDiscountVal").innerText = data.avg_discount;

                    // 2. Update ML predictions
                    document.getElementById("mlForecastVal").innerText = data.forecast_value;
                    
                    const trendEl = document.getElementById("mlForecastTrend");
                    if (trendEl) {
                        trendEl.className = `trend ${data.trend_class}`;
                        trendEl.innerHTML = `<i class="fa-solid fa-arrow-trend-${data.trend_class}"></i> ${data.forecast_trend}`;
                    }
                    
                    document.getElementById("mlForecastAccuracy").innerText = data.forecast_accuracy;

                    // 3. Update Chart.js data
                    if (window.pulseCharts.monthly) {
                        window.pulseCharts.monthly.data.labels = data.months;
                        window.pulseCharts.monthly.data.datasets[0].data = data.month_values;
                        window.pulseCharts.monthly.update();
                    }

                    if (window.pulseCharts.region) {
                        window.pulseCharts.region.data.labels = data.regions;
                        window.pulseCharts.region.data.datasets[0].data = data.region_values;
                        window.pulseCharts.region.update();
                    }

                    if (window.pulseCharts.category) {
                        window.pulseCharts.category.data.labels = data.categories;
                        window.pulseCharts.category.data.datasets[0].data = data.category_values;
                        window.pulseCharts.category.update();
                    }

                    if (window.pulseCharts.segment) {
                        window.pulseCharts.segment.data.labels = data.segments;
                        window.pulseCharts.segment.data.datasets[0].data = data.segment_values;
                        window.pulseCharts.segment.update();
                    }

                    // 4. Update Top Performing Products table
                    const tbody = document.getElementById("topProductsBody");
                    if (tbody) {
                        tbody.innerHTML = "";
                        if (data.top_products.length === 0) {
                            tbody.innerHTML = `<tr><td colspan="4" style="text-align: center; color: var(--text-muted); padding: 24px;">No products found matching filters</td></tr>`;
                        } else {
                            data.top_products.forEach(p => {
                                const tr = document.createElement("tr");
                                tr.innerHTML = `
                                    <td>
                                        <div class="product-cell">
                                            <div class="product-icon"><i class="fa-solid fa-box"></i></div>
                                            <span>${p['Product Name']}</span>
                                        </div>
                                    </td>
                                    <td class="font-medium">${p.total_sales}</td>
                                    <td class="${p.profit_class} font-medium">${p.total_profit}</td>
                                    <td><span class="badge-success">In Stock</span></td>
                                `;
                                tbody.appendChild(tr);
                            });
                        }
                    }
                })
                .catch(err => {
                    if (container) container.classList.remove("loading-overlay");
                    console.error("Error updates: ", err);
                });
        }

        // Attach Select filters listeners
        const yearFilter = document.getElementById("yearFilter");
        const regionFilter = document.getElementById("regionFilter");
        const categoryFilter = document.getElementById("categoryFilter");

        if (yearFilter) yearFilter.addEventListener("change", updateDashboardData);
        if (regionFilter) regionFilter.addEventListener("change", updateDashboardData);
        if (categoryFilter) categoryFilter.addEventListener("change", updateDashboardData);

        // Attach Search input listener with 300ms debounce
        let searchDebounce;
        const mainSearch = document.querySelector(".search-box input");
        if (mainSearch) {
            mainSearch.addEventListener("input", function() {
                clearTimeout(searchDebounce);
                searchDebounce = setTimeout(updateDashboardData, 300);
            });
        }
    }


    // ==========================================
    // SYSTEM 2: DYNAMIC ANALYZER CHARTS
    // ==========================================

    if (typeof dynamicChartsData !== 'undefined' && Array.isArray(dynamicChartsData) && window.PulseChartTheme) {
        const T = PulseChartTheme;
        dynamicChartsData.forEach((chartConfig, index) => {
            const canvasEl = document.getElementById(chartConfig.id);
            if (!canvasEl) return;
            const instance = new Chart(canvasEl, {
                type: chartConfig.type,
                data: {
                    labels: chartConfig.labels,
                    datasets: [T.buildDynDataset(canvasEl, chartConfig, index)],
                },
                options: T.buildDynOptions(chartConfig.type),
            });
            window.dynChartInstances[chartConfig.id] = instance;
        });
    }

    // Analytics page charts
    if (window.PulseChartTheme) {
        PulseChartTheme.initAnalyticsCharts();
    }

    // ── Live filter AJAX for dynamic dashboard ─────────────────────────
    function updateDynamicDashboard() {
        const filterSelects = document.querySelectorAll('[data-filter-col]');
        if (!filterSelects.length) return;

        const params = new URLSearchParams();
        filterSelects.forEach(sel => {
            const colName = sel.getAttribute('data-filter-col');
            params.append(`filter_${colName}`, sel.value || 'All');
        });

        const mainContent = document.querySelector('.main-content');
        if (mainContent) mainContent.classList.add('loading-overlay');

        fetch(`/api/dynamic-dashboard-data?${params.toString()}`)
            .then(res => res.json())
            .then(data => {
                if (mainContent) mainContent.classList.remove('loading-overlay');
                if (!data.success) return;

                // 1. Update KPI cards
                (data.kpis || []).forEach(kpi => {
                    const el = document.getElementById(kpi.id);
                    if (el) el.innerText = kpi.value;
                });

                // 2. Update charts
                (data.charts || []).forEach((chartConfig, index) => {
                    const instance = window.dynChartInstances[chartConfig.id];
                    if (instance) {
                        instance.data.labels = chartConfig.labels;
                        instance.data.datasets[0].data = chartConfig.values;
                        instance.update();
                    }
                });

                // 3. Update top items table
                const tbody = document.getElementById('dynTopItemsBody');
                if (tbody && data.top_items) {
                    const total = data.top_items.reduce((s, i) => s + (i.raw || 0), 0);
                    tbody.innerHTML = data.top_items.map((item, idx) => {
                        const pct = total > 0 ? ((item.raw / total) * 100).toFixed(1) : 0;
                        return `
                        <tr>
                            <td><div class="badge-rank">${idx + 1}</div></td>
                            <td>
                                <div class="product-cell">
                                    <div class="product-icon"><i class="fa-solid fa-layer-group"></i></div>
                                    <span>${item.label}</span>
                                </div>
                            </td>
                            <td class="font-medium">${item.value}</td>
                            <td>
                                <div style="display:flex;align-items:center;gap:10px;">
                                    <div style="flex:1;height:6px;background:var(--border);border-radius:99px;overflow:hidden;">
                                        <div style="width:${pct}%;height:100%;background:var(--primary);border-radius:99px;"></div>
                                    </div>
                                    <span style="font-size:12px;color:var(--text-muted);min-width:36px;">${pct}%</span>
                                </div>
                            </td>
                        </tr>`;
                    }).join('');
                }

                // 4. Update ML Forecast
                if (data.forecast) {
                    const fVal = document.getElementById('dynForecastVal');
                    const fTrend = document.getElementById('dynForecastTrend');
                    const fAcc = document.getElementById('dynForecastAcc');
                    if (fVal) fVal.innerText = data.forecast.value;
                    if (fTrend) {
                        fTrend.className = `trend ${data.forecast.trend_class}`;
                        fTrend.innerHTML = `<i class="fa-solid fa-arrow-trend-${data.forecast.trend_class}"></i> ${data.forecast.trend}`;
                    }
                    if (fAcc) fAcc.innerText = data.forecast.accuracy;
                }

                // 5. Update AI insights
                const insightList = document.getElementById('dynInsightList');
                if (insightList && data.insights) {
                    insightList.innerHTML = data.insights.map(ins => `
                        <li class="insight-item">
                            <div class="insight-icon"><i class="fa-solid ${ins.icon}"></i></div>
                            <div class="insight-content">
                                <h4>${ins.title}</h4>
                                <h2>${ins.value}</h2>
                                <p>${ins.desc}</p>
                            </div>
                        </li>`).join('');
                }
            })
            .catch(err => {
                if (mainContent) mainContent.classList.remove('loading-overlay');
                console.error('Dynamic filter error:', err);
            });
    }

    // Attach filter change listeners
    document.querySelectorAll('[data-filter-col]').forEach(sel => {
        sel.addEventListener('change', updateDynamicDashboard);
    });

    // ==========================================
    // SYSTEM 3: INTERACTIVE HEADER ACTIONS
    // ==========================================
    const notificationsEl = document.querySelector('.notifications');
    const userInfoEl = document.querySelector('.user-info');

    if (notificationsEl || userInfoEl) {
        // Retrieve and Sync User Info
        const syncUserInfo = () => {
            const storedName = localStorage.getItem('admin_name') || 'Admin User';
            const storedRole = localStorage.getItem('admin_role') || 'Superadmin';
            const storedAvatar = localStorage.getItem('admin_avatar') || '/static/images/user_avatar.jpg';

            const nameEls = document.querySelectorAll('.user-info .details h4');
            const roleEls = document.querySelectorAll('.user-info .details p');
            const imgEls = document.querySelectorAll('.user-info img');

            nameEls.forEach(el => el.innerText = storedName);
            roleEls.forEach(el => el.innerText = storedRole);
            imgEls.forEach(el => el.src = storedAvatar);
        };

        syncUserInfo();

        // 1. Dynamic Notification Popover
        if (notificationsEl) {
            // Build the popover HTML dynamically
            const dropdown = document.createElement('div');
            dropdown.className = 'notifications-dropdown';
            dropdown.innerHTML = `
                <div class="notif-header">
                    <h4>Notifications</h4>
                    <button class="clear-notifs-btn">Mark all as read</button>
                </div>
                <div class="notif-list">
                    <div class="notif-item">
                        <div class="notif-icon success"><i class="fa-solid fa-circle-check"></i></div>
                        <div class="notif-content">
                            <p>Spark Session initialized successfully.</p>
                            <span>Just now</span>
                        </div>
                    </div>
                    <div class="notif-item">
                        <div class="notif-icon info"><i class="fa-solid fa-database"></i></div>
                        <div class="notif-content">
                            <p>Enriched sales dataset loaded. Total records: 29,982 rows.</p>
                            <span>5 minutes ago</span>
                        </div>
                    </div>
                    <div class="notif-item">
                        <div class="notif-icon warning"><i class="fa-solid fa-chart-line"></i></div>
                        <div class="notif-content">
                            <p>Linear Regression Sales forecasting model calibrated at 50% accuracy.</p>
                            <span>15 minutes ago</span>
                        </div>
                    </div>
                </div>
            `;
            notificationsEl.appendChild(dropdown);

            const badge = notificationsEl.querySelector('.badge');
            
            // Toggle notifications dropdown
            notificationsEl.addEventListener('click', function(e) {
                if (e.target.classList.contains('clear-notifs-btn')) {
                    if (badge) {
                        badge.style.display = 'none';
                    }
                    return;
                }
                dropdown.classList.toggle('active');
                e.stopPropagation();
            });

            // Close when clicking outside
            document.addEventListener('click', function(e) {
                if (!notificationsEl.contains(e.target)) {
                    dropdown.classList.remove('active');
                }
            });
        }

        // 2. Dynamic Edit Profile Modal
        if (userInfoEl) {
            // Create modal DOM structure
            const modal = document.createElement('div');
            modal.className = 'profile-modal';
            modal.innerHTML = `
                <div class="profile-card">
                    <div class="profile-card-header">
                        <h3>Edit Profile Details</h3>
                        <button class="close-btn">&times;</button>
                    </div>
                    <div class="profile-card-body">
                        <div class="form-group">
                            <label>Choose Preset Avatar</label>
                            <div class="avatar-selector">
                                <img src="/static/images/user_avatar.jpg" class="avatar-option" data-img="/static/images/user_avatar.jpg">
                                <img src="https://images.unsplash.com/photo-1494790108377-be9c29b29330?auto=format&fit=crop&w=150&h=150" class="avatar-option" data-img="https://images.unsplash.com/photo-1494790108377-be9c29b29330?auto=format&fit=crop&w=150&h=150">
                                <img src="https://images.unsplash.com/photo-1535713875002-d1d0cf377fde?auto=format&fit=crop&w=150&h=150" class="avatar-option" data-img="https://images.unsplash.com/photo-1535713875002-d1d0cf377fde?auto=format&fit=crop&w=150&h=150">
                                <img src="https://images.unsplash.com/photo-1570295999919-56ceb5ecca61?auto=format&fit=crop&w=150&h=150" class="avatar-option" data-img="https://images.unsplash.com/photo-1570295999919-56ceb5ecca61?auto=format&fit=crop&w=150&h=150">
                            </div>
                        </div>
                        <div class="form-group">
                            <label for="customAvatarFile">Or Upload Custom Avatar Image</label>
                            <input type="file" id="customAvatarFile" accept="image/*" style="padding: 6px 12px; font-size:12px;">
                        </div>
                        <div class="form-group">
                            <label for="editProfileName">Full Name</label>
                            <input type="text" id="editProfileName" value="Admin User">
                        </div>
                        <div class="form-group">
                            <label for="editProfileRole">Role / Position</label>
                            <select id="editProfileRole">
                                <option value="Superadmin">Superadmin</option>
                                <option value="Administrator">Administrator</option>
                                <option value="Data Analyst">Data Analyst</option>
                                <option value="Sales Manager">Sales Manager</option>
                            </select>
                        </div>
                    </div>
                    <div class="profile-card-footer">
                        <button class="btn-secondary cancel-btn">Cancel</button>
                        <button class="btn-primary save-btn">Save Changes</button>
                    </div>
                </div>
            `;
            document.body.appendChild(modal);

            let customAvatarDataUrl = '';

            // Open Modal
            userInfoEl.addEventListener('click', function(e) {
                const currentName = localStorage.getItem('admin_name') || 'Admin User';
                const currentRole = localStorage.getItem('admin_role') || 'Superadmin';
                const currentAvatar = localStorage.getItem('admin_avatar') || '/static/images/user_avatar.jpg';

                document.getElementById('editProfileName').value = currentName;
                document.getElementById('editProfileRole').value = currentRole;
                document.getElementById('customAvatarFile').value = '';
                customAvatarDataUrl = '';

                // Highlight avatar
                modal.querySelectorAll('.avatar-option').forEach(opt => {
                    if (opt.getAttribute('data-img') === currentAvatar) {
                        opt.classList.add('selected');
                    } else {
                        opt.classList.remove('selected');
                    }
                });

                modal.classList.add('active');
            });

            // Handle avatar selection
            modal.querySelectorAll('.avatar-option').forEach(opt => {
                opt.addEventListener('click', function() {
                    modal.querySelectorAll('.avatar-option').forEach(o => o.classList.remove('selected'));
                    opt.classList.add('selected');
                    customAvatarDataUrl = ''; // Clear custom file upload selection if preset is clicked
                });
            });

            // Handle file input upload
            const fileInput = modal.querySelector('#customAvatarFile');
            fileInput.addEventListener('change', function(e) {
                const file = e.target.files[0];
                if (file) {
                    const reader = new FileReader();
                    reader.onload = function(evt) {
                        customAvatarDataUrl = evt.target.result;
                        // Deselect preset avatars
                        modal.querySelectorAll('.avatar-option').forEach(o => o.classList.remove('selected'));
                    };
                    reader.readAsDataURL(file);
                }
            });

            // Close Modal
            const closeModal = () => modal.classList.remove('active');
            modal.querySelector('.close-btn').addEventListener('click', closeModal);
            modal.querySelector('.cancel-btn').addEventListener('click', closeModal);
            modal.addEventListener('click', function(e) {
                if (e.target === modal) closeModal();
            });

            // Save Changes
            modal.querySelector('.save-btn').addEventListener('click', function() {
                const newName = document.getElementById('editProfileName').value.trim() || 'Admin User';
                const newRole = document.getElementById('editProfileRole').value || 'Superadmin';
                
                let newAvatar = '';
                if (customAvatarDataUrl) {
                    newAvatar = customAvatarDataUrl;
                } else {
                    const selectedAvatarEl = modal.querySelector('.avatar-option.selected');
                    newAvatar = selectedAvatarEl ? selectedAvatarEl.getAttribute('data-img') : '/static/images/user_avatar.jpg';
                }

                localStorage.setItem('admin_name', newName);
                localStorage.setItem('admin_role', newRole);
                localStorage.setItem('admin_avatar', newAvatar);

                syncUserInfo();
                closeModal();
            });
        }
    }

    // ==========================================
    // SYSTEM 4: REPORTS CENTER ACTIONS
    // ==========================================
    const btnExportPdf = document.getElementById('btnExportPdf');
    const btnExportExcel = document.getElementById('btnExportExcel');
    const btnGenerateForecast = document.getElementById('btnGenerateForecast');
    const btnViewDatasetSummary = document.getElementById('btnViewDatasetSummary');

    // Helper to download files dynamically
    const downloadFile = (url, button, originalText) => {
        if (button) {
            button.disabled = true;
            button.innerHTML = `<i class="fa-solid fa-circle-notch fa-spin"></i> Exporting...`;
        }
        
        window.location.href = url;
        
        setTimeout(() => {
            if (button) {
                button.disabled = false;
                button.innerHTML = originalText;
            }
        }, 3000);
    };

    if (btnExportPdf) {
        btnExportPdf.addEventListener('click', function() {
            downloadFile('/reports/export/pdf', btnExportPdf, 'Export PDF');
        });
    }

    if (btnExportExcel) {
        btnExportExcel.addEventListener('click', function() {
            downloadFile('/reports/export/excel', btnExportExcel, 'Export Excel');
        });
    }

    if (btnGenerateForecast) {
        btnGenerateForecast.addEventListener('click', function() {
            downloadFile('/reports/generate/forecast', btnGenerateForecast, 'Generate');
        });
    }

    // Dataset Modal logic
    const datasetModal = document.getElementById('datasetSummaryModal');
    if (btnViewDatasetSummary && datasetModal) {
        const closeBtn = document.getElementById('closeDatasetModal');
        const closeBtn2 = document.getElementById('closeDatasetModalBtn');
        const loadingEl = document.getElementById('datasetLoading');
        const contentEl = document.getElementById('datasetContent');
        
        const openModal = () => datasetModal.classList.add('active');
        const closeModal = () => datasetModal.classList.remove('active');
        
        [closeBtn, closeBtn2].forEach(btn => {
            if (btn) btn.addEventListener('click', closeModal);
        });
        
        // Tab switching
        const tabBtns = datasetModal.querySelectorAll('.dataset-tab-btn');
        const tabContents = datasetModal.querySelectorAll('.dataset-tab-content');
        
        tabBtns.forEach(btn => {
            btn.addEventListener('click', function() {
                const targetTab = this.getAttribute('data-tab');
                
                tabBtns.forEach(b => b.classList.remove('active'));
                tabContents.forEach(c => c.classList.remove('active'));
                
                this.classList.add('active');
                const targetEl = document.getElementById(targetTab);
                if (targetEl) targetEl.classList.add('active');
            });
        });

        btnViewDatasetSummary.addEventListener('click', function() {
            openModal();
            
            // Show loading, hide content
            loadingEl.style.display = 'flex';
            contentEl.style.display = 'none';
            
            fetch('/api/reports/dataset-summary')
                .then(res => res.json())
                .then(data => {
                    if (!data.success) {
                        alert("Failed to compute dataset summary statistics.");
                        closeModal();
                        return;
                    }
                    
                    // Render meta info
                    document.getElementById('datasetTotalRows').innerText = data.rows.toLocaleString();
                    document.getElementById('datasetTotalCols').innerText = data.cols_count.toLocaleString();
                    
                    // Render Descriptive statistics
                    const descBody = document.getElementById('tableDescriptiveBody');
                    descBody.innerHTML = '';
                    data.desc_stats.forEach(stat => {
                        const tr = document.createElement('tr');
                        tr.innerHTML = `
                            <td class="font-medium" style="text-align: left;">${stat.column}</td>
                            <td>${parseInt(stat.count).toLocaleString()}</td>
                            <td>${stat.mean}</td>
                            <td>${stat.stddev}</td>
                            <td>${stat.min}</td>
                            <td>${stat.max}</td>
                            <td class="${stat.null_count > 0 ? 'text-danger' : 'text-green'} font-medium">${stat.null_count.toLocaleString()}</td>
                        `;
                        descBody.appendChild(tr);
                    });
                    
                    // Render Schema details
                    const schemaBody = document.getElementById('tableSchemaBody');
                    schemaBody.innerHTML = '';
                    data.schema.forEach(field => {
                        const tr = document.createElement('tr');
                        tr.innerHTML = `
                            <td class="font-medium" style="text-align: left;">${field.name}</td>
                            <td style="text-align: left;"><code style="background: var(--bg-main); padding: 2px 6px; border-radius: 4px; font-size: 12px; color: var(--primary);">${field.type}</code></td>
                        `;
                        schemaBody.appendChild(tr);
                    });
                    
                    // Hide loading, show content
                    loadingEl.style.display = 'none';
                    contentEl.style.display = 'block';
                })
                .catch(err => {
                    console.error("Error loading dataset summary:", err);
                    alert("An error occurred while calling the Spark analytics engine.");
                    closeModal();
                });
        });
    }
});