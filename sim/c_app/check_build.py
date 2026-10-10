"""Compiler and image rejection tests in isolated fixture/build directories."""
from pathlib import Path
import json
import sys
import uuid

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tests/c_app'))
import pipeline as app

folder = Path(__file__).resolve().parent / 'build_checks' / uuid.uuid4().hex[:8]
folder.mkdir(parents=True, exist_ok=False)
checks = []


def reject(name, source):
    path = folder / (name + '.c')
    path.write_text(source, encoding='utf-8')
    try:
        app.build([path], b'PASS', False, 'reject_' + uuid.uuid4().hex[:12])
    except (ValueError, AssertionError, RuntimeError):
        checks.append(dict(name=name, result='PASS'))
        return
    raise AssertionError('Did not reject ' + name)


reject('compile_error', '#include "bsp.h"\nint main(void) { this is invalid C; }\n')
reject('missing_main', 'int another_function(void) { return 0; }\n')
reject('DDR_BSS_overlaps_stack', '#include "bsp.h"\nvolatile unsigned char huge[65000]; int main(void) { huge[64999]=1; return huge[0]; }\n')
reject('unsupported_M_instruction', '#include "bsp.h"\nint main(void) { __asm__ volatile(".word 0x02000033"); return 0; }\n')
reject('unsupported_compressed_instruction', '#include "bsp.h"\nint main(void) { __asm__ volatile(".word 0x00010001"); return 0; }\n')
reject('unexpected_allocated_section', '#include "bsp.h"\nvolatile unsigned custom __attribute__((section(".other")))=7; int main(void) { return custom; }\n')
app.save(folder / 'results.json', dict(status='C_APP_BUILD_REJECTION_PASS', checks=checks, count=len(checks),
                                      evidence_origin='OFFLINE_COMPILER_NOT_BOARD', serial_opened=False))
print('RESULT: PASS', len(checks), 'build/ISA/layout rejection checks; no serial opened;', folder)
