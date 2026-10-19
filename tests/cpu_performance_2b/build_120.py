"""Build two 120-iteration BINs and native CRC references. No RTL simulation."""
from pathlib import Path
import hashlib
import importlib.util
import json
import re
import subprocess

from measurement_software import ROOT, FORMAL_DIR, audit, legacy

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('measurement_builder', HERE / 'build.py')
builder = importlib.util.module_from_spec(spec)
spec.loader.exec_module(builder)
builder.audit = audit
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    assert not FORMAL_DIR.exists(), 'Preserve existing builds'
    old_paths = [p for p in (HERE / 'build/measure_20261010_c').rglob('*') if p.is_file()]
    algorithm = [p for p in (ROOT / 'coremark-main').glob('*') if p.is_file()]
    protected = {p.relative_to(ROOT).as_posix(): sha(p) for p in old_paths + algorithm}
    reference = ROOT / 'sim/inst_line_buffer/build/formal120_crc_reference_20261011_a'
    reference.mkdir(parents=True, exist_ok=False)
    header = (ROOT / 'tests/bsp_workflow/core_portme.h').read_text()
    assert header.count('typedef ee_u32         ee_ptr_int;') == 1
    header = '#include <stdint.h>\n' + header.replace('typedef ee_u32         ee_ptr_int;', 'typedef uintptr_t      ee_ptr_int;', 1)
    (reference / 'core_portme.h').write_text(header)
    port = r'''#include "coremark.h"
#include <stdio.h>
#include <stdarg.h>
#if VALIDATION_RUN
volatile ee_s32 seed1_volatile=0x3415,seed2_volatile=0x3415;
#else
volatile ee_s32 seed1_volatile=0,seed2_volatile=0;
#endif
volatile ee_s32 seed3_volatile=0x66,seed4_volatile=ITERATIONS,seed5_volatile=0;
ee_u32 default_num_contexts=1;
int ee_printf(const char *fmt,...){va_list args;va_start(args,fmt);int n=vprintf(fmt,args);va_end(args);return n;}
void start_time(void){}
void stop_time(void){}
CORE_TICKS get_time(void){return 12u*93750000u;}
secs_ret time_in_secs(CORE_TICKS ticks){return ticks/93750000u;}
void portable_init(core_portable *p,int *argc,char *argv[]){(void)argc;(void)argv;p->portable_id=1;}
void portable_fini(core_portable *p){p->portable_id=0;}
'''
    (reference / 'host_port.c').write_text(port)
    sources = [ROOT / 'coremark-main' / (name + '.c') for name in
               ('core_main', 'core_list_join', 'core_matrix', 'core_state', 'core_util')]
    crc_records = {}
    for mode in ('performance', 'validation'):
        for iterations in (60, 120):
            name = f'{mode}_{iterations}'
            exe = reference / (name + '.exe')
            command = ['D:/mingw64/bin/gcc.exe', '-O2', '-Wall', '-Wextra',
                       '-I', str(reference), '-I', str(ROOT / 'coremark-main'),
                       '-DTOTAL_DATA_SIZE=2000', f'-DITERATIONS={iterations}',
                       f'-D{mode.upper()}_RUN=1', '-DFLAGS_STR="host CRC reference only"',
                       *map(str, sources), str(reference / 'host_port.c'), '-o', str(exe)]
            compiled = subprocess.run(command, capture_output=True, text=True, timeout=60)
            (reference / (name + '_compile.log')).write_text(compiled.stdout + compiled.stderr)
            assert compiled.returncode == 0, compiled.stderr
            run = subprocess.run([str(exe)], capture_output=True, text=True, timeout=20)
            (reference / (name + '.txt')).write_text(run.stdout)
            assert run.returncode == 0 and 'ERROR' not in run.stdout
            assert 'Correct operation validated.' in run.stdout
            values = [re.findall(r'^' + re.escape(label) + r'\s*:\s*0x([0-9a-f]{4})$', run.stdout, re.M)
                      for label in ('seedcrc', '[0]crclist', '[0]crcmatrix', '[0]crcstate', '[0]crcfinal')]
            assert all(len(v) == 1 for v in values)
            crc = tuple(v[0] for v in values)
            assert crc[:4] == legacy.EXPECTED[mode]
            if iterations == 60:
                assert crc[4] == ('a14c' if mode == 'performance' else '6770')
            crc_records[name] = dict(crc=crc, output_sha256=sha(reference / (name + '.txt')),
                                     clock_is_dummy=True, performance_evidence=False)
            print('CRC REFERENCE', name, crc[4], flush=True)
    for mode in ('performance', 'validation'):
        name = mode + '_120'
        builder.build(name, FORMAL_DIR.name)
        info = json.loads((FORMAL_DIR / name / 'manifest.json').read_text())
        old = json.loads((HERE / f'build/measure_20261010_c/{mode}_60/manifest.json').read_text())
        raw = (ROOT / info['bin_path']).read_bytes()
        previous = (ROOT / old['bin_path']).read_bytes()
        assert info['symbols'] == old['symbols'] and info['sections'] == old['sections']
        assert len(raw) == len(previous)
        offset = info['symbols']['seed4_volatile'] - info['base']
        assert raw[:offset] == previous[:offset] and raw[offset + 4:] == previous[offset + 4:]
        assert int.from_bytes(raw[offset:offset + 4], 'little') == 120
        assert int.from_bytes(previous[offset:offset + 4], 'little') == 60
        base_template = ROOT / f'tools/uart_loader/candidates/bsp_workflow/references/{mode}_60.txt'
        template = base_template.read_text()
        template = template.replace('Iterations       : 60', 'Iterations       : 120')
        template = template.replace('iterations=60', 'iterations=120')
        expected_final = crc_records[name]['crc'][4]
        template = re.sub(r'(^\[0\]crcfinal\s*:\s*0x)[0-9a-f]{4}', lambda m: m[1] + expected_final, template, flags=re.M)
        (FORMAL_DIR / name / 'reference.txt').write_text(template)
    assert all(sha(ROOT / n) == h for n, h in protected.items())
    report = dict(status='FORMAL120_SOFTWARE_BUILD_AND_NATIVE_CRC_PASS', iterations=120,
                  modes=['performance', 'validation'], crc_reference=crc_records,
                  host_reference_path=reference.relative_to(ROOT).as_posix(),
                  changes_in_BIN='ONLY_seed4_volatile_60_TO_120',
                  old_binaries_and_algorithm_unchanged=True, protected_sha256=protected,
                  board_result='NOT_TESTED', simulation_started=False, pds_started=False,
                  reference_clock_is_dummy=True, reference_is_performance_evidence=False,
                  sources_sha256={p.relative_to(ROOT).as_posix(): sha(p) for p in
                                  [Path(__file__), HERE / 'measurement_software.py', HERE / 'build.py'] + sources})
    (FORMAL_DIR / 'formal120_receipt.json').write_text(json.dumps(report, indent=2) + '\n')
    print('RESULT: PASS two formal120 BINs prepared; only iteration data changed; board NOT_TESTED')


if __name__ == '__main__':
    main()
