// The only bridge between the window and the main process. The window can ask
// for data, drive the terminal, and change settings; it cannot touch files.
const { contextBridge, ipcRenderer } = require("electron");

const on = (channel) => (fn) => {
  const listener = (_e, payload) => fn(payload);
  ipcRenderer.on(channel, listener);
  return () => ipcRenderer.removeListener(channel, listener);
};

contextBridge.exposeInMainWorld("flash", {
  info: () => ipcRenderer.invoke("app:info"),
  config: () => ipcRenderer.invoke("config:get"),
  setConfig: (patch) => ipcRenderer.invoke("config:set", patch),
  setupCheck: () => ipcRenderer.invoke("setup:check"),
  chooseVault: () => ipcRenderer.invoke("vault:choose"),
  state: () => ipcRenderer.invoke("state:get"),
  session: (slug) => ipcRenderer.invoke("session:get", slug),
  openExternal: (url) => ipcRenderer.invoke("open:external", url),
  showFile: (rel) => ipcRenderer.invoke("open:file", rel),
  pty: {
    start: (opts) => ipcRenderer.invoke("pty:start", opts),
    running: () => ipcRenderer.invoke("pty:running"),
    stop: () => ipcRenderer.invoke("pty:stop"),
    write: (data) => ipcRenderer.send("pty:write", data),
    resize: (cols, rows) => ipcRenderer.send("pty:resize", { cols, rows }),
    onData: on("pty:data"),
    onExit: on("pty:exit"),
  },
  onState: on("state:changed"),
  onSession: on("session:changed"),
  onMenu: on("menu"),
  onFocus: on("window:focus"),
});
