/* global vis from CDN */
(function () {
  const VIZ_ID = window.__VIZ_ID__;
  if (!VIZ_ID) {
    document.getElementById("status").textContent = "Thiếu viz id.";
    return;
  }

  const GROUP_LABELS = {
    can_cu_chinh: "Căn cứ chính",
    huong_dan: "Căn cứ hướng dẫn",
    bo_tro: "Căn cứ bổ trợ",
    sap_hieu_luc: "Sắp hiệu lực",
    hien_hanh_doi_chieu: "Hiện hành đối chiếu",
    semantic: "Node ngữ nghĩa",
    mau_thuan: "Căn cứ mâu thuẫn",
    default: "Khác",
  };

  let network = null;
  let payload = null;

  function setTab(name) {
    document.querySelectorAll(".tab").forEach((t) => {
      t.classList.toggle("active", t.dataset.tab === name);
    });
    document.querySelectorAll(".panel").forEach((p) => {
      p.classList.toggle("active", p.id === `panel-${name}`);
    });
    if (name === "graph" && network) {
      setTimeout(() => network.fit(), 50);
    }
  }

  document.querySelectorAll(".tab").forEach((tab) => {
    tab.addEventListener("click", () => setTab(tab.dataset.tab));
  });

  document.getElementById("btn-fit").addEventListener("click", () => {
    if (network) network.fit({ animation: true });
  });
  document.getElementById("btn-zoom-in").addEventListener("click", () => {
    if (network) {
      const scale = network.getScale();
      network.moveTo({ scale: scale * 1.2, animation: true });
    }
  });
  document.getElementById("btn-zoom-out").addEventListener("click", () => {
    if (network) {
      const scale = network.getScale();
      network.moveTo({ scale: scale / 1.2, animation: true });
    }
  });

  document.getElementById("search-input").addEventListener("input", (e) => {
    const q = e.target.value.trim().toLowerCase();
    if (!network || !q) {
      if (network) network.unselectAll();
      return;
    }
    const match = payload.nodes.find((n) => n.id.toLowerCase().includes(q));
    if (match) {
      network.selectNodes([match.id]);
      network.focus(match.id, { scale: 1.2, animation: true });
    }
  });

  function renderMeta(meta) {
    const el = document.getElementById("sidebar-meta");
    if (!meta) {
      el.innerHTML = "";
      return;
    }
    const params = typeof meta.params === "object"
      ? JSON.stringify(meta.params, null, 2)
      : String(meta.params || "");
    el.innerHTML = `
      <div class="meta-row"><strong>Template</strong>${escapeHtml(meta.template || "—")}</div>
      <div class="meta-row"><strong>Thời điểm</strong>${escapeHtml(meta.target_date || "—")}</div>
      <div class="meta-row"><strong>Nodes / Edges</strong>${meta.node_count || 0} / ${meta.edge_count || 0}</div>
      <div class="meta-row"><strong>Params</strong><pre>${escapeHtml(params)}</pre></div>
    `;
  }

  function renderLegend() {
    const groups = [...new Set(payload.nodes.map((n) => n.group || "default"))];
    const el = document.getElementById("legend");
    el.innerHTML =
      groups
        .map((g) => {
          const color = payload.nodes.find((n) => n.group === g)?.color || "#9B9B9B";
          return `<div class="legend-item"><span class="legend-dot" style="background:${color}"></span>${GROUP_LABELS[g] || g}</div>`;
        })
        .join("");
  }

  function renderTable() {
    const tbody = document.querySelector("#nodes-table tbody");
    tbody.innerHTML = payload.nodes
      .map(
        (n) =>
          `<tr><td>${escapeHtml(n.id)}</td><td>${escapeHtml(n.label || "")}</td><td>${escapeHtml(n.group || "")}</td></tr>`
      )
      .join("");

    const etbody = document.querySelector("#edges-table tbody");
    etbody.innerHTML = payload.edges
      .map(
        (e) =>
          `<tr><td>${escapeHtml(e.from)}</td><td>${escapeHtml(e.label || "")}</td><td>${escapeHtml(e.to)}</td></tr>`
      )
      .join("");
  }

  function renderRaw() {
    document.getElementById("raw-json").textContent = JSON.stringify(payload, null, 2);
  }

  function buildGraph() {
    const container = document.getElementById("graph-network");
    const nodes = new vis.DataSet(
      payload.nodes.map((n) => ({
        id: n.id,
        label: truncate(n.caption || n.id, 24),
        title: n.id,
        color: {
          background: n.color || "#4C8BF5",
          border: darken(n.color || "#4C8BF5"),
          highlight: { background: n.color, border: "#ff4587" },
        },
        font: { size: 11, face: "Segoe UI", color: "#f5f5f5" },
        shape: "dot",
        size: 18,
      }))
    );

    const edges = new vis.DataSet(
      payload.edges.map((e) => ({
        id: e.id,
        from: e.from,
        to: e.to,
        label: e.label,
        arrows: "to",
        font: { size: 9, align: "middle", color: "#a3a3a3", strokeWidth: 0 },
        color: { color: "#555555", highlight: "#ff4587" },
        smooth: { type: "continuous" },
      }))
    );

    const options = {
      physics: {
        enabled: true,
        barnesHut: {
          gravitationalConstant: -3000,
          springLength: 170,
          springConstant: 0.02,
          avoidOverlap: 0.5,
        },
        stabilization: { iterations: 150 },
      },
      interaction: {
        hover: true,
        tooltipDelay: 100,
        navigationButtons: false,
        dragNodes: true,
      },
    };

    network = new vis.Network(container, { nodes, edges }, options);

    network.once("stabilizationIterationsDone", () => {
      network.setOptions({ physics: { enabled: false } });
      network.fit({ animation: true });
    });

    // Lưu tọa độ sau kéo (không set fixed — node vẫn kéo lại được)
    network.on("dragEnd", (params) => {
      if (!params.nodes.length) return;
      const positions = network.getPositions(params.nodes);
      nodes.update(
        params.nodes.map((id) => ({
          id,
          x: positions[id].x,
          y: positions[id].y,
        }))
      );
    });
  }

  function truncate(s, max) {
    return s.length > max ? s.slice(0, max - 2) + "…" : s;
  }

  function darken(hex) {
    if (!hex || hex[0] !== "#" || hex.length < 7) return "#333";
    const r = Math.max(0, parseInt(hex.slice(1, 3), 16) - 40);
    const g = Math.max(0, parseInt(hex.slice(3, 5), 16) - 40);
    const b = Math.max(0, parseInt(hex.slice(5, 7), 16) - 40);
    return `#${r.toString(16).padStart(2, "0")}${g.toString(16).padStart(2, "0")}${b.toString(16).padStart(2, "0")}`;
  }

  function escapeHtml(s) {
    return String(s)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  async function load() {
    const status = document.getElementById("status");
    try {
      const res = await fetch(`/api/viz/${VIZ_ID}`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      payload = await res.json();
      status.style.display = "none";
      document.querySelector(".layout").style.display = "flex";

      if ((payload.meta?.node_count || 0) > 200) {
        document.getElementById("warning-banner").classList.add("visible");
      }

      renderMeta(payload.meta);
      renderLegend();
      renderTable();
      renderRaw();
      buildGraph();
    } catch (err) {
      status.className = "error";
      status.textContent = `Không tải được đồ thị: ${err.message}`;
    }
  }

  load();
})();
