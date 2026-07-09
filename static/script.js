/*
   Cinema Scale - Interactive Script
   Theme switching logic, dynamic button injection, and responsive Chart.js initialization.
*/

(function () {
    'use strict';

    // Array to track active chart instances for dynamic theme updates
    const activeCharts = [];

    // ==========================================
    // 1. Theme Configuration & Helpers
    // ==========================================

    /**
     * Get theme color values matching current active body theme state
     * Adapts dynamically for dark/light mode updates
     */
    function getThemeColors() {
        const isLight = document.body.classList.contains('light-theme');
        return {
            grid: isLight ? 'rgba(15, 23, 42, 0.08)' : 'rgba(255, 255, 255, 0.08)',
            text: isLight ? '#64748b' : '#8e95b3',
            pointLabel: isLight ? '#0f172a' : '#ffffff',
            accentGold: isLight ? '#ff6b6b' : '#ffcc00', // Light: coral pink, Dark: neon gold
            accentPurple: isLight ? '#00b4d8' : '#8a2be2', // Light: teal, Dark: electric purple
            accentPurpleLight: isLight ? 'rgba(0, 180, 216, 0.2)' : 'rgba(138, 43, 226, 0.2)',
            accentGoldLight: isLight ? 'rgba(255, 107, 107, 0.2)' : 'rgba(255, 204, 0, 0.2)',
            accentPurpleSolid: isLight ? 'rgba(0, 180, 216, 0.8)' : 'rgba(138, 43, 226, 0.8)',
            accentGoldSolid: isLight ? 'rgba(255, 107, 107, 0.8)' : 'rgba(255, 204, 0, 0.8)',
            whiteTransparent: isLight ? 'rgba(15, 23, 42, 0.03)' : 'rgba(255, 255, 255, 0.02)'
        };
    }

    /**
     * Initializes theme preferences on page load
     */
    function initTheme() {
        const savedTheme = localStorage.getItem('theme');
        const systemPrefersLight = window.matchMedia('(prefers-color-scheme: light)').matches;

        // Apply light theme if selected previously
        if (savedTheme === 'light' || (!savedTheme && systemPrefersLight)) {
            document.body.classList.add('light-theme');
            // Adjust bootstrap default classes on body if present
            document.body.classList.remove('bg-light');
        } else {
            document.body.classList.remove('light-theme');
            document.body.classList.remove('bg-light');
        }

        injectThemeToggle();
    }

    /**
     * Injects a floating theme toggle button dynamically if not present in the HTML markup
     */
    function injectThemeToggle() {
        let toggleBtn = document.querySelector('.theme-toggle');
        if (!toggleBtn) {
            toggleBtn = document.createElement('button');
            toggleBtn.className = 'theme-toggle btn rounded-circle d-flex align-items-center justify-content-center';
            toggleBtn.setAttribute('aria-label', 'Toggle theme mode');
            document.body.appendChild(toggleBtn);
        }

        updateToggleIcon(toggleBtn);

        // Add event listener
        toggleBtn.addEventListener('click', function () {
            // Apply a temporary transition class to body to prevent messy styling flashes
            document.body.style.transition = 'background-color 0.5s ease, color 0.3s ease';
            
            const isLight = document.body.classList.toggle('light-theme');
            localStorage.setItem('theme', isLight ? 'light' : 'dark');

            updateToggleIcon(toggleBtn);
            updateAllCharts();

            // Clear temporary transition style after completion
            setTimeout(() => {
                document.body.style.transition = '';
            }, 600);
        });
    }

    /**
     * Updates toggle button icon based on current theme state
     */
    function updateToggleIcon(btn) {
        const isLight = document.body.classList.contains('light-theme');
        btn.innerHTML = isLight 
            ? '<i class="bi bi-moon-stars-fill"></i>' 
            : '<i class="bi bi-sun-fill"></i>';
    }

    // ==========================================
    // 2. Chart.js Dynamic Loader & Renderer
    // ==========================================

    /**
     * Loads Chart.js CDN dynamically if it is not present, then runs chart initializations
     */
    function loadChartJS(callback) {
        if (window.Chart) {
            callback();
            return;
        }

        const script = document.createElement('script');
        script.src = 'https://cdn.jsdelivr.net/npm/chart.js';
        script.async = true;
        script.onload = () => {
            callback();
        };
        document.head.appendChild(script);
    }

    /**
     * Initializes loaded chart configurations on canvas components
     */
    function initAllCharts() {
        const movieChartCanvas = document.getElementById('movieChart');
        const genreChartCanvas = document.getElementById('genreChart');
        const userChartCanvas = document.getElementById('userChart');

        const colors = getThemeColors();

        // 1. Target Movie Critique or Rating Chart (Present in movie_info.html and admin.html)
        if (movieChartCanvas) {
            const isAdminPage = !!document.getElementById('admin-main-content');
            
            if (isAdminPage) {
                // Admin Page - Movie Rating Distribution (Bar Chart)
                const ctx = movieChartCanvas.getContext('2d');
                const movieChartInstance = new Chart(ctx, {
                    type: 'bar',
                    data: {
                        labels: ['1-3 ★', '4-5 ★', '6-7 ★', '8-9 ★', '10 ★'],
                        datasets: [{
                            label: 'Number of Movies',
                            data: [45, 120, 480, 650, 125],
                            backgroundColor: colors.accentPurpleSolid,
                            borderColor: colors.accentPurple,
                            borderWidth: 1.5,
                            borderRadius: 6
                        }]
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        plugins: {
                            legend: { display: false }
                        },
                        scales: {
                            x: {
                                grid: { color: colors.grid },
                                ticks: { color: colors.text }
                            },
                            y: {
                                grid: { color: colors.grid },
                                ticks: { color: colors.text }
                            }
                        }
                    }
                });
                activeCharts.push(movieChartInstance);
            } else {
                // Movie Info Page - Critique Radar Chart
                const ctx = movieChartCanvas.getContext('2d');
                const critiqueChartInstance = new Chart(ctx, {
                    type: 'radar',
                    data: {
                        labels: ['Plot Integrity', 'Acting & Casting', 'Visual Production', 'Sound & Music', 'Pacing & Flow'],
                        datasets: [
                            {
                                label: 'Critique Scores (This Movie)',
                                data: [9.2, 8.8, 9.5, 8.0, 9.0],
                                borderColor: colors.accentGold,
                                backgroundColor: colors.accentPurpleLight,
                                pointBackgroundColor: colors.accentGold,
                                pointBorderColor: '#ffffff',
                                pointHoverBackgroundColor: '#ffffff',
                                pointHoverBorderColor: colors.accentGold,
                                borderWidth: 2.5
                            },
                            {
                                label: 'Platform Average',
                                data: [7.5, 7.8, 8.0, 7.2, 7.9],
                                borderColor: colors.accentPurple,
                                backgroundColor: 'rgba(255, 255, 255, 0.01)',
                                pointBackgroundColor: colors.accentPurple,
                                pointBorderColor: '#ffffff',
                                pointHoverBackgroundColor: '#ffffff',
                                pointHoverBorderColor: colors.accentPurple,
                                borderWidth: 1.5,
                                borderDash: [5, 5]
                            }
                        ]
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        plugins: {
                            legend: {
                                labels: { color: colors.pointLabel, font: { family: 'Outfit', size: 11 } }
                            }
                        },
                        scales: {
                            r: {
                                grid: { color: colors.grid },
                                angleLines: { color: colors.grid },
                                pointLabels: {
                                    color: colors.pointLabel,
                                    font: { family: 'Outfit', size: 11, weight: 'bold' }
                                },
                                ticks: {
                                    color: colors.text,
                                    backdropColor: 'transparent',
                                    showLabelBackdrop: false
                                },
                                min: 0,
                                max: 10
                            }
                        }
                    }
                });
                activeCharts.push(critiqueChartInstance);
            }
        }

        // 2. Admin Page - Genre Popularity (Doughnut Chart)
        if (genreChartCanvas) {
            const ctx = genreChartCanvas.getContext('2d');
            const genreChartInstance = new Chart(ctx, {
                type: 'doughnut',
                data: {
                    labels: ['Sci-Fi', 'Drama', 'Action', 'Comedy', 'Thriller'],
                    datasets: [{
                        data: [35, 20, 25, 12, 8],
                        backgroundColor: [
                            '#8a2be2', // purple
                            '#ff6b6b', // coral pink
                            '#00b4d8', // teal
                            '#ffcc00', // sunny gold
                            '#a04ef6'  // magenta
                        ],
                        borderWidth: 0
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: {
                            position: 'right',
                            labels: { color: colors.pointLabel, font: { family: 'Outfit', size: 10 } }
                        }
                    },
                    cutout: '70%'
                }
            });
            activeCharts.push(genreChartInstance);
        }

        // 3. Admin Page - User Registrations over last 7 Days (Line Chart)
        if (userChartCanvas) {
            const ctx = userChartCanvas.getContext('2d');
            const userChartInstance = new Chart(ctx, {
                type: 'line',
                data: {
                    labels: ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'],
                    datasets: [{
                        label: 'Sessions',
                        data: [150, 240, 190, 310, 280, 420, 480],
                        borderColor: colors.accentPurple,
                        backgroundColor: colors.accentPurpleLight,
                        fill: true,
                        tension: 0.4,
                        borderWidth: 2,
                        pointBackgroundColor: colors.accentPurple
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: { display: false }
                    },
                    scales: {
                        x: {
                            grid: { color: colors.grid },
                            ticks: { color: colors.text }
                        },
                        y: {
                            grid: { color: colors.grid },
                            ticks: { color: colors.text }
                        }
                    }
                }
            });
            activeCharts.push(userChartInstance);
        }
    }

    /**
     * Redraws and updates configurations of all initialized active charts on theme changes
     */
    function updateAllCharts() {
        const colors = getThemeColors();

        activeCharts.forEach(chart => {
            // Update Legend label colors
            if (chart.options.plugins && chart.options.plugins.legend && chart.options.plugins.legend.labels) {
                chart.options.plugins.legend.labels.color = colors.pointLabel;
            }

            if (chart.config.type === 'radar') {
                // Update Radar axes scales
                chart.options.scales.r.grid.color = colors.grid;
                chart.options.scales.r.angleLines.color = colors.grid;
                chart.options.scales.r.pointLabels.color = colors.pointLabel;
                chart.options.scales.r.ticks.color = colors.text;

                // Dataset colors
                chart.data.datasets[0].borderColor = colors.accentGold;
                chart.data.datasets[0].backgroundColor = colors.accentPurpleLight;
                chart.data.datasets[0].pointBackgroundColor = colors.accentGold;
                chart.data.datasets[0].pointHoverBorderColor = colors.accentGold;

                chart.data.datasets[1].borderColor = colors.accentPurple;
                chart.data.datasets[1].pointBackgroundColor = colors.accentPurple;
                chart.data.datasets[1].pointHoverBorderColor = colors.accentPurple;
            } else {
                // Update Cartesian scales (Bar, Line charts)
                if (chart.options.scales) {
                    if (chart.options.scales.x) {
                        chart.options.scales.x.grid.color = colors.grid;
                        chart.options.scales.x.ticks.color = colors.text;
                    }
                    if (chart.options.scales.y) {
                        chart.options.scales.y.grid.color = colors.grid;
                        chart.options.scales.y.ticks.color = colors.text;
                    }
                }

                // Update specific datasets colors for Light/Dark adaptation
                if (chart.config.type === 'bar') {
                    chart.data.datasets[0].backgroundColor = colors.accentPurpleSolid;
                    chart.data.datasets[0].borderColor = colors.accentPurple;
                } else if (chart.config.type === 'line') {
                    chart.data.datasets[0].borderColor = colors.accentPurple;
                    chart.data.datasets[0].backgroundColor = colors.accentPurpleLight;
                    chart.data.datasets[0].pointBackgroundColor = colors.accentPurple;
                } else if (chart.config.type === 'doughnut') {
                    // Update label color in doughnut
                    chart.options.plugins.legend.labels.color = colors.pointLabel;
                }
            }
            chart.update();
        });
    }

    // ==========================================
    // 3. Document Initialization Entrypoint
    // ==========================================

    document.addEventListener('DOMContentLoaded', function () {
        initTheme();

        // Check if any canvas element exists on the page before loading the heavy Chart.js library
        const hasCanvas = !!(
            document.getElementById('movieChart') || 
            document.getElementById('genreChart') || 
            document.getElementById('userChart')
        );

        if (hasCanvas) {
            loadChartJS(initAllCharts);
        }
    });

})();
