// TTTEEEEMMMPPP FIIILLLEEESSS
//
// AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA
const files = [
  {
    id: "report-001",
    name: "Security Assessment.pdf",
    status: "processed"
  },
  {
    id: "report-002",
    name: "Historical Analysis.pdf",
    status: "waiting"
  },
  {
    id: "report-003",
    name: "Policy Memo.pdf",
    status: "processing"
  }
];

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

      if (!file || file.status === job.processState) {
        return;
      }

      file.status = job.processState;
      listChanged = true;

      // MOVE COMPLETED FILE TO TOP
      if (job.processState === "processed") {
        files.splice(files.indexOf(file), 1);
        files.unshift(file);
      }
    });

    if (listChanged) {
      renderFileList();
    }
  } catch (error) {
    console.error("Could not update file statuses.", error);
  }
}

// CHECK STATUS EVERY SECOND
setInterval(refreshFileStatuses, 1000);

// FILE SELECT
function selectFile(fileId) {
  const selectedFile = files.find(file => file.id === fileId);

  // SELECTED BUTTON
  document.querySelectorAll(".file-item").forEach(button => {
    button.classList.remove("selected");
  });

  document
    .querySelector(`[data-file-id="${fileId}"]`)
    .classList.add("selected");

  // UPDATE TITLE
  document.getElementById("docTitle").textContent = selectedFile.name;

  // PDF PLACEHOLDER
  const pdfContainer = document.getElementById("pdfContainer");

  if (selectedFile.status === "processed") {
    pdfContainer.innerHTML = `
      <p><strong>${selectedFile.name}</strong> is ready for review.</p>
      <p>PDF will display here later.</p>
    `;
  } else {
    pdfContainer.innerHTML = `
      <p><strong>${selectedFile.name}</strong> is not ready yet.</p>
      <p>Status: ${selectedFile.status}</p>
    `;
  }

  // HIGHLIGHT PLACEHOLDER
  document.getElementById("highlightDetails").innerHTML = `
    <p>Select a highlight to see its details.</p>
  `;
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
    // GET FILE PATH FROM PYTHON
    const filePath = await eel.import_pdf()();

    // NO FILE SELECTED
    if (!filePath) {
      importMessage.textContent = "No file selected.";
      return;
    }

    // ADD SELECTED FILE
    const importedFile = {
      id: `report-${crypto.randomUUID()}`,
      name: filePath.split(/[\\/]/).pop(),
      status: "processing",
      path: filePath
    };

    files.push(importedFile);
    renderFileList();
    selectFile(importedFile.id);

    // FILE PATH READY FOR OTHER PYTHON CODE
    console.log(filePath);
    importMessage.textContent = "Import started.";
  } catch (error) {
    console.error(error);
    importMessage.textContent = "Could not select a PDF.";
  } finally {
    importButton.disabled = false;
  }
});
