const API = "https://examforge-ai-my1w.onrender.com/api/v1";

function getToken() {
    return localStorage.getItem("token");
}

function authHeaders() {
    return {
        "Content-Type": "application/json",
        "Authorization": `Bearer ${getToken()}`
    };
}

// For multipart/form-data requests (file upload) — do NOT set Content-Type,
// the browser sets the correct multipart boundary automatically.
function authHeadersNoContentType() {
    return {
        "Authorization": `Bearer ${getToken()}`
    };
}

// Redirects to login if there's no token. Call this at the top of every
// protected page's window.onload.
function requireAuth() {
    const token = getToken();
    if (!token) {
        window.location.href = "login.html";
        return false;
    }
    return true;
}

// Centralized fetch wrapper: handles 401 (expired/invalid session) by
// bouncing back to login, and throws on other non-OK responses so callers
// can catch() with a useful message.
async function apiFetch(path, options = {}) {
    const res = await fetch(`${API}${path}`, options);

    if (res.status === 401) {
        localStorage.clear();
        window.location.href = "login.html";
        throw new Error("Session expired");
    }

    if (!res.ok) {
        let detail = "Request failed";
        try {
            const errBody = await res.json();
            detail = errBody.detail || detail;
        } catch (_) {
            // response wasn't JSON
        }
        throw new Error(detail);
    }

    return res;
}

function formatDate(isoString) {
    if (!isoString) return "—";
    const normalized = isoString.endsWith("Z") ? isoString : isoString + "Z";
    const d = new Date(normalized);
    if (isNaN(d.getTime())) return "—";
    const dd = String(d.getDate()).padStart(2, "0");
    const mm = String(d.getMonth() + 1).padStart(2, "0");
    const yyyy = d.getFullYear();
    return `${dd}-${mm}-${yyyy}`;
}

// Fills in the shared sidebar / header bits (username, school name) that
// appear on every page. Safe to call even if elements don't exist.
function fillSharedChrome() {
    const username = document.getElementById("username");
    if (username) {
        username.innerText = localStorage.getItem("user_name") || "User";
    }
    const school = document.getElementById("schoolName");
    if (school) {
        school.innerText = localStorage.getItem("school_name") || "";
    }
    const savedTheme = localStorage.getItem("theme") || "light";
    document.body.classList.toggle("dark", savedTheme === "dark");
}

document.addEventListener("DOMContentLoaded", fillSharedChrome);