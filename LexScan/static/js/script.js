const dropZone = document.getElementById("dropZone");
const fileInput = document.getElementById("fileInput");
const fileName = document.getElementById("fileName");
const textInput = document.getElementById("textInput");
const domainSelect = document.getElementById("domainSelect");
const languageSelect = document.getElementById("languageSelect");
const analyzeBtn = document.getElementById("analyzeBtn");
const analyzeProgress = document.getElementById("analyzeProgress");
const analyzeProgressTitle = document.getElementById("analyzeProgressTitle");
const analyzeProgressList = document.getElementById("analyzeProgressList");
const pdfBtn = document.getElementById("pdfBtn");
const jsonBtn = document.getElementById("jsonBtn");
const uploadStatus = document.getElementById("uploadStatus");
const pdfReadyLine = document.getElementById("pdfReadyLine");
const reportDownloadLine = document.getElementById("reportDownloadLine");
const reportLinkBtn = document.getElementById("reportLinkBtn");
const reportMetaText = document.getElementById("reportMetaText");
const jsonPanel = document.getElementById("jsonPanel");
const jsonPreview = document.getElementById("jsonPreview");
const jsonDownloadBtn = document.getElementById("jsonDownloadBtn");
const jsonCopyBtn = document.getElementById("jsonCopyBtn");
const highlightOutput = document.getElementById("highlightOutput");
const classificationOutput = document.getElementById("classificationOutput");
const reportSummary = document.getElementById("reportSummary");
const domainReasoning = document.getElementById("domainReasoning");
const aiInsight = document.getElementById("aiInsight");
const insightsOutput = document.getElementById("insightsOutput");
const processingTime = document.getElementById("processingTime");
const workspaceTitle = document.getElementById("workspaceTitle");
const workspaceCollection = document.getElementById("workspaceCollection");
const workspaceDomain = document.getElementById("workspaceDomain");
const workspaceSaveMode = document.getElementById("workspaceSaveMode");
const workspaceText = document.getElementById("workspaceText");
const workspaceAnalyzeBtn = document.getElementById("workspaceAnalyzeBtn");
const workspaceUseCurrentBtn = document.getElementById("workspaceUseCurrentBtn");
const workspaceStatus = document.getElementById("workspaceStatus");
const workspaceSubtype = document.getElementById("workspaceSubtype");
const workspaceSummary = document.getElementById("workspaceSummary");
const workspaceFlags = document.getElementById("workspaceFlags");
const workspaceTimeline = document.getElementById("workspaceTimeline");
const workspaceActions = document.getElementById("workspaceActions");
const workspaceRelations = document.getElementById("workspaceRelations");
const workspaceEntities = document.getElementById("workspaceEntities");
const workspaceQuestion = document.getElementById("workspaceQuestion");
const workspaceQuestionBtn = document.getElementById("workspaceQuestionBtn");
const workspaceAnswer = document.getElementById("workspaceAnswer");
const workspaceCompareA = document.getElementById("workspaceCompareA");
const workspaceCompareB = document.getElementById("workspaceCompareB");
const workspaceCompareBtn = document.getElementById("workspaceCompareBtn");
const workspaceCompareOutput = document.getElementById("workspaceCompareOutput");
const workspaceSearchInput = document.getElementById("workspaceSearchInput");
const workspaceSearchBtn = document.getElementById("workspaceSearchBtn");
const workspaceSearchResults = document.getElementById("workspaceSearchResults");
const workspaceRecentDocs = document.getElementById("workspaceRecentDocs");
const compareTabDomainA = document.getElementById("compareTabDomainA");
const compareTabDomainB = document.getElementById("compareTabDomainB");
const compareTabTextA = document.getElementById("compareTabTextA");
const compareTabTextB = document.getElementById("compareTabTextB");
const compareTabRunBtn = document.getElementById("compareTabRunBtn");
const compareTabUseWorkspaceBtn = document.getElementById("compareTabUseWorkspaceBtn");
const compareTabStatus = document.getElementById("compareTabStatus");
const compareTabOutput = document.getElementById("compareTabOutput");

const assistantContext = document.getElementById("assistantContext");
const assistantQuestion = document.getElementById("assistantQuestion");
const assistantAskBtn = document.getElementById("assistantAskBtn");
const assistantStatus = document.getElementById("assistantStatus");
const assistantAnswer = document.getElementById("assistantAnswer");

const batchInput = document.getElementById("batchInput");
const batchDomain = document.getElementById("batchDomain");
const batchRunBtn = document.getElementById("batchRunBtn");
const batchStatus = document.getElementById("batchStatus");
const batchTableBody = document.querySelector("#batchTable tbody");
const batchEntityDetails = document.getElementById("batchEntityDetails");

