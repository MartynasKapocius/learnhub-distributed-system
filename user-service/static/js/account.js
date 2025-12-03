// static/account.js

document.addEventListener("DOMContentLoaded", async () => {
  const API_BASE = "/api"

  // fetch current user
  let user = null
  try {
    const res = await fetch(`${API_BASE}/me`)
    if (res.ok) {
      user = await res.json()
    } else {
      // redirect to login if hasn't logged in
      window.location.href = "/login"
      return
    }
  } catch (err) {
    console.error("Failed to load current user", err)
    window.location.href = "/login"
    return
  }

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

  // Tabs 切換
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
