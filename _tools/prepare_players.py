#!/usr/bin/env python3
"""Prepare supported PICO-8 HTML shells. Standard library only; no upload."""
import argparse
import hashlib
import os
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
START = '\t\t// Arcade desktop embed: fit one square plus a 40px control row.'
ANCHOR = '\t\t// skip if relevant state has not changed'
LEGACY_LINK = '<link rel="stylesheet" href="../player.css">'
BRIDGE = "// Install beside arcade's player.css and include in every prepared export shell.\n// Handshake binds replies to the embedding window without trusting arbitrary messages.\n(() => {\n  if (window.parent === window) return;\n  let parentOrigin = null;\n  let touched = false;\n  const report = () => {\n    if (parentOrigin) window.parent.postMessage({ type: 'portfolio:pico-input', version: 1, touch: touched }, parentOrigin);\n  };\n  window.addEventListener('message', event => {\n    if (event.source !== window.parent || !/^https?:\\/\\//.test(event.origin)) return;\n    if (event.data?.type !== 'portfolio:pico-connect' || event.data.version !== 1) return;\n    if (parentOrigin && parentOrigin !== event.origin) return;\n    parentOrigin = event.origin;\n    report();\n  });\n  window.addEventListener('touchstart', () => {\n    touched = true;\n    report();\n  }, { once: true, passive: true, capture: true });\n})();\n"
LINK = LEGACY_LINK + '\n<script>\n' + BRIDGE + '</script>'
PREVIOUS_LINK = LINK
# Kept inline so the preparer remains a single-file delivery to Arcade.
ADAPTIVE = r'''
var arcade_touch_mode = window.parent === window ? 'auto' : null;
var arcade_touch_key = '';
var arcade_touch_down = false;
var arcade_touch_blocked = false;
var arcade_touch_restore = null;
function arcadeTouchGeometry(w, h, mode) {
  var menu = 40;
  var wide = mode === 'wide' || (mode === 'auto' && w > h);
  var r = Math.max(1, Math.min(40, w / (wide ? 24 : 12), (h - menu) / (wide ? 9 : 16)));
  var size = Math.max(1, Math.floor(Math.min(wide ? w - 12 * r - 16 : w, h - menu - (wide ? 0 : 8 * r))));
  return {
    w: w, h: h, r: r, mode: wide ? 'wide' : 'stacked',
    game: { x: (w - size) / 2, y: Math.max(0, (h - menu - (wide ? 0 : 8 * r) - size) / 2), size: size },
    left: { x: 0, y: wide ? (h - menu - 6 * r) / 2 : h - 6 * r },
    right: { x: w - 6 * r, y: wide ? (h - menu - 8 * r) / 2 : h - 8 * r }
  };
}
function arcadeTouchEnabled() {
  return arcade_touch_mode && typeof p8_touch_detected !== 'undefined' && p8_touch_detected &&
    !(document.fullscreenElement || document.webkitFullscreenElement || document.mozFullScreenElement || document.msFullscreenElement);
}
function arcadeReleaseTouch() {
  if (typeof pico8_buttons !== 'undefined') pico8_buttons[0] = 0;
  if (typeof pico8_mouse !== 'undefined') pico8_mouse[2] = 0;
  arcade_touch_blocked = arcade_touch_down;
}
function arcadeUtilityMenu() {
  var desktop = document.getElementById('p8_menu_buttons');
  var touch = document.getElementById('p8_menu_buttons_touch');
  var play = document.getElementById('p8_playarea');
  if (!desktop || !touch || !play) return;
  var row = document.getElementById('arcade_utility_buttons');
  if (!row) {
    row = document.createElement('div'); row.id = 'arcade_utility_buttons';
    row.setAttribute('role', 'group'); row.setAttribute('aria-label', 'PICO-8 player controls');
    for (var id of ['p8b_controls', 'p8b_pause', 'p8b_sound', 'p8b_full']) row.appendChild(desktop.querySelector('#' + id));
    row.appendChild(touch.querySelector('#p8b_close'));
    play.appendChild(row);
    var labels = ['Controls', 'Pause', 'Sound', 'Fullscreen', 'Close game'];
    Array.from(row.children).forEach((button, index) => {
      button.setAttribute('role', 'button'); button.setAttribute('aria-label', labels[index]); button.tabIndex = 0;
      button.addEventListener('keydown', event => { if (event.key === 'Enter' || event.key === ' ') { event.preventDefault(); button.click(); } });
    });
  }
  var fullscreen = document.fullscreenElement || document.webkitFullscreenElement || document.mozFullScreenElement || document.msFullscreenElement;
  document.documentElement.classList.add('arcade-utility-ready');
  document.documentElement.classList.toggle('arcade-utility-touch', Boolean(p8_touch_detected));
  document.documentElement.classList.toggle('arcade-utility-running', Boolean(p8_is_running && !fullscreen));
}
function arcadePositionUtilityMenu() {
  var row = document.getElementById('arcade_utility_buttons');
  var canvas = document.getElementById('canvas');
  if (!row || !canvas || !p8_is_running) return;
  var screen = canvas.getBoundingClientRect();
  row.style.left = Math.max(0, screen.right - row.getBoundingClientRect().width) + 'px';
  row.style.top = screen.bottom + 'px';
}
function arcadeApplyTouchLayout() {
  arcadeUtilityMenu();
  var active = Boolean(arcadeTouchEnabled());
  document.documentElement.classList.toggle('arcade-adaptive', active);
  if (!active) {
    if (arcade_touch_key) { arcadeReleaseTouch(); arcade_touch_key = ''; }
    if (arcade_touch_restore) {
      for (var entry of arcade_touch_restore) {
        if (entry[1] === null) entry[0].removeAttribute('style'); else entry[0].setAttribute('style', entry[1]);
      }
      arcade_touch_restore = null;
    }
    arcadePositionUtilityMenu();
    return false;
  }
  var canvas = document.getElementById('canvas');
  var container = document.getElementById('p8_container');
  var play = document.getElementById('p8_playarea');
  if (!canvas || !container || !play) return false;
  if (!arcade_touch_restore) {
    var changed = [canvas, canvas.parentElement, ...['p8_frame_0', 'p8_frame', 'p8_container', 'p8_playarea', 'p8_start_button', 'p8_menu_buttons', 'p8_menu_buttons_touch', 'touch_controls_gfx', 'touch_controls_background', 'controls_left_panel', 'controls_right_panel'].map(id => document.getElementById(id))];
    arcade_touch_restore = changed.map(node => [node, node.getAttribute('style')]);
  }
  var g = arcadeTouchGeometry(innerWidth, innerHeight, arcade_touch_mode);
  var key = g.w + ':' + g.h + ':' + g.mode;
  if (key !== arcade_touch_key) { arcadeReleaseTouch(); arcade_touch_key = key; }
  document.documentElement.classList.remove('arcade-windowed');
  var frame = document.getElementById('p8_frame');
  var outer = document.getElementById('p8_frame_0');
  for (var node of [outer, frame, container, play]) {
    node.style.width = '100%'; node.style.height = '100%'; node.style.maxWidth = 'none'; node.style.maxHeight = 'none';
    node.style.margin = '0';
  }
  outer.style.height = innerHeight + 'px';
  frame.style.display = 'block';
  container.style.display = 'block';
  var start = document.getElementById('p8_start_button');
  if (!p8_is_running) {
    play.style.display = 'none'; start.style.display = 'flex'; start.style.height = '100%';
  } else {
    start.style.display = 'none'; play.style.display = 'block';
    canvas.parentElement.style.position = 'static';
    canvas.style.position = 'fixed'; canvas.style.left = g.game.x + 'px'; canvas.style.top = g.game.y + 'px';
    canvas.style.width = g.game.size + 'px'; canvas.style.height = g.game.size + 'px'; canvas.style.margin = '0';
    canvas.style.pointerEvents = 'none';
    document.getElementById('p8_menu_buttons').style.display = 'none';
    for (var id of ['touch_controls_gfx', 'touch_controls_background']) document.getElementById(id).style.display = 'block';
    var left = document.getElementById('controls_left_panel');
    var right = document.getElementById('controls_right_panel');
    for (var pair of [[left, g.left.x, g.left.y, 6], [right, g.right.x, g.right.y + g.r, 7]]) {
      pair[0].style.position = 'fixed'; pair[0].style.left = pair[1] + 'px'; pair[0].style.top = pair[2] + 'px';
      pair[0].style.width = (g.r * 6) + 'px'; pair[0].style.height = (g.r * pair[3]) + 'px';
      var source = p8_gfx_dat[pair[0].id];
      if (pair[0].getAttribute('src') !== source) pair[0].setAttribute('src', source);
    }
  }
  window.arcade_touch_geometry = g;
  arcadePositionUtilityMenu();
  return true;
}
function arcadeHandleTouch(e, step) {
  if (!arcadeTouchEnabled() || !p8_is_running) return false;
  var touches = e.touches || [];
  arcade_touch_down = touches.length > 0;
  pico8_buttons[0] = 0;
  if (typeof pico8_mouse !== 'undefined') pico8_mouse[2] = 0;
  if (arcade_touch_blocked) { if (!touches.length) arcade_touch_blocked = false; return true; }
  var g = arcadeTouchGeometry(innerWidth, innerHeight, arcade_touch_mode), r = g.r;
  for (var touch of touches) {
    var x = touch.clientX, y = touch.clientY, bits = 0;
    if (x >= g.left.x && x < g.left.x + 6*r && y >= g.left.y && y < g.left.y + 6*r) {
      var dx = x - g.left.x - 3*r, dy = y - g.left.y - 3*r;
      if (Math.abs(dx) > Math.abs(dy)*.6) { if (dx < -r/3) bits |= 1; if (dx > r/3) bits |= 2; }
      if (Math.abs(dy) > Math.abs(dx)*.6) { if (dy < -r/3) bits |= 4; if (dy > r/3) bits |= 8; }
    } else if (x >= g.right.x && x < g.right.x + 6*r && y >= g.right.y && y < g.right.y + 8*r) {
      var lx = x - g.right.x, ly = y - g.right.y;
      if (ly < 2*r) { if (lx > 3*r) bits |= 0x40; }
      else { if (8*r - ly > (6*r - lx)*.8) bits |= 0x10; if (6*r - lx > (8*r - ly)*.8) bits |= 0x20; }
    } else if (x >= g.game.x && x < g.game.x + g.game.size && y >= g.game.y && y < g.game.y + g.game.size && typeof pico8_mouse !== 'undefined') {
      pico8_mouse = [Math.floor((x-g.game.x)*128/g.game.size), Math.floor((y-g.game.y)*128/g.game.size), step < 2 ? 1 : 0];
    }
    pico8_buttons[0] |= bits;
    if (bits && e.cancelable) e.preventDefault();
  }
  return true;
}
(() => {
  for (var event of ['resize', 'blur', 'pagehide', 'fullscreenchange', 'webkitfullscreenchange']) window.addEventListener(event, arcadeReleaseTouch);
  document.addEventListener('visibilitychange', () => { if (document.hidden) arcadeReleaseTouch(); });
  window.addEventListener('touchcancel', () => { arcade_touch_down = false; arcadeReleaseTouch(); arcade_touch_blocked = false; });
  if (window.parent === window) return;
  let parentOrigin = null, touched = false;
  const report = () => {
    if (!parentOrigin) return;
    parent.postMessage({ type: 'portfolio:pico-input', version: 1, touch: touched }, parentOrigin);
    parent.postMessage({ type: 'portfolio:pico-capabilities', version: 2, adaptiveTouch: true }, parentOrigin);
  };
  window.addEventListener('message', event => {
    if (event.source !== parent || !/^https?:\/\//.test(event.origin)) return;
    if (parentOrigin && parentOrigin !== event.origin) return;
    if (event.data?.type === 'portfolio:pico-connect' && event.data.version === 1) { parentOrigin = event.origin; report(); }
    if (event.origin !== parentOrigin || event.data?.type !== 'portfolio:pico-layout' || event.data.version !== 2) return;
    if (!['stacked', 'wide'].includes(event.data.layout) || !Number.isSafeInteger(event.data.requestId)) return;
    arcade_touch_mode = event.data.layout;
    arcadeReleaseTouch();
    parent.postMessage({ type: 'portfolio:pico-layout-applied', version: 2, layout: arcade_touch_mode, requestId: event.data.requestId }, parentOrigin);
  });
  window.addEventListener('touchstart', () => { if (!touched) { touched = true; report(); } }, { passive: true, capture: true });
})();
'''
ADAPTIVE_STYLE = '''<style>
html.arcade-adaptive, .arcade-adaptive body { width:100%; height:100%; overflow:hidden; overscroll-behavior:none; }
.arcade-adaptive #p8_frame_0, .arcade-adaptive #p8_frame, .arcade-adaptive #p8_container, .arcade-adaptive #p8_playarea { max-width:none!important; max-height:none!important; }
.arcade-adaptive #canvas { max-width:none!important; max-height:none!important; }
.arcade-utility-ready #p8_menu_buttons_touch { display:none!important; }
#arcade_utility_buttons { display:none; position:fixed; width:148px; height:40px; box-sizing:border-box; padding:4px; gap:4px; align-items:center; flex-wrap:nowrap; z-index:20; }
.arcade-utility-touch #arcade_utility_buttons { width:184px; }
.arcade-utility-running #arcade_utility_buttons { display:flex; }
#arcade_utility_buttons .p8_menu_button { position:static!important; float:none!important; margin:0!important; padding:4px; width:32px; height:32px; box-sizing:border-box; flex:0 0 32px; cursor:pointer; }
.arcade-utility-ready:not(.arcade-utility-touch) #arcade_utility_buttons #p8b_close { display:none!important; }
#arcade_utility_buttons .p8_menu_button:focus-visible { outline:2px solid white; outline-offset:-2px; }
</style>'''
BRIDGE = ADAPTIVE
LINK = LEGACY_LINK + '\n' + ADAPTIVE_STYLE + '\n<script>\n' + BRIDGE + '</script>'
LAYOUT_ENTRY = '\tfunction p8_update_layout()\n\t{'
TOUCH_ENTRY = '\tfunction pico8_buttons_event(e, step)\n\t{'
LAYOUT_HOOK = '\n\t\tif (arcadeApplyTouchLayout()) { requestAnimationFrame(p8_update_layout); return; }'
TOUCH_HOOK = '\n\t\tif (arcadeHandleTouch(e, step)) return;'
BLOCK = '''\t\t// Arcade desktop embed: fit one square plus a 40px control row.
\t\t// Leave the export's touch and fullscreen layout in charge in those modes.
\t\tvar arcade_windowed = !is_fullscreen && !p8_touch_detected;
\t\tdocument.documentElement.classList.toggle("arcade-windowed", arcade_windowed);
\t\tif (arcade_windowed)
\t\t{
\t\t\tcsize = Math.max(1, Math.floor(Math.min(window.innerWidth, window.innerHeight - 40)));
\t\t\tmargin_left = 0;
\t\t\tmargin_top = 0;
\t\t\tp8_container.style.setProperty("--arcade-canvas-size", csize + "px");
\t\t}

'''
LEGACY_BLOCK = BLOCK
BLOCK = BLOCK.replace(
    'Math.min(window.innerWidth, window.innerHeight - 40)',
    'Math.min(Math.floor(p8_frame.getBoundingClientRect().width), Math.floor(p8_frame.getBoundingClientRect().height) - 40)')