const multiLanguageSelect = document.getElementById("multiLanguageSelect");
const multiDomainSelect = document.getElementById("multiDomainSelect");
const multiSourceText = document.getElementById("multiSourceText");
const translateBtn = document.getElementById("translateBtn");
const multiAnalyzeBtn = document.getElementById("multiAnalyzeBtn");
const multiStatus = document.getElementById("multiStatus");
const multiTranslatedOutput = document.getElementById("multiTranslatedOutput");
const multiEntityChips = document.getElementById("multiEntityChips");
const multiClassificationOutput = document.getElementById("multiClassificationOutput");
const multiInsightsOutput = document.getElementById("multiInsightsOutput");
const multiAiInsight = document.getElementById("multiAiInsight");
const multiPdfBtn = document.getElementById("multiPdfBtn");
const multiJsonBtn = document.getElementById("multiJsonBtn");

const menuToggle = document.querySelector(".menu-toggle");
const mainNav = document.querySelector(".main-nav");
const tabPanels = document.querySelectorAll(".tab-panel");
const navTabs = mainNav.querySelectorAll("[data-tab-target]");

let latestAnalysis = null;
let latestMulti = null;
let latestReport = null;
let latestTranslatedText = "";
let analyzeProgressTimer = null;
let latestWorkspace = null;

const esc = (value) =>
    String(value)
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#39;");

const entityClassForLabel = (label) => {
    const key = String(label || "").toUpperCase();
    if (["PERSON", "PER", "JUDGE", "PARTY"].includes(key)) return "entity-person";
    if (["ORG", "COURT"].includes(key)) return "entity-org";
    if (["DATE"].includes(key)) return "entity-date";
    if (["LOCATION", "LOC"].includes(key)) return "entity-loc";
    return "entity-org";
};

function setButtonLoading(button, loadingText, pending) {
    if (!button.dataset.originalText) {
        button.dataset.originalText = button.textContent;
    }
    button.disabled = pending;
    button.textContent = pending ? loadingText : button.dataset.originalText;
}

function startAnalyzeProgress() {
    if (!analyzeProgress || !analyzeProgressList || !analyzeProgressTitle) return;
    analyzeProgress.style.display = "block";
    analyzeProgressTitle.textContent = "Processing document...";
    analyzeProgressList.innerHTML = "";

    const steps = [
        "Validating input text and selected options...",
        "Detecting likely domain (medical / legal / general)...",
        "Running NER model inference...",
        "Aggregating entities and confidence scores...",
        "Generating insights and report metadata...",
    ];

    let idx = 0;
    const pushStep = () => {
        if (idx >= steps.length) return;
        const li = document.createElement("li");
        li.textContent = steps[idx];
        analyzeProgressList.appendChild(li);
        idx += 1;
    };

    pushStep();
    analyzeProgressTimer = setInterval(pushStep, 700);
}

function finishAnalyzeProgress(success, message) {
    if (!analyzeProgress || !analyzeProgressList || !analyzeProgressTitle) return;
    if (analyzeProgressTimer) {
        clearInterval(analyzeProgressTimer);
        analyzeProgressTimer = null;
    }
    analyzeProgressTitle.textContent = success ? "Analysis completed" : "Analysis failed";
    const li = document.createElement("li");
    li.textContent = message;
    analyzeProgressList.appendChild(li);
}

function setActiveTab(tabId) {
    tabPanels.forEach((panel) => panel.classList.toggle("active", panel.id === tabId));
    navTabs.forEach((tab) => tab.classList.toggle("active", tab.dataset.tabTarget === tabId));
}

function bindNavigation() {
    menuToggle.addEventListener("click", () => {
        mainNav.classList.toggle("open");
    });
    navTabs.forEach((tab) => {
        tab.addEventListener("click", (event) => {
            event.preventDefault();
            setActiveTab(tab.dataset.tabTarget);
            mainNav.classList.remove("open");
        });
    });
}

function bindUploadEvents() {
    ["dragenter", "dragover"].forEach((eventName) => {
        dropZone.addEventListener(eventName, (e) => {
            e.preventDefault();
            dropZone.classList.add("dragover");
        });
    });
    ["dragleave", "drop"].forEach((eventName) => {
        dropZone.addEventListener(eventName, (e) => {
            e.preventDefault();
            dropZone.classList.remove("dragover");
        });
    });
    dropZone.addEventListener("drop", (e) => {
        const files = e.dataTransfer.files;
        if (files && files[0]) {
            fileInput.files = files;
            fileName.textContent = `Selected: ${files[0].name}`;
            uploadStatus.textContent = "Uploading and extracting text...";
            extractFileToTextbox(files[0]);
        }
    });
    fileInput.addEventListener("change", () => {
        fileName.textContent = fileInput.files[0] ? `Selected: ${fileInput.files[0].name}` : "No file selected";
        if (fileInput.files[0]) {
            uploadStatus.textContent = "Uploading and extracting text...";
            extractFileToTextbox(fileInput.files[0]);
        }
    });
}

async function extractFileToTextbox(file) {
    try {
        const form = new FormData();
        form.append("file", file);
        const response = await fetch("/api/extract", { method: "POST", body: form });
        const data = await response.json();
        if (!response.ok) throw new Error(data.error || "Extraction failed");
        const extractedText = data.text || "";
        textInput.value = extractedText;
        assistantContext.value = extractedText;
        uploadStatus.textContent = `Loaded ${data.filename || file.name} (${data.file_type || "file"}) into the editor.`;
        uploadStatus.classList.remove("muted");
        return extractedText;
    } catch (error) {
        uploadStatus.textContent = `Upload failed: ${esc(error.message)}`;
        uploadStatus.classList.add("muted");
        return "";
    }
}

