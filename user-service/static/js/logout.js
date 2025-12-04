document.addEventListener("DOMContentLoaded", () => {
  const API_BASE = "/api"

  /**
   * Handles the logout process by calling the backend API to clear the JWT Cookie
   * and redirects the user to the homepage.
   */
  async function handleLogout() {
    try {
      // 1. Call the backend API (POST method) to clear the HTTP-Only Cookie
      const res = await fetch(`${API_BASE}/logout`, {
        method: "POST",
        credentials: "include", // Essential for sending the cookie
      })

      if (res.ok) {
        console.log("Logout successful. Cookies cleared by server.")
      } else {
        console.error(
          "Logout API returned an error status, redirecting.",
          await res.json()
        )
      }
    } catch (error) {
      console.error("Network error during logout. Redirecting.", error)
    }

    // 2. Redirect to the homepage after attempting logout
    // This happens regardless of the API response for consistent user experience.
    window.location.href = "/"
  }

  // --- ATTACH LOGOUT HANDLER ---
  // Get the logout button element
  const logoutButton = document.getElementById("logoutButton")

  // Attach the event listener to the button
  if (logoutButton) {
    logoutButton.addEventListener("click", (e) => {
      e.preventDefault() // Prevent default link behavior
      handleLogout()
    })
  }
})
