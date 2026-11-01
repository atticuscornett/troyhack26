// FILE LIST
const files = [];

let selectedFileId = null;

const pdfjsLibPromise = import("./vendor/pdfjs/pdf.min.mjs");
let pdfRenderId = 0;
const pageViewports = new Map();
let highlightFocusTimer = null;

function drawHighlights(file) {
  document.querySelectorAll('.highlight-layer').forEach(layer => {
    layer.replaceChildren();
    const viewport = pageViewports.get(Number(layer.dataset.page));
    if (!viewport) return;
    (file.issues || []).filter(issue => Number(issue.page) === Number(layer.dataset.page)).forEach(issue => {
      (issue.rectangles || []).forEach(rect => {
        // CONVERT VIEWPORT POINTS
        const [x1, y1] = viewport.convertToViewportPoint(rect[0], rect[1]);
        const [x2, y2] = viewport.convertToViewportPoint(rect[2], rect[3]);
        const highlight = document.createElement('div');
        highlight.className = 'pdf-highlight';
        highlight.dataset.issueId = issue.id;
        highlight.style.left = `${Math.min(x1, x2) / viewport.width * 100}%`;
        highlight.style.top = `${Math.min(y1, y2) / viewport.height * 100}%`;
        highlight.style.width = `${Math.abs(x2 - x1) / viewport.width * 100}%`;
        highlight.style.height = `${Math.abs(y2 - y1) / viewport.height * 100}%`;
        highlight.style.backgroundColor = CSS.supports('color', issue.color) ? issue.color : 'yellow';
        layer.appendChild(highlight);
      });
    });
  });
}

// RENDER PDF.JS DOCUMENT
async function renderPdfDocument(documentUrl, pdfContainer) {
  const renderId = ++pdfRenderId;
  const pdfjsLib = await pdfjsLibPromise;

  // PDF.JS WORKER
  pdfjsLib.GlobalWorkerOptions.workerSrc = new URL(
    "./vendor/pdfjs/pdf.worker.min.mjs",
    window.location.href
  ).href;

  // OPEN PDF
  const loadingTask = pdfjsLib.getDocument({ url: documentUrl });
  const pdfDocument = await loadingTask.promise;

  if (renderId !== pdfRenderId) {
    return;
  }

  pdfContainer.innerHTML = "";
  pageViewports.clear();

  // RENDER PDF PAGES
  for (let pageNumber = 1; pageNumber <= pdfDocument.numPages; pageNumber++) {
    const page = await pdfDocument.getPage(pageNumber);
    if (renderId !== pdfRenderId) return;
    const viewport = page.getViewport({ scale: 1.5 });
    const outputScale = window.devicePixelRatio || 1;
    const canvas = document.createElement("canvas");
    const wrapper = document.createElement("div");
    const layer = document.createElement("div");
    const context = canvas.getContext("2d", { alpha: false });

    canvas.className = "pdf-page";
    canvas.width = Math.floor(viewport.width * outputScale);
    canvas.height = Math.floor(viewport.height * outputScale);
    canvas.setAttribute("aria-label", `PDF page ${pageNumber}`);

    wrapper.className = "pdf-page-wrapper";
    wrapper.style.aspectRatio = `${viewport.width} / ${viewport.height}`;
    layer.className = "highlight-layer";
    layer.dataset.page = pageNumber;
    wrapper.append(canvas, layer);
    pdfContainer.appendChild(wrapper);
    pageViewports.set(pageNumber, viewport);
    const selected = files.find(file => file.id === selectedFileId);
    if (selected) drawHighlights(selected);

    await page.render({
      canvasContext: context,
      transform: outputScale === 1
        ? null
        : [outputScale, 0, 0, outputScale, 0, 0],
      viewport
    }).promise;

    if (renderId !== pdfRenderId) {
      return;
    }
  }
}

// DISPLAY SAFE TEXT
function escapeHtml(value) {
  return String(value).replace(/[&<>"']/g, character => {
    return {
      "&": "&amp;",
      "<": "&lt;",
      ">": "&gt;",
      "\"": "&quot;",
      "'": "&#039;"
    }[character];
  });
}