function highlightText(text, entities) {
    if (!entities.length) return esc(text);
    let cursor = 0;
    let output = "";
    entities.forEach((entity) => {
        if (entity.start < cursor) return;
        output += esc(text.slice(cursor, entity.start));
        output += `<span class="entity ${entityClassForLabel(entity.label)}" title="${esc(entity.label)}">${esc(entity.text)}</span>`;
        cursor = entity.end;
    });
    output += esc(text.slice(cursor));
    return output;
}

function splitBatchInput(text) {
    return (text || "")
        .split(/\n\s*\n/g)
        .map((x) => x.trim())
        .filter(Boolean);
}

function renderStackCards(container, items, formatter) {
    if (!container) return;
    if (!items || !items.length) {
        container.innerHTML = "<span class='muted'>Nothing to show yet.</span>";
        container.classList.remove("muted");
        return;
    }
    container.innerHTML = items.map((item) => formatter(item)).join("");
    container.classList.remove("muted");
}

async function loadLanguages() {
    try {
        const response = await fetch("/api/languages");
        const data = await response.json();
        if (!response.ok || !Array.isArray(data.languages)) return;
        const options = data.languages.map((lang) => `<option value="${esc(lang)}">${esc(lang)}</option>`).join("");
        languageSelect.innerHTML = options;
        multiLanguageSelect.innerHTML = options;
        languageSelect.value = "English";
        multiLanguageSelect.value = "Arabic";
    } catch (_error) {
        // keep UI usable even if language API fails
    }
}

function renderWorkspaceAnalysis(payload) {
    const analysis = payload?.analysis || {};
    const entities = analysis.normalized_entities || analysis.entities || [];
    const documentId = payload?.document_id || null;
    latestWorkspace = { ...payload, analysis };
    workspaceStatus.textContent = documentId
        ? `Smart analysis complete. Saved document ${documentId.slice(0, 8)} in ${payload.collection_name}.`
        : "Smart analysis complete. This run was not saved.";
    workspaceSubtype.innerHTML = `
        <span class="chip">Subtype: ${esc(String(analysis.subtype || "unknown").replace(/_/g, " "))}</span>
        <span class="chip">Domain: ${esc(String(analysis.domain || "unknown").toUpperCase())}</span>
        <span class="chip">Entities: ${entities.length}</span>
        <span class="chip">Saved: ${documentId ? "Yes" : "No"}</span>
    `;
    const plain = analysis.plain_language || {};
    workspaceSummary.innerHTML = `
        <p><strong>${esc(plain.title || "Plain-language explanation")}</strong></p>
        <p>${esc(plain.short_summary || "No summary available.")}</p>
        <ul>${(plain.bullet_points || []).map((item) => `<li>${esc(item)}</li>`).join("")}</ul>
    `;
    renderStackCards(workspaceFlags, analysis.red_flags || [], (item) => `
        <div class="stack-card">
            <strong>${esc(item.title || "Flag")}</strong>
            <div>${esc(item.guidance || "")}</div>
            <div class="stack-meta">Evidence: ${esc(item.evidence || "--")} | Severity: ${esc(item.severity || "medium")}</div>
        </div>
    `);
    renderStackCards(workspaceActions, analysis.action_items || [], (item) => `
        <div class="stack-card">
            <strong>${esc(item.title || "Action item")}</strong>
            <div>${esc(item.action || "")}</div>
            <div class="stack-meta">Priority: ${esc(item.priority || "medium")}</div>
        </div>
    `);
    renderStackCards(workspaceTimeline, analysis.timeline || [], (item) => `
        <div class="stack-card">
            <strong>${esc(item.date || "--")}</strong>
            <div>${esc(item.event || "")}</div>
        </div>
    `);
    renderStackCards(workspaceRelations, analysis.relations || [], (item) => `
        <div class="stack-card">
            <strong>${esc(item.relation || "relation")}</strong>
            <div>${esc((item.entities || []).join(" -> "))}</div>
            <div class="stack-meta">${esc(item.evidence || "")}</div>
        </div>
    `);
    workspaceEntities.innerHTML = entities.length
        ? `<div class="entity-pill-grid">${entities.slice(0, 24).map((item) => `<span class="entity-pill">${esc(item.label || "UNK")}: ${esc(item.canonical_text || item.text || "")}</span>`).join("")}</div>`
        : "<span class='muted'>No normalized entities available.</span>";
    workspaceEntities.classList.remove("muted");
}

async function refreshWorkspaceDocuments() {
    if (!workspaceRecentDocs) return;
    try {
        const response = await fetch("/api/workspace/documents");
        const data = await response.json();
        if (!response.ok) throw new Error(data.detail || data.error || "Could not load workspace documents");
        renderStackCards(workspaceRecentDocs, data.documents || [], (item) => `
            <div class="stack-card" data-document-id="${esc(item.document_id || "")}">
                <strong>${esc(item.title || "Untitled")}</strong>
                <div>${esc(item.collection_name || "Default")} | ${esc(item.subtype || "unknown")}</div>
                <div class="stack-meta">${esc(String(item.domain || "general").toUpperCase())}</div>
            </div>
        `);
        workspaceRecentDocs.querySelectorAll("[data-document-id]").forEach((node) => {
            node.style.cursor = "pointer";
            node.addEventListener("click", () => loadWorkspaceDocument(node.getAttribute("data-document-id")));
        });
    } catch (error) {
        workspaceRecentDocs.innerHTML = `<span class='muted'>${esc(error.message)}</span>`;
    }
}

