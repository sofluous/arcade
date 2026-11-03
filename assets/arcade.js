"use strict";
// One catalog for the bezel keys, transport controls, and dedicated links.
const games = [
  { title: "Jellyfish", path: "Jellyfish", description: "A small world, gently drifting." },
  { title: "Ripples on Water", path: "ripplesonwater", description: "Quiet water. One small disturbance." },
  { title: "Fireworks", path: "fireworks", description: "A little celebration in the night." },
  { title: "Picovarium", path: "picovarium", description: "Life unfolds in a pocket ecosystem." },
  { title: "CtrlFrogZ", path: "CtrlFrogZ", description: "A tiny frog with places to go." },
  { title: "Conbini", path: "conbini", description: "Familiar signs. Familiar little melodies." },
  { title: "Echoes", path: "echoes", description: "Make a sound. Find your way." },
  { title: "Samurai", path: "samurai", description: "Read the guard. Commit to the strike." },
  { title: "SWAT", path: "swat", description: "Small pests. Increasingly large problems." }
];
const port = document.getElementById("display-port");
const status = document.getElementById("screen-status");
const deck = document.getElementById("rolodex");
const symbols = ["\u25ce", "\u224b", "\u2733", "\u25a7", "\u25d2", "\u25a4", "\u25cc", "\u2571", "\u271b"];
const accents = Array(games.length).fill("#f45117");
let selected = 0; // Browsing does not interrupt the loaded game.
let loaded = 0;
let loadingTimer;

const rotor = document.getElementById("cartridge-card");
const number = index => String(index + 1).padStart(2, "0");
const url = game => `pico8/${game.path}/`;
function markLoaded(frame) {
  frame.addEventListener("load", () => {
    if (frame !== document.getElementById("game-frame")) return;
    clearTimeout(loadingTimer);
    status.textContent = `${games[loaded].title} loaded - press play on screen`;
  });
}
function updateCartridge() {
  const game = games[selected];
  document.getElementById("game-number").textContent = number(selected);
  document.getElementById("game-title").textContent = game.title;
  document.getElementById("game-description").textContent = game.description;
  rotor.querySelectorAll(".tape-cartridge").forEach((cartridge, i) => {
    let offset = (i - selected + games.length) % games.length;
    // Cyclic order: selected module above all eight stored cartridges.
    const active = offset === 0;
    cartridge.style.setProperty("--offset", offset);
    cartridge.style.setProperty("--stack-y", `${offset === 0 ? 0 : 273 + (offset - 1) * Math.max(28, (deck.clientHeight - 321) / 7)}px`);
    cartridge.style.zIndex = String(active ? 20 : 10 - Math.abs(offset));
    cartridge.setAttribute("aria-current", String(active));
    cartridge.querySelector(".tape-spine").setAttribute("aria-pressed", String(active));
    cartridge.classList.toggle("is-front", active);
    cartridge.classList.toggle("is-above", offset < 0);
    cartridge.classList.toggle("is-below", offset > 0);
    cartridge.tabIndex = -1;
  });
  rotor.querySelector(".is-front").append(document.getElementById("cart-controls"));
  document.getElementById("browse-position").textContent = `${number(selected)} / ${number(games.length - 1)}`;
  document.getElementById("cartridge-state").textContent = selected === loaded ? "IN THE CONSOLE" : "READY TO LOAD";
  document.getElementById("load-game").textContent = selected === loaded ? "RESTART CARTRIDGE" : "LOAD CARTRIDGE";
}
function browseCartridge(index) {
  const next = (index + games.length) % games.length;
  if (next === selected) return;
  selected = next;
  updateCartridge();
}
function loadCartridge() {
  loaded = selected;
  const game = games[loaded];
  clearTimeout(loadingTimer);
  document.getElementById("open-game").href = url(game);
  document.getElementById("loaded-title").textContent = `${game.title.toUpperCase()} / LOADED`;
  status.textContent = `Loading ${game.title}...`;
  const frame = document.createElement("iframe");
  frame.id = "game-frame";
  frame.title = `${game.title} game player`;
  frame.allow = "autoplay; fullscreen; gamepad";
  frame.allowFullscreen = true;
  markLoaded(frame);
  frame.src = url(game);
  port.replaceChildren(frame);
  updateCartridge();
  loadingTimer = setTimeout(() => { status.textContent = "Still loading? Reset or try the dedicated player."; }, 15000);
}
// One full tape sits forward; other games remain visible as thick stacked spines.
for (const [i, game] of games.entries()) {
  const cartridge = document.createElement("article");
  cartridge.setAttribute("role", "group");
  cartridge.className = "tape-cartridge";
  cartridge.setAttribute("aria-label", `Browse ${game.title}`);
  cartridge.style.setProperty("--cartridge-accent", accents[i]);
  const spine = document.createElement("button");
  spine.type = "button";
  spine.setAttribute("aria-label", `Browse ${game.title}`);
  spine.className = "tape-spine";
  const badge = document.createElement("span");
  badge.textContent = number(i);
  const spineTitle = document.createElement("strong");
  spineTitle.textContent = game.title;
  spine.append(badge, spineTitle);
  const face = document.createElement("span");
  face.className = "tape-face";
  face.setAttribute("aria-hidden", "true");
  const label = document.createElement("span");
  label.className = "tape-label";
  const title = document.createElement("strong");
  title.textContent = game.title;
  const format = document.createElement("small");
  format.textContent = `SOFLUOUS / ${number(i)} / PICO-8`;
  label.append(title, format);
  const window = document.createElement("span");
  window.className = "tape-window";
  window.innerHTML = '<i class="memory-grid"></i><span class="data-port">128<span>MEMORY / PICO-8</span></span><i class="signal-strip"></i>';
  const foot = document.createElement("span");
  foot.className = "tape-foot";
  foot.textContent = "MEMORY CARTRIDGE";
  face.append(label, window, foot);
  const screws = document.createElement("span");
  screws.className = "tape-screws";
  screws.setAttribute("aria-hidden", "true");
  cartridge.append(spine, face, screws);
  spine.addEventListener("click", () => browseCartridge(i));
  rotor.append(cartridge);
}

