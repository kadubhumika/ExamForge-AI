let _assignmentId = null;
let _pollHandle = null;

window.onload = function () {
    if (!requireAuth()) return;
    fillSharedChrome();

    const params = new URLSearchParams(window.location.search);
    _assignmentId = params.get("id");

    if (!_assignmentId) {
        showErrorState("No assignment ID provided.");
        return;
    }

    pollStatus();
    _pollHandle = setInterval(pollStatus, 2000);
};

async function pollStatus() {
    try {
        const res = await apiFetch(`/assignments/${_assignmentId}/status`, {
            method: "GET",
            headers: authHeaders()
        });
        const data = await res.json();

        if (data.status === "DONE") {
            clearInterval(_pollHandle);
            await loadResult();
        } else if (data.status === "FAILED") {
            clearInterval(_pollHandle);
            showErrorState(data.error_message || "The AI could not generate this paper. Please try again.");
        } else if (data.status === "PROCESSING") {
            document.getElementById("loadingText").innerText = "AI is writing your questions…";
        } else {
            document.getElementById("loadingText").innerText = "Queued for generation…";
        }
    } catch (e) {
        console.warn("Status poll failed:", e.message);
    }
}

async function loadResult() {
    try {
        const res = await apiFetch(`/assignments/${_assignmentId}/result`, {
            method: "GET",
            headers: authHeaders()
        });
        const data = await res.json();
        renderPaper(data.title, data.structured_json);

        document.getElementById("loadingState").classList.add("hidden");
        document.getElementById("resultState").classList.remove("hidden");
    } catch (e) {
        showErrorState(e.message);
    }
}

function showErrorState(message) {
    document.getElementById("loadingState").classList.add("hidden");
    document.getElementById("resultState").classList.add("hidden");
    document.getElementById("errorState").classList.remove("hidden");
    document.getElementById("errorMessage").innerText = message;
}

function escapeHtml(str) {
    const div = document.createElement("div");
    div.innerText = str ?? "";
    return div.innerHTML;
}

function renderPaper(title, paper) {
    const schoolName = localStorage.getItem("school_name") || "School";
    const userName = localStorage.getItem("user_name") || "Teacher";

    document.getElementById("resultIntro").innerHTML =
        `Here's your AI-generated <span class="underline decoration-[#E76F51] underline-offset-4">Question Paper</span> for "${escapeHtml(title)}"`;

    const sections = paper.sections || [];

    let sectionsHtml = "";
    let answerKeyHtml = "";

    sections.forEach((section, sIdx) => {
        const sectionLabel = section.section_name || `Section ${String.fromCharCode(65 + sIdx)}`;

        sectionsHtml += `
            <div class="mt-4">
                <h3 class="text-center font-bold text-base tracking-wide border-b-2 border-gray-800 max-w-fit mx-auto px-4 pb-0.5 mb-5">${escapeHtml(sectionLabel)}</h3>
                ${section.section_instructions ? `<p class="text-[11px] text-gray-500 italic mb-3 text-center">${escapeHtml(section.section_instructions)}</p>` : ""}
                <ol class="flex flex-col gap-3.5 mt-2 text-xs font-medium text-gray-800 tracking-normal leading-relaxed">
                    ${(section.questions || []).map(q => `
                        <li class="flex items-start gap-2">
                            <span>${q.question_number}.</span>
                            <span>
                                ${q.difficulty ? `<strong class="font-bold text-gray-500">[${escapeHtml(q.difficulty)}]</strong> ` : ""}
                                ${escapeHtml(q.question_text)}
                                <strong> [${q.marks} Marks]</strong>
                                ${(q.options && q.options.length) ? `
                                    <div class="mt-1.5 flex flex-wrap gap-x-4 gap-y-1 text-gray-600">
                                        ${q.options.map((opt, i) => `<span>(${String.fromCharCode(97 + i)}) ${escapeHtml(opt)}</span>`).join("")}
                                    </div>` : ""}
                            </span>
                        </li>
                    `).join("")}
                </ol>
            </div>
        `;

        answerKeyHtml += `
            <div class="flex flex-col gap-3 mt-4">
                <h4 class="text-xs font-extrabold uppercase tracking-wide text-gray-800">${escapeHtml(sectionLabel)}</h4>
                ${(section.questions || []).map(q => `
                    <div class="flex items-start gap-2.5">
                        <span class="font-bold text-[#1A1A1A]">${q.question_number}.</span>
                        <p class="text-xs text-gray-700 leading-relaxed">${escapeHtml(q.answer)}</p>
                    </div>
                `).join("")}
            </div>
        `;
    });

    const sheet = document.getElementById("paperSheet");
    sheet.innerHTML = `
        <div class="text-center flex flex-col gap-1 border-b border-gray-100 pb-4">
            <h2 class="text-xl font-extrabold tracking-tight">${escapeHtml(schoolName)}</h2>
            <h3 class="text-sm font-bold text-gray-700">Subject: ${escapeHtml(paper.subject || title)}</h3>
            ${paper.class_level ? `<p class="text-xs font-semibold text-gray-500">Class: ${escapeHtml(paper.class_level)}</p>` : ""}
        </div>

        <div class="flex justify-between items-center text-xs font-bold text-gray-800 border-b border-dashed border-gray-100 pb-2">
            <span>Time Allowed: ${paper.time_allowed_minutes || "—"} minutes</span>
            <span>Maximum Marks: ${paper.total_marks || "—"}</span>
        </div>

        <p class="text-xs italic font-medium text-gray-600 -mt-2">All questions are compulsory unless stated otherwise.</p>

        <div class="grid grid-cols-1 sm:grid-cols-2 gap-3 max-w-md text-xs font-bold text-gray-700 mt-1">
            <div class="flex items-center gap-1">
                <span>Name:</span>
                <div class="flex-1 border-b border-gray-400 min-w-[150px] h-4"></div>
            </div>
            <div class="flex items-center gap-1">
                <span>Roll Number:</span>
                <div class="flex-1 border-b border-gray-400 min-w-[100px] h-4"></div>
            </div>
        </div>

        ${sectionsHtml}

        <p class="text-center font-bold text-[11px] tracking-wider text-gray-400 uppercase mt-6 select-none">— End of Question Paper —</p>

        <div class="mt-6 pt-6 border-t border-gray-200">
            <h3 class="text-sm font-black text-[#1A1A1A] mb-4 tracking-tight flex items-center gap-1.5">
                <span>🔑</span> Answer Key
            </h3>
            ${answerKeyHtml}
        </div>
    `;
}

async function downloadPdf() {
    try {
        const res = await apiFetch(`/assignments/${_assignmentId}/download`, {
            method: "GET",
            headers: authHeaders()
        });
        const blob = await res.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = "assignment.pdf";
        document.body.appendChild(a);
        a.click();
        a.remove();
        window.URL.revokeObjectURL(url);
    } catch (e) {
        alert(`Could not download PDF: ${e.message}`);
    }
}