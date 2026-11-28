const { app, BrowserWindow, shell, ipcMain, dialog, net, Menu } = require("electron");
const path = require("path");
const fs = require("fs");

const UA = "OmniPilote/1.0 tableau-de-bord-meteo";

function createWindow() {
  const win = new BrowserWindow({
    width: 1360, height: 900, minWidth: 380, minHeight: 600,
    backgroundColor: "#0b1622", show: false, title: "OmniPilote",
    icon: path.join(__dirname, "..", "www", "icon.png"),
    autoHideMenuBar: true,
    webPreferences: { preload: path.join(__dirname, "preload.js"), contextIsolation: true, sandbox: true }
  });
  Menu.setApplicationMenu(null);
  win.once("ready-to-show", () => { win.maximize(); win.show(); });
  // Liens externes (sites, Google Maps, mail, téléphone) : navigateur ou appli du système
  win.webContents.setWindowOpenHandler(({ url }) => { shell.openExternal(url); return { action: "deny" }; });
  win.webContents.on("will-navigate", (ev, url) => {
    if (!url.startsWith("file://")) { ev.preventDefault(); shell.openExternal(url); }
  });
  win.loadFile(path.join(__dirname, "..", "www", "index.html"));
}

ipcMain.handle("omni:fetchJSON", async (_ev, url) => {
  if (!/^https:\/\/api\.(met\.no|open-meteo\.com)\//.test(url)) throw new Error("adresse refusée");
  const r = await net.fetch(url, { headers: { "User-Agent": UA, Accept: "application/json" } });
  if (!r.ok) throw new Error("HTTP " + r.status);
  return r.json();
});

ipcMain.handle("omni:saveFile", async (ev, name, text) => {
  const win = BrowserWindow.fromWebContents(ev.sender);
  const { canceled, filePath } = await dialog.showSaveDialog(win, {
    defaultPath: path.join(app.getPath("documents"), name),
    filters: name.endsWith(".csv") ? [{ name: "Tableur CSV", extensions: ["csv"] }] : [{ name: "Sauvegarde OmniPilote", extensions: ["json"] }]
  });
  if (canceled || !filePath) return false;
  fs.writeFileSync(filePath, text, "utf8");
  return true;
});

app.whenReady().then(() => {
  createWindow();
  app.on("activate", () => { if (BrowserWindow.getAllWindows().length === 0) createWindow(); });
});
app.on("window-all-closed", () => { if (process.platform !== "darwin") app.quit(); });
