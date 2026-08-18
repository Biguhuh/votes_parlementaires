const POSITIONS = ["pour", "contre", "abstention", "nonVotant"];
const POSITION_LABELS = { pour: "Pour", contre: "Contre", abstention: "Abstention", nonVotant: "Non-votant" };

const state = {
  tab: "deputes",
  deputes: { q: "", page: 1, perPage: 20 },
  scrutins: { q: "", page: 1, perPage: 20 },
};

function debounce(fn, delay) {
  let timer;
  return (...args) => {
    clearTimeout(timer);
    timer = setTimeout(() => fn(...args), delay);
  };
}

async function api(path, params = {}) {
  const url = new URL(path, window.location.origin);
  Object.entries(params).forEach(([k, v]) => {
    if (v !== undefined && v !== null && v !== "") url.searchParams.set(k, v);
  });
  const res = await fetch(url);
  if (!res.ok) throw new Error(`API error ${res.status}`);
  return res.json();
}

function escapeHtml(s) {
  if (s === null || s === undefined) return "";
  return String(s)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;");
}

function statsBar(stats) {
  const total = POSITIONS.reduce((sum, p) => sum + (stats[p] || 0), 0) || 1;
  const segs = POSITIONS.map(
    (p) => `<span class="bar-seg ${p}" style="width:${((stats[p] || 0) / total) * 100}%"></span>`
  ).join("");
  return `<div class="bar">${segs}</div>`;
}

function statsChips(stats) {
  return `<div class="stats-chips">${POSITIONS.map(
    (p) => `<span class="chip"><span class="dot dot-${p}"></span>${POSITION_LABELS[p]} ${stats[p] || 0}</span>`
  ).join("")}</div>`;
}

function positionBadge(position) {
  return `<span class="position-badge ${position}">${POSITION_LABELS[position] || position}</span>`;
}

// -- tabs ---------------------------------------------------------------

function initTabs() {
  document.querySelectorAll(".tab").forEach((btn) => {
    btn.addEventListener("click", () => switchTab(btn.dataset.tab));
  });
}

function switchTab(tab) {
  state.tab = tab;
  document.querySelectorAll(".tab").forEach((b) => b.classList.toggle("active", b.dataset.tab === tab));
  document.querySelectorAll(".view").forEach((v) => v.classList.toggle("active", v.id === `view-${tab}`));
}

// -- meta -----------------------------------------------------------------

async function loadMeta() {
  const meta = await api("/api/meta");
  document.getElementById("meta").textContent =
    `${meta.legislature}e législature — ${meta.nb_scrutins.toLocaleString("fr-FR")} scrutins, ${meta.nb_deputes.toLocaleString("fr-FR")} députés`;
}

// -- députés ---------------------------------------------------------------

function deputeCard(d) {
  const groupe = d.groupe_abrege ? `${d.groupe_abrege}` : "Non inscrit";
  const geo = d.departement ? `${d.departement} (${d.num_departement}) — circo. ${d.num_circonscription}` : "";
  return `
    <div class="card" data-acteur-ref="${d.acteur_ref}">
      <div class="card-row">
        <div>
          <div class="card-title">${escapeHtml(d.civ)} ${escapeHtml(d.nom_complet)} <span class="muted">· ${escapeHtml(groupe)}</span></div>
          <div class="card-sub">${escapeHtml(geo)}</div>
        </div>
      </div>
      ${statsChips(d.stats)}
    </div>`;
}

async function loadDeputes() {
  const { q, page, perPage } = state.deputes;
  const data = await api("/api/deputes", { q, page, per_page: perPage });
  document.getElementById("deputes-results").innerHTML =
    data.results.map(deputeCard).join("") || `<p class="muted">Aucun résultat.</p>`;
  document.querySelectorAll("#deputes-results .card").forEach((el) => {
    el.addEventListener("click", () => openDeputeModal(el.dataset.acteurRef));
  });
  renderPagination("deputes-pagination", data.total, page, perPage, (p) => {
    state.deputes.page = p;
    loadDeputes();
  });
}

function renderPagination(containerId, total, page, perPage, onChange) {
  const pages = Math.max(1, Math.ceil(total / perPage));
  const el = document.getElementById(containerId);
  if (total === 0) {
    el.innerHTML = "";
    return;
  }
  el.innerHTML = `
    <button ${page <= 1 ? "disabled" : ""} id="${containerId}-prev">← Précédent</button>
    <span>Page ${page} / ${pages} — ${total.toLocaleString("fr-FR")} résultats</span>
    <button ${page >= pages ? "disabled" : ""} id="${containerId}-next">Suivant →</button>
  `;
  const prev = document.getElementById(`${containerId}-prev`);
  const next = document.getElementById(`${containerId}-next`);
  if (prev) prev.addEventListener("click", () => onChange(page - 1));
  if (next) next.addEventListener("click", () => onChange(page + 1));
}

