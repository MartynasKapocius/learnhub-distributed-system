document.addEventListener("DOMContentLoaded", async () => {
  const API_BASE = "/api"

  // fetch current user
  let user = null
  try {
    // Fetch user details. The JWT Cookie is sent automatically by the browser.
    const res = await fetch(`${API_BASE}/me`, {
      method: "GET",
      // ESSENTIAL: Add credentials to ensure the browser sends the cookie!
      credentials: "include",
    })

    if (res.ok) {
      user = await res.json()
    } else if (res.status === 401) {
      // Handle 401: Token Cookie is missing or invalid.
      console.error("Authentication failed. Redirecting to login.")
      window.location.href = "/login"
      return
    } else {
      // Handle other API errors
      throw new Error(`API returned status ${res.status}`)
    }
  } catch (err) {
    console.error("Failed to load current user", err)
    // In case of network error, redirect
    window.location.href = "/login"
    return
  }

  // --- Profile Filling Logic ---
  // Fill Profile
  const nameSpan = document.getElementById("profileName")
  const emailSpan = document.getElementById("profileEmail")
  if (nameSpan && emailSpan) {
    nameSpan.textContent = user.name
    emailSpan.textContent = user.email
  }

  // Subscription section
  const subBox = document.getElementById("subscriptionContent")
  if (!subBox) return

  // check if user.subscription exists
  if (!user.subscription) {
    subBox.innerHTML = `
      <p>You do not have an active subscription.</p>
      <button id="goCourses">Browse Courses</button>
    `
    const btn = document.getElementById("goCourses")
    if (btn) {
      btn.addEventListener("click", () => {
        window.location.href = "/courses"
      })
    }
  } else {
    subBox.innerHTML = `
      <p><strong>Plan:</strong> ${user.subscription.plan}</p>
      <p><strong>Renews on:</strong> ${user.subscription.renews}</p>
    `
  }

  // Tabs Switching Logic
  const tabButtons = document.querySelectorAll(".tab-button")
  const tabPanels = document.querySelectorAll(".tab-panel")

  tabButtons.forEach((btn) => {
    btn.addEventListener("click", () => {
      const tab = btn.dataset.tab

      tabButtons.forEach((b) => b.classList.remove("active"))
      btn.classList.add("active")

      tabPanels.forEach((panel) => {
        panel.classList.toggle("active", panel.id === tab)
      })
    })
  })
})
