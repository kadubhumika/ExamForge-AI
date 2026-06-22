const QUESTION_TYPES = [
    "Multiple Choice Questions",
    "Short Answer Questions",
    "Long Answer Questions",
    "Diagram/Graph-Based Questions",
    "Numerical Problems",
    "Fill in the Blanks",
    "True/False",
    "Match the Following",
    "Assertion & Reason",
    "Case Study Questions",
];

let _rowCounter = 0;
let _selectedFile = null;

window.onload = function () {
    if (!requireAuth()) return;
    fillSharedChrome();

    const due = new Date();
    due.setDate(due.getDate() + 7);
    document.getElementById("dueDate").value = due.toISOString().split("T")[0];

    addQuestionRow("Multiple Choice Questions", 4, 1);
    addQuestionRow("Short Answer Questions", 5, 2);

    document.getElementById("fileInput").addEventListener("change", handleFileSelect);

    const dropZone = document.getElementById("dropZone");
    dropZone.addEventListener("dragover", (e) => {
        e.preventDefault();
        dropZone.classList.add("bg-gray-100");
    });
    dropZone.addEventListener("dragleave", () => dropZone.classList.remove("bg-gray-100"));
    dropZone.addEventListener("drop", (e) => {
        e.preventDefault();
        dropZone.classList.remove("bg-gray-100");
        if (e.dataTransfer.files.length > 0) {
            document.getElementById("fileInput").files = e.dataTransfer.files;
            handleFileSelect();
        }
    });
};

function handleFileSelect() {
    const fileInput = document.getElementById("fileInput");
    const file = fileInput.files[0];
    if (!file) return;
    if (file.size > 10 * 1024 * 1024) {
        alert("File exceeds 10MB limit");
        fileInput.value = "";
        return;
    }
    _selectedFile = file;
    document.getElementById("dropZoneText").innerText = `📎 ${file.name}`;
}

function buildDatalistHtml() {
    return `<datalist id="qtypeList">
        ${QUESTION_TYPES.map(t => `<option value="${t}">`).join("")}
    </datalist>`;
}

function addQuestionRow(type = "", count = 5, marksPer = 2) {
    const rowId = `row-${_rowCounter++}`;
    const container = document.getElementById("questionRows");

    // Only add datalist once
    if (!document.getElementById("qtypeList")) {
        container.insertAdjacentHTML("beforebegin", buildDatalistHtml());
    }

    const row = document.createElement("div");
    row.id = rowId;
    row.className = "grid grid-cols-12 gap-3 items-center";
    row.innerHTML = `
        <div class="col-span-6 md:col-span-7 flex items-center gap-2">
            <input
                type="text"
                list="qtypeList"
                value="${type}"
                placeholder="Type or choose question type…"
                class="qtype-input w-full bg-white border border-[#E5E7EB] text-xs font-medium text-[#1A1A1A] px-3 py-2 rounded-xl focus:outline-none focus:border-black"
                oninput="updateTotals()"
            />
            <button type="button" onclick="removeQuestionRow('${rowId}')" class="text-gray-400 hover:text-red-500 font-bold transition text-sm cursor-pointer px-1 shrink-0">×</button>
        </div>
        <div class="col-span-3 md:col-span-2 flex items-center justify-center bg-[#F9FAFB] border border-[#E5E7EB] rounded-full p-1 max-w-[100px] mx-auto w-full">
            <button type="button" onclick="stepCounter('${rowId}', '.count-val', -1, 1)" class="w-5 h-5 text-gray-400 hover:text-black font-bold text-xs rounded-full flex items-center justify-center cursor-pointer">-</button>
            <span class="count-val flex-1 text-center text-xs font-bold text-[#1A1A1A]">${count}</span>
            <button type="button" onclick="stepCounter('${rowId}', '.count-val', 1, 1)" class="w-5 h-5 text-gray-400 hover:text-black font-bold text-xs rounded-full flex items-center justify-center cursor-pointer">+</button>
        </div>
        <div class="col-span-3 md:col-span-2 flex items-center justify-center bg-[#F9FAFB] border border-[#E5E7EB] rounded-full p-1 max-w-[100px] mx-auto w-full">
            <button type="button" onclick="stepCounter('${rowId}', '.marks-val', -1, 1)" class="w-5 h-5 text-gray-400 hover:text-black font-bold text-xs rounded-full flex items-center justify-center cursor-pointer">-</button>
            <span class="marks-val flex-1 text-center text-xs font-bold text-[#1A1A1A]">${marksPer}</span>
            <button type="button" onclick="stepCounter('${rowId}', '.marks-val', 1, 1)" class="w-5 h-5 text-gray-400 hover:text-black font-bold text-xs rounded-full flex items-center justify-center cursor-pointer">+</button>
        </div>
    `;
    container.appendChild(row);
    updateTotals();
}