async function loadWorkspaceDocument(documentId) {
    if (!documentId) return;
    try {
        const response = await fetch(`/api/workspace/documents/${encodeURIComponent(documentId)}`);
        const data = await response.json();
        if (!response.ok) throw new Error(data.detail || data.error || "Could not load document");
        workspaceTitle.value = data.title || "";
        workspaceCollection.value = data.collection_name || "";
        workspaceText.value = data.text || "";
        workspaceDomain.value = data.domain || "auto";
        renderWorkspaceAnalysis({
            title: data.title,
            collection_name: data.collection_name,
            document_id: data.document_id,
            analysis: data.analysis,
        });
        workspaceStatus.textContent = `Loaded saved document ${documentId.slice(0, 8)}.`;
        setActiveTab("tab-smart");
    } catch (error) {
        workspaceStatus.textContent = esc(error.message);
    }
}

async function runWorkspaceAnalysis() {
    const text = workspaceText.value.trim();
    if (!text) {
        workspaceStatus.textContent = "Please paste a document into the smart workspace first.";
        return;
    }
    setButtonLoading(workspaceAnalyzeBtn, "Analyzing...", true);
    workspaceStatus.textContent = "Running smart document intelligence...";
    try {
        const response = await fetch("/api/workspace/analyze", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                title: workspaceTitle.value,
                collection_name: workspaceCollection.value,
                text,
                domain: workspaceDomain.value,
                save_document: workspaceSaveMode.value === "save",
            }),
        });
        const data = await response.json();
        if (!response.ok) throw new Error(data.detail || data.error || "Workspace analysis failed");
        renderWorkspaceAnalysis(data);
        await refreshWorkspaceDocuments();
    } catch (error) {
        workspaceStatus.textContent = esc(error.message);
    } finally {
        setButtonLoading(workspaceAnalyzeBtn, "Analyzing...", false);
    }
}

async function runWorkspaceQuestion() {
    const text = (latestWorkspace?.analysis?.text || workspaceText.value || "").trim();
    const question = workspaceQuestion.value.trim();
    if (!text || !question) {
        workspaceAnswer.textContent = "Please analyze a document and enter a question.";
        workspaceAnswer.classList.remove("muted");
        return;
    }
    setButtonLoading(workspaceQuestionBtn, "Answering...", true);
    try {
        const response = await fetch("/api/workspace/question", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ text, question }),
        });
        const data = await response.json();
        if (!response.ok) throw new Error(data.detail || data.error || "Question answering failed");
        workspaceAnswer.innerHTML = `
            <p>${esc(data.answer || "")}</p>
            <ul>${(data.citations || []).map((item) => `<li>${esc(item)}</li>`).join("")}</ul>
        `;
        workspaceAnswer.classList.remove("muted");
    } catch (error) {
        workspaceAnswer.textContent = esc(error.message);
        workspaceAnswer.classList.remove("muted");
    } finally {
        setButtonLoading(workspaceQuestionBtn, "Answering...", false);
    }
}

async function runWorkspaceCompare() {
    const textA = workspaceCompareA.value.trim();
    const textB = workspaceCompareB.value.trim();
    if (!textA || !textB) {
        workspaceCompareOutput.textContent = "Please provide both documents for comparison.";
        workspaceCompareOutput.classList.remove("muted");
        return;
    }
    setButtonLoading(workspaceCompareBtn, "Comparing...", true);
    try {
        const response = await fetch("/api/workspace/compare", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                text_a: textA,
                text_b: textB,
                domain_a: workspaceDomain.value,
                domain_b: workspaceDomain.value,
            }),
        });
        const data = await response.json();
        if (!response.ok) throw new Error(data.detail || data.error || "Comparison failed");
        const comparison = data.comparison || {};
        workspaceCompareOutput.innerHTML = `
            <ul>${(comparison.summary || []).map((item) => `<li>${esc(item)}</li>`).join("")}</ul>
            <p><strong>Only in A:</strong> ${esc((comparison.only_in_a || []).join(", ") || "None")}</p>
            <p><strong>Only in B:</strong> ${esc((comparison.only_in_b || []).join(", ") || "None")}</p>
        `;
        workspaceCompareOutput.classList.remove("muted");
    } catch (error) {
        workspaceCompareOutput.textContent = esc(error.message);
        workspaceCompareOutput.classList.remove("muted");
    } finally {
        setButtonLoading(workspaceCompareBtn, "Comparing...", false);
    }
}

