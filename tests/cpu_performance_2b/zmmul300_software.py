"""Independent 300-iteration Zmmul audits; frozen 1/120 software stays untouched."""
import inspect
import json
import sys
from zmmul_software import ROOT, HERE, FLAGS, load, sha, legacy, zmmul_legal
import zmmul_software as old

BUILD_DIR = HERE / 'build/measure_zmmul300_20261013_a'
code = inspect.getsource(legacy.audit)
guard = "for i in range(0,len(code),4):assert isa.legal_instruction(int.from_bytes(code[i:i+4],'little')),(name,i)"
assert code.count(guard) == code.count('iterations in (1,60)') == 1
code = code.replace(guard, "for i in range(0,len(code),4):assert (isa.legal_instruction(int.from_bytes(code[i:i+4],'little')) or zmmul_legal(int.from_bytes(code[i:i+4],'little'))),(name,i)")
code = code.replace('iterations in (1,60)', 'iterations == 300')
namespace = dict(legacy.__dict__, zmmul_legal=zmmul_legal)
exec(compile(code, '<300_Zmmul_ELF_layout>', 'exec'), namespace)
namespace = dict(old.__dict__, layout_audit=namespace['audit'])
exec(compile(inspect.getsource(old.audit), '<300_Zmmul_ELF_audit>', 'exec'), namespace)
audit = namespace['audit']
exec(compile(inspect.getsource(old.require_manifest), '<300_manifest_audit>', 'exec'), namespace)
require_manifest = namespace['require_manifest']

measurement = old.measurement
code = inspect.getsource(measurement.parse_measurement)
reference = "reference = (FORMAL_DIR / f'{mode}_120/reference.txt' if iterations == 120 else\n                 ROOT / f'tools/uart_loader/candidates/bsp_workflow/references/{mode}_{iterations}.txt')"
assert code.count(reference) == 1 and code.count('iterations in (60, 120)') == 1
code = code.replace(reference, "reference = BUILD_DIR / f'{mode}_{iterations}/reference.txt'")
code = code.replace('iterations in (60, 120)', 'iterations == 300')
code = code.replace('if iterations == 120:', 'if iterations == 300:')
namespace = dict(measurement.__dict__, BUILD_DIR=BUILD_DIR)
exec(compile(code, '<300_exact_UART_and_13_counters>', 'exec'), namespace)
_parse = namespace['parse_measurement']


def parse_measurement(info, data, *, board=False, elapsed=None):
    assert info['iterations'] == 300 and info['isa'] == 'rv32i_zmmul' and info['compiler_flags'] == FLAGS
    result = _parse(info, data, board=board, elapsed=elapsed)
    return dict(result, isa='rv32i_zmmul', cycles_per_iteration=result['ticks']/300,
                comparison_kind='Normalize cycles/iteration and iterations/second against RV32I120; different BIN and iteration count',
                crc_functional_only=not board)
