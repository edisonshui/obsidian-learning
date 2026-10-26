// Flash: the window. Screens are drawn from learn-status.py --json; the tutor
// runs in a real terminal; the live log is read from the subject's log.md.
"use strict";

const { esc, inline, renderMd, typeset } = window.MD;
const F = window.flash;
const $ = (id) => document.getElementById(id);

// ---------- state ----------
let S = null, cfg = null, info = null;
let route = { name: "home", slug: null };
let setupInfo = null;
const scrolls = {};
const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
const DAYS = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];
const SUBJECT_ROUTES = ["session", "progress", "map"];
const MAPS = ["map", "system"];
const NAMES = { home: "Home", session: "Session", system: "All skills", dashboard: "Dashboard", progress: "Progress", map: "Skill map", setup: "Set up" };

// ---------- small helpers ----------
const icon = (id, cls = "") => `<svg class="i ${cls}" aria-hidden="true"><use href="#${id}"/></svg>`;
const isMac = () => !info || info.platform === "darwin";
const key = (k) => (isMac() ? "⌘" : "Ctrl+Shift+") + k;
const keyAlt = (k) => (isMac() ? "⌥⌘" : "Ctrl+Shift+Alt+") + k;
const keyShift = (k) => (isMac() ? "⇧⌘" : "Ctrl+Shift+Alt+") + k;
const cap = (t) => (t ? t[0].toUpperCase() + t.slice(1) : t);
const sentence = (t) => (!t ? "" : /[.?!]$/.test(t.trim()) ? t.trim() : t.trim() + ".");
const isoDate = (t) => (/^\d{4}-\d{2}-\d{2}/.test(t || "") ? new Date(t.slice(0, 10) + "T12:00:00") : null);
const shortD = (t) => { const d = isoDate(t); return d ? `${d.getDate()} ${MONTHS[d.getMonth()]}` : ""; };
const longD = (t) => { const d = isoDate(t); return d ? `${d.getDate()} ${MONTHS[d.getMonth()]} ${d.getFullYear()}` : ""; };
const subj = (slug) => (S && S.subjects.find((s) => s.slug === slug)) || null;
const dotColor = (s) => `var(--subject-${(s && s.theme) || "calm"})`;
const dot = (s) => `<i class="dot" style="background:${dotColor(s)}"></i>`;
const lightOf = (s) => `--s:var(--holo-${(s && s.theme) || "calm"})`;
// The sidebar's short name: the record title up to its first dash or parenthesis.
const shortTitle = (s) => String(s.title || s.slug).replace(/\s+[—–-]\s+.*$/, "").replace(/\s*\(.*\)\s*$/, "");
const courseCode = (s) => (s.title.match(/^[A-Z]{2,5} \d{2,3}/) || [shortTitle(s)])[0];
const afterCode = (s) => s.title.replace(/^[A-Z]{2,5} \d{2,3}\s+/, "");
// Node names carry their strand, "(S2)", which is the tutor's bookkeeping.
const nodeName = (n) => String(n || "").replace(/\s*\(S\d+\)\s*$/, "");
const md = (t) => inline(nodeName(t));
const sigil = () => (cfg && cfg.host === "codex" ? "$" : "/");
const tutorName = () => (cfg && cfg.host === "codex" ? "Codex" : "Claude Code");
const firstName = () => (cfg && cfg.name) || (info && info.firstName) || "";

function greeting() {
  const h = new Date().getHours();
  const part = h < 5 ? "Good evening" : h < 12 ? "Good morning" : h < 18 ? "Good afternoon" : "Good evening";
  return firstName() ? `${part}, ${firstName()}` : part;
}
function dayWord(days) {
  if (days === 0) return "Today";
  if (days === 1) return "Tomorrow";
  const d = new Date(S.today + "T12:00:00");
  d.setDate(d.getDate() + days);
  return days < 7 ? DAYS[d.getDay()] : shortD(d.toISOString());
}

// The ranking speaks the vault's own words ("nodes", "s01 note"). The app says
// what happens instead (vault-design, Voice).
function plain(found) {
  const s = found.subject ? subj(found.subject) : null;
  let reason = String(found.reason || "").replace(/\*/g, "");
  reason = reason.replace(/\s*Its open s\d+ note is closed out first\./, "").replace(/\bnodes\b/g, "skills").replace(/\bnode\b/g, "skill");
  reason = reason.replace(/\s*\(S\d+\)/g, "");
  let why = null;
  if (found.kind === "Deadline") {
    const m = reason.match(/^deadline ([^:]+):\s*(.*)$/);
    if (m) { why = cap(`deadline ${m[1]}`); reason = m[2]; }
  }
  if (found.kind === "Repair") reason = reason.replace(/^(.*) slipped on (.*)$/, "Worth a refresh: $1. It slipped on $2");
  if (s && s.status === "diagnosing") reason = "a few more questions to find where you start";
  return { why, line: sentence(cap(reason)) };
}
const VERB = { Deadline: "Resume", Repair: "Repair", Review: "Review", Resume: "Resume", Start: "Start", "Continue a break": "Resume" };

// ---------- clicks: one listener, actions by name ----------
const ACTIONS = {};
document.addEventListener("click", (e) => {
  const link = e.target.closest("a.lnk[data-href]");
  if (link) { e.preventDefault(); F.openExternal(link.dataset.href); return; }
  const el = e.target.closest("[data-act]");
  if (!el || el.disabled) return;
  const fn = ACTIONS[el.dataset.act];
  if (fn) { e.preventDefault(); fn(el.dataset.arg, el, e); }
});
document.addEventListener("mouseover", (e) => {
  const el = e.target.closest("[data-prefetch]");
  if (el) prefetchSession(el.dataset.prefetch);
});

// ---------- routing ----------
function routeKey(r = route) { return SUBJECT_ROUTES.includes(r.name) ? `${r.name}/${r.slug}` : r.name; }
function swap(paint) {
  const calm = matchMedia("(prefers-reduced-motion: reduce)").matches;
  if (document.startViewTransition && !calm) document.startViewTransition(paint); else paint();
}
function go(name, slug) {
  if (!S && name !== "setup") return;
  if (SUBJECT_ROUTES.includes(name) && !slug) slug = route.slug || defaultSlug();
  if (SUBJECT_ROUTES.includes(name) && !subj(slug)) return;
  const before = routeKey();
  scrolls[before] = $("screen").scrollTop;
  route = { name, slug: slug || route.slug };
  const after = routeKey();
  if (before === after) return render();
  swap(() => {
    render();
    // A new screen opens at the top; coming back returns to where you were.
    $("screen").scrollTop = scrolls[after] || 0;
  });
}
function defaultSlug() {
  if (!S) return null;
  const top = S.ranked.find((x) => x.subject);
  return top ? top.subject : S.subjects[0] && S.subjects[0].slug;
}

function render() {
  if (route.name === "setup") return paintSetup();
  if (!S) return;
  if (route.slug && !subj(route.slug)) route.slug = defaultSlug();
  paintRail(); paintSide(); paintChrome();
  const s = subj(route.slug);
  $("ttl").textContent = SUBJECT_ROUTES.includes(route.name) && s ? `${s.title} · ${NAMES[route.name]}` : NAMES[route.name];
  const inSession = route.name === "session";
  $("session").classList.toggle("hidden", !inSession);
  $("screen").classList.toggle("hidden", inSession);
  const theme = SUBJECT_ROUTES.includes(route.name) && s ? s.theme
    : route.name === "home" && S.ranked[0] && S.ranked[0].subject ? (subj(S.ranked[0].subject) || {}).theme : "calm";
  document.documentElement.style.setProperty("--s", `var(--holo-${theme || "calm"})`);
  // Ambient light on reading screens; Home has its wash, the maps their graphite.
  $("ambientBg").classList.toggle("on", ["dashboard", "progress"].includes(route.name));
  if (inSession) return paintSession();
  ({ home: paintHome, dashboard: paintDashboard, system: paintSystem, progress: paintProgress, map: paintMap })[route.name]();
}

// ---------- shell ----------
function paintChrome() {
  const side = $("side"), sb = $("sideBtn"), pb = $("panelBtn");
  side.classList.toggle("hide", !cfg.sidebar);
  sb.classList.toggle("on", cfg.sidebar);
  sb.setAttribute("aria-label", cfg.sidebar ? "Hide sidebar" : "Show sidebar");
  sb.dataset.tip = `${cfg.sidebar ? "Hide" : "Show"} sidebar  ${key("\\")}`;
  $("searchBtn").dataset.tip = `Search and commands  ${key("K")}`;
  $("searchBtn").dataset.tipSide = "left-down";
  pb.style.display = route.name === "session" ? "" : "none";
  pb.classList.toggle("on", cfg.panel);
  pb.setAttribute("aria-label", cfg.panel ? "Hide panel" : "Show panel");
  pb.dataset.tip = `${cfg.panel ? "Hide" : "Show"} panel  ${keyAlt("0")}`;
  pb.dataset.tipSide = "left-down";
}
function paintRail() {
  const items = [["home", "home", "Home", "1"], ["session", "terminal", "Session", "2"], ["system", "map", "All skills", "3"], ["dashboard", "book", "Dashboard", "4"]];
  $("rail").innerHTML = items.map(([r, ic, name, k]) => {
    const on = route.name === r || (r === "session" && false);
    const live = r === "session" && T.running && route.name !== "session" ? " live" : "";
    return `<button class="${on ? "on" : ""}${live}" data-act="go" data-arg="${r}" aria-label="${name}" data-tip="${name}  ${key(k)}" data-tip-side="right">${icon(ic)}</button>`;
  }).join("") + `<span class="sp"></span><button data-act="settings" aria-label="Settings" data-tip="Settings  ${key(",")}" data-tip-side="right">${icon("gear")}</button>`;
}
let doneOpen = false;
function rightTag(s) {
  if (s.days_to_deadline !== null && s.days_to_deadline >= 0 && s.days_to_deadline < 7) return dayWord(s.days_to_deadline);
  const m = (s.pending || "").match(/^(\d+)/);
  return m ? m[1] : "";
}
function paintSide() {
  const el = $("side");
  const due = S.subjects.reduce((n, s) => n + s.nodes.filter((x) => x.due).length, 0);
  const repairs = S.ranked.filter((x) => x.kind === "Repair");
  const live = S.subjects.filter((s) => s.status !== "done");
  const done = S.subjects.filter((s) => s.status === "done");
  const row = (s) => {
    const on = s.slug === route.slug && SUBJECT_ROUTES.includes(route.name);
    const tag = rightTag(s);
    let h = `<button class="srow ${on ? "on" : ""}" data-prefetch="${s.slug}" data-act="subject" data-arg="${s.slug}" title="${esc(s.title)}">${dot(s)}<span>${esc(shortTitle(s))}</span><span class="n">${esc(tag)}</span></button>`;
    if (on) {
      h += ["session:terminal:Session", "map:map:Skill map", "progress:chart:Progress"].map((x) => {
        const [r, ic, name] = x.split(":");
        return `<button class="srow sub ${route.name === r ? "on" : ""}" data-act="go-subject" data-arg="${r}">${icon(ic, "sm")}${name}</button>`;
      }).join("");
    }
    return h;
  };
  el.innerHTML = `<div class="wordmark">${esc(info.name)}</div><div class="scroll">
    <button class="search" data-act="palette" data-tip="${key("K")}">${icon("search", "sm")}Search</button>
    <h4>Today</h4>
    <button class="srow" data-act="review" ${due ? "" : "disabled"}>${icon("cards", "sm ink3")}Reviews due<span class="n">${due}</span></button>
    <button class="srow" data-act="repair" ${repairs.length ? "" : "disabled"}>${icon("refresh", "sm ink3")}To repair<span class="n">${repairs.length}</span></button>
    <h4>Subjects</h4>
    ${live.map(row).join("") || `<div class="t-cap" style="padding:4px 8px">No subjects yet.</div>`}
    ${done.length ? `<button class="srow ink2" data-act="toggle-done" aria-expanded="${doneOpen}">${icon(doneOpen ? "down" : "chev", "sm")}Done<span class="n">${done.length}</span></button>` : ""}
    ${doneOpen ? done.map(row).join("") : ""}
  </div>`;
}