// -- groupes ----------------------------------------------------------------

function groupeCard(g) {
  return `
    <div class="card" data-organe-ref="${g.organe_ref}">
      <div class="card-row">
        <div>
          <div class="card-title">${escapeHtml(g.libelle || g.libelle_abrege)}</div>
          <div class="card-sub">${g.effectif} membres</div>
        </div>
      </div>
      ${statsBar(g.stats)}
      ${statsChips(g.stats)}
    </div>`;
}

async function loadGroupes() {
  const groupes = await api("/api/groupes");
  document.getElementById("groupes-results").innerHTML = groupes.map(groupeCard).join("");
  document.querySelectorAll("#groupes-results .card").forEach((el) => {
    el.addEventListener("click", () => openGroupeModal(el.dataset.organeRef));
  });
}

// -- scrutins -----------------------------------------------------------------

function scrutinCard(s) {
  const decompte = { pour: s.decompte_pour, contre: s.decompte_contre, abstention: s.decompte_abstentions, nonVotant: s.decompte_non_votants };
  return `
    <div class="card" data-scrutin-uid="${s.scrutin_uid}">
      <div class="card-row">
        <div>
          <div class="card-title">${escapeHtml(s.titre)}</div>
          <div class="card-sub">${escapeHtml(s.date_scrutin)} · ${escapeHtml(s.sort_libelle)}</div>
        </div>
      </div>
      ${statsChips(decompte)}
    </div>`;
}

async function loadScrutins() {
  const { q, page, perPage } = state.scrutins;
  const data = await api("/api/scrutins", { q, page, per_page: perPage });
  document.getElementById("scrutins-results").innerHTML =
    data.results.map(scrutinCard).join("") || `<p class="muted">Aucun résultat.</p>`;
  document.querySelectorAll("#scrutins-results .card").forEach((el) => {
    el.addEventListener("click", () => openScrutinModal(el.dataset.scrutinUid));
  });
  renderPagination("scrutins-pagination", data.total, page, perPage, (p) => {
    state.scrutins.page = p;
    loadScrutins();
  });
}

// -- modal / détail -----------------------------------------------------------

const modalBackdrop = document.getElementById("modal-backdrop");
const modalContent = document.getElementById("modal-content");

function openModal(html) {
  modalContent.innerHTML = html;
  modalBackdrop.classList.add("open");
}
function closeModal() {
  modalBackdrop.classList.remove("open");
  modalContent.innerHTML = "";
}
document.getElementById("modal-close").addEventListener("click", closeModal);
modalBackdrop.addEventListener("click", (e) => {
  if (e.target === modalBackdrop) closeModal();
});

async function openDeputeModal(acteurRef) {
  const d = await api(`/api/deputes/${acteurRef}`);
  const geo = d.departement ? `${d.departement} (${d.num_departement}) — circonscription ${d.num_circonscription}` : "Département inconnu";
  openModal(`
    <h2 class="detail-title">${escapeHtml(d.civ)} ${escapeHtml(d.nom_complet)}</h2>
    <div class="detail-sub">${escapeHtml(d.groupe_libelle || "Non inscrit")} · ${escapeHtml(geo)}</div>
    ${statsBar(d.stats)}
    <div style="margin-top:8px">${statsChips(d.stats)}</div>
    <div class="section-title">Historique des votes</div>
    <input type="search" id="depute-votes-search" placeholder="Filtrer par titre de scrutin…" />
    <div id="depute-votes-results" style="margin-top:10px"></div>
    <div id="depute-votes-pagination" class="pagination"></div>
  `);

  const votesState = { q: "", page: 1, perPage: 20 };
  const load = async () => {
    const data = await api(`/api/deputes/${acteurRef}/votes`, { q: votesState.q, page: votesState.page, per_page: votesState.perPage });
    const rows = data.results
      .map(
        (v) =>
          `<tr><td>${escapeHtml(v.date_scrutin)}</td><td>${escapeHtml(v.titre)}</td><td>${positionBadge(v.position)}</td></tr>`
      )
      .join("");
    document.getElementById("depute-votes-results").innerHTML = `
      <table><thead><tr><th>Date</th><th>Scrutin</th><th>Position</th></tr></thead>
      <tbody>${rows || `<tr><td colspan="3" class="muted">Aucun résultat.</td></tr>`}</tbody></table>`;
    renderPagination("depute-votes-pagination", data.total, votesState.page, votesState.perPage, (p) => {
      votesState.page = p;
      load();
    });
  };
  document.getElementById("depute-votes-search").addEventListener(
    "input",
    debounce((e) => {
      votesState.q = e.target.value;
      votesState.page = 1;
      load();
    }, 300)
  );
  load();
}

