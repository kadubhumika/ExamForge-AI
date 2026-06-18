window.handleGoogleLogin = async function (response) {
    const res = await fetch(`${API}/auth/google`, {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({ id_token: response.credential })
    });

    const data = await res.json();

    if (res.ok) {
        localStorage.setItem("token", data.access_token);
        localStorage.setItem("user_id", data.user_id);
        localStorage.setItem("school_id", data.school_id);
        localStorage.setItem("user_name", data.user_name);
        localStorage.setItem("school_name", data.school_name);
        window.location.href = "dashboard.html";
    } else {
        alert("Google login failed");
    }
}