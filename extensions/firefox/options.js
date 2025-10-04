const DEFAULT_SUMMARIZER_URL = "http://homeassistant.local:8082/";
const STORAGE_KEY = "summarizerBaseUrl";

async function loadOptions() {
  try {
    const stored = await browser.storage.sync.get(STORAGE_KEY);
    const configuredUrl = stored[STORAGE_KEY] || DEFAULT_SUMMARIZER_URL;
    document.getElementById("baseUrl").value = configuredUrl;
  } catch (error) {
    console.error("Failed to load stored options", error);
    document.getElementById("baseUrl").value = DEFAULT_SUMMARIZER_URL;
  }
}

async function saveOptions(event) {
  event.preventDefault();

  const input = document.getElementById("baseUrl");
  const status = document.getElementById("status");
  const value = input.value.trim() || DEFAULT_SUMMARIZER_URL;

  try {
    new URL(value);
  } catch (error) {
    status.textContent = "Please enter a valid URL including http:// or https://.";
    return;
  }

  try {
    await browser.storage.sync.set({ [STORAGE_KEY]: value });
    status.textContent = "Saved.";
    setTimeout(() => {
      status.textContent = "";
    }, 2000);
  } catch (error) {
    console.error("Failed to save options", error);
    status.textContent = "Unable to save settings. Check the console for details.";
  }
}

document.addEventListener("DOMContentLoaded", () => {
  loadOptions();
  document.getElementById("optionsForm").addEventListener("submit", saveOptions);
});
