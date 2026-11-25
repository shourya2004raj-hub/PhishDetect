/**
 * Content Script for Real-Time In-Browser Link Scanning
 * Inspects anchor tags on hover and alerts users before navigating to phishing sites.
 */

const scannedLinks = new Set();

function inspectLink(anchorElement) {
  const url = anchorElement.href;
  if (!url || !url.startsWith("http") || scannedLinks.has(url)) {
    return;
  }
  scannedLinks.add(url);

  chrome.runtime.sendMessage({ action: "check_url", url: url }, response => {
    if (response && response.is_phishing) {
      flagSuspiciousLink(anchorElement, response);
    }
  });
}

function flagSuspiciousLink(anchorElement, detection) {
  if (anchorElement.dataset.phishBadged) return;
  anchorElement.dataset.phishBadged = "true";

  // Add red highlight
  anchorElement.style.borderBottom = "2px dashed #ef4444";
  anchorElement.style.color = "#ef4444";

  // Create indicator badge
  const badge = document.createElement("span");
  badge.textContent = ` ⚠️ [Phish Risk: ${(detection.risk_score * 100).toFixed(0)}%]`;
  badge.style.fontSize = "0.75em";
  badge.style.fontWeight = "bold";
  badge.style.color = "#dc2626";
  badge.style.backgroundColor = "#fee2e2";
  badge.style.padding = "2px 4px";
  badge.style.borderRadius = "4px";
  badge.style.marginLeft = "4px";
  badge.title = detection.reasons ? detection.reasons.join("\n") : "Potential phishing target";

  anchorElement.parentNode.insertBefore(badge, anchorElement.nextSibling);

  // Intercept click with security warning modal
  anchorElement.addEventListener("click", e => {
    e.preventDefault();
    showWarningModal(anchorElement.href, detection);
  });
}

function showWarningModal(targetUrl, detection) {
  const existing = document.getElementById("phishing-detector-modal");
  if (existing) existing.remove();

  const modal = document.createElement("div");
  modal.id = "phishing-detector-modal";
  modal.style.position = "fixed";
  modal.style.top = "0";
  modal.style.left = "0";
  modal.style.width = "100vw";
  modal.style.height = "100vh";
  modal.style.backgroundColor = "rgba(11, 15, 25, 0.85)";
  modal.style.backdropFilter = "blur(8px)";
  modal.style.zIndex = "9999999";
  modal.style.display = "flex";
  modal.style.alignItems = "center";
  modal.style.justifyContent = "center";
  modal.style.fontFamily = "system-ui, -apple-system, sans-serif";

  const reasonsHtml = detection.reasons && detection.reasons.length > 0
    ? detection.reasons.map(r => `<li style="margin-bottom: 6px;">${r}</li>`).join("")
    : "<li>Statistical pattern alignment with known credential harvesting portals.</li>";

  modal.innerHTML = `
    <div style="background: #1e293b; color: #f8fafc; border: 1px solid #ef4444; border-radius: 14px; max-width: 520px; width: 90%; padding: 24px; box-shadow: 0 20px 40px rgba(0,0,0,0.6);">
      <div style="display: flex; align-items: center; gap: 12px; margin-bottom: 16px;">
        <span style="font-size: 32px;">🛑</span>
        <div>
          <h2 style="margin: 0; font-size: 20px; color: #f87171;">Security Warning: Phishing Suspected</h2>
          <p style="margin: 4px 0 0; font-size: 13px; color: #94a3b8;">PhishDetect: AI-Driven Phishing URL Detection</p>
        </div>
      </div>
      <p style="font-size: 14px; word-break: break-all; background: #0f172a; padding: 10px; border-radius: 6px; border: 1px solid rgba(255,255,255,0.06); font-family: monospace;">
        ${targetUrl}
      </p>
      <div style="margin: 16px 0; font-size: 13px; color: #cbd5e1;">
        <p style="font-weight: 600; margin-bottom: 8px; color: #fca5a5;">Threat Signals Identified (Risk: ${(detection.risk_score * 100).toFixed(1)}%):</p>
        <ul style="padding-left: 20px; line-height: 1.4;">${reasonsHtml}</ul>
      </div>
      <div style="display: flex; justify-content: flex-end; gap: 10px; margin-top: 20px;">
        <button id="phish-abort-btn" style="padding: 10px 18px; background: #2563eb; color: #fff; border: none; border-radius: 8px; font-weight: 600; cursor: pointer;">
          Stay Safe (Recommended)
        </button>
        <button id="phish-proceed-btn" style="padding: 10px 14px; background: transparent; color: #94a3b8; border: 1px solid #475569; border-radius: 8px; font-size: 12px; cursor: pointer;">
          Proceed Anyway
        </button>
      </div>
    </div>
  `;

  document.body.appendChild(modal);

  document.getElementById("phish-abort-btn").onclick = () => modal.remove();
  document.getElementById("phish-proceed-btn").onclick = () => {
    modal.remove();
    window.location.href = targetUrl;
  };
}

// Hover listener on document
document.addEventListener("mouseover", e => {
  const anchor = e.target.closest("a");
  if (anchor && anchor.href) {
    inspectLink(anchor);
  }
}, { passive: true });