REPLACEMENTS = {
    'canvas.style.width = csize;': 'canvas.style.width = csize + "px";',
    'canvas.style.height = csize;': 'canvas.style.height = csize + "px";',
    'p8_container.style.width = csize;': 'p8_container.style.width = csize + "px";',
    'p8_container.style.height = csize;': 'p8_container.style.height = (arcade_windowed ? csize + 40 : csize) + "px";',
}
# Exact known layout function fingerprints after removing managed edits.
# Unknown exporters must be inspected and tested before extending this set.
SUPPORTED_LAYOUTS = {'97cd517e4beef6df93593876758de25760f5f2c9e74861d49f5c549a36104d37'}
LAYOUT_PATTERN = re.compile(r'\tfunction p8_update_layout\(\)\n\t\{.*?\n\t\}', re.S)
TOUCH_PATTERN = re.compile(r'\tfunction pico8_buttons_event\(e, step\)\n\t\{.*?\n\t\}', re.S)
SUPPORTED_TOUCH = {'e4e518ff736ba0831af7a3308b4db6fe7e81cba34b7527feaa1f92183dca5107'}


def sha(data):
    return hashlib.sha256(data).hexdigest()


def original_shell(text):
    """Recognize stock or our exact managed integration; reject partial edits."""
    # Upgrade only the exact previously shipped adaptive bridge/style pair.
    previous = re.search(re.escape(LEGACY_LINK) + r'\n<style>.*?</style>\n<script>\n.*?</script>', text, re.S)
    if previous and sha(previous[0].encode()) == 'a2bf11695612f02d4c16dafdedd2c4110b83774f1b465c746a143b4b2aa748e3':
        text = text[:previous.start()] + LINK + text[previous.end():]
    adaptive = LINK in text
    if adaptive:
        if text.count(LAYOUT_HOOK) != 1 or text.count(TOUCH_HOOK) != 1:
            raise ValueError('partial adaptive integration')
        text = text.replace(LAYOUT_HOOK, '').replace(TOUCH_HOOK, '')
    elif LAYOUT_HOOK in text or TOUCH_HOOK in text:
        raise ValueError('partial adaptive integration')
    if PREVIOUS_LINK in text:
        text = text.replace(PREVIOUS_LINK, LINK)
    # Upgrade only the exact previous sizing integration.
    if LEGACY_BLOCK in text:
        text = text.replace(LEGACY_BLOCK, BLOCK)
    # Upgrade existing prepared shells before exact managed-edit validation.
    if LEGACY_LINK in text and 'portfolio:pico-connect' not in text:
        text = text.replace(LEGACY_LINK, LINK)
    managed = any(token in text for token in (START, LINK, 'arcade_windowed'))
    if managed:
        if text.count(BLOCK) != 1 or text.count(LINK + '\n') != 1:
            raise ValueError('partial or unfamiliar Arcade integration')
        text = text.replace(BLOCK, '').replace(LINK + '\n', '')
        for old, new in REPLACEMENTS.items():
            if text.count(new) != 1:
                raise ValueError('unfamiliar managed dimension assignment')
            text = text.replace(new, old)
        if 'arcade_windowed' in text or '../player.css' in text:
            raise ValueError('unexpected remaining Arcade customization')
    return text


