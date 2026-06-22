async function signup() {
    const name = document.getElementById("fullname").value.trim();
    const email = document.getElementById("email").value.trim();
    const password = document.getElementById("password").value;
    const school_name = document.getElementById("school").value.trim();

    if (!name || !email || !password || !school_name) {
        alert("Please fill in all fields");
        return;
    }

    try {
        const res = await fetch(`${API}/auth/register`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ name, email, password, school_name })
        });

        const data = await res.json();

        if (res.ok) {
            alert("Account created — please sign in.");
            window.location.href = "login.html";
        } else {
            alert(data.detail || "Signup failed");
        }
    } catch (e) {
        alert("Could not reach the server. Is the backend running?");
    }
}

async function login() {
    const email = document.getElementById("email").value.trim();
    const password = document.getElementById("password").value;

    if (!email || !password) {
        alert("Please enter email and password");
        return;
    }

    try {
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
            localStorage.setItem("email", data.email);
            localStorage.setItem("theme", data.theme || "light");

            window.location.href = "dashboard.html";
        } else {
            alert(data.detail || "Login failed");
        }
    } catch (e) {
        alert("Could not reach the server. Is the backend running?");
    }
}