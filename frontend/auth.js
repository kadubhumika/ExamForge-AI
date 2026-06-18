async function signup() {
    const name = document.getElementById("fullname").value;
    const email = document.getElementById("email").value;
    const password = document.getElementById("password").value;
    const school_name = document.getElementById("school").value;

    const res = await fetch(`${API}/auth/register`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name, email, password, school_name })
    });

    const data = await res.json();

    if (res.ok) {
        alert("Signup success → go login");
        window.location.href = "login.html";
    } else {
        alert("Signup failed");
    }
}
async function login() {
    const email = document.getElementById("email").value;
    const password = document.getElementById("password").value;

    const res = await fetch(`${API}/auth/login`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, password })
    });

    const data = await res.json();

    if (res.ok) {
    localStorage.setItem("token", data.access_token);
    localStorage.setItem("user_id", data.user_id);
    localStorage.setItem("school_id", data.school_id);
    localStorage.setItem("user_name", data.user_name);
    localStorage.setItem("school_name", data.school_name);

    window.location.href = "dashboard.html";
    }
    else {
        alert("Login failed");
    }
}