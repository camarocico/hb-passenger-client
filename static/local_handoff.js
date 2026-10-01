(() => {
  "use strict";

  const root = document.getElementById("local-handoff");
  const form = document.getElementById("handoff-form");
  const input = document.getElementById("input-file");
  const button = document.getElementById("run-button");
  const status = document.getElementById("handoff-status");
  const linkContainer = document.getElementById("review-link-container");
  const reviewLink = document.getElementById("review-link");
  const portalUrl = new URL(root.dataset.portalPrepareUrl);
  const portalOrigin = portalUrl.origin;
  const localOrigin = root.dataset.localOrigin;
  const maxInputBytes = 10 * 1024 * 1024;

  let portalWindow = null;
  let state = null;
  let pendingFile = null;
  let transferStarted = false;

  function makeState() {
    const randomBytes = new Uint8Array(24);
    crypto.getRandomValues(randomBytes);
    return Array.from(randomBytes, (value) => value.toString(16).padStart(2, "0"))
      .join("");
  }

  async function sendFileWhenReady() {
    if (!portalWindow || !pendingFile || !state || transferStarted) return;
    transferStarted = true;
    const bytes = await pendingFile.arrayBuffer();
    portalWindow.postMessage(
      {
        type: "hb-passenger:input",
        state,
        filename: pendingFile.name,
        bytes,
      },
      portalOrigin,
      [bytes],
    );
    status.textContent = "Input sent to the OOD page. Complete preparation there.";
  }

  window.addEventListener("message", (event) => {
    if (event.origin !== portalOrigin || event.source !== portalWindow) return;
    const message = event.data;
    if (!message || message.state !== state) return;

    if (message.type === "hb-passenger:ready") {
      sendFileWhenReady().catch(() => {
        status.textContent = "Could not read the selected input file.";
        button.disabled = false;
      });
      return;
    }

    if (message.type === "hb-passenger:prepared") {
      let review;
      try {
        review = new URL(message.reviewUrl);
      } catch (_error) {
        return;
      }
      if (
        review.origin !== portalOrigin ||
        !review.pathname.startsWith(portalUrl.pathname.replace(/prepare$/, "review/"))
      ) {
        return;
      }
      reviewLink.href = review.href;
      linkContainer.hidden = false;
      status.textContent = "Input is ready for review in OOD.";
    }
  });

  form.addEventListener("submit", (event) => {
    event.preventDefault();
    const file = input.files && input.files[0];
    if (!file || !file.name.toLowerCase().endsWith(".inp")) {
      status.textContent = "Select one file with the .inp extension.";
      return;
    }
    if (file.size > maxInputBytes) {
      status.textContent = "The input exceeds the 10 MiB limit.";
      return;
    }
    if (!window.isSecureContext) {
      status.textContent = "Open this page at its 127.0.0.1 address.";
      return;
    }

    state = makeState();
    pendingFile = file;
    transferStarted = false;
    linkContainer.hidden = true;
    button.disabled = true;
    status.textContent = "Opening the authenticated OOD preparation page…";
    portalUrl.search = "";
    portalUrl.hash = "";
    portalUrl.searchParams.set("handoff_state", state);
    portalWindow = window.open(portalUrl.href, "hb-passenger-ood");
    if (!portalWindow) {
      status.textContent = "Allow the OOD window, then press Run on Habrok again.";
      button.disabled = false;
      pendingFile = null;
      state = null;
    }
  });

  window.addEventListener("pagehide", () => {
    pendingFile = null;
  });
})();