document.getElementById("game-count").textContent = number(games.length - 1);
document.getElementById("previous-game").addEventListener("click", () => browseCartridge(selected - 1));
document.getElementById("next-game").addEventListener("click", () => browseCartridge(selected + 1));
document.getElementById("load-game").addEventListener("click", loadCartridge);
document.getElementById("restart-game").addEventListener("click", () => {
  const browsing = selected;
  selected = loaded;
  loadCartridge();
  selected = browsing;
  updateCartridge();
});
deck.addEventListener("keydown", event => {
  if (event.target !== deck) return;
  if (["ArrowUp", "ArrowDown", "ArrowLeft", "ArrowRight"].includes(event.key)) {
    event.preventDefault();
    browseCartridge(selected + (event.key === "ArrowRight" || event.key === "ArrowDown" ? 1 : -1));
  } else if (event.key === "Enter" || event.key === " ") {
    event.preventDefault();
    loadCartridge();
  }
});
updateCartridge();
markLoaded(document.getElementById("game-frame"));

let pointerStart = null;
let suppressCartridgeClick = 0;
deck.style.touchAction = "none";
deck.addEventListener("pointerdown", event => {
  if (!event.isPrimary || event.button !== 0 || event.target.closest(".cart-console")) return;
  pointerStart = { id: event.pointerId, x: event.clientX, y: event.clientY };

});
window.addEventListener("pointerup", event => {
  if (!pointerStart || event.pointerId !== pointerStart.id) return;
  const dx = event.clientX - pointerStart.x;
  const dy = event.clientY - pointerStart.y;
  pointerStart = null;
  if (Math.abs(dy) > 30 && Math.abs(dy) > Math.abs(dx)) {
    suppressCartridgeClick = performance.now() + 350;
    browseCartridge(selected + (dy < 0 ? 1 : -1));
  }
});
deck.addEventListener("pointercancel", () => { pointerStart = null; });
deck.addEventListener("click", event => {
  if (event.isTrusted && performance.now() < suppressCartridgeClick) { event.preventDefault(); event.stopImmediatePropagation(); }
}, true);

// Resize the complete console + carousel, rather than clipping either half.
const station = document.querySelector(".arcade-station");
let fitRequest = 0;
function fitViewport() {
  fitRequest = 0;
  const viewport = window.visualViewport;
  const width = viewport ? viewport.width : window.innerWidth;
  const height = viewport ? viewport.height : window.innerHeight;
  updateCartridge();
  // Extra margin protects projecting base edges, focus outlines and hardware depth.
  const scale = Math.max(0.05, Math.min(1,
    (width - 32) / (station.offsetWidth + 20),
    (height - 36) / (station.offsetHeight + 20)));
  station.style.setProperty("--viewport-fit", String(scale));
}
function requestViewportFit() {
  if (!fitRequest) fitRequest = requestAnimationFrame(fitViewport);
}
new ResizeObserver(requestViewportFit).observe(station);
window.addEventListener("resize", requestViewportFit);
window.visualViewport?.addEventListener("resize", requestViewportFit);
fitViewport();

// Wheel input advances one physical slot; a brief detent prevents trackpad runaway.
let wheelReady = 0;
deck.addEventListener("wheel", event => {
  event.preventDefault();
  if (Math.abs(event.deltaY) < 8 || performance.now() < wheelReady) return;
  wheelReady = performance.now() + 220;
  browseCartridge(selected + (event.deltaY > 0 ? 1 : -1));
}, {passive:false});

const cartridgeMocks = ["module", "edge", "core"];
function setCartridgeMock(name) {
  if (!cartridgeMocks.includes(name)) name = "module";
  document.body.dataset.cartridge = name;
  document.querySelectorAll("[data-cart-choice]").forEach(button => button.setAttribute("aria-pressed", String(button.dataset.cartChoice === name)));
  const address = new URL(location.href);
  address.searchParams.set("cart", name);
  history.replaceState(null, "", address);
  requestViewportFit();
}
document.querySelectorAll("[data-cart-choice]").forEach(button => button.addEventListener("click", () => setCartridgeMock(button.dataset.cartChoice)));
setCartridgeMock(new URL(location.href).searchParams.get("cart") || "module");