// ---------- running things ----------
// Every command goes to the tutor's terminal, exactly as the learner would type it.
function command(cmd) { return sigil() + cmd; }
function run(found) {
  if (!found || !found.command) return toast("Nothing to run right now.");
  const slug = found.subject || (found.command.match(/^learn-\w+ ([a-z0-9-]+)/) || [])[1] || route.slug;
  runTyped(found.typed || command(found.command), slug);
}
function runTyped(text, slug) {
  if (slug && subj(slug)) route.slug = slug;
  go("session", route.slug);
  tutorSend(text);
}
ACTIONS.go = (r) => go(r);
ACTIONS["go-subject"] = (r) => go(r, route.slug);
ACTIONS.subject = (slug) => go(SUBJECT_ROUTES.includes(route.name) ? route.name : "progress", slug);
ACTIONS["toggle-done"] = () => { doneOpen = !doneOpen; paintSide(); };
ACTIONS.review = () => run(S.ranked.find((x) => x.kind === "Review") || { command: "learn-review" });
ACTIONS.repair = () => run(S.ranked.find((x) => x.kind === "Repair"));
ACTIONS.start = () => runTyped(command("learn-start"), null);
ACTIONS.run = (i) => run(S.ranked[+i]);
ACTIONS.resume = (slug) => run(S.ranked.find((x) => x.subject === slug && x.kind !== "Repair") || { command: `learn-resume ${slug}`, subject: slug });
ACTIONS.practice = (slug) => run({ command: `learn-practice ${slug}`, subject: slug });
ACTIONS["toggle-side"] = () => { setCfg({ sidebar: !cfg.sidebar }); paintChrome(); };
ACTIONS["toggle-panel"] = () => { setCfg({ panel: !cfg.panel }); paintChrome(); paintPanelShell(); fitSoon(); };
let inkAction = null;
ACTIONS.ink = () => inkAction && inkAction();

async function setCfg(patch) { cfg = { ...cfg, ...patch }; cfg = await F.setConfig(patch); }

// ---------- Home ----------
let optsOpen = false;
function paintHome() {
  const top = S.ranked[0], s = top && top.subject ? subj(top.subject) : null;
  inkAction = () => run(top);
  const { why, line } = plain(top);
  const others = S.ranked.slice(1);
  const dueN = S.subjects.reduce((n, x) => n + x.nodes.filter((y) => y.due).length, 0);
  const repairs = others.filter((x) => x.kind === "Repair");
  const bar = s && s.total ? `<div class="bar" style="margin-top:14px" title="${s.proven} of ${s.total} skills passed"><i style="width:${Math.round((100 * s.proven) / s.total)}%"></i></div>` : "";
  $("screen").innerHTML = `<div class="holo-page"><div class="holo-wash" style="${lightOf(s)}"></div>
    <div class="holo-content" style="width:600px;max-width:calc(100% - 48px);margin:0 auto;padding:clamp(40px,10vh,96px) 0 80px">
      <h1 class="t-title" style="text-align:center;margin:0 0 28px">${esc(greeting())}</h1>
      <div class="card float" style="padding:20px 22px">
        ${why ? `<div class="ember-t" style="font-size:11.5px;line-height:16px;font-weight:700;margin-bottom:8px">${esc(why)}</div>` : ""}
        ${s ? `<div class="t-cap" style="display:flex;align-items:center;gap:6px">${dot(s)}${esc(courseCode(s))}</div>` : ""}
        <div class="t-head" style="margin-top:2px">${s ? md(afterCode(s)) : top.kind === "Review" ? "Review across subjects" : "Start something new"}</div>
        <div class="t-ui ink2" style="margin-top:4px">${md(line)}</div>
        ${bar}
        <div style="margin-top:16px"><button class="btn ink" data-act="ink" data-prefetch="${s ? s.slug : ""}" data-tip="${key("↩")}">${VERB[top.kind] || "Start"}</button></div>
      </div>
      <div style="display:flex;gap:8px;justify-content:center;margin-top:14px;flex-wrap:wrap">
        ${dueN && top.kind !== "Review" ? `<button class="pill" data-act="review" data-tip="${key("R")}">${icon("cards", "sm")}Review ${dueN} due</button>` : ""}
        ${repairs.length ? `<button class="pill" data-act="repair">${icon("refresh", "sm")}Repair ${repairs.length}</button>` : ""}
        ${top.kind !== "Start" ? `<button class="pill" data-act="start" data-tip="${key("N")}">${icon("flag", "sm")}Start a subject</button>` : ""}
        ${others.length ? `<button class="pill" data-act="home-more" aria-expanded="${optsOpen}">${icon(optsOpen ? "down" : "chev", "sm")}${optsOpen ? "Fewer" : "More"}</button>` : ""}
      </div>
      ${optsOpen ? `<div class="card" style="margin-top:12px;padding:4px 16px">${others.map((o, k) => {
        const os = o.subject ? subj(o.subject) : null;
        const p = plain(o);
        return `<button class="row" style="grid-template-columns:14px 80px 1fr;gap:8px" data-act="run" data-arg="${k + 1}" data-prefetch="${os ? os.slug : ""}">${os ? dot(os) : "<i></i>"}<span class="t-ui" style="font-weight:700">${esc(o.kind === "Continue a break" ? "Resume" : o.kind)}</span><span class="t-ui">${os ? esc(shortTitle(os)) : "Any subject"}<span class="ink3"> · ${md([p.why, p.line].filter(Boolean).join(". "))}</span></span></button>`;
      }).join("")}</div>` : ""}
    </div></div>`;
}
ACTIONS["home-more"] = () => { optsOpen = !optsOpen; paintHome(); };

// ---------- Dashboard ----------
let badgesOpen = false;
function badgeName(b) { return b.kind === "Goal met" ? shortTitle({ title: b.title }) : nodeName(b.name); }
const BADGE_FOIL = { Solid: ["f-gold", "star"], Recovered: ["f-mint", "refresh"], "Goal met": ["f-goal", "flag"] };
function badgeEl(b, size) {
  const [f, ic] = BADGE_FOIL[b.kind] || BADGE_FOIL.Solid;
  const isz = Math.round(size / 2);
  return `<i class="badge ${f}" style="width:${size}px;height:${size}px"><svg class="i" style="width:${isz}px;height:${isz}px"><use href="#${ic}"/></svg></i>`;
}
function paintDashboard() {
  const top = S.ranked[0];
  inkAction = () => run(top);
  const solid = S.subjects.reduce((n, s) => n + s.nodes.filter((x) => x.status === "solid").length, 0);
  const groups = [["Active", (s) => s.status === "active" || s.status === "diagnosing"], ["Paused", (s) => s.status === "paused"], ["Done", (s) => s.status === "done"]];
  const recallOnly = S.subjects.reduce((n, s) => n + s.recall_only, 0);
  const list = groups.map(([g, f]) => {
    const rows = S.subjects.filter(f).sort((a, b) => (b.last_session || "").localeCompare(a.last_session || ""));
    if (!rows.length) return "";
    return `<div class="t-ui" style="font-weight:700;color:var(--color-ink-2);padding:12px 0 4px">${g}</div>` + rows.map((s) => {
      const meter = s.total ? `<span class="meter" title="${s.proven} of ${s.total} skills passed"><i style="width:${Math.round((100 * s.proven) / s.total)}%"></i></span>` : "<span></span>";
      const dl = s.days_to_deadline;
      const tag = (s.pending || "").includes("repair") ? `${icon("refresh", "sm")}${esc(s.pending)}`
        : dl !== null && dl >= 0 ? `${icon("flag", "sm")}Deadline ${dayWord(dl).toLowerCase()}`
        : s.pending ? esc(s.pending.replace(" for review", "")) : s.goal_met ? "Goal met" : "";
      return `<button class="row t-ui" style="grid-template-columns:16px 1fr 88px 56px 150px" data-act="subject-progress" data-arg="${s.slug}" data-prefetch="${s.slug}">${dot(s)}<span style="padding-right:8px">${md(s.title)}</span>${meter}<span class="ink3">${shortD(s.last_session)}</span><span class="ink2" style="display:flex;gap:4px;align-items:center;justify-content:flex-end;white-space:nowrap">${tag}</span></button>`;
    }).join("");
  }).join("");
  const badges = S.rewards_on && S.badges.length ? `<div class="card" style="padding:14px 16px">
      <div style="display:flex;align-items:center"><span class="t-ui" style="font-weight:700">Recently earned</span>${S.badges.length > 3 ? `<button class="btn txt" style="margin-left:auto;font-size:11.5px" data-act="badges-more">${badgesOpen ? "Fewer" : `All ${S.badges.length}`}</button>` : ""}</div>
      <div style="display:grid;grid-template-columns:repeat(3,1fr);gap:12px 10px;margin-top:10px;text-align:center">
      ${S.badges.slice(0, badgesOpen ? 999 : 3).map((b) => `<div title="${esc(b.text)}"><div style="display:flex;justify-content:center">${badgeEl(b, 44)}</div><div style="font-size:11px;line-height:14px;font-weight:700;margin-top:6px">${esc(b.kind)}: ${md(badgeName(b))}</div><div class="ink3" style="font:10px/14px var(--font-mono)">${longD(b.date)}</div></div>`).join("")}
      </div></div>` : "";
  $("screen").innerHTML = `<div class="holo-content" style="padding:28px 32px 80px;max-width:1200px">
    <div style="display:flex;align-items:flex-end;gap:12px;flex-wrap:wrap">
      <h1 class="t-title">All subjects</h1>
      <button style="margin-left:auto" class="btn sec sm" data-act="start" data-tip="${key("N")}">Start a subject</button>
      <button class="btn ink" data-act="ink" data-tip="${key("↩")}">${VERB[top.kind] || "Start"}${top.subject ? " " + esc(shortTitle(subj(top.subject))) : ""}</button>
    </div>
    <div style="display:grid;grid-template-columns:minmax(0,1fr) 300px;gap:28px;margin-top:22px">
      <div>
        <div style="display:grid;grid-template-columns:repeat(${S.rewards_on ? 4 : 2},1fr);gap:10px;margin-bottom:20px">
          <div class="tile"><div class="t-num c-gold">${solid}</div><div class="lb">Skills solid</div></div>
          <div class="tile"><div class="t-num c-green">${S.counts.nodes_proven}</div><div class="lb">Skills passed</div></div>
          ${S.rewards_on ? `<div class="tile"><div class="t-num ember-t">${S.counts.current_streak}</div><div class="lb">Week streak</div></div>
          <div class="tile"><div class="t-num">${S.counts.goals_met}</div><div class="lb">Goals met</div></div>` : ""}
        </div>
        <div class="card" style="padding:4px 16px 8px">${list || `<div class="t-ui ink2" style="padding:16px 0">No subjects yet. Start one to see it here.</div>`}</div>
      </div>
      <div style="display:flex;flex-direction:column;gap:14px">
        ${S.rewards_on ? streakCard() : ""}
        <div class="card" style="padding:14px 16px"><div class="t-ui" style="font-weight:700;margin-bottom:8px">Checks passed</div>${heat(S.heat, 16)}</div>
        ${badges}
        ${recallOnly ? `<div class="card" style="padding:12px 16px"><div class="t-ui">${recallOnly} skills passed from memory only</div><div class="t-cap" style="margin-top:2px">A review asks one of them a new way.</div></div>` : ""}
      </div>
    </div></div>`;
}
ACTIONS["badges-more"] = () => { badgesOpen = !badgesOpen; paintDashboard(); };
ACTIONS["subject-progress"] = (slug) => go("progress", slug);