function removeQuestionRow(rowId) {
    const row = document.getElementById(rowId);
    if (row) row.remove();
    updateTotals();
}

function stepCounter(rowId, selector, delta, min) {
    const row = document.getElementById(rowId);
    const span = row.querySelector(selector);
    let val = parseInt(span.innerText, 10) + delta;
    if (val < min) val = min;
    span.innerText = val;
    updateTotals();
}

function getStructureScheme() {
    const rows = document.querySelectorAll("#questionRows > div");
    const scheme = [];
    rows.forEach(row => {
        const typeInput = row.querySelector(".qtype-input");
        const type = typeInput ? typeInput.value.trim() : "";
        const count = parseInt(row.querySelector(".count-val").innerText, 10);
        const marksPer = parseInt(row.querySelector(".marks-val").innerText, 10);
        if (type) scheme.push({ type, count, marks_per: marksPer });
    });
    return scheme;
}

function updateTotals() {
    const scheme = getStructureScheme();
    const totalQ = scheme.reduce((sum, s) => sum + s.count, 0);
    const totalM = scheme.reduce((sum, s) => sum + s.count * s.marks_per, 0);
    document.getElementById("totalQuestions").innerText = totalQ;
    document.getElementById("totalMarks").innerText = totalM;
}

function showError(message) {
    const banner = document.getElementById("errorBanner");
    banner.innerText = message;
    banner.classList.remove("hidden");
}

function clearError() {
    document.getElementById("errorBanner").classList.add("hidden");
}

async function submitAssignment() {
    clearError();

    const title = document.getElementById("assignmentTitle").value.trim();
    const dueDate = document.getElementById("dueDate").value;
    const instructions = document.getElementById("additionalInstructions").value.trim();
    const scheme = getStructureScheme();

    if (!title) return showError("Please enter an assignment title.");
    if (!_selectedFile) return showError("Please upload a source PDF or image.");
    if (!dueDate) return showError("Please pick a due date.");
    if (scheme.length === 0) return showError("Add at least one question type.");

    const nextBtn = document.getElementById("nextBtn");
    const nextBtnText = document.getElementById("nextBtnText");
    nextBtn.disabled = true;
    nextBtn.classList.add("opacity-60", "cursor-not-allowed");
    nextBtnText.innerText = "Uploading…";

    const formData = new FormData();
    formData.append("title", title);
    formData.append("due_date", dueDate);
    formData.append("instructions", instructions);
    formData.append("structure_scheme", JSON.stringify(scheme));
    formData.append("file", _selectedFile);

    try {
        const res = await fetch(`${API}/assignments/upload-and-create`, {
            method: "POST",
            headers: authHeadersNoContentType(),
            body: formData,
        });

        if (res.status === 401) {
            localStorage.clear();
            window.location.href = "login.html";
            return;
        }

        if (!res.ok) {
            const err = await res.json().catch(() => ({}));
            throw new Error(err.detail || "Could not create assignment");
        }

        const assignment = await res.json();
        window.location.href = `assignment_output.html?id=${assignment.id}`;
    } catch (e) {
        showError(e.message);
        nextBtn.disabled = false;
        nextBtn.classList.remove("opacity-60", "cursor-not-allowed");
        nextBtnText.innerText = "Generate Assignment";
    }
}