"""Run: python -B _tests/test_prepare_players.py from the Arcade folder."""
import importlib.util
from pathlib import Path
import tempfile
import unittest

BASE = Path(__file__).resolve().parents[1]
TOOL = BASE / 'arcade-dev/_tools/prepare_players.py'
spec = importlib.util.spec_from_file_location('prepare_players', TOOL)
prep = importlib.util.module_from_spec(spec)
spec.loader.exec_module(prep)
SHELL = BASE / 'arcade-dev/pico8/Jellyfish/index.html'


class PreparationTests(unittest.TestCase):
    def setUp(self):
        scratch = BASE / '_tests/_tmp'
        scratch.mkdir(exist_ok=True)
        # Retain disposable fixtures under _tmp: cloud-sync directories can
        # race recursive temporary-directory cleanup on Windows.
        self.root = Path(tempfile.mkdtemp(prefix="prepare-", dir=scratch))
        self.game = self.root / 'pico8/example'
        self.game.mkdir(parents=True)
        self.stock = prep.original_shell(SHELL.read_text()).encode()
        (self.game / 'index.html').write_bytes(self.stock)
        (self.game / 'jellyfish.js').write_bytes(b'load("jellyfish.wasm")')
        (self.game / 'jellyfish.wasm').write_bytes(b'wasm-fixture')
        (self.root / 'pico8/player.css').write_text(':root { color-scheme: light dark; }')

    def test_stock_then_repeat_is_byte_identical(self):
        result = prep.prepare(self.stock)
        self.assertEqual(prep.prepare(result), result)
        self.assertEqual(prep.original_shell(result.decode()).encode(), self.stock)

    def test_previous_sizing_block_upgrades_without_losing_bridge(self):
        current = prep.prepare(self.stock)
        previous = current.replace(prep.BLOCK.encode(), prep.LEGACY_BLOCK.encode())
        self.assertEqual(prep.prepare(previous), current)
        self.assertIn(b'portfolio:pico-connect', prep.prepare(previous))
        self.assertIn(b'p8_frame.getBoundingClientRect().width', current)

    def test_crlf_preserved(self):
        raw = self.stock.replace(b'\n', b'\r\n')
        result = prep.prepare(raw)
        self.assertNotIn(b'\n', result.replace(b'\r\n', b''))
        self.assertEqual(prep.prepare(result), result)

    def test_unknown_layout_rejected(self):
        raw = self.stock.replace(b'var csize = 512;', b'var csize = 256;')
        with self.assertRaisesRegex(ValueError, 'unsupported layout'):
            prep.prepare(raw)

    def test_partial_patch_rejected(self):
        raw = prep.prepare(self.stock).replace(prep.LINK.encode(), b'')
        with self.assertRaisesRegex(ValueError, 'partial'):
            prep.prepare(raw)

    def test_bad_second_package_blocks_all_writes(self):
        bad = self.root / 'pico8/broken'
        bad.mkdir()
        (bad / 'index.html').write_bytes(self.stock)
        before = {p: p.read_bytes() for p in self.root.rglob('*') if p.is_file()}
        with self.assertRaisesRegex(ValueError, 'missing or nonlocal runtime'):
            prep.plan(self.root)
        self.assertEqual(before, {p: p.read_bytes() for p in self.root.rglob('*') if p.is_file()})

    def test_missing_wasm_warns_and_treatment_applies(self):
        (self.game / 'jellyfish.wasm').unlink()
        warnings = []
        work = prep.plan(self.root, warnings)
        self.assertEqual(len(warnings), 1)
        self.assertIn('jellyfish.wasm', warnings[0])
        self.assertIn('may not play', warnings[0])
        self.assertEqual(len(prep.apply(work, self.root / 'backups')), 1)
        self.assertEqual((self.game / 'index.html').read_bytes(), prep.prepare(self.stock))
        self.assertFalse((self.game / 'jellyfish.wasm').exists())

    def test_empty_wasm_warns(self):
        (self.game / 'jellyfish.wasm').write_bytes(b'')
        warnings = []
        self.assertEqual(len(prep.plan(self.root, warnings)), 1)
        self.assertEqual(len(warnings), 1)

    def test_js_only_runtime_needs_no_wasm(self):
        (self.game / 'jellyfish.js').write_bytes(b'// JS-only runtime fixture')
        (self.game / 'jellyfish.wasm').unlink()
        warnings = []
        self.assertEqual(len(prep.plan(self.root, warnings)), 1)
        self.assertEqual(warnings, [])

    def test_apply_preserves_input_and_runtime(self):
        js = (self.game / 'jellyfish.js').read_bytes()
        backup = self.root / 'backups'
        self.assertEqual(len(prep.apply(prep.plan(self.root), backup)), 1)
        self.assertEqual((backup / (prep.sha(self.stock) + '.html')).read_bytes(), self.stock)
        self.assertEqual((self.game / 'jellyfish.js').read_bytes(), js)
        self.assertEqual(prep.apply(prep.plan(self.root), backup), [])


if __name__ == '__main__':
    unittest.main()