function streakCard() {
  const weeks = S.streak.weeks.slice(-8);
  const disc = (w) => w.result === "pass" || w.result === "repaired" ? `<i title="Week of ${longD(w.start)}">${icon("check")}</i>`
    : w.result === "pending" ? `<i class="empty" title="Week of ${longD(w.start)}: still open"></i>`
    : w.result === "miss" ? `<i class="miss" title="Week of ${longD(w.start)}: missed"></i>`
    : `<i class="none" title="Week of ${longD(w.start)}: nothing due"></i>`;
  return `<div class="card" style="padding:14px 16px">
    <div style="display:flex;align-items:center;gap:10px"><span class="t-num ember-t">${S.streak.current}</span><span class="t-ui" style="font-weight:700">${S.streak.current === 1 ? "week" : "weeks"} of reviews</span></div>
    <div class="streak" style="margin-top:10px">${weeks.map(disc).join("")}</div></div>`;
}
function subjectWeeks(s) {
  const first = Object.keys(s.heat).sort()[0];
  if (!first) return 6;
  return Math.max(6, Math.min(16, Math.ceil((new Date(S.today) - new Date(first)) / 6048e5) + 1));
}
function heat(data, weeks) {
  const today = new Date(S.today + "T12:00:00");
  const end = new Date(today); end.setDate(end.getDate() + (7 - (end.getDay() || 7)));
  const start = new Date(end); start.setDate(end.getDate() - 7 * weeks + 1);
  const lvl = (n) => (!n ? "" : n <= 2 ? "h1" : n <= 5 ? "h2" : n <= 9 ? "h3" : "h4");
  let h = "";
  for (let d = new Date(start); d <= end; d.setDate(d.getDate() + 1)) {
    const k = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
    const n = data[k] || 0;
    h += `<i class="${lvl(n)}${d > today ? " fut" : ""}" title="${longD(k)}: ${n} ${n === 1 ? "check" : "checks"} passed"></i>`;
  }
  return `<div class="heat">${h}</div>`;
}

