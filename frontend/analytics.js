let _teacherChart = null;
let _myChart = null;

window.onload = function () {
    if (!requireAuth()) return;
    fillSharedChrome();
    loadSchoolAnalytics();
    loadMyAnalytics();
};

async function loadSchoolAnalytics() {
    try {
        const res = await apiFetch("/analytics/school", { headers: authHeaders() });
        const data = await res.json();

        document.getElementById("schoolTitle").innerText = `🏫 ${data.school_name || "Your School"}`;
        document.getElementById("statTeachers").innerText = data.total_teachers || 0;
        document.getElementById("statAssignments").innerText = data.total_assignments || 0;
        document.getElementById("statEvaluations").innerText = data.total_evaluations || 0;

        const teachers = data.teachers || [];

        renderTeacherList(teachers);
        renderTeacherChart(teachers);

    } catch (e) {
        document.getElementById("schoolTitle").innerText = "Could not load school data";
        console.error(e.message);
    }
}

function renderTeacherList(teachers) {
    const container = document.getElementById("teacherList");
    if (teachers.length === 0) {
        container.innerHTML = `<p class="text-xs text-gray-400 text-center py-6">No data yet — evaluate some students first</p>`;
        return;
    }

    const medals = ["🥇", "🥈", "🥉"];
    container.innerHTML = teachers.map((t, i) => {
        const pctColor = t.average_marks_percentage >= 75
            ? "text-green-600 bg-green-50"
            : t.average_marks_percentage >= 50
            ? "text-amber-600 bg-amber-50"
            : "text-red-500 bg-red-50";

        return `
            <div class="flex items-center gap-3 bg-[#F9FAFB] border border-[#E5E7EB] rounded-xl px-4 py-3">
                <span class="text-lg shrink-0">${medals[i] || `${i + 1}.`}</span>
                <div class="flex-1 min-w-0">
                    <p class="text-xs font-bold text-[#1A1A1A] truncate">${t.teacher_name}</p>
                    <p class="text-[11px] text-gray-400">${t.total_assignments} assignments · ${t.total_students_evaluated} students graded</p>
                </div>
                <span class="text-xs font-black px-2.5 py-1 rounded-lg ${pctColor}">${t.average_marks_percentage}%</span>
            </div>
        `;
    }).join("");
}

function renderTeacherChart(teachers) {
    const ctx = document.getElementById("teacherChart").getContext("2d");
    if (_teacherChart) _teacherChart.destroy();

    if (teachers.length === 0) {
        ctx.canvas.style.display = "none";
        return;
    }

    _teacherChart = new Chart(ctx, {
        type: "bar",
        data: {
            labels: teachers.map(t => t.teacher_name),
            datasets: [{
                label: "Avg Marks %",
                data: teachers.map(t => t.average_marks_percentage),
                backgroundColor: teachers.map(t =>
                    t.average_marks_percentage >= 75
                        ? "rgba(74, 222, 128, 0.7)"
                        : t.average_marks_percentage >= 50
                        ? "rgba(251, 191, 36, 0.7)"
                        : "rgba(248, 113, 113, 0.7)"
                ),
                borderColor: teachers.map(t =>
                    t.average_marks_percentage >= 75
                        ? "#16a34a"
                        : t.average_marks_percentage >= 50
                        ? "#d97706"
                        : "#dc2626"
                ),
                borderWidth: 1.5,
                borderRadius: 8,
            }]
        },
        options: {
            responsive: true,
            plugins: {
                legend: { display: false },
                tooltip: {
                    callbacks: {
                        label: ctx => `Average: ${ctx.parsed.y}%`
                    }
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    max: 100,
                    ticks: { callback: v => `${v}%`, font: { size: 10 } },
                    grid: { color: "#F3F4F6" }
                },
                x: {
                    ticks: { font: { size: 10 } },
                    grid: { display: false }
                }
            }
        }
    });
}

async function loadMyAnalytics() {
    try {
        const res = await apiFetch("/analytics/teacher", { headers: authHeaders() });
        const data = await res.json();

        const assignments = data.assignments || [];
        if (assignments.length === 0) return;

        const ctx = document.getElementById("myChart").getContext("2d");
        if (_myChart) _myChart.destroy();

        _myChart = new Chart(ctx, {
            type: "line",
            data: {
                labels: assignments.map(a => a.assignment_title.substring(0, 20)),
                datasets: [{
                    label: "Class Average %",
                    data: assignments.map(a => a.average_percentage),
                    borderColor: "#E76F51",
                    backgroundColor: "rgba(231, 111, 81, 0.1)",
                    tension: 0.4,
                    fill: true,
                    pointBackgroundColor: "#D05230",
                    pointRadius: 5,
                }]
            },
            options: {
                responsive: true,
                plugins: {
                    legend: { display: false },
                    tooltip: {
                        callbacks: {
                            label: ctx => `Avg: ${ctx.parsed.y}% (${assignments[ctx.dataIndex]?.total_students || 0} students)`
                        }
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        max: 100,
                        ticks: { callback: v => `${v}%`, font: { size: 10 } },
                        grid: { color: "#F3F4F6" }
                    },
                    x: {
                        ticks: { font: { size: 10 }, maxRotation: 30 },
                        grid: { display: false }
                    }
                }
            }
        });

    } catch (e) {
        console.error("My analytics error:", e.message);
    }
}