// SHOW FILE ISSUES
function renderHighlightDetails(file) {
  const details = document.getElementById("highlightDetails");
  const issues = (file.issues || [])
    .filter(issue => issue.location === "available")
    .sort((first, second) => {
      const pageDifference = Number(first.page) - Number(second.page);
      if (pageDifference) return pageDifference;

      const firstRectangle = first.rectangles?.[0] || [0, 0, 0, 0];
      const secondRectangle = second.rectangles?.[0] || [0, 0, 0, 0];
      const firstTop = Math.max(firstRectangle[1], firstRectangle[3]);
      const secondTop = Math.max(secondRectangle[1], secondRectangle[3]);
      return secondTop - firstTop;
    });

  if (!issues.length) {
    details.innerHTML = "<p>No located issues found.</p>";
    return;
  }

  details.innerHTML = issues.map(issue => {
    return `
      <article class="issue-item" data-issue-id="${escapeHtml(issue.id || "")}" data-location="${escapeHtml(issue.location || "unavailable")}">
        <button class="dismiss-issue" type="button" aria-label="Dismiss highlight" title="Dismiss highlight">&times;</button>
        <p><strong>Page ${escapeHtml(issue.page)}${issue.flag ? ` (${escapeHtml(issue.flag)})` : ""}</strong></p>
        <p>${escapeHtml(issue.explanation || issue.flag)}</p>
        <p>${escapeHtml(issue.text)}</p>
      </article>
    `;
  }).join("");
}

function updateReviewActions(file) {
  const canReview = file?.status === "processed";
  document.querySelectorAll("[data-review-status]").forEach(button => {
    button.disabled = !canReview;
  });
}

// FOCUS OR DISMISS FLAG HIGHLIGHT
document.getElementById("highlightDetails").addEventListener("click", event => {
  const dismissButton = event.target.closest(".dismiss-issue");
  if (dismissButton) {
    const issueCard = dismissButton.closest(".issue-item[data-issue-id]");
    const selectedFile = files.find(file => file.id === selectedFileId);
    if (!issueCard || !selectedFile?.path) return;

    const issueId = issueCard.dataset.issueId;
    selectedFile.issues = (selectedFile.issues || []).filter(issue => issue.id !== issueId);
    renderHighlightDetails(selectedFile);
    drawHighlights(selectedFile);

    eel.dismiss_issue(selectedFile.path, issueId)().catch(error => {
      console.error("Could not dismiss highlight.", error);
    });
    return;
  }

  const issueCard = event.target.closest(".issue-item[data-issue-id]");
  if (!issueCard || issueCard.dataset.location === "unavailable") return;

  const highlight = [...document.querySelectorAll(".pdf-highlight")].find(element => {
    return element.dataset.issueId === issueCard.dataset.issueId;
  });
  if (!highlight) return;

  document.querySelectorAll(".pdf-highlight").forEach(element => {
    element.style.outline = "";
    element.style.outlineOffset = "";
  });
  highlight.scrollIntoView({ behavior: "smooth", block: "center", inline: "nearest" });
  highlight.style.outline = "3px solid #1d4ed8";
  highlight.style.outlineOffset = "2px";

  window.clearTimeout(highlightFocusTimer);
  highlightFocusTimer = window.setTimeout(() => {
    highlight.style.outline = "";
    highlight.style.outlineOffset = "";
  }, 1800);
});

// BUTTON DISPLAY FOR FILES
function renderFileList() {
  // EMPTY LIST AREA
  const list = document.getElementById("fileList");

  // BUTTONS FOR TEMP ARRAY
  list.innerHTML = files.map(file => {
    return `
      <button class="file-item ${file.status}${file.id === selectedFileId ? " selected" : ""}" data-file-id="${file.id}">
        ${file.name}
        <span class="status ${file.status}">${file.status}</span>
      </button>
    `;
  }).join("");
}

renderFileList();

// UPDATE FILE STATUSES
async function refreshFileStatuses() {
  try {
    const importStatuses = await eel.get_import_statuses()();
    const jobStatuses = await eel.get_processing_statuses()();
    let listChanged = false;
    let selectedFileToLoad = null;

    importStatuses.forEach(importStatus => {
      const file = files.find(item => item.importId === importStatus.importId);
      if (!file) return;

      const canUpdateStatus = !file.reviewStatus && (importStatus.state !== "processing" || file.status !== "processed");
      const statusChanged = canUpdateStatus && file.status !== importStatus.state;
      const documentReady = !file.documentUrl && importStatus.documentUrl;

      if (canUpdateStatus) {
        file.status = importStatus.state;
      }
      if (importStatus.filePath) file.path = importStatus.filePath;
      if (importStatus.documentUrl) file.documentUrl = importStatus.documentUrl;
      if (importStatus.error) file.error = importStatus.error;

      if (statusChanged) listChanged = true;
      if (documentReady && file.id === selectedFileId) {
        selectedFileToLoad = file;
      }
    });

    jobStatuses.forEach(job => {
      const file = files.find(item => item.path === job.filePath);

      if (!file) {
        return;
      }

      // SAVE ISSUES FROM JOB DISPATCH
      file.issues = Array.isArray(job.issues) ? job.issues : [];
      const nextStatus = file.reviewStatus || job.processState;
      const statusChanged = file.status !== nextStatus;

      if (statusChanged) {
        file.status = nextStatus;
        listChanged = true;

        // MOVE COMPLETED FILE TO TOP
        if (job.processState === "processed" && nextStatus === "processed") {
          files.splice(files.indexOf(file), 1);
          files.unshift(file);
        }
      }

    });

    if (listChanged) {
      renderFileList();
    }
    if (selectedFileToLoad) {
      selectFile(selectedFileToLoad.id);
    }
    const selected = files.find(file => file.id === selectedFileId);
    if (selected) {
      renderHighlightDetails(selected);
      drawHighlights(selected);
      updateReviewActions(selected);
    }
  } catch (error) {
    console.error("Could not update file statuses.", error);
  }
}