// ---------- Progress ----------
function discClass(n, s) {
  if (n.status === "solid") return "solid";
  if (n.status === "checked" || n.status === "decayed") return "checked";
  if (n.status === "introduced") return "learn";
  if (n.status === "planned" && n.id === s.up_next) return "up";
  return "not";
}
function discEl(n, s, extra = "") {
  const c = discClass(n, s);
  const ic = c === "solid" ? icon("star") : c === "checked" ? icon("check") : "";
  const rf = n.status === "decayed" ? `<i class="rf">${icon("refresh")}</i>` : "";
  return `<i class="disc ${c} ${extra}">${ic}${rf}</i>`;
}
const STATUS_WORD = { solid: "Solid", checked: "Checked", decayed: "Worth a refresh", introduced: "Learning", planned: "Not yet" };
let canOpen = false;
function paintProgress() {
  const s = subj(route.slug);
  inkAction = () => ACTIONS.resume(s.slug);
  const canNow = s.nodes.filter((n) => ["checked", "solid", "decayed"].includes(n.status));
  const up = s.nodes.find((n) => n.id === s.up_next);
  const solid = s.nodes.filter((n) => n.status === "solid").length;
  const notes = s.notes.slice().reverse();
  const verb = s.status === "done" ? "Practice" : "Resume";
  inkAction = s.status === "done" ? () => ACTIONS.practice(s.slug) : () => ACTIONS.resume(s.slug);
  $("screen").innerHTML = `
    <div class="holo-content" style="padding:24px 28px 18px;display:flex;align-items:flex-end;gap:12px;flex-wrap:wrap">
      <h1 class="t-title" style="min-width:0;flex:1 1 400px">${md(s.title)}</h1>
      <button class="btn sec sm" data-act="go-subject" data-arg="map" data-tip="${key("6")}">${icon("map", "sm")}Skill map</button>
      <button class="btn ink" data-act="ink" data-prefetch="${s.slug}" data-tip="${key("↩")}">${verb}</button>
    </div>
    <div class="holo-content" style="display:grid;grid-template-columns:minmax(0,1fr) 270px;gap:24px;padding:8px 28px 80px;max-width:1200px">
      <div>
        ${s.total ? `<div class="card" style="padding:20px 16px"><div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(130px,1fr));gap:18px 8px">
          ${s.nodes.map((n) => `<div style="text-align:center" title="${STATUS_WORD[n.status] || ""}${n.checked && n.checked !== "—" ? ", last checked " + longD(n.checked) : ""}">
            <div style="display:flex;justify-content:center">${discEl(n, s)}</div>
            <div class="t-cap" style="color:var(--color-${discClass(n, s) === "not" ? "ink-3" : "ink"});margin-top:8px;${n.id === s.up_next ? "font-weight:700" : ""}">${md(n.name)}</div>
          </div>`).join("")}</div></div>` : `<div class="card" style="padding:20px"><div class="t-ui ink2">No plan yet. A few more questions to find where you start.</div></div>`}
        <div style="display:grid;grid-template-columns:1fr 1fr;gap:20px;margin-top:22px">
          <div><div class="t-sub">You can now</div>
            ${canNow.length ? `<ul style="list-style:none;margin-top:4px" class="t-ui">${canNow.slice(0, canOpen ? 999 : 4).map((n) => `<li style="display:flex;gap:6px;padding:3px 0"><span class="c-green">${icon("check", "sm")}</span><span>${md(cap(n.can_do))}.</span></li>`).join("")}</ul>
            ${canNow.length > 4 ? `<button class="btn txt" style="margin-left:16px" data-act="can-more">${canOpen ? "Fewer" : `${canNow.length - 4} more`}</button>` : ""}` : `<div class="t-ui ink2" style="margin-top:6px">Nothing passed yet.</div>`}
          </div>
          <div><div class="t-sub">Up next</div>
            <div class="t-ui" style="margin-top:6px">${up ? `<b>${md(up.name)}.</b> You'll be able to ${md(up.can_do)}.` : s.status === "done" ? "Goal met. Nothing left to teach." : "Nothing planned yet."}</div>
          </div>
        </div>
      </div>
      <div style="display:flex;flex-direction:column;gap:12px">
        <div class="lit-card" style="${lightOf(s)}">
          <div style="padding:16px 16px 22px">
            <div style="display:flex;align-items:center;justify-content:space-between"><span class="t-ui" style="font-weight:700">${esc(courseCode(s))}</span>${dot(s)}</div>
            <div class="t-ui" style="margin-top:34px">${md(afterCode(s))}</div>
            <div class="t-num" style="margin-top:2px">${s.total ? `${s.proven} of ${s.total} skills` : "No plan yet"}</div>
          </div>
          <div style="background:var(--color-surface);border-top:1px solid var(--color-line);padding:10px 16px;display:flex;justify-content:space-between;gap:12px">
            <span style="min-width:0"><span class="t-cap" style="color:var(--color-ink)">Next</span><br><span class="t-ui">${up ? md(up.name) : s.status === "done" ? "Goal met" : "A few more questions"}</span></span>
            ${s.deadline ? `<span style="text-align:right;flex:none"><span class="t-cap" style="color:var(--color-ink)">Deadline</span><br><span class="t-ui ${s.days_to_deadline !== null && s.days_to_deadline >= 0 ? "ember-t" : "ink2"}" style="font-weight:700">${shortD(s.deadline)}</span></span>` : ""}
          </div>
        </div>
        <div style="display:grid;grid-template-columns:1fr 1fr;gap:10px">
          <div class="tile"><div class="t-num c-gold">${solid}</div><div class="lb">Skills solid</div></div>
          <div class="tile"><div class="t-num c-green">${s.proven}</div><div class="lb">Skills passed</div></div>
          ${S.rewards_on ? `<div class="tile"><div class="t-num ember-t">${S.counts.current_streak}</div><div class="lb">Week streak</div></div>
          <div class="tile"><div class="t-num">${S.counts.best_streak}</div><div class="lb">Best streak</div></div>` : ""}
        </div>
        <div class="card" style="padding:12px 14px"><div class="t-ui" style="font-weight:700;margin-bottom:8px">Checks passed</div>${heat(s.heat, subjectWeeks(s))}</div>
        <div class="card" style="padding:8px 14px"><div class="t-ui" style="font-weight:700;padding:4px 0">Sessions</div>
          ${notes.length ? notes.slice(0, 6).map((n) => `<div class="srow" style="padding:0 0;cursor:default">${noteLabel(n.name)}<span class="n">${shortD(n.name)}</span></div>`).join("") : `<div class="t-cap" style="padding-bottom:6px">No sessions yet.</div>`}
        </div>
      </div>
    </div>`;
}
ACTIONS["can-more"] = () => { canOpen = !canOpen; paintProgress(); };
function noteLabel(name) {
  const m = String(name).match(/-([sr])0*(\d+)$/);
  return m ? `${m[1] === "s" ? "Session" : "Review"} ${m[2]}` : esc(name);
}

// ---------- Skill map ----------
let mapView = null;
function paintMap() {
  const s = subj(route.slug);
  inkAction = s.status === "done" ? () => ACTIONS.practice(s.slug) : () => ACTIONS.resume(s.slug);
  const el = $("screen");
  if (!s.nodes.length || !s.layout) {
    el.innerHTML = `<div class="skill-map map-empty" data-theme="night"><div><div class="t-head">No map yet</div><div class="t-ui ink2" style="margin-top:6px">${esc(shortTitle(s))} has no plan yet. A few more questions to find where you start.</div><button class="btn ink" style="margin-top:16px" data-act="ink">Resume</button></div></div>`;
    return;
  }
  const L = s.layout, W = 210, H = 92, GY = 64;
  const top = Math.max(...Object.values(L.rank));
  const X = (v) => 60 + L.x[v], Y = (v) => 50 + (top - L.rank[v]) * (H + GY), pos = {};
  s.nodes.forEach((n) => { pos[n.id] = { x: X(n.id) - W / 2 + 105, y: Y(n.id) }; });
  const edges = L.chains.map(([a, b, chain]) => {
    const pts = chain.map((v) => [X(v) + 105, Y(v) + H / 2]);
    pts[0][1] = Y(a);
    pts[pts.length - 1][1] = Y(b) + H;
    let d = `M${pts[0][0]} ${pts[0][1]}`;
    for (let i = 1; i < pts.length; i++) { const [x1, y1] = pts[i - 1], [x2, y2] = pts[i], m = (y1 + y2) / 2; d += ` C ${x1} ${m}, ${x2} ${m}, ${x2} ${y2}`; }
    return `<path d="${d}"/>`;
  }).join("");
  const widthPx = 120 + Math.max(...Object.values(L.x)) + W, heightPx = 100 + (top + 1) * (H + GY);
  const line = (n) => {
    const c = discClass(n, s);
    if (c === "not" || !n.can_do) return "";
    return `${c === "up" || c === "learn" ? "You'll be able to" : "You can"} ${md(n.can_do)}.`;
  };
  el.innerHTML = `<div class="mapwrap skill-map" data-theme="night" id="mapwrap">
    <div class="canvas" id="canvas" style="width:${widthPx}px;height:${heightPx}px">
      <svg width="${widthPx}" height="${heightPx}" style="position:absolute;left:0;top:0" stroke="#46464C" stroke-width="1.2" fill="none">${edges}</svg>
      ${s.nodes.map((n) => { const c = discClass(n, s); return `<div class="node ${c === "not" ? "not" : ""} ${c === "up" ? "upn" : ""}" style="left:${pos[n.id].x}px;top:${pos[n.id].y}px;min-height:${H}px" title="${STATUS_WORD[n.status] || ""}">${discEl(n, s, "s28")}<div><b>${md(n.name)}</b><span>${line(n)}</span></div></div>`; }).join("")}
    </div>
    <div class="card mapctl">
      <button class="btn txt" data-act="zoom" data-arg="in" aria-label="Zoom in" data-tip="${key("=")}" data-tip-side="up">+</button><button class="btn txt" data-act="zoom" data-arg="out" aria-label="Zoom out" data-tip="${key("-")}" data-tip-side="up">−</button><button class="btn txt" data-act="zoom" data-arg="fit" data-tip="${key("0")}" data-tip-side="up">Fit</button>
      <button class="btn ink sm" style="margin-left:6px" data-act="ink" data-tip="${key("↩")}" data-tip-side="up">${s.status === "done" ? "Practice" : "Resume"}</button>
    </div>
  </div>`;
  const wrap = $("mapwrap");
  const keyName = `map/${s.slug}`;
  mapView = mapViews[keyName] || null;
  if (!mapView) {
    const target = pos[s.up_next];
    if (target) mapView = { k: 1, x: wrap.clientWidth / 2 - (target.x + W / 2), y: wrap.clientHeight / 2 - (target.y + H / 2) };
    else fitMap(true);
  }
  mapViews[keyName] = mapView;
  applyMap();
  panZoom(wrap, keyName);
}
const mapViews = {};
function panZoom(wrap, keyName) {
  let dragging = null;
  wrap.onmousedown = (e) => { if (e.target.closest("button") || e.button !== 0) return; dragging = { x: e.clientX - mapView.x, y: e.clientY - mapView.y }; wrap.classList.add("drag"); };
  window.onmousemove = (e) => { if (dragging) { mapView.x = e.clientX - dragging.x; mapView.y = e.clientY - dragging.y; applyMap(); } };
  window.onmouseup = () => { dragging = null; wrap.classList.remove("drag"); mapViews[keyName] = mapView; };
  wrap.onwheel = (e) => {
    e.preventDefault();
    if (e.ctrlKey || e.metaKey) zoomBy(e.deltaY < 0 ? 1.08 : 1 / 1.08, e);
    else { mapView.x -= e.deltaX; mapView.y -= e.deltaY; applyMap(); }
    mapViews[keyName] = mapView;
  };
}
function applyMap() { const c = $("canvas"); if (c && mapView) c.style.transform = `translate(${mapView.x}px,${mapView.y}px) scale(${mapView.k})`; }
function zoomBy(f, e) {
  const wrap = $("mapwrap"); if (!wrap || !mapView) return;
  const r = wrap.getBoundingClientRect();
  const cx = e ? e.clientX - r.left : r.width / 2, cy = e ? e.clientY - r.top : r.height / 2;
  const k = Math.min(2.5, Math.max(0.3, mapView.k * f)), ratio = k / mapView.k;
  mapView.x = cx - (cx - mapView.x) * ratio; mapView.y = cy - (cy - mapView.y) * ratio; mapView.k = k;
  applyMap();
}
function fitMap(noApply) {
  const wrap = $("mapwrap"), c = $("canvas"); if (!wrap || !c) return;
  const k = Math.max(0.4, Math.min(1, wrap.clientWidth / c.offsetWidth, (wrap.clientHeight - 60) / c.offsetHeight));
  mapView = { k, x: (wrap.clientWidth - c.offsetWidth * k) / 2, y: (wrap.clientHeight - 60 - c.offsetHeight * k) / 2 };
  if (!noApply) applyMap();
}
ACTIONS.zoom = (how) => {
  if (!MAPS.includes(route.name)) return;
  if (how === "in") zoomBy(1.15); else if (how === "out") zoomBy(1 / 1.15); else fitMap();
  mapViews[route.name === "map" ? `map/${route.slug}` : "system"] = mapView;
};

// ---------- All skills ----------
// Edison's merge (17 Oct 2026): branches from You to each domain and on to each
// subject; subjects on three orbits; each subject a constellation of its skills
// with a glow of the domain color. Overlaps are inferred (skill_overlap.py).
const DOMAIN = { code: "Code", math: "Math", circuits: "Circuits", literature: "Literature", design: "Design", calm: "Other" };
const ORBIT = { active: 0, diagnosing: 0, paused: 1, done: 2 };
function statusOf(n, x) { return ({ solid: "m-solid", checked: "m-checked", decayed: "m-checked", introduced: "m-learn" })[n.status] || (n.id === x.up_next ? "m-up" : "m-not"); }
function paintSystem() {
  inkAction = () => run(S.ranked[0]);
  const el = $("screen");
  if (!S.subjects.length) { el.innerHTML = `<div class="skill-map map-empty" data-theme="night"><div class="t-ui ink2">No subjects yet.</div></div>`; return; }
  const C = 585, R = [235, 350, 465], RIM = 515, HUB = 140, rad = (d) => (d * Math.PI) / 180;
  const pt = (r, d) => [C + r * Math.cos(rad(d)), C + r * Math.sin(rad(d))];
  const byTheme = {};
  S.subjects.forEach((x) => (byTheme[x.theme || "calm"] ??= []).push(x));
  const themes = Object.keys(DOMAIN).filter((t) => byTheme[t]);
  let spans = themes.map((t) => Math.max(36, (360 * byTheme[t].length) / S.subjects.length));
  const k0 = 360 / spans.reduce((a, b) => a + b, 0); spans = spans.map((x) => x * k0);
  let a = -90 - spans[0] / 2;
  const sectors = [];
  themes.forEach((t, i) => { sectors.push({ t, from: a, to: a + spans[i] }); a += spans[i]; });
  const wedge = ({ from, to }) => { const [x1, y1] = pt(RIM, from), [x2, y2] = pt(RIM, to); return `M${C} ${C} L${x1} ${y1} A${RIM} ${RIM} 0 ${to - from > 180 ? 1 : 0} 1 ${x2} ${y2} Z`; };
  const bend = (x1, y1, x2, y2, pull = 0.45) => { const mx = (x1 + x2) / 2, my = (y1 + y2) / 2; return `M${x1.toFixed(1)} ${y1.toFixed(1)} Q${(C + (mx - C) * pull).toFixed(1)} ${(C + (my - C) * pull).toFixed(1)} ${x2.toFixed(1)} ${y2.toFixed(1)}`; };
  const label = (x) => { const words = shortTitle(x).split(" "), lines = [""]; words.forEach((w) => ((lines[lines.length - 1] + " " + w).trim().length > 18 ? lines.push(w) : (lines[lines.length - 1] = (lines[lines.length - 1] + " " + w).trim()))); return lines; };
  const tip = (x, n) => `<title>${esc(nodeName(n.name).replace(/`/g, ""))} · ${esc(shortTitle(x))}</title>`;
  const radial = (r0, a0, r1, a1) => { const [x0, y0] = pt(r0, a0), [x3, y3] = pt(r1, a1), rm = (r0 + r1) / 2, [x1, y1] = pt(rm, a0), [x2, y2] = pt(rm, a1); return `M${x0.toFixed(1)} ${y0.toFixed(1)} C${x1.toFixed(1)} ${y1.toFixed(1)} ${x2.toFixed(1)} ${y2.toFixed(1)} ${x3.toFixed(1)} ${y3.toFixed(1)}`; };
  const col = (t) => `var(--subject-${t})`;
  const planets = {};
  sectors.forEach(({ t, from, to }) => [0, 1, 2].forEach((o) => {
    const list = byTheme[t].filter((x) => (ORBIT[x.status] ?? 1) === o).sort((p, q) => (q.last_session || "").localeCompare(p.last_session || ""));
    list.forEach((x, k) => {
      const d = from + ((to - from) * (k + 1)) / (list.length + 1), r = R[o] + (list.length > 2 && k % 2 ? 56 : 0);
      const [px, py] = pt(r, d);
      planets[x.slug] = { x, px, py, d };
    });
  }));
  const pairs = {};
  S.overlaps.forEach((o) => { const k = [o.a, o.b].sort().join("|"); (pairs[k] ??= []).push(o); });
  const mid = Object.fromEntries(sectors.map((sc) => [sc.t, (sc.from + sc.to) / 2]));
  const reach = parseFloat(getComputedStyle(document.documentElement).getPropertyValue("--glow-reach")) || 26;
  let body = `<defs>${themes.map((t) => `<radialGradient id="g-${t}"><stop offset="0" style="stop-color:${col(t)};stop-opacity:var(--glow-subject)"/><stop offset="1" stop-color="${col(t)}" stop-opacity="0"/></radialGradient>`).join("")}<radialGradient id="g-you"><stop offset="0" style="stop-color:var(--color-ink);stop-opacity:var(--glow-you)"/><stop offset="1" stop-color="var(--color-ink)" stop-opacity="0"/></radialGradient></defs><circle cx="${C}" cy="${C}" r="120" fill="url(#g-you)"/>`;
  body += themes.map((t) => `<path d="${radial(40, mid[t], HUB, mid[t])}" fill="none" stroke="${col(t)}" stroke-width="2.4"/>`).join("");
  body += Object.entries(pairs).map(([k, list]) => { const [p, q] = k.split("|").map((x) => planets[x]); if (!p || !q) return ""; return `<path class="plink" data-a="${p.x.slug}" data-b="${q.x.slug}" stroke-dasharray="3 5" stroke-width="${(1 + Math.log2(list.length) * 0.6).toFixed(1)}" d="${bend(p.px, p.py, q.px, q.py)}"><title>${list.length} skills overlap (inferred from their names)</title></path>`; }).join("");
  const nodePos = {};
  body += Object.values(planets).map((p) => {
    const { x, px, py, d } = p, t = x.theme || "calm", rc = 20 + Math.sqrt(x.total) * 4.5, L = x.layout;
    const r = Math.hypot(px - C, py - C);
    let stars = "", lines = "", ring = "";
    if (L && x.nodes.length) {
      const ids = x.nodes.map((n) => n.id), xs = ids.map((i) => L.x[i]), top = Math.max(...ids.map((i) => L.rank[i]), 1);
      const minx = Math.min(...xs), spanx = Math.max(...xs) - minx || 1;
      ids.forEach((i) => {
        let dx = ((L.x[i] - minx) / spanx - 0.5) * 1.5 * rc, dy = (0.5 - L.rank[i] / top) * 1.5 * rc;
        const len = Math.hypot(dx, dy), max = rc * 0.78; if (len > max) { dx *= max / len; dy *= max / len; }
        nodePos[`${x.slug}/${i}`] = [px + dx, py + dy];
      });
      lines = x.nodes.flatMap((n) => n.prereqs.filter((q) => nodePos[`${x.slug}/${q}`]).map((q) => { const [x1, y1] = nodePos[`${x.slug}/${q}`], [x2, y2] = nodePos[`${x.slug}/${n.id}`]; return `<line x1="${x1.toFixed(1)}" y1="${y1.toFixed(1)}" x2="${x2.toFixed(1)}" y2="${y2.toFixed(1)}" stroke="${col(t)}" stroke-opacity=".9" stroke-width="1.2"/>`; })).join("");
      stars = x.nodes.map((n) => { const [sx, sy] = nodePos[`${x.slug}/${n.id}`], cls = statusOf(n, x), rr = cls === "m-solid" ? 4.6 : cls === "m-not" ? 2.6 : 3.8; return `<circle class="moon ${cls}" cx="${sx.toFixed(1)}" cy="${sy.toFixed(1)}" r="${rr}">${tip(x, n)}</circle>`; }).join("");
      ring = x.nodes.map((n, m) => { const ang = rad(-90 + (m * 360) / x.nodes.length), rr = rc + 10; return `<circle class="${statusOf(n, x)}" cx="${(px + rr * Math.cos(ang)).toFixed(1)}" cy="${(py + rr * Math.sin(ang)).toFixed(1)}" r="2.4"/>`; }).join("");
    } else ring = `<circle cx="${px}" cy="${py}" r="${rc}" fill="none" stroke="${col(t)}" stroke-dasharray="2 4"/>`;
    const branch = `<path d="${radial(HUB, mid[t], Math.max(HUB + 20, r - rc - 14), d)}" fill="none" stroke="${col(t)}" stroke-opacity=".85" stroke-width="1.6"/>`;
    return `${branch}<g class="planet" data-slug="${x.slug}" data-act="subject-map" data-arg="${x.slug}" role="button" aria-label="${esc(x.title)}">
      <circle cx="${px}" cy="${py}" r="${rc + 16}" fill="transparent"/><circle cx="${px}" cy="${py}" r="${rc + reach}" fill="url(#g-${t})"/>${ring}${lines}${stars}
      ${label(x).map((l, i) => `<text x="${px}" y="${py + rc + 30 + i * 17}" text-anchor="middle" font-size="14.5" fill="var(--color-ink)">${esc(l)}</text>`).join("")}
    </g>`;
  }).join("");
  body += themes.map((t) => { const [x, y] = pt(HUB, mid[t]), w = DOMAIN[t].length * 8.4 + 26; return `<g><rect x="${x - w / 2}" y="${y - 13}" width="${w}" height="26" rx="13" fill="var(--color-surface)" stroke="${col(t)}" stroke-width="1.6"/><circle cx="${x - w / 2 + 13}" cy="${y}" r="4" fill="${col(t)}"/><text x="${x + 5}" y="${y + 5}" text-anchor="middle" font-size="13" font-weight="600" fill="var(--color-ink)">${DOMAIN[t]}</text></g>`; }).join("");
  const you = `<circle cx="${C}" cy="${C}" r="70" fill="none" stroke="var(--color-line)"/><circle cx="${C}" cy="${C}" r="54" fill="none" stroke="var(--color-line-strong)" stroke-dasharray="1 4"/><circle cx="${C}" cy="${C}" r="38" fill="var(--color-surface)" stroke="var(--color-line-strong)"/><text x="${C}" y="${C + 5}" text-anchor="middle" font-size="15" font-weight="700" fill="var(--color-ink)">You</text>`;
  el.innerHTML = `<div class="mapwrap skill-map" data-theme="night" id="mapwrap">
    <div class="canvas" id="canvas" style="width:${2 * C}px;height:${2 * C}px">
      <svg class="sys" id="sys" width="${2 * C}" height="${2 * C}" style="position:absolute;left:0;top:0;overflow:visible">
        ${sectors.map((sc) => `<path d="${wedge(sc)}" fill="var(--subject-${sc.t})" fill-opacity=".06"/>`).join("")}
        ${sectors.map((sc) => { const [x1, y1] = pt(80, sc.from), [x2, y2] = pt(RIM, sc.from); return `<line x1="${x1}" y1="${y1}" x2="${x2}" y2="${y2}" stroke="var(--color-line)"/>`; }).join("")}
        ${R.map((r) => `<circle cx="${C}" cy="${C}" r="${r}" fill="none" stroke="var(--color-line)" stroke-dasharray="2 6"/>`).join("")}
        ${you}${body}
      </svg>
    </div>
    <div class="card mapctl">
      <button class="btn txt" data-act="zoom" data-arg="in" aria-label="Zoom in" data-tip="${key("=")}" data-tip-side="up">+</button><button class="btn txt" data-act="zoom" data-arg="out" aria-label="Zoom out" data-tip="${key("-")}" data-tip-side="up">−</button><button class="btn txt" data-act="zoom" data-arg="fit" data-tip="${key("0")}" data-tip-side="up">Fit</button>
      <button class="btn ink sm" style="margin-left:6px" data-act="ink" data-tip="${key("↩")}" data-tip-side="up">${VERB[S.ranked[0].kind] || "Start"}</button>
    </div>
  </div>`;
  const wrap = $("mapwrap");
  mapView = mapViews.system || null;
  if (!mapView) fitMap(true);
  mapViews.system = mapView;
  applyMap();
  panZoom(wrap, "system");
  const svg = $("sys");
  svg.querySelectorAll(".planet").forEach((g) => {
    g.addEventListener("mouseenter", () => sysFocus(g.dataset.slug));
    g.addEventListener("mouseleave", () => sysFocus(null));
  });
}
ACTIONS["subject-map"] = (slug) => go("map", slug);
function sysFocus(slug) {
  const svg = $("sys"); if (!svg) return;
  svg.querySelectorAll(".hot").forEach((e) => e.classList.remove("hot"));
  svg.classList.toggle("focus", !!slug);
  if (!slug) return;
  const others = new Set([slug]);
  svg.querySelectorAll(".plink").forEach((e) => { if (e.dataset.a === slug || e.dataset.b === slug) { e.classList.add("hot"); others.add(e.dataset.a); others.add(e.dataset.b); } });
  svg.querySelectorAll(".planet").forEach((g) => { if (others.has(g.dataset.slug)) { g.classList.add("hot"); g.querySelectorAll(".moon").forEach((m) => m.classList.add("hot")); } });
}

// ---------- the tutor's terminal ----------
const T = { term: null, fit: null, running: false, starting: false, startedAt: 0, ended: null, queue: null };
function termTheme() {
  const css = getComputedStyle(document.documentElement), v = (n) => css.getPropertyValue(n).trim();
  const night = document.documentElement.dataset.theme === "night";
  // ANSI colors keep their hue and sit at the contrast the app's text does.
  return night ? {
    background: v("--color-surface"), foreground: v("--color-ink"), cursor: v("--color-ink"), cursorAccent: v("--color-surface"),
    selectionBackground: "#3B3A55", black: "#1C1C1F", red: "#F07A52", green: "#3FB98A", yellow: "#F6CF5F", blue: "#8FA8D8", magenta: "#C9A0DC", cyan: "#5FC4CF", white: "#D9D7D2",
    brightBlack: "#8F8D87", brightRed: "#FF9A78", brightGreen: "#6FD3A8", brightYellow: "#FFE08A", brightBlue: "#B3C6EE", brightMagenta: "#DDBDEA", brightCyan: "#8ADCE4", brightWhite: "#F2F1EE",
  } : {
    background: v("--color-surface"), foreground: v("--color-ink"), cursor: v("--color-ink"), cursorAccent: v("--color-surface"),
    selectionBackground: "#D9D5FB", black: "#1B1A17", red: "#B8432A", green: "#137352", yellow: "#8A600A", blue: "#3A5C93", magenta: "#7D3F90", cyan: "#1F6E79", white: "#646059",
    brightBlack: "#646059", brightRed: "#C2482A", brightGreen: "#17865F", brightYellow: "#9A6D10", brightBlue: "#4A6FA5", brightMagenta: "#8E4FA0", brightCyan: "#267C88", brightWhite: "#1B1A17",
  };
}
async function ensureTerm() {
  if (T.term) return T.term;
  await document.fonts.load('13px "Atkinson Hyperlegible Mono"');
  const term = new window.Terminal({
    fontFamily: '"Atkinson Hyperlegible Mono", ui-monospace, monospace', fontSize: 13, lineHeight: 1.2,
    cursorBlink: true, cursorStyle: "bar", scrollback: 10000, allowProposedApi: true,
    macOptionIsMeta: true, theme: termTheme(), drawBoldTextInBrightColors: false, minimumContrastRatio: 4.5,
  });
  T.fit = new window.FitAddon.FitAddon();
  term.loadAddon(T.fit);
  term.loadAddon(new window.WebLinksAddon.WebLinksAddon((_e, url) => F.openExternal(url)));
  term.open($("term"));
  term.onData((d) => { if (T.running) F.pty.write(d); });
  F.pty.onData((d) => term.write(d));
  F.pty.onExit(() => {
    T.running = false;
    T.ended = new Date();
    paintTermState();
    paintRail();
  });
  new ResizeObserver(() => fitSoon()).observe($("termcard"));
  T.term = term;
  return term;
}
let fitTimer = null;
function fitSoon() {
  clearTimeout(fitTimer);
  fitTimer = setTimeout(() => {
    if (!T.term || route.name !== "session" || !$("termcard").offsetWidth) return;
    try { T.fit.fit(); } catch { return; }
    if (T.running) F.pty.resize(T.term.cols, T.term.rows);
  }, 30);
}
async function startTutor(prompt) {
  if (T.starting) return;
  T.starting = true;
  paintTermState();
  await ensureTerm();
  T.fit.fit();
  T.term.clear();
  T.term.reset();
  const result = await F.pty.start({ cols: T.term.cols, rows: T.term.rows, prompt: prompt || "" });
  T.starting = false;
  if (result && result.error) {
    T.failed = result.error;
    paintTermState();
    return;
  }
  T.running = true; T.startedAt = Date.now(); T.ended = null; T.failed = null;
  paintTermState(); paintRail();
  T.term.focus();
}
// Type into the running tutor as the learner would: the text, then Return.
async function tutorSend(text) {
  if (!text) return;
  if (!T.running) return startTutor(text);
  await ensureTerm();
  F.pty.write(text);
  setTimeout(() => F.pty.write("\r"), 90);
  T.term.focus();
}
ACTIONS["tutor-start"] = (arg) => startTutor(arg === "plain" ? "" : arg);
ACTIONS.hint = () => T.running ? tutorSend("Can I have a hint?") : toast(`The tutor isn't running. Open Session to start ${tutorName()}.`);
ACTIONS.check = () => T.running || route.slug ? tutorSend(command("learn-check")) : null;
ACTIONS.break = () => T.running ? tutorSend(command("learn-end break")) : toast("No session is running.");
ACTIONS.end = () => T.running ? tutorSend(command("learn-end")) : toast("No session is running.");
ACTIONS.restart = async () => { await F.pty.stop(); T.running = false; startTutor(""); };

function paintTermState() {
  const s = subj(route.slug);
  const empty = $("termempty");
  empty.style.display = T.running ? "none" : "flex";
  const head = $("termhead");
  head.innerHTML = s ? `${dot(s)}<span class="t-sub">${md(s.title)}</span><span class="t-cap" style="margin-left:auto">${T.running ? `${esc(tutorName())} is running in your vault` : T.starting ? "Starting…" : ""}</span>` : "";
  const acts = [["hint", "Hint", key("/")], ["check", "Check me", key("J")], ["break", "Break", key("B")], ["end", "End", keyShift("E")]];
  $("termacts").innerHTML = acts.map(([a, label, k]) => `<button class="btn txt" data-act="${a}" data-tip="${k}" data-tip-side="up" ${T.running ? "" : "disabled"}>${label}</button>`).join("");
  if (T.running) { inkAction = null; return; }
  const resume = s && (S.ranked.find((x) => x.subject === s.slug && x.kind !== "Repair") || { command: `learn-resume ${s.slug}`, subject: s.slug, kind: "Resume" });
  const verb = s && s.status === "done" ? "Practice" : "Resume";
  const typed = s ? (s.status === "done" ? command(`learn-practice ${s.slug}`) : resume.typed || command(resume.command)) : "";
  inkAction = () => startTutor(typed);
  empty.innerHTML = T.starting ? `<div class="t-ui ink2">Starting ${esc(tutorName())}…</div>` : `
    <div class="t-head">${T.ended ? `${esc(tutorName())} stopped` : s ? `${verb} ${md(shortTitle(s))}` : `Start ${esc(tutorName())}`}</div>
    ${T.failed ? `<p>Could not start ${esc(tutorName())}: <span class="mono">${esc(T.failed)}</span>. Check that it runs in Terminal, then try again.</p>` : ""}
    <p>${T.ended ? "The tutor's session ended. Your records are saved as the tutor left them." : `${esc(tutorName())} opens in your vault and runs ${s ? `<span class="mono">${esc(typed)}</span>` : "with no command"}. Reply in the terminal; the log on the right follows along.`}</p>
    <button class="btn ink" data-act="ink" data-tip="${key("↩")}">${T.ended ? "Start again" : s ? verb : "Start"}</button>
    ${s ? `<button class="btn txt" data-act="tutor-start" data-arg="plain">Open with no command</button>` : ""}`;
  if (T.ended) inkAction = () => startTutor("");
}

// ---------- session screen ----------
const LOG = { slug: null, data: null, tab: "log", showAll: false, think: {}, keys: [], stick: true, loading: false };
const sessionCache = {};
function prefetchSession(slug) { if (slug && !sessionCache[slug]) sessionCache[slug] = F.session(slug); }

async function paintSession() {
  const s = subj(route.slug);
  paintTermState();
  paintPanelShell();
  await ensureTerm();
  fitSoon();
  if (T.running) T.term.focus();
  if (!s) return;
  if (LOG.slug !== s.slug) {
    LOG.slug = s.slug; LOG.showAll = false; LOG.think = {}; LOG.keys = []; LOG.stick = true;
    prefetchSession(s.slug);
    LOG.data = await sessionCache[s.slug];
    if (LOG.slug !== s.slug) return;
    paintPanelBody(true);
  } else paintPanelBody(false);
}
function paintPanelShell() {
  const p = $("wpanel");
  p.classList.toggle("hide", !cfg.panel);
  p.style.width = `${Math.max(320, Math.min(420, cfg.panelWidth || 400))}px`;
  $("tabs").innerHTML = [["log", "Log", "1"], ["note", "Note", "2"]].map(([k, name, n]) => `<button class="tab ${LOG.tab === k ? "on" : ""}" data-act="tab" data-arg="${k}" data-tip="${keyAlt(n)}">${name}</button>`).join("");
}
ACTIONS.tab = (k) => { if (!cfg.panel) setCfg({ panel: true }); LOG.tab = k; LOG.keys = []; paintPanelShell(); paintPanelBody(true); paintChrome(); };

function paintPanelBody(full) {
  const body = $("panelBody");
  if (!LOG.data) { body.innerHTML = `<div class="t-cap">Reading the log…</div>`; return; }
  if (LOG.tab === "note") {
    const note = LOG.data.note;
    const top = body.scrollTop;
    body.innerHTML = note ? `<div class="t-sub" style="margin-bottom:6px">${noteLabel(note.name)} · ${longD(note.name)}</div><div class="note">${renderMd(note.text.replace(/^# .*\n/, ""))}</div>` : `<div class="t-ui ink2">No session note yet. The tutor writes one when a session starts.</div>`;
    if (!full) body.scrollTop = top;
    typeset(body);
    return;
  }
  paintLog(full);
}

// The log, drawn item by item: a streaming reply repaints only itself, so the
// rest of the log, its diagrams, and your scroll position stay put.
const SHOW = 80;
function logEntries() {
  const convos = LOG.data.conversations || [];
  const out = [];
  convos.forEach((c, ci) => {
    out.push({ key: `c${ci}`, html: `<div class="convo-sep">${longD(c.date)}${c.model ? ` · ${esc(c.model.split("·")[0].trim())}` : ""}</div>` });
    const lastQ = ci === convos.length - 1 ? c.items.map((x) => x.kind).lastIndexOf("question") : -1;
    c.items.forEach((it, i) => {
      const html = itemHtml(it, i === lastQ && !it.answered && !it.withdrawn, `${ci}:${i}`);
      if (html) out.push({ key: `${ci}:${i}`, html });
    });
  });
  return out;
}
function itemHtml(it, waiting, k) {
  if (it.kind === "tutor") return `<div class="tutor">${renderMd(it.text)}</div>`;
  if (it.kind === "you") {
    const cmd = /^[/$]learn-/.test(it.text);
    return `<div class="you"><div class="${cmd ? "cmd" : ""}" title="${esc(it.time)}">${cmd ? esc(it.text.split("\n")[0]) : youText(it.text)}</div></div>`;
  }
  if (it.kind === "code") return `<div class="you"><div><span class="cap">Your code</span>${renderMd(it.text)}</div></div>`;
  if (it.kind === "thinking") {
    const open = LOG.think[k];
    return `<div class="thinking"><button class="btn txt" data-act="think" data-arg="${k}" aria-expanded="${!!open}">${icon(open ? "down" : "chev", "sm")}Thinking</button>${open ? `<div class="body">${renderMd(it.text)}</div>` : ""}</div>`;
  }
  if (it.kind === "question") {
    if (it.withdrawn) return "";
    return (it.groups || []).map((g) => `${waiting ? `<div class="lit-card qframe" style="${lightOf(subj(LOG.slug))}">` : ""}<div class="card qcard">
      ${g.body.trim() ? `<div class="qbody">${renderMd(g.body)}</div>` : ""}
      ${g.options.map((o, n) => `<div class="opt ${it.picked.includes(o.label) ? "sel" : ""}"><i class="r"></i><span><span class="${/[;(){}=]/.test(o.label) ? "codey" : ""}">${inline(o.label)}</span>${o.desc.length > 2 && o.desc !== o.label ? `<span class="d">${inline(o.desc)}</span>` : ""}</span><span class="k">${n + 1}</span></div>`).join("")}
    </div>${waiting ? "</div>" : ""}`).join("");
  }
  if (it.kind === "answer") {
    if (it.skipped) return `<div class="you"><div class="ink2">Skipped the question to say something first.</div></div>`;
    return it.parts && it.parts.length ? `<div class="you"><div>${it.parts.map(youText).join("\n\n")}</div></div>` : "";
  }
  return "";  // probe notices and the hook's own messages are plumbing
}
function youText(t) {
  return esc(t).replace(/!\[\[([^\]|]+?\.(?:png|jpe?g|gif|webp))(?:\|\d+)?\]\]/gi,
    (_, p) => `<img class="shot" alt="Screenshot you sent" src="vault-file:///${encodeURIComponent(p.replace(/&amp;/g, "&").split("/").pop())}">`).trim();
}
function paintLog(full) {
  const body = $("panelBody");
  let entries = logEntries();
  if (!entries.some((e) => e.key.includes(":"))) {
    body.innerHTML = `<div class="t-ui ink2" style="padding:10px 0">No conversation yet. Start the tutor and the log fills in here as it writes.</div>`;
    LOG.keys = [];
    return;
  }
  const hidden = LOG.showAll ? 0 : Math.max(0, entries.length - SHOW);
  entries = entries.slice(hidden);
  let list = body.querySelector(".log");
  const atBottom = body.scrollHeight - body.scrollTop - body.clientHeight < 60;
  if (full || !list) {
    body.innerHTML = `${hidden ? `<button class="btn txt earlier" data-act="log-all">${icon("chev", "sm")}Show ${hidden} earlier</button>` : ""}<div class="log"></div>`;
    list = body.querySelector(".log");
    LOG.keys = [];
  } else {
    const btn = body.querySelector(".earlier");
    if (btn) btn.innerHTML = `${icon("chev", "sm")}Show ${hidden} earlier`;
  }
  const existing = new Map([...list.children].map((n) => [n.dataset.key, n]));
  const changed = [];
  let prev = null;
  for (const e of entries) {
    let node = existing.get(e.key);
    if (node && node.dataset.html !== String(hash(e.html))) { node.innerHTML = e.html; node.dataset.html = hash(e.html); changed.push(node); }
    if (!node) {
      node = document.createElement("div");
      node.className = "item";
      node.dataset.key = e.key;
      node.dataset.html = hash(e.html);
      node.innerHTML = e.html;
      changed.push(node);
    }
    existing.delete(e.key);
    if (prev ? prev.nextSibling !== node : list.firstChild !== node) list.insertBefore(node, prev ? prev.nextSibling : list.firstChild);
    prev = node;
  }
  existing.forEach((n) => n.remove());
  changed.forEach((n) => typeset(n));
  if (full || atBottom || LOG.stick) { body.scrollTop = body.scrollHeight; LOG.stick = false; $("newPill").classList.remove("on"); }
  else if (changed.length) $("newPill").classList.add("on");
}
function hash(s) { let h = 0; for (let i = 0; i < s.length; i++) h = (Math.imul(31, h) + s.charCodeAt(i)) | 0; return h; }
$("panelBody").addEventListener("scroll", () => {
  const b = $("panelBody");
  if (b.scrollHeight - b.scrollTop - b.clientHeight < 60) $("newPill").classList.remove("on");
});
ACTIONS["log-bottom"] = () => { const b = $("panelBody"); b.scrollTop = b.scrollHeight; $("newPill").classList.remove("on"); };
ACTIONS["log-all"] = () => { LOG.showAll = true; paintPanelBody(true); };
ACTIONS.think = (k, el) => {
  LOG.think[k] = !LOG.think[k];
  const top = $("panelBody").scrollTop;
  paintLog(false);
  $("panelBody").scrollTop = top;
};
ACTIONS["copy-code"] = (_a, el) => {
  const pre = el.parentElement.querySelector("pre");
  navigator.clipboard.writeText(pre ? pre.textContent : "");
  el.textContent = "Copied";
  setTimeout(() => { el.textContent = "Copy"; }, 1200);
};

// The panel's width is the learner's: drag its edge, within the guideline's 320 to 420.
(() => {
  const r = $("resizer");
  let start = null;
  r.addEventListener("mousedown", (e) => { start = { x: e.clientX, w: $("wpanel").offsetWidth }; r.classList.add("drag"); e.preventDefault(); });
  window.addEventListener("mousemove", (e) => {
    if (!start) return;
    const w = Math.max(320, Math.min(420, start.w - (e.clientX - start.x)));
    $("wpanel").style.width = `${w}px`;
    fitSoon();
  });
  window.addEventListener("mouseup", () => { if (!start) return; start = null; r.classList.remove("drag"); setCfg({ panelWidth: $("wpanel").offsetWidth }); });
})();

// ---------- palette ----------
let pal = null;
function openPalette() {
  if (!S) return;
  const top = S.ranked[0];
  const recents = top ? [{ label: `${VERB[top.kind] || "Start"} ${top.subject ? esc(shortTitle(subj(top.subject))) : top.kind === "Review" ? "review" : "something new"}`, why: plain(top).line, dot: top.subject ? subj(top.subject) : null, run: () => run(top), keys: key("↩") }] : [];
  const session = [
    { label: "Start a review", ic: "cards", run: ACTIONS.review, keys: key("R") },
    { label: "Check me", ic: "check", run: ACTIONS.check, keys: key("J") },
    { label: "Ask for a hint", ic: "send", run: ACTIONS.hint, keys: key("/") },
    { label: "Take a break", ic: "week", run: ACTIONS.break, keys: key("B") },
    { label: "End and save the session", ic: "note", run: ACTIONS.end, keys: keyShift("E") },
    { label: "Start a subject", ic: "flag", run: ACTIONS.start, keys: key("N") },
    { label: `Restart ${tutorName()}`, ic: "refresh", run: ACTIONS.restart },
  ];
  const resumes = S.ranked.filter((x) => x.subject && x.kind !== "Review").slice(0, 12).map((x) => {
    const s = subj(x.subject);
    return { label: `${x.kind === "Repair" ? "Repair" : "Resume"} ${esc(shortTitle(s))}`, why: plain(x).line, dot: s, run: () => run(x) };
  });
  const practice = S.subjects.filter((s) => s.proven).map((s) => ({ label: `Practice ${esc(shortTitle(s))}`, dot: s, run: () => ACTIONS.practice(s.slug) }));
  const goTo = [
    { label: "Home", ic: "home", run: () => go("home"), keys: key("1") },
    { label: "Session", ic: "terminal", run: () => go("session"), keys: key("2") },
    { label: "All skills", ic: "map", run: () => go("system"), keys: key("3") },
    { label: "Dashboard", ic: "book", run: () => go("dashboard"), keys: key("4") },
    { label: "Progress", ic: "chart", run: () => go("progress"), keys: key("5") },
    { label: "Skill map", ic: "map", run: () => go("map"), keys: key("6") },
    { label: "Settings", ic: "gear", run: openSettings, keys: key(",") },
    { label: "Open another vault", ic: "book", run: chooseVault, keys: key("O") },
  ];
  const subjects = S.subjects.map((s) => ({ label: md(s.title), dot: s, run: () => go("progress", s.slug) }));
  pal = { q: "", sel: 0, groups: [["Next step", recents], ["Session", session], ["Resume", resumes], ["Go to", goTo], ["Subjects", subjects], ["Practice", practice]] };
  const scrim = $("scrim");
  scrim.classList.add("on");
  scrim.innerHTML = `<div class="card float palette" role="dialog" aria-label="Search and commands"><div class="head">${icon("search")}<input id="palq" placeholder="Search or run a command" autocomplete="off" spellcheck="false" aria-label="Search"></div><div class="list" id="palList" role="listbox"></div><div class="foot t-cap"><span class="kbd">↑</span><span class="kbd">↓</span>Move<span class="kbd" style="margin-left:10px">↩</span>Open<span class="kbd" style="margin-left:10px">Esc</span>Close</div></div>`;
  const q = $("palq");
  q.focus();
  q.oninput = () => { pal.q = q.value.toLowerCase().trim(); pal.sel = 0; palList(); };
  palList();
}
function palItems() {
  return pal.groups.map(([g, items]) => [g, items.filter((i) => !pal.q || (i.label + " " + (i.why || "")).replace(/<[^>]+>/g, "").toLowerCase().includes(pal.q))])
    .filter(([g, items]) => items.length && (pal.q || g !== "Practice"));
}
function palList() {
  let i = 0;
  $("palList").innerHTML = palItems().map(([g, items]) => `<div class="t-cap grp">${g}</div>` + items.map((it) => {
    const n = i++;
    return `<button class="item ${n === pal.sel ? "sel" : ""}" role="option" aria-selected="${n === pal.sel}" data-act="pal-run" data-arg="${n}" data-pal="${n}">${it.dot ? dot(it.dot) : icon(it.ic || "chev", "sm")}<span style="flex:none">${it.label}</span>${it.why ? `<span class="why">${md(it.why)}</span>` : ""}${it.keys ? `<span style="margin-left:auto;padding-left:10px" class="keys">${it.keys.split(/(?<=⌘|⇧|⌥)|\+/).filter(Boolean).map((x) => `<span class="kbd">${esc(x)}</span>`).join("")}</span>` : ""}</button>`;
  }).join("")).join("") || `<div class="t-cap" style="padding:16px">Nothing matches.</div>`;
  const sel = document.querySelector(".palette .item.sel");
  if (sel) sel.scrollIntoView({ block: "nearest" });
}
$("scrim").addEventListener("mousemove", (e) => {
  const it = e.target.closest("[data-pal]");
  if (it && pal && +it.dataset.pal !== pal.sel) { pal.sel = +it.dataset.pal; [...document.querySelectorAll(".palette .item")].forEach((x) => x.classList.toggle("sel", +x.dataset.pal === pal.sel)); }
});
$("scrim").addEventListener("mousedown", (e) => { if (e.target === $("scrim")) closeOverlay(); });
ACTIONS["pal-run"] = (n) => palRun(+n);
function palRun(n) { const it = palItems().flatMap(([, items]) => items)[n]; closeOverlay(); if (it) it.run(); }
ACTIONS.palette = () => openPalette();

// ---------- settings ----------
async function openSettings() {
  pal = null;
  const scrim = $("scrim");
  scrim.classList.add("on");
  const theme = cfg.theme || "system";
  const pv = (bg, ink) => `<span style="flex:1;background:${bg};display:flex;flex-direction:column;gap:5px;padding:12px"><i style="height:6px;width:60%;border-radius:3px;background:${ink}"></i><i style="height:6px;width:40%;border-radius:3px;background:${ink};opacity:.5"></i></span>`;
  const thumb = (value, label, preview) => `<button class="thumb ${theme === value ? "on" : ""}" data-act="set-theme" data-arg="${value}" aria-pressed="${theme === value}"><div class="pv">${preview}</div><div class="lab">${label}</div></button>`;
  scrim.innerHTML = `<div class="card float sheet" role="dialog" aria-label="Settings">
    <div style="display:flex;align-items:center"><h2 class="t-head">Settings</h2><button style="margin-left:auto" class="tbbtn" data-act="close" aria-label="Close" data-tip="Esc">${icon("x")}</button></div>
    <div class="sec"><div class="t-sub">Appearance</div>
      <div class="thumbs">${thumb("system", "System", pv("#F6F5F2", "#1B1A17") + pv("#141416", "#F2F1EE"))}${thumb("light", "Light", pv("#F6F5F2", "#1B1A17"))}${thumb("night", "Night", pv("#141416", "#F2F1EE"))}</div></div>
    <div class="sec"><div class="t-sub">Your name</div>
      <div class="t-cap" style="margin-top:2px">For the greeting on Home.</div>
      <input id="nameIn" class="search" style="margin-top:8px;color:var(--color-ink);font-size:13px" value="${esc(firstName())}" placeholder="Your first name" aria-label="Your first name"></div>
    <div class="sec"><div class="t-sub">Tutor</div>
      <div class="t-cap" style="margin-top:2px">The command Flash runs in your vault. It uses your own sign-in.</div>
      <div class="seg" style="margin-top:8px" role="radiogroup">${[["claude", "Claude Code"], ["codex", "Codex"]].map(([v, l]) => `<button class="${cfg.host === v ? "on" : ""}" role="radio" aria-checked="${cfg.host === v}" data-act="set-host" data-arg="${v}">${l}</button>`).join("")}</div></div>
    <div class="sec"><div class="t-sub">Rewards ${S && S.rewards_on ? "on" : "off"}</div>
      <div class="t-cap" style="margin-top:2px">Badges and the review streak. Ask the tutor to turn them ${S && S.rewards_on ? "off" : "on"}; it is the <span class="mono">rewards:</span> line in learn/me/preferences.md.</div></div>
    <div class="sec"><div style="display:flex;align-items:center;gap:12px"><div style="min-width:0;flex:1"><div class="t-sub">Vault folder</div><div class="t-cap mono selectable" style="margin-top:2px;word-break:break-all">${esc(cfg.vault || "None")}</div></div><button class="btn sec sm" style="flex:none" data-act="choose-vault" data-tip="${key("O")}">Change…</button></div></div>
    <div class="t-cap" style="padding-top:12px;border-top:1px solid var(--color-line)">${esc(info.name)} ${esc(info.version)}. Flash writes no learning record; the tutor does.</div>
  </div>`;
  const nameIn = $("nameIn");
  nameIn.addEventListener("change", () => { setCfg({ name: nameIn.value.trim() }); if (route.name === "home") paintHome(); });
}
ACTIONS.settings = () => openSettings();
ACTIONS.close = () => closeOverlay();
ACTIONS["set-theme"] = async (t) => { await setCfg({ theme: t }); applyTheme(); openSettings(); };
ACTIONS["set-host"] = async (h) => {
  if (h === cfg.host) return;
  if (T.running && !confirm(`Switch to ${h === "codex" ? "Codex" : "Claude Code"}? The running tutor stops. Your records stay as they are.`)) return;
  await F.pty.stop(); T.running = false;
  await setCfg({ host: h });
  closeOverlay();
  boot();
};
ACTIONS["choose-vault"] = () => chooseVault();
function closeOverlay() { const s = $("scrim"); s.classList.remove("on"); s.innerHTML = ""; pal = null; if (route.name === "session" && T.running) T.term.focus(); }

async function chooseVault() {
  closeOverlay();
  const r = await F.chooseVault();
  if (r.canceled) return;
  if (r.problem) { toast(r.problem); return; }
  T.running = false;
  Object.keys(sessionCache).forEach((k) => delete sessionCache[k]);
  Object.keys(mapViews).forEach((k) => delete mapViews[k]);
  LOG.slug = null;
  if (T.term) T.term.reset();
  boot();
}
ACTIONS["open-vault"] = () => chooseVault();

// ---------- setup ----------
function paintSetup() {
  $("session").classList.add("hidden");
  $("screen").classList.remove("hidden");
  $("rail").classList.add("hide");
  $("side").classList.add("hide");
  $("panelBtn").style.display = "none";
  $("sideBtn").style.display = "none";
  $("searchBtn").style.display = "none";
  $("ttl").textContent = `Set up ${info.name}`;
  document.documentElement.style.setProperty("--s", "var(--holo-calm)");
  $("ambientBg").classList.add("on");
  const v = setupInfo || {};
  const vaultOk = !v.vaultProblem;
  const steps = [
    { ok: vaultOk, title: "Your learning vault", text: vaultOk ? "" : v.vault ? v.vaultProblem : `Pick the folder that holds your copy of the learning vault. It has a learn/ folder inside.`, path: v.vault, action: true },
    ...(v.problems || []).map((p) => ({ ok: false, title: p.what, text: p.fix })),
  ];
  if (!(v.problems || []).length) steps.push({ ok: true, title: `Python 3 and ${tutorName()} found`, text: "" });
  inkAction = vaultOk ? null : chooseVault;
  $("screen").innerHTML = `<div class="holo-content setup">
    <h1 class="t-title">Welcome to ${esc(info.name)}</h1>
    <p class="t-ui ink2" style="font-size:15px;line-height:22px;margin-top:8px">Your tutor's terminal, the live log, and your progress in one window. ${esc(info.name)} runs your own ${esc(tutorName())} in your vault, so everything works as it does in the terminal.</p>
    ${steps.map((st, i) => `<div class="card stepc"><span class="num ${st.ok ? "ok" : ""}">${st.ok ? icon("check", "sm") : i + 1}</span><div style="flex:1;min-width:0">
      <div class="t-sub">${esc(st.title)}</div>${st.path ? `<div class="path">${esc(st.path)}</div>` : ""}${st.text ? `<div class="fix">${esc(st.text)}</div>` : ""}
      ${st.action ? `<div style="margin-top:12px">${vaultOk ? `<button class="btn sec sm" data-act="choose-vault">Choose another folder</button>` : `<button class="btn ink" data-act="choose-vault" data-tip="${key("O")}">Choose folder</button>`}</div>` : ""}
    </div></div>`).join("")}
    ${vaultOk && (v.problems || []).length ? `<div style="margin-top:18px;display:flex;gap:10px;align-items:center"><button class="btn ink" data-act="recheck">Check again</button><span class="t-cap">After installing, check again.</span></div>` : ""}
    <div class="seg" style="margin-top:22px" role="radiogroup" aria-label="Tutor">${[["claude", "Claude Code"], ["codex", "Codex"]].map(([h, l]) => `<button class="${cfg.host === h ? "on" : ""}" role="radio" aria-checked="${cfg.host === h}" data-act="setup-host" data-arg="${h}">${l}</button>`).join("")}</div>
  </div>`;
  if (vaultOk && (v.problems || []).length) inkAction = boot;
}
ACTIONS.recheck = () => boot();
ACTIONS["setup-host"] = async (h) => { await setCfg({ host: h }); boot(); };

function paintError(state) {
  route = { name: "home", slug: route.slug };
  $("session").classList.add("hidden");
  $("screen").classList.remove("hidden");
  inkAction = boot;
  $("screen").innerHTML = `<div class="setup"><h1 class="t-head">Could not read the records</h1>
    <p class="t-ui ink2" style="margin-top:8px">learn-status.py stopped with an error, so nothing is shown. Your files were not changed.</p>
    ${state.detail ? `<pre class="card selectable" style="margin-top:14px;padding:12px;white-space:pre-wrap;font:12px/18px var(--font-mono);color:var(--color-ink-2)">${esc(state.detail)}</pre>` : ""}
    <div style="margin-top:16px;display:flex;gap:10px"><button class="btn ink" data-act="recheck">Try again</button><button class="btn sec sm" style="height:36px" data-act="choose-vault">Choose another folder</button></div></div>`;
}

// ---------- toast ----------
let toastTimer;
function toast(text) {
  const t = $("toast");
  t.innerHTML = `<span>${esc(text)}</span><button class="tbbtn" data-act="toast-close" aria-label="Dismiss">${icon("x", "sm")}</button>`;
  t.classList.add("on");
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => t.classList.remove("on"), 5000);
}
ACTIONS["toast-close"] = () => $("toast").classList.remove("on");