async function runWorkspaceSearch() {
    const query = workspaceSearchInput.value.trim();
    if (!query) {
        workspaceSearchResults.textContent = "Enter a search query first.";
        workspaceSearchResults.classList.remove("muted");
        return;
    }
    setButtonLoading(workspaceSearchBtn, "Searching...", true);
    try {
        const response = await fetch(`/api/workspace/search?query=${encodeURIComponent(query)}`);
        const data = await response.json();
        if (!response.ok) throw new Error(data.detail || data.error || "Search failed");
        renderStackCards(workspaceSearchResults, data.results || [], (item) => `
            <div class="stack-card" data-document-id="${esc(item.document_id || "")}">
                <strong>${esc(item.title || "Untitled")}</strong>
                <div>${esc(item.preview || "")}</div>
                <div class="stack-meta">${esc(item.collection_name || "Default")} | ${esc(String(item.domain || "general").toUpperCase())} | Entities: ${item.entity_count ?? 0}</div>
            </div>
        `);
        workspaceSearchResults.querySelectorAll("[data-document-id]").forEach((node) => {
            node.style.cursor = "pointer";
            node.addEventListener("click", () => loadWorkspaceDocument(node.getAttribute("data-document-id")));
        });
    } catch (error) {
        workspaceSearchResults.textContent = esc(error.message);
        workspaceSearchResults.classList.remove("muted");
    } finally {
        setButtonLoading(workspaceSearchBtn, "Searching...", false);
    }
}

async function runCompareTab() {
    const textA = compareTabTextA.value.trim();
    const textB = compareTabTextB.value.trim();
    if (!textA || !textB) {
        compareTabStatus.textContent = "Please provide both documents first.";
        return;
    }
    setButtonLoading(compareTabRunBtn, "Comparing...", true);
    compareTabStatus.textContent = "Comparing documents...";
    try {
        const response = await fetch("/api/workspace/compare", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                text_a: textA,
                text_b: textB,
                domain_a: compareTabDomainA.value,
                domain_b: compareTabDomainB.value,
            }),
        });
        const data = await response.json();
        if (!response.ok) throw new Error(data.detail || data.error || "Comparison failed");
        const comparison = data.comparison || {};
        compareTabStatus.textContent = "Comparison complete.";
        compareTabOutput.innerHTML = `
            <ul>${(comparison.summary || []).map((item) => `<li>${esc(item)}</li>`).join("")}</ul>
            <p><strong>Only in A:</strong> ${esc((comparison.only_in_a || []).join(", ") || "None")}</p>
            <p><strong>Only in B:</strong> ${esc((comparison.only_in_b || []).join(", ") || "None")}</p>
        `;
        compareTabOutput.classList.remove("muted");
    } catch (error) {
        compareTabStatus.textContent = esc(error.message);
        compareTabOutput.textContent = esc(error.message);
        compareTabOutput.classList.remove("muted");
    } finally {
        setButtonLoading(compareTabRunBtn, "Comparing...", false);
    }
}

async function runDocumentAnalysis() {
    let sourceText = textInput.value.trim();
    const selectedFile = fileInput?.files?.[0];
    // If user selected a file but textbox is empty, auto-extract now.
    if (!sourceText && selectedFile) {
        uploadStatus.textContent = "Extracting text from selected file...";
        sourceText = (await extractFileToTextbox(selectedFile)).trim();
    }
    if (!sourceText) {
        highlightOutput.innerHTML = "<span class='muted'>Paste text or upload a file, then analyze.</span>";
        return;
    }
    const started = performance.now();
    setButtonLoading(analyzeBtn, "Analyzing...", true);
    startAnalyzeProgress();
    try {
        const response = await fetch("/api/document/analyze", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ text: sourceText, domain: domainSelect.value, language: languageSelect.value }),
        });
        const data = await response.json();
        if (!response.ok) throw new Error(data.error || "Request failed");

        const result = data.result || {};
        const entities = result.entities || [];
        const confidence = entities.length
            ? (entities.reduce((sum, entity) => sum + (Number(entity.confidence) || 0), 0) / entities.length).toFixed(2)
            : "--";
        const riskSignals = sourceText.toLowerCase().match(/risk|liability|critical|urgent|breach|fraud/g)?.length || 0;
        const elapsed = `${Math.max(0.2, (performance.now() - started) / 1000).toFixed(2)}s`;

        highlightOutput.innerHTML = data.highlight_html || highlightText(sourceText, entities);
        if (reportSummary) {
            reportSummary.innerHTML = data.summary_html || "<span class='muted'>Summary not available.</span>";
            reportSummary.classList.remove("muted");
        }
        if (domainReasoning) {
            domainReasoning.innerHTML = data.domain_html || "<span class='muted'>Domain reasoning not available.</span>";
            domainReasoning.classList.remove("muted");
        }
        if (aiInsight) {
            aiInsight.innerHTML = data.insight_html || "<span class='muted'>AI insight not available.</span>";
            aiInsight.classList.remove("muted");
        }
        classificationOutput.innerHTML = `
            <span class="chip">Domain: ${esc((result.domain || "unknown").toUpperCase())}</span>
            <span class="chip">Confidence: ${esc(confidence)}</span>
            <span class="chip">Language: ${esc(languageSelect.value)}</span>
        `;
        processingTime.textContent = elapsed;
        insightsOutput.innerHTML = `
            <div class="insight-item"><p class="insight-title">Total Entities</p><p class="insight-value">${entities.length}</p></div>
            <div class="insight-item"><p class="insight-title">Risk Signals</p><p class="insight-value">${riskSignals}</p></div>
            <div class="insight-item"><p class="insight-title">Detected Language</p><p class="insight-value">${esc(languageSelect.value)}</p></div>
            <div class="insight-item"><p class="insight-title">Processing Time</p><p class="insight-value">${elapsed}</p></div>
        `;
        latestAnalysis = {
            text: sourceText,
            domain: result.domain,
            language: languageSelect.value,
            confidence,
            entities,
            result,
            generatedAt: new Date().toISOString(),
        };
        latestReport = data.report || null;
        assistantContext.value = sourceText;

        // Show "PDF ready" line after a successful analysis.
        if (pdfReadyLine) {
            pdfReadyLine.style.display = "block";
            pdfReadyLine.classList.remove("muted");
            pdfReadyLine.textContent = `PDF ready. Click Download PDF to save the report (${esc(languageSelect.value)}).`;
        }
        if (reportDownloadLine && latestReport) {
            reportDownloadLine.style.display = "block";
            reportDownloadLine.classList.remove("muted");
            if (reportMetaText) {
                reportMetaText.textContent = `(${latestReport.filename}, ${latestReport.size_label})`;
            }
        }
        finishAnalyzeProgress(true, `Done in ${elapsed}. Entities found: ${entities.length}.`);
    } catch (error) {
        highlightOutput.innerHTML = `<span class='muted'>${esc(error.message)}</span>`;
        finishAnalyzeProgress(false, `Stopped: ${esc(error.message)}`);
        if (pdfReadyLine) {
            pdfReadyLine.style.display = "block";
            pdfReadyLine.classList.add("muted");
            pdfReadyLine.textContent = "PDF will be available after a successful analysis.";
        }
        if (reportDownloadLine) {
            reportDownloadLine.style.display = "none";
        }
    } finally {
        setButtonLoading(analyzeBtn, "Analyzing...", false);
    }
}