def prepare(raw):
    text = raw.decode('utf-8').replace('\r\n', '\n')
    original = original_shell(text)
    layout = LAYOUT_PATTERN.findall(original)
    if len(layout) != 1 or sha(layout[0].encode()) not in SUPPORTED_LAYOUTS:
        raise ValueError('unsupported layout function; no automatic patch attempted')
    touch = TOUCH_PATTERN.findall(original)
    if len(touch) != 1 or sha(touch[0].encode()) not in SUPPORTED_TOUCH:
        raise ValueError('unsupported touch handler; no automatic patch attempted')
    for element in ('p8_frame_0', 'p8_frame', 'p8_container', 'p8_playarea', 'canvas', 'p8_menu_buttons', 'p8_menu_buttons_touch', 'p8_start_button', 'controls_left_panel', 'controls_right_panel', 'touch_controls_gfx', 'touch_controls_background', 'p8b_controls', 'p8b_pause', 'p8b_close'):
        if len(re.findall(r'\bid=["\x27]' + element + r'["\x27]', original)) != 1:
            raise ValueError('missing or duplicate player element: ' + element)
    if original.count('</head>') != 1 or original.count(ANCHOR) != 1:
        raise ValueError('unrecognized HTML integration points')
    result = original.replace(ANCHOR, BLOCK + ANCHOR)
    if original.count(TOUCH_ENTRY) != 1:
        raise ValueError('unsupported touch handler; no automatic patch attempted')
    result = result.replace(LAYOUT_ENTRY, LAYOUT_ENTRY + LAYOUT_HOOK).replace(TOUCH_ENTRY, TOUCH_ENTRY + TOUCH_HOOK)
    for old, new in REPLACEMENTS.items():
        if result.count(old) != 1:
            raise ValueError('unrecognized dimension assignment: ' + old)
        result = result.replace(old, new)
    result = result.replace('</head>', LINK + '\n</head>')
    nl = '\r\n' if b'\r\n' in raw else '\n'
    return result.replace('\n', nl).encode('utf-8')