// ---------- theme ----------
function applyTheme() {
  const pref = cfg.theme || "system";
  const night = pref === "night" || (pref === "system" && matchMedia("(prefers-color-scheme: dark)").matches);
  if (night) document.documentElement.dataset.theme = "night"; else delete document.documentElement.dataset.theme;
  if (T.term) T.term.options.theme = termTheme();
  if (S && route.name !== "session") render();
  else if (S) { paintPanelBody(true); }
}
matchMedia("(prefers-color-scheme: dark)").addEventListener("change", applyTheme);

// ---------- keys ----------
document.addEventListener("keydown", (e) => {
  if (pal) {
    const n = palItems().flatMap(([, i]) => i).length;
    if (e.key === "ArrowDown") { pal.sel = Math.min(n - 1, pal.sel + 1); palList(); e.preventDefault(); }
    else if (e.key === "ArrowUp") { pal.sel = Math.max(0, pal.sel - 1); palList(); e.preventDefault(); }
    else if (e.key === "Enter") { palRun(pal.sel); e.preventDefault(); }
    else if (e.key === "Escape") { closeOverlay(); e.preventDefault(); }
    return;
  }
  if (e.key === "Escape" && $("scrim").classList.contains("on")) { closeOverlay(); e.preventDefault(); }
});
F.onMenu((id) => {
  if ($("scrim").classList.contains("on") && !["palette", "settings"].includes(id)) closeOverlay();
  if (route.name === "setup" && !["open-vault", "settings"].includes(id)) return;
  if (id.startsWith("go:")) return go(id.slice(3));
  if (id.startsWith("tab:")) { if (route.name !== "session") go("session"); return ACTIONS.tab(id.slice(4)); }
  const map = {
    palette: openPalette, settings: openSettings, "open-vault": chooseVault, ink: ACTIONS.ink,
    review: ACTIONS.review, check: ACTIONS.check, hint: ACTIONS.hint, break: ACTIONS.break, end: ACTIONS.end,
    start: ACTIONS.start, restart: ACTIONS.restart, "toggle-side": ACTIONS["toggle-side"],
    "toggle-panel": () => { if (route.name === "session") ACTIONS["toggle-panel"](); },
    "zoom-in": () => ACTIONS.zoom("in"), "zoom-out": () => ACTIONS.zoom("out"), "zoom-fit": () => ACTIONS.zoom("fit"),
  };
  if (map[id]) map[id]();
});