async function downloadPdf({ text, domain, targetLanguage, title }) {
    const response = await fetch("/api/report/pdf", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
            text,
            domain: domain || "auto",
            target_language: targetLanguage || "English",
            title: title || "LexScan NER Report",
        }),
    });
    if (!response.ok) {
        const err = await response.json().catch(() => ({}));
        throw new Error(err.error || "PDF generation failed");
    }
    const blob = await response.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "lexscan-report.pdf";
    a.click();
    URL.revokeObjectURL(url);
}

async function runAssistant() {
    const question = assistantQuestion.value.trim();
    if (!question) {
        assistantStatus.textContent = "Please enter a question.";
        return;
    }
    setButtonLoading(assistantAskBtn, "Asking...", true);
    assistantStatus.textContent = "Submitting request...";
    try {
        const response = await fetch("/api/assistant", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                context: assistantContext.value,
                question,
            }),
        });
        const data = await response.json();
        if (!response.ok) throw new Error(data.error || "Assistant failed");
        assistantStatus.textContent = data.status || "Assistant response ready.";
        assistantAnswer.innerHTML = esc(data.answer || "").replace(/\n/g, "<br>");
        assistantAnswer.classList.remove("muted");
    } catch (error) {
        assistantStatus.textContent = esc(error.message);
    } finally {
        setButtonLoading(assistantAskBtn, "Asking...", false);
    }
}

async function runBatch() {
    const chunks = splitBatchInput(batchInput.value);
    if (!chunks.length) {
        batchStatus.textContent = "Please add at least one document block.";
        return;
    }
    setButtonLoading(batchRunBtn, "Running...", true);
    batchStatus.textContent = "Running batch analysis...";
    try {
        const response = await fetch("/api/batch", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ text_blocks: chunks.join("\n\n"), domain: batchDomain.value }),
        });
        const data = await response.json();
        if (!response.ok) throw new Error(data.error || "Batch failed");
        batchStatus.textContent = data.status || "Batch complete.";
        batchTableBody.innerHTML = (data.rows || [])
            .map((row) => {
                const [idx, dom, count, preview] = row;
                return `<tr><td>${idx}</td><td>${esc(dom)}</td><td>${count}</td><td>${esc(preview)}</td></tr>`;
            })
            .join("");

        const fullResults = data.full?.results || [];
        if (batchEntityDetails) {
            if (!fullResults.length) {
                batchEntityDetails.innerHTML = "<span class='batch-entity-empty'>No batch results available.</span>";
                batchEntityDetails.classList.remove("muted");
            } else {
                batchEntityDetails.innerHTML = fullResults
                    .map((item, index) => {
                        const entities = item.entities || [];
                        const title = `Document ${index + 1} - ${esc(item.domain || "unknown")}`;
                        const meta = `${entities.length} entit${entities.length === 1 ? "y" : "ies"}`;
                        if (!entities.length) {
                            return `
                                <div class="batch-entity-group">
                                    <div class="batch-entity-title">${title}</div>
                                    <div class="batch-entity-meta">${meta}</div>
                                    <div class="batch-entity-empty">No entities detected.</div>
                                </div>
                            `;
                        }
                        const rows = entities
                            .map((e) => {
                                return `
                                    <tr>
                                        <td>${esc(e.text || "")}</td>
                                        <td>${esc(e.label || "")}</td>
                                        <td>${typeof e.confidence === "number" ? `${(e.confidence * 100).toFixed(1)}%` : "--"}</td>
                                        <td>[${e.start ?? "-"}:${e.end ?? "-"}]</td>
                                    </tr>
                                `;
                            })
                            .join("");
                        return `
                            <div class="batch-entity-group">
                                <div class="batch-entity-title">${title}</div>
                                <div class="batch-entity-meta">${meta}</div>
                                <table class="mini-table">
                                    <thead>
                                        <tr>
                                            <th>Entity</th>
                                            <th>Label</th>
                                            <th>Confidence</th>
                                            <th>Position</th>
                                        </tr>
                                    </thead>
                                    <tbody>${rows}</tbody>
                                </table>
                            </div>
                        `;
                    })
                    .join("");
                batchEntityDetails.classList.remove("muted");
            }
        }
    } catch (error) {
        batchStatus.textContent = esc(error.message);
        if (batchEntityDetails) {
            batchEntityDetails.innerHTML = `<span class='batch-entity-empty'>${esc(error.message)}</span>`;
            batchEntityDetails.classList.remove("muted");
        }
    } finally {
        setButtonLoading(batchRunBtn, "Running...", false);
    }
}

