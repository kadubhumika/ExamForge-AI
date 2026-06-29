let _assignmentId = null;

window.onload = function () {
    if (!requireAuth()) return;
    fillSharedChrome();

    const params = new URLSearchParams(window.location.search);
    _assignmentId = params.get("id");

    if (!_assignmentId) {
        document.getElementById("loadingState").innerHTML =
            `<p class="text-sm text-red-400">No assignment ID provided.</p>`;
        return;
    }

    loadResults();
};

async function loadResults() {
    try {
        const res = await apiFetch(`/evaluations/${_assignmentId}/results`, { headers: authHeaders() });
        const data = await res.json();

        document.getElementById("resultsTitle").innerText = data.assignment_title || "Results";
        document.getElementById("statTotal").innerText = data.total_students;
        document.getElementById("statAvg").innerText = `${data.class_average}%`;

        const results = data.results || [];
        const topScore = results.length > 0 ? results[0].percentage : 0;
        document.getElementById("statTop").innerText = `${topScore}%`;

        document.getElementById("loadingState").classList.add("hidden");

        if (results.length === 0) {
            document.getElementById("resultsTable").classList.remove("hidden");
            document.getElementById("tableBody").innerHTML =
                `<tr><td colspan="10" class="text-center py-8 text-gray-400 text-xs">No results yet</td></tr>`;
            return;
        }

        // Build dynamic question columns from first result
        const firstScores = results[0].scores_json || {};
        const questionKeys = Object.keys(firstScores).sort((a, b) => {
            const na = parseInt(a.replace("Q", ""));
            const nb = parseInt(b.replace("Q", ""));
            return na - nb;
        });

        // Table header
        document.getElementById("tableHead").innerHTML = `
            <tr>
                <th class="px-4 py-3 text-left font-bold text-[11px] uppercase tracking-wide">Rank</th>
                <th class="px-4 py-3 text-left font-bold text-[11px] uppercase tracking-wide">Student Name</th>
                ${questionKeys.map(q => {
                    const maxQ = firstScores[q]?.max || "?";
                    return `<th class="px-3 py-3 text-center font-bold text-[11px] uppercase tracking-wide">${q}<br><span class="text-[9px] opacity-60">/${maxQ}</span></th>`;
                }).join("")}
                <th class="px-4 py-3 text-center font-bold text-[11px] uppercase tracking-wide">Total</th>
                <th class="px-4 py-3 text-center font-bold text-[11px] uppercase tracking-wide">%</th>
            </tr>
        `;

        const rankColors = ["bg-yellow-50", "bg-gray-50", "bg-orange-50"];

        document.getElementById("tableBody").innerHTML = results.map((r, i) => {
            const scores = r.scores_json || {};
            const bgClass = i < 3 ? rankColors[i] : (i % 2 === 0 ? "bg-white" : "bg-[#FAFAFA]");
            const rankBadge = i === 0 ? "🥇" : i === 1 ? "🥈" : i === 2 ? "🥉" : `${i + 1}`;
            const pctColor = r.percentage >= 75 ? "text-green-600" : r.percentage >= 50 ? "text-amber-600" : "text-red-500";

            return `
                <tr class="${bgClass} hover:bg-blue-50/30 transition cursor-pointer" onclick="toggleDetails('detail-${i}')">
                    <td class="px-4 py-3 text-center font-bold">${rankBadge}</td>
                    <td class="px-4 py-3 font-semibold text-[#1A1A1A]">${r.student_name}</td>
                    ${questionKeys.map(q => {
                        const awarded = scores[q]?.awarded ?? "-";
                        const max = scores[q]?.max ?? "-";
                        const isGood = awarded >= max * 0.75;
                        const colorClass = isGood ? "text-green-600" : awarded < max * 0.5 ? "text-red-500" : "text-amber-600";
                        return `<td class="px-3 py-3 text-center font-bold ${colorClass}">${awarded}</td>`;
                    }).join("")}
                    <td class="px-4 py-3 text-center font-black text-[#1A1A1A]">${r.total_marks}/${r.max_marks}</td>
                    <td class="px-4 py-3 text-center font-black ${pctColor}">${r.percentage}%</td>
                </tr>
                <tr id="detail-${i}" class="hidden">
                    <td colspan="${questionKeys.length + 4}" class="px-6 py-4 bg-blue-50/30">
                        <div class="flex flex-col gap-2">
                            <p class="text-xs font-bold text-[#1A1A1A] mb-1">Question-wise feedback for ${r.student_name}:</p>
                            ${questionKeys.map(q => {
                                const qData = scores[q] || {};
                                return `
                                    <div class="bg-white rounded-xl px-4 py-2.5 border border-[#E5E7EB]">
                                        <div class="flex items-center justify-between mb-1">
                                            <span class="text-xs font-bold text-[#1A1A1A]">${q} — ${qData.awarded ?? 0}/${qData.max ?? 0} marks</span>
                                        </div>
                                        <p class="text-[11px] text-gray-500">${qData.reason || "No feedback"}</p>
                                    </div>
                                `;
                            }).join("")}
                        </div>
                    </td>
                </tr>
            `;
        }).join("");

        document.getElementById("resultsTable").classList.remove("hidden");

    } catch (e) {
        document.getElementById("loadingState").innerHTML =
            `<p class="text-sm text-red-400">Could not load results: ${e.message}</p>`;
    }
}

function toggleDetails(id) {
    const row = document.getElementById(id);
    if (row) row.classList.toggle("hidden");
}

async function downloadResultsPdf() {
    try {
        const res = await apiFetch(`/evaluations/${_assignmentId}/download-results`, { headers: authHeaders() });
        const blob = await res.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = "results.pdf";
        document.body.appendChild(a);
        a.click();
        a.remove();
        window.URL.revokeObjectURL(url);
    } catch (e) {
        alert(`Could not download: ${e.message}`);
    }
}