// ---------- live updates ----------
F.onState((state) => {
  if (!state || state.error) return;
  const screen = $("screen"), top = screen.scrollTop;
  S = state;
  // A refresh repaints what changed and keeps your place; the terminal and the
  // log are never repainted by it.
  paintRail(); paintSide();
  if (route.name === "session") { paintTermState(); return; }
  if (pal || $("scrim").classList.contains("on")) return;
  render();
  screen.scrollTop = top;
});
F.onSession(async ({ slug, kind }) => {
  delete sessionCache[slug];
  // While the tutor runs, the log follows the subject it is writing to.
  if (T.running && kind === "log" && route.name === "session" && slug !== route.slug && subj(slug)) {
    const data = await F.session(slug);
    if (data.logMtime > T.startedAt) { sessionCache[slug] = Promise.resolve(data); route.slug = slug; render(); return; }
  }
  if (slug !== LOG.slug) return;
  prefetchSession(slug);
  const data = await sessionCache[slug];
  if (slug !== LOG.slug) return;
  LOG.data = data;
  if (route.name === "session" && (kind === "log" ? LOG.tab === "log" : LOG.tab === "note")) paintPanelBody(false);
});
F.onFocus(async () => {
  if (!S || route.name === "setup") return;
  const state = await F.state();
  if (state && !state.error && JSON.stringify(state) !== JSON.stringify(S)) { S = state; const top = $("screen").scrollTop; paintRail(); paintSide(); if (route.name !== "session") { render(); $("screen").scrollTop = top; } }
});
window.addEventListener("resize", () => { if (MAPS.includes(route.name)) applyMap(); });

// ---------- boot ----------
async function boot() {
  info = info || await F.info();
  cfg = await F.config();
  document.body.classList.toggle("mac", info.platform === "darwin");
  document.body.classList.toggle("win", info.platform !== "darwin");
  applyTheme();
  setupInfo = await F.setupCheck();
  if (setupInfo.vaultProblem || setupInfo.problems.length) {
    route = { name: "setup", slug: null };
    return paintSetup();
  }
  $("sideBtn").style.display = ""; $("searchBtn").style.display = ""; $("rail").classList.remove("hide");
  $("screen").innerHTML = `<div style="padding:40px" class="t-cap">Reading your records…</div>`;
  const state = await F.state();
  if (!state || state.error) return paintError(state || {});
  S = state;
  if (route.name === "setup") route = { name: "home", slug: null };
  if (!route.slug || !subj(route.slug)) route.slug = defaultSlug();
  render();
}
boot();
