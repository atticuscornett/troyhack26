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
    // CALL PYTHON
    const importedFile = await eel.import_pdf()();

    if (!importedFile) {
      importMessage.textContent = "No file selected.";
      return;
    }

    // ADD FILE
    files.push(importedFile);
    renderFileList();
    selectFile(importedFile.id);

    importMessage.textContent = "Import complete.";
  } catch (error) {
    importMessage.textContent = "Eel import service is not available yet.";
  } finally {
    importButton.disabled = false;
  }
});