async function runTranslateOnly() {
    const text = multiSourceText.value.trim();
    if (!text) {
        multiStatus.textContent = "Please enter source text first.";
        return;
    }
    setButtonLoading(translateBtn, "Translating...", true);
    multiStatus.textContent = "Translating text...";
    try {
        const response = await fetch("/api/multilang/translate", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ text, language: multiLanguageSelect.value }),
        });
        const data = await response.json();
        if (!response.ok) throw new Error(data.error || "Translation failed");
        multiTranslatedOutput.innerHTML = esc(data.translated_text || "").replace(/\n/g, "<br>");
        multiTranslatedOutput.classList.remove("muted");
        multiStatus.textContent = data.status || `Translation complete (${esc(multiLanguageSelect.value)}).`;
        latestTranslatedText = data.translated_text || "";
    } catch (error) {
        multiStatus.textContent = esc(error.message);
    } finally {
        setButtonLoading(translateBtn, "Translating...", false);
    }
}

async function runMultiAnalyze() {
    const text = multiSourceText.value.trim();
    if (!text) {
        multiStatus.textContent = "Please enter source text first.";
        return;
    }
    setButtonLoading(multiAnalyzeBtn, "Analyzing...", true);
    multiStatus.textContent = "Running cross-language analysis...";
    try {
        const response = await fetch("/api/multilang/analyze", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                source_text: text,
                translated_text: latestTranslatedText || "",
                domain: multiDomainSelect.value,
                language: multiLanguageSelect.value,
            }),
        });
        const data = await response.json();
        if (!response.ok) throw new Error(data.error || "Cross-language analysis failed");

        const result = data.result || {};
        multiStatus.textContent = data.status || "Analysis completed.";
        multiTranslatedOutput.innerHTML = esc(data.display_text || "").replace(/\n/g, "<br>");
        multiTranslatedOutput.classList.remove("muted");
        multiEntityChips.innerHTML = data.badges_html || "<span class='chip'>No entities detected</span>";
        const entities = result.entities || [];
        if (multiClassificationOutput) {
            multiClassificationOutput.innerHTML = `
                <span class="chip">Domain: ${esc((result.domain || "unknown").toUpperCase())}</span>
                <span class="chip">Entities: ${entities.length}</span>
                <span class="chip">Language: ${esc(multiLanguageSelect.value)}</span>
            `;
        }
        if (multiInsightsOutput) {
            multiInsightsOutput.innerHTML = `
                <div class="insight-item">
                    <p class="insight-title">Total Entities</p>
                    <p class="insight-value">${entities.length}</p>
                </div>
                <div class="insight-item">
                    <p class="insight-title">Detected Domain</p>
                    <p class="insight-value">${esc((result.domain || "--").toUpperCase())}</p>
                </div>
                <div class="insight-item">
                    <p class="insight-title">Selected Language</p>
                    <p class="insight-value">${esc(multiLanguageSelect.value)}</p>
                </div>
                <div class="insight-item">
                    <p class="insight-title">Processing Time</p>
                    <p class="insight-value">${esc(result.processing_time_seconds ?? "--")}s</p>
                </div>
            `;
        }
        if (multiAiInsight) {
            multiAiInsight.innerHTML = data.insight_html || "<span class='muted'>AI insight unavailable.</span>";
            multiAiInsight.classList.remove("muted");
        }
        latestMulti = {
            source_text: text,
            translated_text: data.display_text,
            analysis_text: result.text,
            domain: result.domain,
            target_language: multiLanguageSelect.value,
            entities: result.entities || [],
            report: data.report || null,
            generatedAt: new Date().toISOString(),
        };
    } catch (error) {
        multiStatus.textContent = esc(error.message);
    } finally {
        setButtonLoading(multiAnalyzeBtn, "Analyzing...", false);
    }
}

