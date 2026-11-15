const { contextBridge, ipcRenderer } = require("electron");
contextBridge.exposeInMainWorld("omniNative", {
  platform: "windows",
  fetchJSON: (url) => ipcRenderer.invoke("omni:fetchJSON", url),
  saveFile: (name, text) => ipcRenderer.invoke("omni:saveFile", name, text)
});
