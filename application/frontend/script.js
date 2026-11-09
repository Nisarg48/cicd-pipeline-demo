async function loadVersion() {
  const shaEl = document.getElementById("build-sha");
  const timeEl = document.getElementById("build-time");

  try {
    const response = await fetch("/version", {
      headers: { Accept: "application/json" },
    });

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }

    const data = await response.json();
    shaEl.textContent = data.sha || "unknown";
    timeEl.textContent = data.build_time || "unknown";
  } catch (error) {
    shaEl.textContent = "unknown";
    timeEl.textContent = "unknown";
    console.error("Failed to load version info:", error);
  }
}

loadVersion();
