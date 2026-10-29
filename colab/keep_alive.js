/* Chạy trong Console của chính tab Colab. Không chạy trong ô Python. */
(() => {
  "use strict";
  if (location.hostname !== "colab.research.google.com") {
    throw new Error("Chỉ chạy script trong tab Google Colab.");
  }
  window.colabKeepAlive?.stop();
  const MIN_MS = 90_000;
  const MAX_MS = 150_000;
  let timer = null;
  const state = { running: true, pulses: 0, lastPulse: null, nextPulse: null };

  function getControl() {
    const host = document.querySelector("colab-connect-button");
    if (!host) return null;
    const root = host.shadowRoot || host;
    const toolbar = root.querySelector("colab-toolbar-button#connect");
    const textButton = toolbar?.shadowRoot?.querySelector("md-text-button#button");
    const button = textButton?.shadowRoot?.querySelector("button#button") || root.querySelector("button");
    if (!button || button.disabled || button.getAttribute("aria-disabled") === "true") return null;
    const description = [textButton?.textContent, host.innerText, host.textContent, host.getAttribute("aria-label"),
      button.innerText, button.textContent, button.getAttribute("aria-label"), button.getAttribute("title")]
      .filter(Boolean).join(" ");
    // Không bấm Connect/Reconnect nếu runtime đã ngắt; chỉ chạm nút tài nguyên đang kết nối.
    return /\bRAM\b|connected to|đã kết nối|compute resources/i.test(description) ? button : null;
  }

  function pulse() {
    if (!state.running) return false;
    const button = getControl();
    if (!button) {
      console.warn("[Colab keep-alive] Không thấy nút tài nguyên đang kết nối; bỏ lượt này.");
      return false;
    }
    button.click();
    state.pulses++;
    state.lastPulse = new Date().toISOString();
    console.log("[Colab keep-alive] pulse", state.pulses, state.lastPulse);
    return true;
  }

  function schedule() {
    if (!state.running) return;
    const random = new Uint32Array(1);
    crypto.getRandomValues(random);
    const delay = MIN_MS + Math.floor((random[0] / 4294967296) * (MAX_MS - MIN_MS + 1));
    state.nextPulse = new Date(Date.now() + delay).toISOString();
    timer = setTimeout(() => {
      try { pulse(); } catch (error) { console.warn("[Colab keep-alive]", error); }
      schedule();
    }, delay);
  }

  window.colabKeepAlive = {
    status: () => ({ ...state }),
    pulse,
    stop: () => {
      state.running = false;
      state.nextPulse = null;
      clearTimeout(timer);
      console.log("[Colab keep-alive] Đã dừng.");
    }
  };
  schedule();
  console.log("[Colab keep-alive] Đã bật; nhịp ngẫu nhiên 90–150 giây.", state.nextPulse);
  console.log("Dừng: colabKeepAlive.stop() | Trạng thái: colabKeepAlive.status()");
})();