def dependencies(path, text):
    warnings = []
    scripts = re.findall(r'\be\.src\s*=\s*["\x27]([^"\x27]+\.js)["\x27]', text)
    if len(scripts) != 1:
        raise ValueError('expected one local exported runtime script')
    for name in scripts:
        if Path(name).name != name or not (path.parent / name).is_file():
            raise ValueError('missing or nonlocal runtime: ' + name)
        runtime = (path.parent / name).read_bytes()
        if not runtime:
            raise ValueError('empty runtime: ' + name)
        # These known exporters name the WASM dependency in their runtime.
        for wasm in set(re.findall(rb'[A-Za-z0-9_.-]+\.wasm', runtime)):
            dep = path.parent / wasm.decode('ascii')
            if not dep.is_file() or dep.stat().st_size == 0:
                warnings.append('missing or empty WASM file: ' + dep.name +
                                '; HTML/CSS treatment can proceed, but this runtime may not play until the file is restored.')
    return warnings


def plan(root, warnings=None):
    if warnings is None:
        warnings = []
    css = root / 'pico8/player.css'
    if not css.is_file() or 'color-scheme: light dark' not in css.read_text():
        raise ValueError('missing or incompatible shared pico8/player.css')
    work = []
    errors = []
    for folder in sorted((root / 'pico8').iterdir()):
        if not folder.is_dir():
            continue
        files = list(folder.iterdir())
        if not files:  # Empty placeholders are not packages.
            continue
        html = list(folder.glob('*.html'))
        if len(html) != 1:
            errors.append(str(folder.relative_to(root)) + ': expected exactly one HTML entry')
            continue
        path = html[0]
        try:
            raw = path.read_bytes()
            for warning in dependencies(path, raw.decode('utf-8')):
                warnings.append(str(path.relative_to(root)) + ': ' + warning)
            output = prepare(raw)
            work.append((path, raw, output))
        except (ValueError, UnicodeError, OSError) as error:
            errors.append(str(path.relative_to(root)) + ': ' + str(error))
    if errors:
        raise ValueError('\n'.join(errors))
    if not work:
        raise ValueError('no game packages found')
    return work


