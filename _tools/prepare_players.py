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


def sha(data):
    return hashlib.sha256(data).hexdigest()


def original_shell(text):
    """Recognize stock or our exact managed integration; reject partial edits."""
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
    for element in ('p8_frame_0', 'p8_frame', 'p8_container', 'p8_playarea', 'canvas', 'p8_menu_buttons', 'p8_start_button'):
        if len(re.findall(r'\bid=["\x27]' + element + r'["\x27]', original)) != 1:
            raise ValueError('missing or duplicate player element: ' + element)
    if original.count('</head>') != 1 or original.count(ANCHOR) != 1:
        raise ValueError('unrecognized HTML integration points')
    result = original.replace(ANCHOR, BLOCK + ANCHOR)
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
