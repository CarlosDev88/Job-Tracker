/**
 * popup.js — Controla la UI del popup y orquesta la extracción.
 */

// --- Helpers de vista ---
function show(id) {
    document.querySelectorAll('main > div').forEach(el => el.classList.add('hidden'));
    document.getElementById(id).classList.remove('hidden');
}

function setProgress(current, total) {
    const pct = total > 0 ? (current / total) * 100 : 0;
    document.getElementById('progress-fill').style.width = `${pct}%`;
    document.getElementById('progress-text').textContent = `${current} / ${total}`;
}

function generateFilename() {
    const now = new Date();
    const pad = n => String(n).padStart(2, '0');
    const ts = `${now.getFullYear()}${pad(now.getMonth() + 1)}${pad(now.getDate())}_${pad(now.getHours())}${pad(now.getMinutes())}${pad(now.getSeconds())}`;
    return `linkedin_${ts}.json`;
}

// --- Escucha progreso desde content.js ---
chrome.runtime.onMessage.addListener((message) => {
    if (message.type === 'PROGRESS') {
        setProgress(message.current, message.total);
    }
});

// --- Extracción principal ---
async function startExtraction() {
    show('view-progress');
    setProgress(0, 0);

    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });

    if (!tab.url.includes('linkedin.com/jobs')) {
        show('view-error');
        document.getElementById('error-text').textContent =
            'Abre LinkedIn Jobs primero (linkedin.com/jobs/search)';
        return;
    }

    // Asegura que content.js está inyectado
    await chrome.scripting.executeScript({
        target: { tabId: tab.id },
        files: ['content.js']
    }).catch(() => { }); // Ya inyectado → ignora error

    // Envía mensaje al content script
    chrome.tabs.sendMessage(tab.id, { type: 'START_EXTRACTION' }, (result) => {
        if (chrome.runtime.lastError || !result) {
            show('view-error');
            document.getElementById('error-text').textContent =
                'No se pudo comunicar con la página. Recarga LinkedIn e intenta de nuevo.';
            return;
        }

        if (result.error) {
            show('view-error');
            document.getElementById('error-text').textContent = result.error;
            return;
        }

        // Éxito — descarga el JSON
        const filename = generateFilename();
        chrome.runtime.sendMessage({
            type: 'DOWNLOAD_JSON',
            data: result.ofertas,
            filename
        });

        document.getElementById('result-number').textContent = result.total;
        document.getElementById('result-filename').textContent = filename;
        show('view-result');
    });
}

// --- Event listeners ---
document.getElementById('btn-extract').addEventListener('click', startExtraction);
document.getElementById('btn-again').addEventListener('click', () => show('view-idle'));
document.getElementById('btn-retry').addEventListener('click', () => show('view-idle'));