function exportJSON() {
    if (!latestAnalysis) return;
    const blob = new Blob([JSON.stringify(latestAnalysis, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "lexscan-analysis.json";
    a.click();
    URL.revokeObjectURL(url);
}

function toggleJsonPanel() {
    if (!jsonPanel) return;
    const next = jsonPanel.style.display === "none" ? "block" : "none";
    jsonPanel.style.display = next;
    if (next === "block") {
        const value = latestAnalysis ? JSON.stringify(latestAnalysis, null, 2) : "{}";
        if (jsonPreview) jsonPreview.textContent = value;
    }
}

async function copyJsonPreview() {
    if (!latestAnalysis) return;
    const value = JSON.stringify(latestAnalysis, null, 2);
    try {
        await navigator.clipboard.writeText(value);
    } catch (_e) {
        // ignore
    }
}

async function exportPDF() {
    if (!latestAnalysis) return;
    setButtonLoading(pdfBtn, "Preparing PDF...", true);
    try {
        if (latestReport?.id) {
            window.open(`/api/reports/${encodeURIComponent(latestReport.id)}`, "_blank");
        } else {
            const response = await fetch("/api/document/report/pdf", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ text: latestAnalysis.text, domain: domainSelect.value, language: languageSelect.value }),
            });
            if (!response.ok) throw new Error("PDF generation failed");
            const blob = await response.blob();
            const url = URL.createObjectURL(blob);
            const a = document.createElement("a");
            a.href = url;
            a.download = "lexscan-report.pdf";
            a.click();
            URL.revokeObjectURL(url);
        }
    } finally {
        setButtonLoading(pdfBtn, "Preparing PDF...", false);
    }
}

function exportMultiJSON() {
    if (!latestMulti) return;
    const blob = new Blob([JSON.stringify(latestMulti, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "lexscan-multilang.json";
    a.click();
    URL.revokeObjectURL(url);
}

async function exportMultiPDF() {
    const text = multiSourceText.value.trim();
    if (!text) return;
    setButtonLoading(multiPdfBtn, "Preparing PDF...", true);
    try {
        if (latestMulti?.report?.id) {
            window.open(`/api/reports/${encodeURIComponent(latestMulti.report.id)}`, "_blank");
            return;
        }
        const response = await fetch("/api/multilang/report/pdf", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                source_text: text,
                translated_text: latestTranslatedText || "",
                domain: multiDomainSelect.value,
                language: multiLanguageSelect.value,
            }),
        });
        if (!response.ok) throw new Error("PDF generation failed");
        const blob = await response.blob();
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = "lexscan-multilang-report.pdf";
        a.click();
        URL.revokeObjectURL(url);
    } finally {
        setButtonLoading(multiPdfBtn, "Preparing PDF...", false);
    }
}

bindUploadEvents();
bindNavigation();
loadLanguages();
refreshWorkspaceDocuments();
setActiveTab("tab-document");

analyzeBtn.addEventListener("click", runDocumentAnalysis);
workspaceAnalyzeBtn?.addEventListener("click", runWorkspaceAnalysis);
workspaceQuestionBtn?.addEventListener("click", runWorkspaceQuestion);
workspaceCompareBtn?.addEventListener("click", runWorkspaceCompare);
workspaceSearchBtn?.addEventListener("click", runWorkspaceSearch);
workspaceUseCurrentBtn?.addEventListener("click", () => {
    workspaceText.value = textInput.value || assistantContext.value || "";
    if (!workspaceTitle.value) workspaceTitle.value = "Imported from Document Analysis";
    if (!workspaceCollection.value) workspaceCollection.value = "Imported Workspace";
});
compareTabRunBtn?.addEventListener("click", runCompareTab);
compareTabUseWorkspaceBtn?.addEventListener("click", () => {
    compareTabTextA.value = workspaceText.value || textInput.value || "";
    compareTabTextB.value = multiSourceText.value || "";
});
assistantAskBtn.addEventListener("click", runAssistant);
batchRunBtn.addEventListener("click", runBatch);
translateBtn.addEventListener("click", runTranslateOnly);
multiAnalyzeBtn.addEventListener("click", runMultiAnalyze);
// JSON button: open/close dropdown panel (no PDF download).
jsonBtn.addEventListener("click", (e) => {
    e.preventDefault();
    toggleJsonPanel();
});
pdfBtn.addEventListener("click", exportPDF);
multiJsonBtn.addEventListener("click", exportMultiJSON);
multiPdfBtn.addEventListener("click", exportMultiPDF);

if (jsonDownloadBtn) {
    jsonDownloadBtn.addEventListener("click", (e) => {
        e.preventDefault();
        exportJSON();
    });
}
if (jsonCopyBtn) {
    jsonCopyBtn.addEventListener("click", (e) => {
        e.preventDefault();
        copyJsonPreview();
    });
}
if (reportLinkBtn) {
    reportLinkBtn.addEventListener("click", (e) => {
        e.preventDefault();
        exportPDF();
    });
}