// CHECK STATUS EVERY SECOND
setInterval(refreshFileStatuses, 1000);

// FILE SELECT
async function selectFile(fileId) {
  const selectedFile = files.find(file => file.id === fileId);
  selectedFileId = fileId;
  updateReviewActions(selectedFile);

  // SELECTED BUTTON
  document.querySelectorAll(".file-item").forEach(button => {
    button.classList.remove("selected");
  });

  document
    .querySelector(`[data-file-id="${fileId}"]`)
    .classList.add("selected");

  // UPDATE TITLE
  document.getElementById("docTitle").textContent = selectedFile.name;

  // PDF PANEL
  const pdfContainer = document.getElementById("pdfContainer");

  // NO LOCAL PDF URL
  if (!selectedFile.documentUrl) {
    const message = selectedFile.status === "error"
      ? selectedFile.error || "Could not convert DOCX."
      : selectedFile.status === "queued"
        ? "DOCX conversion is queued..."
        : "Converting DOCX...";
    pdfContainer.innerHTML = `
      <p><strong>${selectedFile.name}</strong> ${message}</p>
    `;
    return;
  }

  // LOADING MESSAGE
  pdfContainer.innerHTML = "<p>Loading PDF pages...</p>";

  try {
    // SHOW PDF.JS PAGES
    await renderPdfDocument(selectedFile.documentUrl, pdfContainer);
  } catch (error) {
    console.error(error);
    pdfContainer.innerHTML = "<p>Could not load PDF.</p>";
  }

  // SHOW FILE ISSUES
  renderHighlightDetails(selectedFile);
}

// ACCEPT OR REJECT THE REVIEWED FILE
document.getElementById("reviewActions").addEventListener("click", async event => {
  const button = event.target.closest("[data-review-status]");
  const selectedFile = files.find(file => file.id === selectedFileId);
  if (!button || !selectedFile?.path || selectedFile.status !== "processed") return;

  const reviewStatus = button.dataset.reviewStatus;
  selectedFile.reviewStatus = reviewStatus;
  selectedFile.status = reviewStatus;
  files.splice(files.indexOf(selectedFile), 1);
  files.push(selectedFile);
  renderFileList();
  updateReviewActions(selectedFile);

  try {
    const saved = await eel.set_review_status(selectedFile.path, reviewStatus)();
    if (!saved) throw new Error("Review status was not saved.");
  } catch (error) {
    console.error("Could not save review status.", error);
    selectedFile.reviewStatus = null;
    selectedFile.status = "processed";
    renderFileList();
    updateReviewActions(selectedFile);
  }
});

// FILE BUTTON CLICKS
document.getElementById("fileList").addEventListener("click", event => {
  const button = event.target.closest(".file-item");

  if (button) {
    selectFile(button.dataset.fileId);
  }
});

// IMPORT BUTTON
const importButton = document.getElementById("importButton");
const importMessage = document.getElementById("importMessage");

// IMPORT FILES
importButton.addEventListener("click", async () => {
  importMessage.textContent = "Choose files...";
  importButton.disabled = true;

  try {
    // GET DOCUMENT INFO FROM PYTHON
    const importedDocuments = await eel.import_pdfs()();

    // NO FILES
    if (!importedDocuments.length) {
      importMessage.textContent = "No files selected.";
      return;
    }

    // ADD FILES
    const importedFiles = importedDocuments.map(importedDocument => {
      const filePath = importedDocument.filePath;
      return {
        id: `report-${crypto.randomUUID()}`,
        name: importedDocument.displayName || filePath.split(/[\\/]/).pop(),
        status: importedDocument.state || "processing",
        path: filePath || null,
        documentUrl: importedDocument.documentUrl,
        importId: importedDocument.importId,
        issues: []
      };
    });

    files.push(...importedFiles);
    renderFileList();
    selectFile(importedFiles[0].id);

    importMessage.textContent = `${importedFiles.length} import${importedFiles.length === 1 ? "" : "s"} started.`;
  } catch (error) {
    console.error(error);
    importMessage.textContent = "Could not import files.";
  } finally {
    importButton.disabled = false;
  }
});