def apply(work, backups):
    changed = [(p, old, new) for p, old, new in work if old != new]
    # Preserve exact input HTML before any writes. These are HTML rollback
    # inputs, not complete source/game-package backups.
    for path, raw, _ in changed:
        target = backups / (sha(raw) + '.html')
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists():
            if target.read_bytes() != raw:
                raise ValueError('backup hash collision or corrupt backup: ' + str(target))
        else:
            with target.open('xb') as stream:
                stream.write(raw)
    written = []
    try:
        for path, raw, output in changed:
            if path.read_bytes() != raw:
                raise ValueError('input changed during preparation: ' + str(path))
            # Atomic replacement avoids truncated HTML on an interrupted write.
            temp = path.with_name(path.name + '.arcade-tmp')
            with temp.open('xb') as stream:
                stream.write(output)
            os.replace(temp, path)
            written.append((path, raw))
    except Exception:
        for path, raw in reversed(written):
            path.write_bytes(raw)
        raise
    return changed


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true', help='check HTML/CSS treatment without writing; exit 1 when preparation is needed; WASM warnings do not fail the check')
    args = parser.parse_args()
    try:
        warnings = []
        work = plan(ROOT, warnings)
        for warning in warnings:
            print('WARNING: ' + warning, file=sys.stderr)
        pending = [p for p, old, new in work if old != new]
        for path, old, new in work:
            print(('NEEDS PREPARATION ' if old != new else 'TREATMENT READY ') + str(path.relative_to(ROOT)))
        if args.check:
            print(f'{len(work)} HTML shells checked; {len(pending)} need treatment; {len(warnings)} WASM warnings. Playback is not verified.')
            return int(bool(pending))
        changed = apply(work, ROOT.parent / '_exports/player-html-inputs')
        print(f'{len(work)} HTML shells checked; {len(changed)} HTML files updated; {len(warnings)} WASM warnings. No runtime files changed; no upload. Playback is not verified.')
        return 0
    except (ValueError, OSError) as error:
        print('STOP: ' + str(error), file=sys.stderr)
        return 2


if __name__ == '__main__':
    sys.exit(main())
