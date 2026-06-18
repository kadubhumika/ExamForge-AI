window.onload = function () {
    const token = localStorage.getItem("token");
    const user_name = localStorage.getItem("user_name");
    const user_id = localStorage.getItem("user_id");
    const school_id = localStorage.getItem("school_id");
    const school_name = localStorage.getItem("school_name");

    if (!token) {
        window.location.href = "login.html";
        return;
    }

    // UI update
    document.getElementById("username").innerText = user_name || "User";
    document.getElementById("schoolName").innerText = school_name;

    loadDashboard(user_id);
    loadLibrary(user_id);
};
async function loadDashboard(user_id) {
    const res = await fetch(`${API}/assignments/dashboard/${user_id}`, {
        method: "GET",
        headers: authHeaders()
    });

    const data = await res.json();
    console.log("Dashboard:", data);
}
async function loadLibrary(user_id) {
    const res = await fetch(`${API}/assignments/my-library/${user_id}`, {
        method: "GET",
        headers: authHeaders()
    });

    const data = await res.json();
    console.log("Library:", data);
}
async function search(query) {
    const school_id = localStorage.getItem("school_id");

    const res = await fetch(
        `${API}/assignments/search?school_id=${school_id}&query=${query}`,
        {
            method: "GET",
            headers: authHeaders()
        }
    );

    const data = await res.json();
    console.log(data);
}
