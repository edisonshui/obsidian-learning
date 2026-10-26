// Flash: the main process. It owns the window, the tutor's terminal (the
// learner's own `claude` or `codex`, run in their vault), and every read of the
// vault. It writes no learning record: records change only through the tutor.

const { app, BrowserWindow, Menu, dialog, ipcMain, nativeTheme, protocol, shell, net } = require("electron");
const { execFile } = require("child_process");
const fs = require("fs");
const path = require("path");
const { pathToFileURL } = require("url");
const env = require("./lib/env");
const { readLog, stripFrontmatter } = require("./lib/log");

const APP_NAME = "Flash";
app.setName(APP_NAME);
// Never hand this to the tutor: it would make any Electron tool it starts run as plain Node.
delete process.env.ELECTRON_RUN_AS_NODE;

protocol.registerSchemesAsPrivileged([{ scheme: "vault-file", privileges: { standard: false, supportFetchAPI: true } }]);

// ---------- settings ----------
const CONFIG = path.join(app.getPath("userData"), "config.json");
const DEFAULTS = { vault: null, host: "claude", theme: "system", sidebar: true, panel: true, panelWidth: 400 };
let config = { ...DEFAULTS };
try { config = { ...DEFAULTS, ...JSON.parse(fs.readFileSync(CONFIG, "utf8")) }; } catch { /* first run */ }
function saveConfig() {
  fs.mkdirSync(path.dirname(CONFIG), { recursive: true });
  fs.writeFileSync(CONFIG, JSON.stringify(config, null, 2));
}

let win = null;
let PATH = process.env.PATH;
let tools = { python: null, tutor: null, problems: [] };
const send = (channel, payload) => { if (win && !win.isDestroyed()) win.webContents.send(channel, payload); };

// ---------- reading the vault ----------
let lastState = "";
function readState() {
  return new Promise((resolve) => {
    if (!config.vault || !tools.python) return resolve({ error: "no-vault" });
    const script = path.join(config.vault, ".claude", "hooks", "learn-status.py");
    execFile(tools.python, [script, "--json", "--host", config.host, "--vault", config.vault],
      { env: { ...process.env, PATH, PYTHONDONTWRITEBYTECODE: "1" }, maxBuffer: 32 * 1024 * 1024, timeout: 20000 },
      (error, stdout, stderr) => {
        if (error) return resolve({ error: "status-failed", detail: String(stderr || error.message).trim().split("\n").slice(-4).join("\n") });
        lastState = stdout;
        try { resolve(JSON.parse(stdout)); } catch (e) { resolve({ error: "status-failed", detail: e.message }); }
      });
  });
}

const SLUG = /^[a-z0-9][a-z0-9-]*$/;
function readSession(slug) {
  if (!config.vault || !SLUG.test(slug || "")) return { slug, conversations: [], note: null };
  const folder = path.join(config.vault, "learn", "subjects", slug);
  const log = path.join(folder, "log.md");
  const sessions = path.join(folder, "sessions");
  const notes = fs.existsSync(sessions) ? fs.readdirSync(sessions).filter((f) => f.endsWith(".md")).sort() : [];
  const latest = notes[notes.length - 1];
  return {
    slug,
    conversations: fs.existsSync(log) ? readLog(fs.readFileSync(log, "utf8")) : [],
    note: latest ? { name: latest.replace(/\.md$/, ""), text: stripFrontmatter(fs.readFileSync(path.join(sessions, latest), "utf8")) } : null,
    logMtime: fs.existsSync(log) ? fs.statSync(log).mtimeMs : 0,
  };
}

// ---------- watching ----------
// Any change under learn/ may change what the screens show. A log.md change is
// the tutor streaming, so it goes straight to the log panel; everything else
// re-reads the records, and only a real difference repaints.
let watcher = null, stateTimer = null;
const logTimers = {};
function watchVault() {
  if (watcher) watcher.close();
  watcher = null;
  if (!config.vault) return;
  try {
    watcher = fs.watch(path.join(config.vault, "learn"), { recursive: true }, (event, file) => {
      if (!file) return;
      const parts = file.split(path.sep);
      if (parts[0] === "subjects" && parts[1]) {
        const slug = parts[1];
        if (parts[2] === "log.md" || parts[2] === "sessions") {
          const kind = parts[2] === "log.md" ? "log" : "note";
          clearTimeout(logTimers[slug + kind]);
          logTimers[slug + kind] = setTimeout(() => send("session:changed", { slug, kind }), 120);
          if (parts[2] === "log.md") return;
        }
        if (parts[2] === "progress.md") return;  // generated from the records; they are watched already
      }
      if (/^(Home|Dashboard)\.md$/.test(parts[0])) return;
      clearTimeout(stateTimer);
      stateTimer = setTimeout(async () => {
        const before = lastState;
        const state = await readState();
        if (lastState !== before) send("state:changed", state);
      }, 400);
    });
  } catch (e) {
    console.error("watch failed", e);
  }
}

