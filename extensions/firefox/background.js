const DEFAULT_SUMMARIZER_URL = "http://homeassistant.local:8082/";
const STORAGE_KEY = "summarizerBaseUrl";

async function getConfiguredBaseUrl() {
  try {
    const stored = await browser.storage.sync.get(STORAGE_KEY);
    const configured = stored[STORAGE_KEY];

    if (typeof configured === "string" && configured.trim()) {
      return configured.trim();
    }
  } catch (error) {
    console.error("Failed to read stored base URL", error);
  }

  return DEFAULT_SUMMARIZER_URL;
}

async function buildSummarizerUrl(videoUrl) {
  let baseUrlString = await getConfiguredBaseUrl();

  try {
    const baseUrl = new URL(baseUrlString);
    baseUrl.searchParams.set("video_url", videoUrl);
    return baseUrl.toString();
  } catch (error) {
    console.error("Invalid base URL, falling back to default", error);
    const fallback = new URL(DEFAULT_SUMMARIZER_URL);
    fallback.searchParams.set("video_url", videoUrl);
    return fallback.toString();
  }
}

browser.browserAction.onClicked.addListener(async (tab) => {
  if (!tab || !tab.url) {
    return;
  }

  const targetUrl = await buildSummarizerUrl(tab.url);
  browser.tabs.create({ url: targetUrl });
});

browser.runtime.onInstalled.addListener(async () => {
  const stored = await browser.storage.sync.get(STORAGE_KEY);
  if (!stored[STORAGE_KEY]) {
    await browser.storage.sync.set({ [STORAGE_KEY]: DEFAULT_SUMMARIZER_URL });
  }
});
