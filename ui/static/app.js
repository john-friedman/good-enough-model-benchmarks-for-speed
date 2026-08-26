const initialState = JSON.parse(document.getElementById("initial-state").textContent);
const initialModels = initialState.models || [];
const initialEndpoints = initialState.endpoints || {};
const models = new Map();

const tagbox = document.getElementById("model_tagbox");
const input = document.getElementById("model_input");
const hiddenModels = document.getElementById("models");
const endpointsPresent = document.getElementById("endpoints_present");
const statusEl = document.getElementById("model_status");
const endpointsPanel = document.getElementById("endpoints_panel");
const endpointsEl = document.getElementById("endpoints");
const benchmarkForm = document.getElementById("benchmark_form");

function setStatus(message, isError = false) {
  statusEl.textContent = message;
  statusEl.className = isError ? "error message" : "muted";
}

function syncHiddenModels() {
  hiddenModels.value = Array.from(models.keys()).join("\n");
}

function endpointName(endpoint) {
  return endpoint.name || endpoint.provider_name || "";
}

function renderModels() {
  tagbox.querySelectorAll(".tag").forEach((tag) => tag.remove());
  for (const slug of models.keys()) {
    const tag = document.createElement("span");
    tag.className = "tag";
    tag.innerHTML = `<code></code><button type="button" aria-label="Remove ${slug}">&times;</button>`;
    tag.querySelector("code").textContent = slug;
    tag.querySelector("button").addEventListener("click", () => {
      models.delete(slug);
      render();
    });
    tagbox.insertBefore(tag, input);
  }
}

function renderEndpoints() {
  endpointsEl.textContent = "";
  endpointsPanel.hidden = models.size === 0;
  endpointsPresent.value = models.size === 0 ? "" : "1";

  for (const [model, endpoints] of models.entries()) {
    const details = document.createElement("details");
    details.className = "table-section endpoint-results";

    const summary = document.createElement("summary");
    const heading = document.createElement("h2");
    const code = document.createElement("code");
    code.textContent = model;
    heading.appendChild(code);
    summary.appendChild(heading);
    details.appendChild(summary);

    const table = document.createElement("table");
    table.innerHTML = `
      <thead>
        <tr>
          <th></th>
          <th>Tag</th>
          <th>Name</th>
          <th>Context</th>
        </tr>
      </thead>
      <tbody></tbody>
    `;
    const tbody = table.querySelector("tbody");
    for (const endpoint of endpoints) {
      const row = document.createElement("tr");
      const value = `${model}|||${endpoint.tag}`;
      row.innerHTML = `
        <td><input type="checkbox" name="endpoint" checked></td>
        <td><code></code></td>
        <td></td>
        <td></td>
      `;
      row.querySelector("input").value = value;
      row.querySelector("code").textContent = endpoint.tag;
      row.children[2].textContent = endpointName(endpoint);
      row.children[3].textContent = endpoint.context_length || "";
      tbody.appendChild(row);
    }
    details.appendChild(table);
    endpointsEl.appendChild(details);
  }
}

function render() {
  renderModels();
  renderEndpoints();
  syncHiddenModels();
}

async function addModel(raw) {
  const slug = raw.trim();
  if (!slug || models.has(slug)) {
    input.value = "";
    return;
  }

  setStatus(`Checking ${slug}...`);
  input.disabled = true;
  try {
    const response = await fetch(`/api/endpoints?model=${encodeURIComponent(slug)}`);
    const data = await response.json();
    if (!response.ok) {
      throw new Error(data.error || "Endpoint lookup failed.");
    }
    if (!data.endpoints || data.endpoints.length === 0) {
      throw new Error("No endpoints returned.");
    }
    models.set(slug, data.endpoints);
    input.value = "";
    setStatus("");
    render();
  } catch (error) {
    setStatus(`${slug} rejected: ${error.message}`, true);
  } finally {
    input.disabled = false;
    input.focus();
  }
}

function resultTable(id) {
  return document.querySelector(`[data-table-id="${id}"]`);
}

function filterTable(id, query) {
  const table = resultTable(id);
  if (!table) {
    return;
  }
  const value = query.trim().toLowerCase();
  for (const row of table.tBodies[0].rows) {
    row.hidden = value !== "" && !row.dataset.endpoint.includes(value);
  }
}

function dataSortName(key) {
  return `sort${key[0].toUpperCase()}${key.slice(1)}`;
}

function sortTable(id, key, direction = null) {
  const table = resultTable(id);
  if (!table) {
    return;
  }
  const nextDirection = direction || table.dataset.sortDirection || (key === "prefill" || key === "decode" ? "desc" : "asc");
  table.dataset.sortKey = key;
  table.dataset.sortDirection = nextDirection;

  const body = table.tBodies[0];
  const rows = Array.from(body.rows);
  rows.sort((a, b) => {
    if (key === "endpoint") {
      const compared = a.dataset.sortEndpoint.localeCompare(b.dataset.sortEndpoint);
      return nextDirection === "desc" ? -compared : compared;
    }
    const left = Number(a.dataset[dataSortName(key)]);
    const right = Number(b.dataset[dataSortName(key)]);
    const compared = left - right;
    const multiplier = nextDirection === "desc" ? -1 : 1;
    return multiplier * compared || a.dataset.sortEndpoint.localeCompare(b.dataset.sortEndpoint);
  });
  rows.forEach((row) => body.appendChild(row));

  for (const header of table.tHead.rows[0].cells) {
    const button = header.querySelector("[data-sort-key]");
    if (!button || button.dataset.sortKey !== key) {
      header.setAttribute("aria-sort", "none");
      continue;
    }
    header.setAttribute("aria-sort", nextDirection === "desc" ? "descending" : "ascending");
  }
}

input.addEventListener("keydown", (event) => {
  if (event.key === "Enter" || event.key === ",") {
    event.preventDefault();
    addModel(input.value.replace(",", ""));
  }
  if (event.key === "Backspace" && input.value === "" && models.size > 0) {
    const last = Array.from(models.keys()).at(-1);
    models.delete(last);
    render();
  }
});

input.addEventListener("blur", () => addModel(input.value));

for (const filter of document.querySelectorAll("[data-filter-for]")) {
  filter.addEventListener("input", () => filterTable(filter.dataset.filterFor, filter.value));
}

for (const sorter of document.querySelectorAll("[data-sort-key]")) {
  sorter.addEventListener("click", () => {
    const table = resultTable(sorter.dataset.sortFor);
    const sameKey = table && table.dataset.sortKey === sorter.dataset.sortKey;
    const defaultDirection = sorter.dataset.sortKey === "prefill" || sorter.dataset.sortKey === "decode" ? "desc" : "asc";
    const nextDirection = sameKey && table.dataset.sortDirection === defaultDirection
      ? (defaultDirection === "asc" ? "desc" : "asc")
      : defaultDirection;
    sortTable(sorter.dataset.sortFor, sorter.dataset.sortKey, nextDirection);
  });
}

for (const table of document.querySelectorAll(".result-table")) {
  sortTable(table.dataset.tableId, "tbf", "asc");
}

benchmarkForm.addEventListener("submit", (event) => {
  syncHiddenModels();
  if (models.size === 0) {
    event.preventDefault();
    setStatus("Add at least one valid model slug.", true);
  }
});

async function initializeModels() {
  for (const model of initialModels) {
    const endpoints = initialEndpoints[model];
    if (endpoints && endpoints.length > 0) {
      models.set(model, endpoints);
    } else {
      await addModel(model);
    }
  }
  render();
}

initializeModels();
