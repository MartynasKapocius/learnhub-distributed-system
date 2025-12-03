// REGISTER + LOGIN
document.addEventListener("DOMContentLoaded", () => {
  const API_BASE = "/api"

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

      // 1. password match check
      if (password !== confirmPassword) {
        resultBox.textContent = "Passwords do not match."
        resultBox.style.color = "red"
        return
      }

      // 2. call backend API
      try {
        const res = await fetch(`${API_BASE}/users`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ name, email, password }),
        })

        const data = await res.json()

        console.log(data, res)

        if (res.ok) {
          resultBox.textContent = `User created! ID: ${data.id}`
          resultBox.style.color = "green"

          // redirect after 800ms
          setTimeout(() => {
            window.location.href = "/account"
          }, 800)
        } else {
          resultBox.textContent = data.error || "Register failed."
          resultBox.style.color = "red"
        }
      } catch (err) {
        console.error(err)
        resultBox.textContent = "Network error. Please try again."
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
      const password = document.getElementById("loginPassword").value // you will need to add this field

      const resultBox = document.getElementById("loginResult")

      try {
        const res = await fetch(`${API_BASE}/login`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ email, password }),
        })

        const data = await res.json()

        if (res.ok) {
          resultBox.textContent = "Login success!"
          resultBox.style.color = "green"

          // redirect after 800ms
          setTimeout(() => {
            window.location.href = "/account"
          }, 800)
        } else {
          resultBox.textContent = data.error || "Login failed."
          resultBox.style.color = "red"
        }
      } catch (err) {
        console.error(err)
        resultBox.textContent = "Network error."
        resultBox.style.color = "red"
      }
    })
  }
})
