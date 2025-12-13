document.addEventListener("DOMContentLoaded", async () => {
  const API_BASE = "/api"

  // ----------------------
  // 1. Fetch current user
  // ----------------------
  let user = null
  try {
    const res = await fetch(`${API_BASE}/me`, {
      method: "GET",
      credentials: "include",
    })

    if (!res.ok) {
      window.location.href = "/login"
      return
    }

    user = await res.json()
  } catch (err) {
    console.error("Failed to load user", err)
    window.location.href = "/login"
    return
  }

  // Fill profile info
  document.getElementById("profileName").textContent = user.name
  document.getElementById("profileEmail").textContent = user.email

  // ----------------------
  // 2. Subscription section
  // ----------------------
  loadSubscriptions(user)

  // ----------------------
  // 3. Tabs logic
  // ----------------------
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

// ================================================
// Load Subscription Items
// ================================================
async function loadSubscriptions(user) {
  const subBox = document.getElementById("subscriptionContent")

  const subs = user.subscriptions || []

  if (subs.length === 0) {
    subBox.innerHTML = `<p>You have no active subscriptions.</p>`
    return
  }

  // fetch all courses to look up names
  const courseRes = await fetch("/api/courses-data")
  const allCourses = await courseRes.json()

  subBox.innerHTML = ""

  subs.forEach((sub) => {
    const course = allCourses.find((c) => c.id === sub.course_id)

    const name = course ? course.title : "Unknown Course"
    const date = new Date(sub.subscribed_at.$date).toLocaleDateString()

    const div = document.createElement("div")
    div.className = "subscription-item"
    div.innerHTML = `
      <p><strong>${name}</strong></p>
      <p>Subscribed on: ${date}</p>
      <a href="/quiz/${sub.course_id}" class="cta-button secondary" style="margin-right:10px;">
        Start Quiz
      </a>
      <button class="unsubscribe-btn" data-id="${sub.course_id}">
        Cancel Subscription
      </button>
    `
    subBox.appendChild(div)
  })

  // bind cancel buttons
  document.querySelectorAll(".unsubscribe-btn").forEach((btn) => {
    btn.addEventListener("click", async () => {
      const id = btn.dataset.id
      await unsubscribeCourse(id)

      // refresh UI
      const res = await fetch("/api/me", { credentials: "include" })
      const user = await res.json()
      loadSubscriptions(user)
    })
  })
}

function getCookie(name) {
  const value = `; ${document.cookie}`
  const parts = value.split(`; ${name}=`)
  if (parts.length === 2) return parts.pop().split(";").shift()
}

const csrf = getCookie("csrf_access_token")

// ================================================
// Unsubscribe
// ================================================
async function unsubscribeCourse(courseId) {
  const res = await fetch(`/api/unsubscribe/${courseId}`, {
    method: "DELETE",
    credentials: "include",
    headers: {
      "X-CSRF-TOKEN": csrf,
    },
  })

  if (!res.ok) {
    alert("Failed to unsubscribe.")
    return
  }

  alert("Subscription cancelled.")
}
