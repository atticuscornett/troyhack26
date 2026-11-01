// FILE LIST
const files = [];

let selectedFileId = null;

const pdfjsLibPromise = import("./vendor/pdfjs/pdf.min.mjs");
let pdfRenderId = 0;
const pageViewports = new Map();

function drawHighlights(file) {
  document.querySelectorAll('.highlight-layer').forEach(layer => {
    layer.replaceChildren();
    const viewport = pageViewports.get(Number(layer.dataset.page));
    if (!viewport) return;
    (file.issues || []).filter(issue => Number(issue.page) === Number(layer.dataset.page)).forEach(issue => {
      (issue.rectangles || []).forEach(rect => {
        // PDF.js 6 exposes point conversion, not convertToViewportRectangle.
        // Transform the two opposing PDF corners, then normalize below so this
        // also works for rotated pages.
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
  const issues = file.issues || [];

  if (!issues.length) {
    details.innerHTML = "<p>No issues found yet.</p>";
    return;
  }

  details.innerHTML = issues.map(issue => {
    return `
      <article class="issue-item">
        <p><strong>Page ${escapeHtml(issue.page)}${issue.flag ? ` (${escapeHtml(issue.flag)})` : ""}</strong></p>
        <p>${escapeHtml(issue.explanation || issue.flag)}</p>
        <p>${escapeHtml(issue.text)}</p>
        ${issue.location === "unavailable" ? '<p>Location unavailable</p>' : ''}
      </article>
    `;
  }).join("");
}

// BUTTON DISPLAY FOR FILES
function renderFileList() {
  // EMPTY LIST AREA
  const list = document.getElementById("fileList");

  // BUTTONS FOR TEMP ARRAY
  list.innerHTML = files.map(file => {
    return `
      <button class="file-item" data-file-id="${file.id}">
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
    const jobStatuses = await eel.get_processing_statuses()();
    let listChanged = false;

    jobStatuses.forEach(job => {
      const file = files.find(item => item.path === job.filePath);

      if (!file) {
        return;
      }

      // SAVE ISSUES FROM JOB DISPATCH
      file.issues = Array.isArray(job.issues) ? job.issues : [];
      const statusChanged = file.status !== job.processState;

      if (statusChanged) {
        file.status = job.processState;
        listChanged = true;

        // MOVE COMPLETED FILE TO TOP
        if (statusChanged && job.processState === "processed") {
          files.splice(files.indexOf(file), 1);
          files.unshift(file);
        }
      }

    });

    if (listChanged) {
      renderFileList();
    }
    const selected = files.find(file => file.id === selectedFileId);
    if (selected) {
      renderHighlightDetails(selected);
      drawHighlights(selected);
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
    pdfContainer.innerHTML = `
      <p><strong>${selectedFile.name}</strong> has no local PDF URL.</p>
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

// IMPORT PDF
importButton.addEventListener("click", async () => {
  importMessage.textContent = "Choose a PDF...";
  importButton.disabled = true;

  try {
    // GET DOCUMENT INFO FROM PYTHON
    const importedDocument = await eel.import_pdf()();

    // NO FILE SELECTED
    if (!importedDocument) {
      importMessage.textContent = "No file selected.";
      return;
    }

    // DOCUMENT PATH
    const filePath = importedDocument.filePath;

    // ADD SELECTED FILE
    const importedFile = {
      id: `report-${crypto.randomUUID()}`,
      name: filePath.split(/[\\/]/).pop(),
      status: "processing",
      path: filePath,
      documentUrl: importedDocument.documentUrl,
      issues: []
    };

    files.push(importedFile);
    renderFileList();
    selectFile(importedFile.id);

    // DOCUMENT READY FOR PDF.JS
    console.log(filePath);
    importMessage.textContent = "Import started.";
  } catch (error) {
    console.error(error);
    importMessage.textContent = "Could not select a PDF.";
  } finally {
    importButton.disabled = false;
  }
});
