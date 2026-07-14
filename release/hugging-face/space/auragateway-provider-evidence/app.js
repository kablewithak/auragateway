const evidence = window.AURAGATEWAY_EVIDENCE;

function text(tag, className, value) {
  const element = document.createElement(tag);
  if (className) element.className = className;
  element.textContent = value;
  return element;
}

function renderStatus() {
  const row = document.getElementById("status-row");
  [
    "2 closed provider lineages",
    "0 eligible cache comparisons",
    "No live inference",
    "No credentials",
  ].forEach((label) => row.appendChild(text("span", "status-pill", label)));
}

function renderLineages() {
  const grid = document.getElementById("lineage-grid");
  evidence.provider_lineages.forEach((lineage) => {
    const card = text("article", "lineage-card", "");
    card.appendChild(text("div", "section-kicker", lineage.provider));
    card.appendChild(text("h3", "", lineage.lineage_id));
    card.appendChild(text("p", "", lineage.summary));

    const metrics = text("div", "metric-grid", "");
    [
      [lineage.attempts, "attempts"],
      [lineage.provider_successes, "successes"],
      [lineage.cache_telemetry_observed ? "yes" : "no", "cache telemetry"],
    ].forEach(([value, label]) => {
      const metric = text("div", "metric", "");
      metric.appendChild(text("strong", "", String(value)));
      metric.appendChild(text("span", "", label));
      metrics.appendChild(metric);
    });
    card.appendChild(metrics);
    card.appendChild(text("div", "badge blocked", lineage.status.replaceAll("_", " ")));
    grid.appendChild(card);
  });
}

function renderClaims(filter = "all") {
  const grid = document.getElementById("claims-grid");
  grid.replaceChildren();
  evidence.claims
    .filter((claim) => filter === "all" || claim.disposition === filter)
    .forEach((claim) => {
      const card = text("article", "claim-card", "");
      card.appendChild(text("span", `badge ${claim.disposition}`, claim.disposition));
      card.appendChild(text("h3", "", claim.claim_id.replaceAll("-", " ")));
      card.appendChild(text("p", "", claim.statement));
      grid.appendChild(card);
    });
}

function renderBoundary() {
  const included = [
    "Sanitized terminal outcomes and attempt accounting",
    "Provider and model identifiers",
    "Safe failure labels and HTTP status",
    "SHA-256 source and candidate manifests",
    "Explicit permitted and blocked claims",
  ];
  const excluded = [
    "API keys or Authorization header values",
    "Raw prompts or protected prompt bundles",
    "Raw provider response bodies",
    "Customer data or private documents",
    "Live inference or remote API calls",
  ];
  const renderList = (id, values) => {
    const list = document.getElementById(id);
    values.forEach((value) => list.appendChild(text("li", "", value)));
  };
  renderList("included-list", included);
  renderList("excluded-list", excluded);
}

function bindFilters() {
  document.querySelectorAll(".filter-button").forEach((button) => {
    button.addEventListener("click", () => {
      document.querySelectorAll(".filter-button").forEach((item) => {
        item.classList.remove("active");
      });
      button.classList.add("active");
      renderClaims(button.dataset.filter);
    });
  });
}

renderStatus();
renderLineages();
renderClaims();
renderBoundary();
bindFilters();