// ---------- the terminal ----------
let pty = null, term = null;
const isWin = process.platform === "win32";
function quote(arg) {
  return isWin ? '"' + String(arg).replace(/"/g, '""') + '"' : "'" + String(arg).replace(/'/g, "'\\''") + "'";
}
// The tutor gets the learner's own environment, minus anything that would make
// it think it runs inside another agent session. An inherited
// CLAUDE_CODE_CHILD_SESSION turns transcript saving off, and the live log is
// built from the transcript.
function tutorEnv() {
  const out = { ...process.env, PATH, TERM: "xterm-256color", COLORTERM: "truecolor", TERM_PROGRAM: APP_NAME };
  for (const name of Object.keys(out)) {
    if (/^(CLAUDECODE|CLAUDE_CODE_|CLAUDE_AGENT_SDK|CLAUDE_PID|CLAUDE_EFFORT|T3CODE_|ELECTRON_RUN_AS_NODE)/.test(name)) delete out[name];
  }
  return out;
}
function startTerminal({ cols, rows, prompt }) {
  if (term) return { running: true };
  if (!pty) pty = require("node-pty");
  const command = [config.host, ...(prompt ? [quote(prompt)] : [])].join(" ");
  const shellName = env.loginShell();
  const args = isWin ? ["/d", "/s", "/c", command] : ["-ilc", `exec ${command}`];
  term = pty.spawn(shellName, args, {
    name: "xterm-256color",
    cols: Math.max(20, cols | 0), rows: Math.max(5, rows | 0),
    cwd: config.vault,
    env: tutorEnv(),
  });
  const mine = term;
  term.onData((data) => { if (term === mine) send("pty:data", data); });
  term.onExit(({ exitCode }) => { if (term === mine) { term = null; send("pty:exit", exitCode); } });
  return { running: true };
}
function stopTerminal() { if (term) { const t = term; term = null; try { t.kill(); } catch { /* gone */ } } }

// ---------- IPC ----------
// The first name for Home's greeting, until the learner sets one in Settings.
let firstName = "";
function readFirstName() {
  if (process.platform !== "darwin") return;
  execFile("id", ["-F"], { timeout: 2000 }, (error, stdout) => {
    const full = String(stdout || "").trim();
    firstName = !error && full ? full.split(/\s+/)[0] : "";
  });
}
ipcMain.handle("app:info", () => ({ name: APP_NAME, version: app.getVersion(), platform: process.platform, firstName }));
ipcMain.handle("config:get", () => config);
ipcMain.handle("config:set", async (_e, patch) => {
  const hostChanged = patch.host && patch.host !== config.host;
  const vaultChanged = "vault" in patch && patch.vault !== config.vault;
  if (vaultChanged && env.checkVault(patch.vault)) delete patch.vault;
  config = { ...config, ...patch };
  saveConfig();
  if (vaultChanged && "vault" in patch) { stopTerminal(); lastState = ""; watchVault(); }
  if (patch.theme) nativeTheme.themeSource = config.theme === "night" ? "dark" : config.theme === "light" ? "light" : "system";
  if (hostChanged) { tools = env.checkTools(PATH, config.host); lastState = ""; }
  return config;
});
ipcMain.handle("setup:check", () => {
  tools = env.checkTools(PATH, config.host);
  return { vaultProblem: env.checkVault(config.vault), vault: config.vault, problems: tools.problems, host: config.host };
});
ipcMain.handle("vault:choose", async () => {
  const result = await dialog.showOpenDialog(win, { title: "Open your learning vault", properties: ["openDirectory"], buttonLabel: "Open vault" });
  if (result.canceled || !result.filePaths[0]) return { canceled: true };
  const dir = result.filePaths[0];
  const problem = env.checkVault(dir);
  if (problem) return { problem, dir };
  stopTerminal();
  config.vault = dir;
  saveConfig();
  lastState = "";
  watchVault();
  return { dir };
});
ipcMain.handle("state:get", () => readState());
ipcMain.handle("session:get", (_e, slug) => readSession(slug));
ipcMain.handle("pty:start", (_e, opts) => {
  try { return startTerminal(opts || {}); } catch (e) { term = null; console.error("tutor failed to start", e); return { error: String(e.message || e) }; }
});
ipcMain.handle("pty:running", () => !!term);
ipcMain.on("pty:write", (_e, data) => { if (term) term.write(data); });
ipcMain.on("pty:resize", (_e, { cols, rows }) => { if (term && cols > 0 && rows > 0) try { term.resize(cols, rows); } catch { /* exiting */ } });
ipcMain.handle("pty:stop", () => { stopTerminal(); return true; });
ipcMain.handle("open:external", (_e, url) => { if (/^https?:\/\//.test(url)) shell.openExternal(url); });
ipcMain.handle("open:file", (_e, rel) => {
  if (!config.vault) return;
  const full = path.resolve(config.vault, rel);
  if (full.startsWith(path.resolve(config.vault) + path.sep) && fs.existsSync(full)) shell.showItemInFolder(full);
});

// ---------- menus ----------
// Native menus carry every shortcut; each item sends its command to the window.
function buildMenu() {
  const cmd = (id) => () => send("menu", id);
  const isMac = process.platform === "darwin";
  // On Windows and Linux, Ctrl+letter belongs to the terminal (Ctrl+C stops a
  // command, Ctrl+R searches history), so the app's keys add Shift there.
  const a = (key) => (isMac ? "Cmd+" : "Ctrl+Shift+") + key;
  const template = [
    ...(isMac ? [{ label: APP_NAME, submenu: [
      { role: "about", label: `About ${APP_NAME}` },
      { type: "separator" },
      { label: "Settings…", accelerator: a(","), click: cmd("settings") },
      { type: "separator" }, { role: "hide" }, { role: "hideOthers" }, { role: "unhide" },
      { type: "separator" }, { role: "quit" },
    ] }] : []),
    { label: "File", submenu: [
      { label: "Open Vault…", accelerator: a("O"), click: cmd("open-vault") },
      ...(isMac ? [] : [{ label: "Settings…", accelerator: a(","), click: cmd("settings") }]),
      { type: "separator" }, isMac ? { role: "close" } : { role: "quit" },
    ] },
    { label: "Edit", submenu: [
      // Roles, so inputs behave natively; the terminal answers the same copy and
      // paste events with its own selection.
      { role: "undo" }, { role: "redo" }, { type: "separator" },
      { role: "cut" }, { role: "copy", ...(isMac ? {} : { accelerator: "Ctrl+Shift+C" }) },
      { role: "paste", ...(isMac ? {} : { accelerator: "Ctrl+Shift+V" }) }, { role: "selectAll" },
    ] },
    { label: "Go", submenu: [
      { label: "Home", accelerator: a("1"), click: cmd("go:home") },
      { label: "Session", accelerator: a("2"), click: cmd("go:session") },
      { label: "All Skills", accelerator: a("3"), click: cmd("go:system") },
      { label: "Dashboard", accelerator: a("4"), click: cmd("go:dashboard") },
      { label: "Subject Progress", accelerator: a("5"), click: cmd("go:progress") },
      { label: "Subject Skill Map", accelerator: a("6"), click: cmd("go:map") },
      { type: "separator" },
      { label: "Search and Commands…", accelerator: a("K"), click: cmd("palette") },
    ] },
    { label: "Session", submenu: [
      { label: "Do the Next Step", accelerator: a("Enter"), click: cmd("ink") },
      { label: "Start a Review", accelerator: a("R"), click: cmd("review") },
      { label: "Check Me", accelerator: a("J"), click: cmd("check") },
      { label: "Ask for a Hint", accelerator: a("/"), click: cmd("hint") },
      { label: "Take a Break", accelerator: a("B"), click: cmd("break") },
      { label: "End and Save", accelerator: isMac ? "Shift+Cmd+E" : "Ctrl+Shift+Alt+E", click: cmd("end") },
      { label: "Start a Subject…", accelerator: a("N"), click: cmd("start") },
      { type: "separator" },
      { label: "Restart the Tutor", click: cmd("restart") },
    ] },
    { label: "View", submenu: [
      { label: "Toggle Sidebar", accelerator: a("\\"), click: cmd("toggle-side") },
      { label: "Toggle Panel", accelerator: isMac ? "Alt+Cmd+0" : "Ctrl+Shift+Alt+0", click: cmd("toggle-panel") },
      { label: "Show Log", accelerator: isMac ? "Alt+Cmd+1" : "Ctrl+Shift+Alt+1", click: cmd("tab:log") },
      { label: "Show Session Note", accelerator: isMac ? "Alt+Cmd+2" : "Ctrl+Shift+Alt+2", click: cmd("tab:note") },
      { type: "separator" },
      { label: "Zoom In", accelerator: a("="), click: cmd("zoom-in") },
      { label: "Zoom Out", accelerator: a("-"), click: cmd("zoom-out") },
      { label: "Fit Map", accelerator: a("0"), click: cmd("zoom-fit") },
      { type: "separator" },
      { role: "togglefullscreen" },
      ...(app.isPackaged ? [] : [{ role: "toggleDevTools" }, { role: "reload" }]),
    ] },
    { role: "windowMenu" },
  ];
  Menu.setApplicationMenu(Menu.buildFromTemplate(template));
}

// ---------- window ----------
function createWindow() {
  const night = nativeTheme.shouldUseDarkColors;
  win = new BrowserWindow({
    width: 1360, height: 860, minWidth: 980, minHeight: 600,
    title: APP_NAME,
    backgroundColor: night ? "#141416" : "#F6F5F2",
    titleBarStyle: process.platform === "darwin" ? "hiddenInset" : "hidden",
    trafficLightPosition: { x: 14, y: 13 },
    ...(process.platform === "darwin" ? {} : { titleBarOverlay: { color: night ? "#0E0E10" : "#EEECE7", symbolColor: night ? "#B9B7B1" : "#4A4741", height: 38 } }),
    show: false,
    webPreferences: { preload: path.join(__dirname, "preload.js"), contextIsolation: true, nodeIntegration: false, sandbox: true, spellcheck: false },
  });
  win.loadFile(path.join(__dirname, "renderer", "index.html"));
  win.once("ready-to-show", () => win.show());
  if (!app.isPackaged || process.env.FLASH_SHOTS) win.webContents.on("console-message", (e) => { if (e.level !== "info" && e.level !== "debug") console.log(`[window ${e.level}] ${e.message} (${e.sourceId}:${e.lineNumber})`); });
  if (process.env.FLASH_SHOTS) win.webContents.once("did-finish-load", () => shots(process.env.FLASH_SHOTS));
  win.on("focus", () => send("window:focus"));
  win.webContents.setWindowOpenHandler(({ url }) => { if (/^https?:\/\//.test(url)) shell.openExternal(url); return { action: "deny" }; });
  win.webContents.on("will-navigate", (e, url) => { if (!url.startsWith("file:")) { e.preventDefault(); if (/^https?:/.test(url)) shell.openExternal(url); } });
  win.on("closed", () => { win = null; stopTerminal(); });
}

// Development only: FLASH_SHOTS=<dir> FLASH_STEPS='<js>;;<js>' npm start runs
// each step in the window and saves a screenshot after it, then quits.
async function shots(dir) {
  const wait = (ms) => new Promise((r) => setTimeout(r, ms));
  fs.mkdirSync(dir, { recursive: true });
  const steps = (process.env.FLASH_STEPS || "0").split(";;");
  await wait(Number(process.env.FLASH_WAIT || 2500));
  for (let i = 0; i < steps.length; i++) {
    try { await win.webContents.executeJavaScript(steps[i]); } catch (e) { console.error("step", i, e.message); }
    await wait(Number(process.env.FLASH_STEP_WAIT || 1500));
    const image = await win.webContents.capturePage();
    fs.writeFileSync(path.join(dir, `${String(i).padStart(2, "0")}.png`), image.toPNG());
  }
  app.quit();
}

if (!app.requestSingleInstanceLock()) app.quit();
app.on("second-instance", () => { if (win) { if (win.isMinimized()) win.restore(); win.focus(); } });

app.whenReady().then(async () => {
  nativeTheme.themeSource = config.theme === "night" ? "dark" : config.theme === "light" ? "light" : "system";
  // Screenshots the learner pasted, which the log embeds. Only image files, and
  // only from the vault's attachments folder.
  protocol.handle("vault-file", (request) => {
    const rel = decodeURIComponent(new URL(request.url).pathname.replace(/^\/+/, ""));
    const base = path.resolve(config.vault || "/nonexistent", "Claude outputs", "attachments");
    const full = path.resolve(base, path.basename(rel));
    if (!/\.(png|jpe?g|gif|webp)$/i.test(full) || !fs.existsSync(full)) return new Response("not found", { status: 404 });
    return net.fetch(pathToFileURL(full).toString());
  });
  readFirstName();
  PATH = await env.shellPath();
  tools = env.checkTools(PATH, config.host);
  buildMenu();
  watchVault();
  createWindow();
});
app.on("window-all-closed", () => app.quit());
app.on("before-quit", () => { stopTerminal(); if (watcher) watcher.close(); });
