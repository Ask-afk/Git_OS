"use strict";
const form = document.getElementById("form");
const password = document.getElementById("password");
const confirmation = document.getElementById("confirm");
const message = document.getElementById("message");
let setup = false;
fetch("/api/status", {cache: "no-store"}).then(r => r.json()).then(status => {
  if (status.authenticated) return location.replace("/");
  setup = status.setup;
  if (setup) {
    document.getElementById("heading").textContent = "Make it yours";
    document.getElementById("intro").textContent = "Create a password to protect access to this tablet.";
    document.getElementById("confirm-wrap").hidden = false;
    document.getElementById("submit").textContent = "Set password";
    password.autocomplete = "new-password";
    confirmation.required = true;
  }
}).catch(() => { message.textContent = "Daywell could not load. Please try again."; });
form.addEventListener("submit", async event => {
  event.preventDefault();
  if (setup && password.value !== confirmation.value) {
    message.textContent = "Passwords do not match.";
    confirmation.focus();
    return;
  }
  const button = document.getElementById("submit");
  button.disabled = true;
  message.textContent = "";
  try {
    const response = await fetch(setup ? "/api/setup" : "/api/login", {
      method: "POST", headers: {"Content-Type": "application/json", "X-Daywell-Request": "1"},
      body: JSON.stringify({password: password.value})
    });
    const result = await response.json();
    if (!response.ok) throw new Error(result.error || "Could not unlock Daywell");
    location.replace("/");
  } catch (error) {
    message.textContent = error.message;
    password.value = "";
    confirmation.value = "";
    password.focus();
    button.disabled = false;
  }
});
