// REGISTER + LOGIN
// Ensure the script runs after the entire HTML document is loaded
document.addEventListener("DOMContentLoaded", () => {
  const API_BASE = "/api"
  // NOTE: TOKEN_STORAGE_KEY constant is removed as we are now using HTTP-Only Cookies.

  // Helper function to handle successful authentication
  const handleAuthSuccess = (data, resultBox) => {
    // 1. The token is now stored in an HTTP-Only Cookie by the backend response.
    //    We only check for a success message/status.

    resultBox.textContent =
      data.message || "Operation successful! Logging in..."
    resultBox.style.color = "green"

    // 2. Redirect to the account page after a short delay
    setTimeout(() => {
      window.location.href = "/account"
    }, 300)
    // NOTE: No localStorage operations are needed here.
  }

  // Helper function for error handling
  const handleAuthError = (res, data, resultBox) => {
    const errorMsg = data.error || `Error ${res.status}: Operation failed.`
    resultBox.textContent = errorMsg
    resultBox.style.color = "red"
    console.error("API Error:", data)
  }

  // -----------------------------
  // REGISTER
  // -----------------------------
  const registerForm = document.getElementById("registerForm")
  if (registerForm) {
    registerForm.addEventListener("submit", async (e) => {
      e.preventDefault()

      const name = document.getElementById("name").value.trim()
      const email = document.getElementById("email").value.trim()
      const password = document.getElementById("Password").value
      const confirmPassword = document.getElementById("Confirm").value
      const resultBox = document.getElementById("registerResult")

      // 1. Password match check
      if (password !== confirmPassword) {
        resultBox.textContent = "Passwords do not match."
        resultBox.style.color = "red"
        return
      }

      // 2. Call backend API (Registration + Automatic Login)
      try {
        const res = await fetch(`${API_BASE}/users`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ name, email, password }),
          // IMPORTANT: Must include credentials for the browser to receive and save the JWT Cookie from the backend
          credentials: "include",
        })

        const data = await res.json()

        if (res.ok) {
          // If registration is successful, the API has set the JWT Cookie.
          handleAuthSuccess(data, resultBox)
        } else {
          // Handle registration failure
          handleAuthError(res, data, resultBox)
        }
      } catch (err) {
        console.error("Network Error:", err)
        resultBox.textContent = "Network error. Please check your connection."
        resultBox.style.color = "red"
      }
    })
  }

  // -----------------------------
  // LOGIN
  // -----------------------------
  const loginForm = document.getElementById("loginForm")
  if (loginForm) {
    loginForm.addEventListener("submit", async (e) => {
      e.preventDefault()

      const email = document.getElementById("loginEmail").value.trim()
      const password = document.getElementById("loginPassword").value
      const resultBox = document.getElementById("loginResult")

      try {
        const res = await fetch(`${API_BASE}/login`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ email, password }),
          // IMPORTANT: Must include credentials for the browser to receive and save the JWT Cookie
          credentials: "include",
        })

        const data = await res.json()

        if (res.ok) {
          // If login is successful, the API has set the JWT Cookie.
          handleAuthSuccess(data, resultBox)
        } else {
          // Handle login failure
          handleAuthError(res, data, resultBox)
        }
      } catch (err) {
        console.error("Network Error:", err)
        resultBox.textContent = "Network error. Please check your connection."
        resultBox.style.color = "red"
      }
    })
  }
})
