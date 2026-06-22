window.onload = function () {
    if (!requireAuth()) return;
    fillSharedChrome();

    const userName = localStorage.getItem("user_name") || "";
    const schoolName = localStorage.getItem("school_name") || "";
    const theme = localStorage.getItem("theme") || "light";

    document.getElementById("fullName").value = userName;
    document.getElementById("email").value = localStorage.getItem("email") || "";
    document.getElementById("school").value = schoolName;

    const radio = document.querySelector(`input[name="themeSelection"][value="${theme}"]`);
    if (radio) radio.checked = true;
};

function showSettingsBanner(message, isError = false) {
    const banner = document.getElementById("settingsBanner");
    banner.innerText = message;
    banner.className = isError
        ? "text-xs font-semibold px-4 py-2.5 rounded-xl bg-red-50 text-red-600"
        : "text-xs font-semibold px-4 py-2.5 rounded-xl bg-green-50 text-green-700";
    banner.classList.remove("hidden");
    setTimeout(() => banner.classList.add("hidden"), 4000);
}

async function updateProfile() {
    const name = document.getElementById("fullName").value.trim();
    const theme = document.querySelector('input[name="themeSelection"]:checked').value;

    if (!name) {
        showSettingsBanner("Name cannot be empty", true);
        return;
    }

    try {
        const res = await apiFetch(`/auth/profile/update`, {
            method: "PUT",
            headers: authHeaders(),
            body: JSON.stringify({ name, theme })
        });
        const data = await res.json();

        localStorage.setItem("user_name", data.user_name);
        localStorage.setItem("theme", data.theme);

        showSettingsBanner("Profile updated successfully");
        document.body.classList.toggle("dark", data.theme === "dark");

        const username = document.getElementById("username");
        if (username) username.innerText = data.user_name;
    } catch (e) {
        showSettingsBanner(e.message || "Profile update failed", true);
    }
}