const API_ENDPOINT = "http://127.0.0.1:8000/predict";

document.addEventListener("DOMContentLoaded", () => {
  const urlInput = document.getElementById("url-input");
  const scanBtn = document.getElementById("scan-btn");
  const scanTabBtn = document.getElementById("scan-tab-btn");
  const container = document.getElementById("verdict-container");
  const verdictText = document.getElementById("verdict-text");
  const scoreText = document.getElementById("score-text");
  const reasonsList = document.getElementById("reasons-list");
  const latencyText = document.getElementById("latency-text");
  const engineStatus = document.getElementById("engine-status");

  // Check backend health
  fetch("http://127.0.0.1:8000/health")
    .then(r => r.json())
    .then(d => {
      engineStatus.textContent = d.active_model ? "Engine: Ready (Region-Aware)" : "Engine: Online";
    })
    .catch(() => {
      engineStatus.textContent = "Engine: Offline";
      engineStatus.style.color = "#ef4444";
    });

  // Scan current tab
  scanTabBtn.addEventListener("click", () => {
    chrome.tabs.query({ active: true, currentWindow: true }, tabs => {
      if (tabs && tabs[0] && tabs[0].url) {
        urlInput.value = tabs[0].url;
        analyze(tabs[0].url);
      }
    });
  });

  scanBtn.addEventListener("click", () => {
    if (urlInput.value.trim()) {
      analyze(urlInput.value.trim());
    }
  });

  function analyze(targetUrl) {
    scanBtn.disabled = true;
    scanBtn.textContent = "...";

    fetch(API_ENDPOINT, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ url: targetUrl, include_regional: true })
    })
      .then(res => {
        if (!res.ok) throw new Error("API response error");
        return res.json();
      })
      .then(data => {
        container.style.display = "block";
        container.className = data.is_phishing ? "verdict-card phish" : "verdict-card legit";

        verdictText.textContent = data.is_phishing ? "⚠️ PHISHING DETECTED" : "✓ VERIFIED SAFE";
        scoreText.textContent = `Risk: ${(data.risk_score * 100).toFixed(1)}%`;
        latencyText.textContent = `⚡ ${data.latency_ms} ms`;

        reasonsList.innerHTML = "";
        if (data.reasons && data.reasons.length > 0) {
          data.reasons.forEach(r => {
            const li = document.createElement("li");
            li.textContent = r;
            reasonsList.appendChild(li);
          });
        } else {
          const li = document.createElement("li");
          li.textContent = "No anomalous indicators detected.";
          reasonsList.appendChild(li);
        }
      })
      .catch(err => {
        container.style.display = "block";
        container.className = "verdict-card phish";
        verdictText.textContent = "Scan Error";
        scoreText.textContent = "--";
        reasonsList.innerHTML = `<li>Could not communicate with local detection engine (127.0.0.1:8000).</li>`;
      })
      .finally(() => {
        scanBtn.disabled = false;
        scanBtn.textContent = "Scan";
      });
  }
});
