const S = { role: "CONTRATANTE", current: null };
const LABEL = { PENDENTE: "Pendente", EM_EXECUCAO: "Em execução", ENTREGUE: "Entregue", EM_ANALISE: "Em análise",
  APROVADO: "Aprovado", REJEITADO: "Rejeitado", CONCLUIDO: "Concluído", EM_REVISAO: "Em revisão", ATIVO: "Ativo" };
const EXEC = { PENDENTE: ["EM_EXECUCAO"], EM_EXECUCAO: ["ENTREGUE"], REJEITADO: ["EM_EXECUCAO"] };
const APPR = { ENTREGUE: ["EM_ANALISE"], EM_ANALISE: ["APROVADO", "REJEITADO"], APROVADO: ["CONCLUIDO"] };
const ACTION = { EM_EXECUCAO: "Iniciar execução", ENTREGUE: "Registrar entrega", EM_ANALISE: "Iniciar análise",
  APROVADO: "Aprovar", REJEITADO: "Rejeitar", CONCLUIDO: "Concluir" };
const $ = s => document.querySelector(s);
const esc = s => String(s ?? "").replace(/[&<>"]/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
const short = h => h ? h.replace(/^0x/, "").slice(0, 10) + "…" : "—";
const fmtDate = d => d ? d.split("-").reverse().join("/") : "—";
const badge = s => `<span class="badge s-${s}">${LABEL[s] || s}</span>`;

function toast(msg, err) { const t = $("#toast"); t.textContent = msg; t.className = "show" + (err ? " err" : ""); clearTimeout(t._h); t._h = setTimeout(() => t.className = "", 3500); }
async function api(path, opts = {}) {
  const r = await fetch(path, opts); const j = await r.json().catch(() => ({}));
  if (!r.ok) throw new Error(typeof j.detail === "string" ? j.detail : JSON.stringify(j.detail || j));
  return j;
}

document.querySelectorAll("#roleSeg button").forEach(b => b.onclick = () => {
  S.role = b.dataset.r; document.querySelectorAll("#roleSeg button").forEach(x => { x.classList.toggle("on", x === b); x.setAttribute("aria-pressed", x === b); });
  $("#userName").value = S.role === "CONTRATANTE" ? "ana.contratante" : "bruno.contratada";
  if (S.current) render(S.current);
});

async function loadList() {
  const list = await api("/api/contracts");
  $("#clist").innerHTML = list.map(c => `<li class="${S.current && S.current.id === c.id ? "on" : ""}"><button type="button" data-id="${c.id}" ${S.current && S.current.id === c.id ? 'aria-current="true"' : ""}>
    <div class="t">${esc(c.titulo)}</div><div class="muted" style="font-size:12px">${esc(c.contratante || "")} ${badge(c.status)}</div></li>`).join("");
  document.querySelectorAll("#clist button").forEach(b => b.onclick = () => openContract(+b.dataset.id));
  const ci = await api("/api/chain");
  $("#chainInfo").innerHTML = `Rede: ${esc(ci.mode)}<br>Smart contract: ${esc(ci.contract_address)}<br>Bloco atual: ${ci.block}`;
}

async function openContract(id) { S.current = await api(`/api/contracts/${id}`); render(S.current); loadList(); }

function render(c) {
  const head = `<div class="card">
    <div style="display:flex;justify-content:space-between;gap:12px;align-items:start">
      <div><h3>${esc(c.titulo)}</h3><div class="muted">Arquivo: ${esc(c.arquivo)} · <a href="/api/contracts/${c.id}/pdf" target="_blank">abrir PDF</a></div></div>
      ${badge(c.status)}</div>
    <div class="grid2">
      <div class="kv"><div class="k">Contratante</div><div class="v">${esc(c.contratante)}</div></div>
      <div class="kv"><div class="k">Contratada</div><div class="v">${esc(c.contratada)}</div></div>
      <div class="kv"><div class="k">Hash SHA-256 do contrato</div><div class="hash">${c.sha256}</div></div>
      <div class="kv"><div class="k">Registro on-chain</div><div class="v chain-ok">${c.registrado_onchain_em ? "✓ registrado · tx " + short(c.tx) : "—"}</div></div>
    </div></div>`;
  $("#detail").innerHTML = head + (c.status === "EM_REVISAO" ? reviewView(c) : obligationsView(c)) + timelineView(c);
  bind(c);
}

function reviewView(c) {
  const ex = c.extracao;
  const rows = ex.obrigacoes.map((o, i) => `<tr data-i="${i}">
    <td><input type="checkbox" class="inc" checked aria-label="Incluir a obrigação da cláusula ${esc(o.clausula)}"></td>
    <td style="width:64px"><input class="f" data-k="clausula" value="${esc(o.clausula)}" aria-label="Cláusula"></td>
    <td><input class="f" data-k="entregavel" value="${esc(o.entregavel)}" aria-label="Entregável da cláusula ${esc(o.clausula)}"><div class="muted" style="font-size:12px;margin-top:4px">${esc(o.descricao)}</div></td>
    <td style="width:170px"><select class="f" data-k="responsavel" aria-label="Responsável pela cláusula ${esc(o.clausula)}">${["CONTRATANTE", "CONTRATADA", ""].map(p => `<option ${p === o.responsavel ? "selected" : ""} value="${p}">${p || "— definir —"}</option>`).join("")}</select></td>
    <td style="width:150px"><input type="date" class="f" data-k="prazo" value="${o.prazo || ""}" aria-label="Prazo da cláusula ${esc(o.clausula)}"></td>
    <td style="width:200px"><input class="f" data-k="evidencia_esperada" value="${esc(o.evidencia_esperada)}" aria-label="Evidência esperada da cláusula ${esc(o.clausula)}"></td>
    <td class="conf ${o.confianca < .8 ? "low" : ""}">${(o.confianca ?? 0).toFixed(2)}</td></tr>`).join("");
  return `<div class="card">
    <h2>Revisão humana da extração</h2>
    <div class="note">A IA sugeriu <b>${ex.obrigacoes.length} obrigações</b> (provedor: ${esc(ex.provedor)}${ex.data_assinatura ? ", assinatura em " + fmtDate(ex.data_assinatura) : ""}).
      Confira, corrija o que precisar e confirme. Itens com confiança baixa aparecem em laranja.${ex.aviso ? "<br>" + esc(ex.aviso) : ""}</div>
    <div class="grid2">
      <div class="kv"><label class="k" for="rvA">Contratante</label><input id="rvA" value="${esc(ex.contratante)}" style="width:100%" autocomplete="off"></div>
      <div class="kv"><label class="k" for="rvB">Contratada</label><input id="rvB" value="${esc(ex.contratada)}" style="width:100%" autocomplete="off"></div>
    </div>
    <table style="margin-top:14px"><thead><tr><th></th><th>Cl.</th><th>Entregável / texto da cláusula</th><th>Responsável</th><th>Prazo</th><th>Evidência esperada</th><th>Conf.</th></tr></thead>
    <tbody>${rows}</tbody></table>
    <div style="margin-top:14px;text-align:right"><button type="button" class="btn primary" id="confirmBtn">Confirmar e registrar na blockchain</button></div>
  </div>`;
}

function obligationsView(c) {
  const total = c.obrigacoes.length, done = c.obrigacoes.filter(o => ["APROVADO", "CONCLUIDO"].includes(o.status)).length;
  const late = c.obrigacoes.filter(o => o.atrasada).length;
  const rows = c.obrigacoes.map(o => {
    const isExec = S.role === o.responsavel;
    const moves = (isExec ? EXEC : APPR)[o.status] || [];
    const acts = moves.map(m => m === "ENTREGUE"
      ? `<label class="btn small primary">${ACTION[m]}<input type="file" class="evid vh" data-id="${o.id}" aria-label="Arquivo de evidência da cláusula ${esc(o.clausula)}"></label>`
      : `<button type="button" class="btn small ${m === "REJEITADO" ? "" : "primary"} mv" data-id="${o.id}" data-to="${m}">${ACTION[m]}</button>`).join("");
    const ev = o.evidencias.map(e => `<div class="hash">📎 ${esc(e.nome_original)} · ${short(e.sha256)}</div>`).join("");
    return `<tr>
      <td class="mono">${esc(o.clausula)}</td>
      <td><b>${esc(o.entregavel)}</b>${o.editada ? ' <span class="muted" style="font-size:11px">(corrigida)</span>' : ""}
        <div class="muted" style="font-size:12px">Evidência esperada: ${esc(o.evidencia_esperada || "—")}</div>${ev}</td>
      <td>${esc(o.responsavel)}</td>
      <td class="${o.atrasada ? "late" : ""}">${fmtDate(o.prazo)}${o.atrasada ? "<br>em atraso" : ""}</td>
      <td>${badge(o.status)}<div class="${o.onchain_status === o.status ? "chain-ok" : "late"}">${o.onchain_status === o.status ? "✓ estado on-chain" : "⚠ estado divergente"}</div>
        <div class="${o.dados_integros ? "chain-ok" : "late"}">${o.dados_integros ? "✓ dados íntegros" : "⚠ dados alterados fora do sistema"}</div></td>
      <td><div class="actions">${acts || '<span class="muted" style="font-size:12px">—</span>'}</div></td></tr>`;
  }).join("");
  return `<div class="card">
    <h2>Obrigações</h2>
    <div class="grid2" style="margin:0 0 12px">
      <div class="kv"><div class="k">Total</div><div class="v">${total}</div></div>
      <div class="kv"><div class="k">Aprovadas/concluídas</div><div class="v">${done}</div></div>
      <div class="kv"><div class="k">Em atraso</div><div class="v ${late ? "late" : ""}">${late}</div></div>
    </div>
    <div class="note" style="margin-bottom:10px">Você atua como <b>${S.role}</b>: executa as obrigações sob sua responsabilidade e analisa as entregas da outra parte.</div>
    <table><thead><tr><th>Cl.</th><th>Obrigação</th><th>Responsável</th><th>Prazo</th><th>Estado</th><th>Ações</th></tr></thead><tbody>${rows}</tbody></table>
  </div>`;
}

const TIPO = { CONTRATO_CADASTRADO: "Contrato cadastrado", EXTRACAO_SUGERIDA: "Extração sugerida pela IA",
  OBRIGACAO_CRIADA: "Obrigação criada", MUDANCA_DE_ESTADO: "Mudança de estado" };
function timelineView(c) {
  const cl = Object.fromEntries(c.obrigacoes.map(o => [o.id, o.clausula]));
  const items = c.eventos.map(e => `<li>
    <div class="muted" style="font-size:12px">${e.timestamp.replace("T", " ")}</div>
    <div><b>${TIPO[e.tipo] || esc(e.tipo)}</b>${e.entidade === "obrigacao" && cl[e.entidade_id] ? ` <span class="mono">· cl. ${esc(cl[e.entidade_id])}</span>` : ""}${e.estado_anterior ? ` · ${badge(e.estado_anterior)} → ${badge(e.estado_posterior)}` : e.estado_posterior ? " · " + badge(e.estado_posterior) : ""}
      <span class="muted"> por ${esc(e.usuario)}${e.papel && e.papel !== "SISTEMA" ? " (" + esc(e.papel) + ")" : ""}</span>
      ${e.observacao ? `<div class="muted" style="font-size:12px">${esc(e.observacao)}</div>` : ""}
      ${e.tx ? `<div class="hash">tx ${short(e.tx)} · bloco ${e.bloco}${e.hash_relacionado ? " · hash " + short(e.hash_relacionado) : ""}</div>` : ""}</div></li>`).join("");
  return `<div class="card"><h2>Trilha de auditoria</h2><ul class="timeline">${items}</ul></div>`;
}

function bind(c) {
  const cb = $("#confirmBtn");
  if (cb) cb.onclick = async () => {
    const ex = c.extracao;
    const obrigacoes = [...document.querySelectorAll("tbody tr[data-i]")].filter(tr => tr.querySelector(".inc").checked).map(tr => {
      const orig = ex.obrigacoes[+tr.dataset.i], o = { descricao: orig.descricao, confianca: orig.confianca };
      tr.querySelectorAll(".f").forEach(f => o[f.dataset.k] = f.value || (f.dataset.k === "prazo" ? null : ""));
      o.editada = ["clausula", "entregavel", "responsavel", "prazo", "evidencia_esperada"].some(k => (o[k] || "") !== (orig[k] || ""));
      return o;
    });
    try {
      cb.disabled = true;
      S.current = await api(`/api/contracts/${c.id}/confirmar`, { method: "POST", headers: { "content-type": "application/json" },
        body: JSON.stringify({ usuario: $("#userName").value, contratante: $("#rvA").value, contratada: $("#rvB").value, obrigacoes }) });
      toast(`${obrigacoes.length} obrigações confirmadas e registradas on-chain`); render(S.current); loadList();
    } catch (e) { cb.disabled = false; toast(e.message, true); }
  };
  document.querySelectorAll(".mv").forEach(b => b.onclick = () => move(b.dataset.id, b.dataset.to));
  document.querySelectorAll(".evid").forEach(i => i.onchange = () => i.files[0] && move(i.dataset.id, "ENTREGUE", i.files[0]));
}

async function move(id, to, file) {
  const fd = new FormData();
  fd.append("para", to); fd.append("usuario", $("#userName").value); fd.append("papel", S.role);
  if (to === "REJEITADO") { const m = prompt("Motivo da rejeição:"); if (m === null) return; fd.append("observacao", m); }
  if (file) fd.append("evidencia", file);
  try { await api(`/api/obligations/${id}/transicao`, { method: "POST", body: fd }); toast(`${LABEL[to]} · registrado on-chain`); openContract(S.current.id); }
  catch (e) { toast(e.message, true); }
}

$("#upload").onchange = async e => {
  const f = e.target.files[0]; if (!f) return;
  const fd = new FormData(); fd.append("arquivo", f); fd.append("usuario", $("#userName").value);
  const lab = $("#uploadLabel"); lab.setAttribute("aria-busy", "true"); toast("Processando o contrato…");
  try { const r = await api("/api/contracts", { method: "POST", body: fd }); toast("Contrato registrado. Revise a extração e confirme."); openContract(r.id); }
  catch (err) { toast(err.message, true); }
  finally { lab.removeAttribute("aria-busy"); }
  e.target.value = "";
};
$("#sampleBtn").onclick = async () => {
  const b = $("#sampleBtn"); b.disabled = true; b.setAttribute("aria-busy", "true"); toast("Processando o contrato de exemplo…");
  try { const r = await api("/api/contracts/exemplo", { method: "POST" }); toast("Contrato registrado. Revise a extração e confirme."); openContract(r.id); }
  catch (e) { toast(e.message, true); }
  finally { b.disabled = false; b.removeAttribute("aria-busy"); }
};
$("#verifyFile").onchange = async e => {
  const f = e.target.files[0]; if (!f) return;
  const fd = new FormData(); fd.append("arquivo", f);
  const r = await api("/api/verificar", { method: "POST", body: fd });
  $("#verifyOut").innerHTML = `<div class="${r.integro ? "result-ok" : "result-bad"}">${r.integro ? "✓" : "✗"} ${esc(r.mensagem)}
    ${r.tipo ? "<br>Tipo: " + r.tipo + (r.obrigacao_id ? " (obrigação #" + r.obrigacao_id + ")" : "") : ""}${r.tx ? "<br><span class='hash'>tx " + short(r.tx) + "</span>" : ""}${r.registrado_em ? "<br>Registrado em " + r.registrado_em.replace("T", " ") : ""}</div><div class="hash" style="margin-top:6px">${r.sha256}</div>`;
  e.target.value = "";
};
loadList().then(() => { const m = location.hash.match(/c=(\d+)/); if (m) openContract(+m[1]); });
