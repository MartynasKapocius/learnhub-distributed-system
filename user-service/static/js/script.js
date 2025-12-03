// Function to handle the click event
function handleLoginClick() {
  // A simple alert for demonstration purposes
  alert(
    "Welcome to LearnHub! You are now being redirected to the Login/Registration page."
  )

  // In a real application, you would typically redirect the user:
  // window.location.href = "/login";
}

// Get the button element by its ID
const loginButton = document.getElementById("login-register-btn")

// Check if the element exists before adding the listener
if (loginButton) {
  // Add the click event listener
  loginButton.addEventListener("click", handleLoginClick)
}

// Optional: A simple feature to make course cards clickable
document.querySelectorAll(".course-card").forEach((card) => {
  card.addEventListener("click", function () {
    const courseTitle = this.querySelector("h3").textContent
    console.log(`Course card clicked: ${courseTitle}`)
    // In a real app, you would navigate to the course details page
    // window.location.href = `/courses/${courseTitle.toLowerCase().replace(/\s/g, '-')}`;
  })
})
