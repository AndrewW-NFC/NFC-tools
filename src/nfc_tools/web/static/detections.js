// Click-to-play handler for the detections table.
document.addEventListener("click", (e) => {
  const btn = e.target.closest(".play");
  if (!btn) return;
  const src = btn.dataset.src;
  const audio = document.getElementById("player");
  if (!audio) return;
  audio.src = src;
  audio.play().catch(() => {});
});
