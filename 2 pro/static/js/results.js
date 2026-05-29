document.addEventListener("DOMContentLoaded", () => {
  const holder = document.querySelector("[data-results-url]");
  if (!holder || !window.Chart) return;

  const palette = ["#2563eb", "#14b8a6", "#f59e0b", "#e11d48", "#7c3aed", "#0ea5e9", "#84cc16"];
  const bar = new Chart(document.getElementById("barChart"), {
    type: "bar",
    data: { labels: [], datasets: [{ label: "Votes", data: [], backgroundColor: palette }] },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      animation: { duration: 600 },
      scales: { y: { beginAtZero: true, ticks: { precision: 0 } } },
      plugins: { legend: { display: false } }
    }
  });

  const pie = new Chart(document.getElementById("pieChart"), {
    type: "doughnut",
    data: { labels: [], datasets: [{ data: [], backgroundColor: palette }] },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      animation: { duration: 600 },
      plugins: { legend: { position: "bottom" } }
    }
  });

  async function refreshResults() {
    holder.classList.add("loading");
    const response = await fetch(holder.dataset.resultsUrl);
    const data = await response.json();
    bar.data.labels = data.labels;
    bar.data.datasets[0].data = data.values;
    pie.data.labels = data.labels;
    pie.data.datasets[0].data = data.values;
    bar.update();
    pie.update();
    document.getElementById("totalVotes").textContent = data.total;
    document.getElementById("participation").textContent = `${data.participation}%`;
    document.getElementById("pollState").textContent = data.active ? "Active" : "Closed";
    data.results.forEach((result) => {
      const row = document.querySelector(`[data-result-option="${result.id}"]`);
      if (!row) return;
      row.querySelector(".result-votes").textContent = result.votes;
      row.querySelector(".result-percentage").textContent = result.percentage;
      const bar = row.querySelector(".progress-bar");
      bar.style.width = `${result.percentage}%`;
      bar.parentElement.setAttribute("aria-valuenow", result.percentage);
    });
    holder.classList.remove("loading");
  }

  refreshResults();
  setInterval(refreshResults, 4000);
});
