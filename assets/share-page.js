(() => {
  const list = document.getElementById("track-list");
  const player = document.getElementById("main-player");
  const nowTitle = document.getElementById("now-title");
  const nowDate = document.getElementById("now-date");
  const copyStatus = document.getElementById("copy-status");
  const slug = document.body.dataset.shareSlug || "";

  const escapeHtml = (value) => String(value).replace(/[&<>"']/g, (ch) => ({
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    "\"": "&quot;",
    "'": "&#39;"
  }[ch]));

  const displayTitle = (track) => {
    return (track.file || track.title || "Untitled").trim() || "Untitled";
  };

  const trackUrl = (track) => {
    if (track.url) return track.url;
    return `/${slug}/audio/${encodeURIComponent(track.file || "")}`;
  };

  const setNowPlaying = (track) => {
    nowTitle.textContent = displayTitle(track);
    nowDate.textContent = track.date_label || "";
    player.src = trackUrl(track);
  };

  const setStatus = (message) => {
    copyStatus.textContent = message;
    window.clearTimeout(setStatus.timer);
    setStatus.timer = window.setTimeout(() => {
      copyStatus.textContent = "";
    }, 2200);
  };

  const row = (track, idx) => {
    const safeTitle = escapeHtml(displayTitle(track));
    const safeDate = escapeHtml(track.date_label || "");
    const safeUrl = escapeHtml(trackUrl(track));
    const copyLabel = (track.file || "").toLowerCase().endsWith(".wav") ? "Copy WAV Link" : "Copy MP3 Link";
    return `
      <article class="work-row">
        <div class="work-meta">
          <button class="work-play" type="button" data-idx="${idx}">Play</button>
          <div>
            <p class="work-title">${safeTitle}</p>
            <p class="work-date">${safeDate}</p>
          </div>
        </div>
        <div class="work-actions">
          <a class="work-link" href="${safeUrl}" download>Download</a>
          <button class="work-link work-copy" type="button" data-url="${safeUrl}">${copyLabel}</button>
        </div>
      </article>
    `;
  };

  let tracks = [];
  let current = -1;

  const highlight = () => {
    Array.from(list.querySelectorAll(".work-row")).forEach((rowEl, idx) => {
      rowEl.classList.toggle("active", idx === current);
    });
  };

  const loadTrack = (idx, autoplay) => {
    if (idx < 0 || idx >= tracks.length) return;
    current = idx;
    setNowPlaying(tracks[idx]);
    highlight();
    if (autoplay) {
      player.play().catch(() => {});
    }
  };

  const copyLink = async (url) => {
    const absolute = new URL(url, window.location.origin).toString();
    try {
      await navigator.clipboard.writeText(absolute);
      setStatus("Link copied.");
    } catch (error) {
      setStatus("Could not copy link.");
    }
  };

  fetch("tracks.json?t=" + Date.now(), { cache: "no-store" })
    .then((res) => {
      if (!res.ok) throw new Error("HTTP " + res.status);
      return res.json();
    })
    .then((data) => {
      tracks = Array.isArray(data.tracks) ? data.tracks : [];
      if (!tracks.length) {
        list.innerHTML = '<p class="empty">No beats yet.</p>';
        return;
      }
      list.innerHTML = tracks.map((track, idx) => row(track, idx)).join("");
      list.addEventListener("click", (event) => {
        const playBtn = event.target.closest(".work-play");
        if (playBtn) {
          loadTrack(Number(playBtn.dataset.idx), true);
          return;
        }
        const copyBtn = event.target.closest(".work-copy");
        if (copyBtn) {
          copyLink(copyBtn.dataset.url);
        }
      });
      loadTrack(0, false);
    })
    .catch(() => {
      list.innerHTML = '<p class="empty">Could not load beats.</p>';
    });
})();
