const defaults = { language: "hi", speechEnabled: true, elevenLabsEnabled: true, voiceName: "", localOnly: false, sensitiveCaptureEnabled: false, screenshotBackendUrl: "", localScreenshotStorage: false, screenshotServerEnabled: true, screenshotServerUrl: "http://127.0.0.1:8787", ollamaUrl: "http://127.0.0.1:11434", model: "gemma4:31b-cloud" };
const ids = ["language", "speechEnabled", "elevenLabsEnabled", "voiceName", "localOnly", "sensitiveCaptureEnabled", "screenshotBackendUrl", "localScreenshotStorage", "screenshotServerEnabled", "screenshotServerUrl", "ollamaUrl", "model"];
const fields = Object.fromEntries(ids.map(id => [id, document.getElementById(id)]));
function loadVoices() {
  if (!("speechSynthesis" in window)) return;
  const selected = fields.voiceName.value;
  fields.voiceName.replaceChildren(new Option("Automatic", ""));
  speechSynthesis.getVoices().filter(voice => /^(hi|bn|gu|pa|en)(-|$)/i.test(voice.lang)).forEach(voice => fields.voiceName.add(new Option(`${voice.name} (${voice.lang})`, voice.name)));
  fields.voiceName.value = selected;
}
chrome.storage.local.get(defaults).then(settings => {
  ids.forEach(id => fields[id].type === "checkbox" ? fields[id].checked = settings[id] : fields[id].value = settings[id]);
  loadVoices();
});
if ("speechSynthesis" in window) speechSynthesis.addEventListener("voiceschanged", loadVoices);
document.getElementById("save").addEventListener("click", async () => {
  const settings = Object.fromEntries(ids.map(id => [id, fields[id].type === "checkbox" ? fields[id].checked : fields[id].value.trim()]));
  if (!/^https?:\/\//.test(settings.ollamaUrl)) return setStatus("Use an http:// or https:// Ollama URL.");
  if (!/^http:\/\/(127\.0\.0\.1|localhost)(:\d+)?\/?$/.test(settings.screenshotServerUrl)) return setStatus("The screenshot helper must be a local address such as http://127.0.0.1:8787.");
  if (settings.sensitiveCaptureEnabled && !/^https:\/\/[^/]+(?:\/[^/]*)?$/i.test(settings.screenshotBackendUrl)) return setStatus("Sensitive capture requires an HTTPS screenshot backend URL.");
  if (settings.sensitiveCaptureEnabled) {
    const origin = `${new URL(settings.screenshotBackendUrl).origin}/*`;
    const granted = await chrome.permissions.request({ origins: [origin] });
    if (!granted) return setStatus("Backend permission was not granted; sensitive capture remains disabled.");
  }
  await chrome.storage.local.set(settings); setStatus("Settings saved.");
});
document.getElementById("testAi").addEventListener("click", async () => {
  setStatus("Testing Ollama and configured model...");
  const result = await chrome.runtime.sendMessage({ type: "ollama-test" }).catch(() => ({ status: "unavailable", reason: "extension service worker unavailable" }));
  setStatus(result.status === "success" ? result.reason : `AI unavailable: ${result.reason}`);
});
document.getElementById("testVisual").addEventListener("click", async () => {
  setStatus("Testing Gemma image support...");
  const result = await chrome.runtime.sendMessage({ type: "visual-model-test" }).catch(() => ({ status: "unavailable", reason: "extension service worker unavailable" }));
  setStatus(result.status === "success" ? result.reason : `Visual AI unavailable: ${result.reason}`);
});
document.getElementById("testHelper").addEventListener("click", async () => {
  setStatus("Checking screenshot helper...");
  const result = await chrome.runtime.sendMessage({ type: "screenshot-server-test" }).catch(() => ({ status: "unavailable", reason: "extension service worker unavailable" }));
  setStatus(result.status === "success" ? result.reason : `Helper unavailable: ${result.reason}`);
});
document.getElementById("chooseFolder").addEventListener("click", async () => {
  if (!window.showDirectoryPicker) return setFolderStatus("This Chrome version does not support folder access.");
  try {
    const handle = await window.showDirectoryPicker({ mode: "readwrite" });
    const permission = await handle.requestPermission({ mode: "readwrite" });
    if (permission !== "granted") return setFolderStatus("Folder permission was not granted.");
    const request = indexedDB.open("suraksha-mitra", 1);
    request.onupgradeneeded = () => request.result.createObjectStore("settings");
    request.onsuccess = () => {
      const transaction = request.result.transaction("settings", "readwrite");
      transaction.objectStore("settings").put(handle, "screenshot-directory");
      transaction.oncomplete = () => setFolderStatus(`Selected: ${handle.name}`);
    };
    request.onerror = () => setFolderStatus("Could not save the folder permission.");
  } catch (error) {
    if (error.name !== "AbortError") setFolderStatus("Folder selection failed.");
  }
});
function setStatus(text) { document.getElementById("status").textContent = text; }
function setFolderStatus(text) { document.getElementById("folderStatus").textContent = text; }
