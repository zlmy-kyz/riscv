"""Software-only audit extension for 120 iterations; retain the legacy checker."""
from pathlib import Path
import importlib.util
import inspect
import json

ROOT = Path(__file__).resolve().parents[2]
FORMAL_DIR = ROOT / 'tests/cpu_performance_2b/build/measure_20261011_120'
path = ROOT / 'tools/uart_loader/candidates/bsp_workflow/application.py'
spec = importlib.util.spec_from_file_location('legacy_application_audit', path)
legacy = importlib.util.module_from_spec(spec)
spec.loader.exec_module(legacy)
code = inspect.getsource(legacy.audit)
assert code.count('iterations in (1,60)') == 1
code = code.replace('iterations in (1,60)', 'iterations in (1,60,120)', 1)
namespace = dict(legacy.__dict__)
exec(compile(code, '<120_iteration_software_audit>', 'exec'), namespace)
layout_audit = namespace['audit']


def audit(elf, bin_file, kind, mode=None, iterations=None):
    info = layout_audit(elf, bin_file, kind, mode, iterations)
    if kind == 'coremark':
        offset = info['symbols']['seed4_volatile'] - info['base']
        assert int.from_bytes(Path(bin_file).read_bytes()[offset:offset + 4], 'little') == iterations
    return info


def require_manifest(path):
    info = json.loads(Path(path).read_text())
    assert info['status'] == 'DDR_APPLICATION_AUDIT_PASS'
    assert legacy.sha(ROOT / info['bin_path']) == info['bin_sha256']
    assert legacy.sha(ROOT / info['elf_path']) == info['elf_sha256']
    assert audit(ROOT / info['elf_path'], ROOT / info['bin_path'], info['kind'], info['mode'], info['iterations']) == info
    return info
