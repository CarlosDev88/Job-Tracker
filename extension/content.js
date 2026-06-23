
const DELAY_MS = 2000;

function sleep(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
}

function safeNotify(msg) {
    try {
        chrome.runtime.sendMessage(msg);
    } catch (_) { }
}

async function waitForPanelUpdate(oldTitle, timeout = 8000) {

    console.log("[JobTracker] Esperando actualización del panel...");

    const start = Date.now();

    while (Date.now() - start < timeout) {

        const title =
            document.querySelector(
                '.job-details-jobs-unified-top-card__job-title, h1.t-24'
            )?.innerText?.trim();

        const desc =
            document.querySelector(
                '.jobs-description__content .jobs-box__html-content, #job-details'
            )?.innerText?.trim();

        if (
            title &&
            title !== oldTitle &&
            desc &&
            desc.length > 100
        ) {
            console.log("[JobTracker] Panel actualizado:", title);
            return true;
        }

        await sleep(300);
    }

    console.warn("[JobTracker] Timeout esperando panel");
    return false;
}

function extractJobDetail(link) {

    const getText = (selector) => {
        const el = document.querySelector(selector);
        return el ? el.innerText.trim() : null;
    };

    const titulo =
        getText('.job-details-jobs-unified-top-card__job-title')
        || getText('h1.t-24');

    const empresa =
        getText('.job-details-jobs-unified-top-card__company-name')
        || getText('.jobs-unified-top-card__company-name a');

    const ubicacion =
        getText('.job-details-jobs-unified-top-card__bullet')
        || getText('.jobs-unified-top-card__bullet');

    const descripcion =
        getText('.jobs-description__content .jobs-box__html-content')
        || getText('#job-details');

    const oferta = {
        titulo,
        empresa,
        ubicacion,
        descripcion,
        link,
        extraido_en: new Date().toISOString()
    };

    console.log("[JobTracker] Oferta extraída:", oferta);

    return oferta;
}

function getJobCards() {
    return Array.from(
        document.querySelectorAll(
            'li.jobs-search-results__list-item, li.scaffold-layout__list-item'
        )
    );
}

async function extractAllJobs() {

    const totalCards = getJobCards().length;

    if (totalCards === 0) {
        return { error: "No se encontraron tarjetas" };
    }

    const ofertas = [];
    const seen = new Set();

    console.log(`[JobTracker] Encontradas ${totalCards} tarjetas`);

    safeNotify({
        type: "PROGRESS",
        current: 0,
        total: totalCards
    });

    for (let i = 0; i < totalCards; i++) {

        try {

            // IMPORTANTE: volver a obtener las tarjetas
            const cards = getJobCards();

            const card = cards[i];

            if (!card) {
                console.warn(`[JobTracker] Tarjeta ${i} no existe`);
                continue;
            }

            const cardLinkEl =
                card.querySelector('a[href*="/jobs/view/"]');

            const expectedLink =
                cardLinkEl?.href.split("?")[0];

            console.log("================================");
            console.log(`[JobTracker] Procesando ${i + 1}/${totalCards}`);
            console.log("[JobTracker] Link:", expectedLink);

            const oldTitle =
                document.querySelector(
                    '.job-details-jobs-unified-top-card__job-title, h1.t-24'
                )?.innerText?.trim();

            card.scrollIntoView({
                behavior: "smooth",
                block: "center"
            });

            await sleep(500);

            const rect = card.getBoundingClientRect();

            const clickTarget = cardLinkEl || card;

            clickTarget.dispatchEvent(
                new MouseEvent("mousedown", {
                    bubbles: true,
                    cancelable: true,
                    clientX: rect.left + 10,
                    clientY: rect.top + 10
                })
            );

            clickTarget.dispatchEvent(
                new MouseEvent("mouseup", {
                    bubbles: true,
                    cancelable: true,
                    clientX: rect.left + 10,
                    clientY: rect.top + 10
                })
            );

            clickTarget.dispatchEvent(
                new MouseEvent("click", {
                    bubbles: true,
                    cancelable: true,
                    clientX: rect.left + 10,
                    clientY: rect.top + 10
                })
            );

            console.log("[JobTracker] Click realizado");

            await sleep(DELAY_MS);

            const loaded =
                await waitForPanelUpdate(oldTitle);

            console.log("[JobTracker] loaded =", loaded);

            if (!loaded) {
                continue;
            }

            const oferta = extractJobDetail(expectedLink);

            if (!oferta) {
                console.warn("[JobTracker] Oferta nula");
                continue;
            }

            if (!seen.has(expectedLink)) {

                seen.add(expectedLink);

                ofertas.push(oferta);

                console.log(
                    `[JobTracker] Guardada ${ofertas.length}:`,
                    oferta.titulo
                );

            } else {

                console.warn(
                    "[JobTracker] Link duplicado:",
                    expectedLink
                );
            }

        }
        catch (err) {

            console.error(
                `[JobTracker] Error tarjeta ${i + 1}`,
                err
            );
        }

        safeNotify({
            type: "PROGRESS",
            current: i + 1,
            total: totalCards
        });
    }

    console.log("[JobTracker] FIN");
    console.log(ofertas);

    return {
        ofertas,
        total: ofertas.length
    };
}

chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {

    if (message.type === "START_EXTRACTION") {

        extractAllJobs()
            .then(sendResponse)
            .catch(err => {
                console.error(err);
                sendResponse({
                    error: err.message
                });
            });

        return true;
    }
});