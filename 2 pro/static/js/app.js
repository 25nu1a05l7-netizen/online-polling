document.addEventListener("DOMContentLoaded", () => {
  const html = document.documentElement;
  const storedTheme = localStorage.getItem("theme");
  if (storedTheme) html.setAttribute("data-bs-theme", storedTheme);

  document.getElementById("themeToggle")?.addEventListener("click", () => {
    const next = html.getAttribute("data-bs-theme") === "dark" ? "light" : "dark";
    html.setAttribute("data-bs-theme", next);
    localStorage.setItem("theme", next);
  });

  document.querySelectorAll(".toast").forEach((toastNode) => {
    const toast = bootstrap.Toast.getOrCreateInstance(toastNode, { delay: 3500 });
    toast.show();
  });

  document.getElementById("addOption")?.addEventListener("click", () => {
    const list = document.getElementById("optionsList");
    const input = document.createElement("input");
    input.className = "form-control";
    input.name = "options[]";
    input.required = true;
    input.placeholder = `Option ${list.children.length + 1}`;
    list.appendChild(input);
    input.focus();
  });

  document.querySelectorAll(".copy-btn").forEach((button) => {
    button.addEventListener("click", async () => {
      const input = document.getElementById(button.dataset.copyTarget);
      await navigator.clipboard.writeText(input.value);
      button.textContent = "Copied";
      setTimeout(() => (button.textContent = "Copy"), 1400);
    });
  });

  document.querySelectorAll(".vote-option").forEach((button) => {
    button.addEventListener("click", () => {
      document.querySelectorAll(".vote-option").forEach((item) => item.classList.remove("selected"));
      button.classList.add("selected");
      document.getElementById("optionId").value = button.dataset.option;
      document.getElementById("voteSubmit").disabled = false;
    });
  });

  function tickCountdowns() {
    document.querySelectorAll("[data-expires]").forEach((box) => {
      const target = new Date(box.dataset.expires).getTime();
      const diff = target - Date.now();
      const output = box.querySelector(".countdown");
      if (!output) return;
      if (diff <= 0) {
        output.textContent = "Closed";
        return;
      }
      const days = Math.floor(diff / 86400000);
      const hours = Math.floor((diff % 86400000) / 3600000);
      const minutes = Math.floor((diff % 3600000) / 60000);
      const seconds = Math.floor((diff % 60000) / 1000);
      output.textContent = days > 0 ? `${days}d ${hours}h ${minutes}m` : `${hours}h ${minutes}m ${seconds}s`;
    });
  }

  tickCountdowns();
  setInterval(tickCountdowns, 1000);
});
