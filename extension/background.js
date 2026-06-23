chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
    if (message.type === 'DOWNLOAD_JSON') {
        const { data, filename } = message;

        // ✅ data: URL funciona en Service Workers
        const json = JSON.stringify(data, null, 2);
        const dataUrl = 'data:application/json;charset=utf-8,' + encodeURIComponent(json);

        chrome.downloads.download({
            url: dataUrl,
            filename: filename,
            saveAs: false
        }, (downloadId) => {
            if (chrome.runtime.lastError) {
                console.error('[JobTracker] Download error:', chrome.runtime.lastError.message);
                sendResponse({ ok: false, error: chrome.runtime.lastError.message });
            } else {
                sendResponse({ ok: true, downloadId });
            }
        });

        return true;
    }
});