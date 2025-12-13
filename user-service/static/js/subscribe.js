function getCookie(name) {
  const value = `; ${document.cookie}`
  const parts = value.split(`; ${name}=`)
  if (parts.length === 2) return parts.pop().split(";").shift()
}

document.addEventListener("DOMContentLoaded", () => {
  document.querySelectorAll(".subscribe-btn").forEach((el) => {
    el.addEventListener("click", async (e) => {
      e.preventDefault() // avoid <a> redirect

      const courseId = el.dataset.courseId
      if (!courseId) return

      // Step 1: check login
      const loginCheck = await fetch("/api/check-login", {
        credentials: "include",
      })
      const loginData = await loginCheck.json()

      if (!loginData.logged_in) {
        Swal.fire({
          icon: "warning",
          title: "Please log in first",
          confirmButtonText: "Go to Login",
        }).then(() => {
          window.location.href = "/login"
        })
        return
      }

      const csrf = getCookie("csrf_access_token")

      // Step 2: confirm subscription
      Swal.fire({
        title: "Subscribe to this course?",
        text: "You will get full access after subscribing.",
        icon: "question",
        showCancelButton: true,
        confirmButtonText: "Yes, subscribe",
      }).then(async (result) => {
        if (!result.isConfirmed) return

        const res = await fetch(`/api/subscribe/${courseId}`, {
          method: "POST",
          credentials: "include",
          headers: {
            "X-CSRF-TOKEN": csrf,
          },
        })

        const data = await res.json()

        if (data.success) {
          Swal.fire({
            title: "Subscription Activated!",
            text: "You now have access to this course.",
            icon: "success",
          }).then(() => {
            window.location.href = `/account`
          })
        } else {
          Swal.fire({
            icon: "error",
            title: "Unable to Subscribe",
            text: data.error || "Please try again later.",
          })
        }
      })
    })
  })
})