async function openGroupeModal(organeRef) {
  const g = await api(`/api/groupes/${organeRef}`);
  openModal(`
    <h2 class="detail-title">${escapeHtml(g.libelle)}</h2>
    <div class="detail-sub">${g.membres.length} membres</div>
    <div class="section-title">Membres</div>
    <div class="results">${g.membres.map(deputeCard).join("")}</div>
  `);
  document.querySelectorAll("#modal-content .card").forEach((el) => {
    el.addEventListener("click", () => openDeputeModal(el.dataset.acteurRef));
  });
}

async function openScrutinModal(scrutinUid) {
  const s = await api(`/api/scrutins/${scrutinUid}`);
  const parGroupeRows = s.par_groupe
    .map(
      (g) => `<tr>
        <td>${escapeHtml(g.libelle_abrege || g.organe_ref)}</td>
        <td>${g.pour}</td><td>${g.contre}</td><td>${g.abstention}</td><td>${g.nonVotant}</td>
      </tr>`
    )
    .join("");
  const votantsRows = s.votants
    .map(
      (v) =>
        `<tr><td>${escapeHtml(v.nom_complet)}</td><td>${escapeHtml(v.groupe_abrege || "")}</td><td>${positionBadge(v.position)}</td></tr>`
    )
    .join("");
  openModal(`
    <h2 class="detail-title">${escapeHtml(s.titre)}</h2>
    <div class="detail-sub">${escapeHtml(s.date_scrutin)} · ${escapeHtml(s.type_vote_libelle)} · ${escapeHtml(s.sort_libelle)}</div>
    ${escapeHtml(s.demandeur) ? `<div class="detail-sub">Demandé par : ${escapeHtml(s.demandeur)}</div>` : ""}
    ${statsChips({ pour: s.decompte_pour, contre: s.decompte_contre, abstention: s.decompte_abstentions, nonVotant: s.decompte_non_votants })}
    <div class="section-title">Par groupe</div>
    <table><thead><tr><th>Groupe</th><th>Pour</th><th>Contre</th><th>Abst.</th><th>N/V</th></tr></thead>
    <tbody>${parGroupeRows}</tbody></table>
    <div class="section-title">Votants (${s.votants.length})</div>
    <input type="search" id="scrutin-votants-search" placeholder="Filtrer par nom ou groupe…" />
    <div style="max-height:320px;overflow-y:auto;margin-top:8px">
      <table><thead><tr><th>Député</th><th>Groupe</th><th>Position</th></tr></thead>
      <tbody id="scrutin-votants-body">${votantsRows}</tbody></table>
    </div>
  `);
  document.getElementById("scrutin-votants-search").addEventListener(
    "input",
    debounce((e) => {
      const q = e.target.value.trim().toLowerCase();
      const filtered = s.votants.filter(
        (v) => (v.nom_complet || "").toLowerCase().includes(q) || (v.groupe_abrege || "").toLowerCase().includes(q)
      );
      document.getElementById("scrutin-votants-body").innerHTML = filtered
        .map(
          (v) =>
            `<tr><td>${escapeHtml(v.nom_complet)}</td><td>${escapeHtml(v.groupe_abrege || "")}</td><td>${positionBadge(v.position)}</td></tr>`
        )
        .join("");
    }, 200)
  );
}

// -- init ---------------------------------------------------------------

document.getElementById("deputes-search").addEventListener(
  "input",
  debounce((e) => {
    state.deputes.q = e.target.value;
    state.deputes.page = 1;
    loadDeputes();
  }, 300)
);

document.getElementById("scrutins-search").addEventListener(
  "input",
  debounce((e) => {
    state.scrutins.q = e.target.value;
    state.scrutins.page = 1;
    loadScrutins();
  }, 300)
);

initTabs();
loadMeta();
loadDeputes();
loadGroupes();
loadScrutins();
