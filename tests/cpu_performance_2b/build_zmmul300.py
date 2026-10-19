"""Build only new P/V300 and native CRC references; no HDL/PDS/serial."""
from pathlib import Path
import inspect
import json
import re
import subprocess
from zmmul300_software import ROOT, HERE, BUILD_DIR, FLAGS, load, sha, audit, require_manifest
from zmmul_software import BUILD_DIR as OLD


def main():
    assert not BUILD_DIR.exists(), 'Preserve independent build outputs'
    protected = {p.relative_to(ROOT).as_posix(): sha(p) for folder in
                 [OLD, HERE/'build/measure_20261011_120'] for p in folder.rglob('*') if p.is_file()}
    prior = json.loads((OLD/'build_review.json').read_text())
    protected.update(prior['source_sha256'])
    assert all(sha(ROOT/n) == h for n, h in protected.items())
    builder = load('zmmul300_same_recipe', HERE/'build.py')
    code = inspect.getsource(builder.build)
    assert code.count('-march=rv32i') == 2
    code = code.replace('-march=rv32i', '-march=rv32i_zmmul')
    namespace = dict(builder.__dict__, audit=audit, __file__=str(Path(__file__).resolve()))
    exec(compile(code, '<same_recipe_Zmmul300>', 'exec'), namespace)
    BUILD_DIR.mkdir()
    host = BUILD_DIR/'native_crc'; host.mkdir()
    old_host = ROOT/'sim/inst_line_buffer/build/formal120_crc_reference_20261011_a'
    for name in ['core_portme.h', 'host_port.c']:
        (host/name).write_bytes((old_host/name).read_bytes())
    sources = [ROOT/'coremark-main'/(name+'.c') for name in
               ['core_main', 'core_list_join', 'core_matrix', 'core_state', 'core_util']]
    crc = {}; outputs = {}
    for mode in ['performance', 'validation']:
        name = mode+'_300'; exe = host/(name+'.exe')
        argv = ['D:/mingw64/bin/gcc.exe', '-O2', '-Wall', '-Wextra', '-I', str(host),
                '-I', str(ROOT/'coremark-main'), '-DTOTAL_DATA_SIZE=2000', '-DITERATIONS=300',
                '-D'+mode.upper()+'_RUN=1', '-DFLAGS_STR="host CRC reference only"',
                *map(str, sources), str(host/'host_port.c'), '-o', str(exe)]
        for step, command in [('compile', argv), ('run', [str(exe)])]:
            result = subprocess.run(command, capture_output=True, text=True, timeout=60, check=False)
            (host/(name+'_'+step+'.log')).write_text(result.stdout+result.stderr)
            (host/(name+'_'+step+'.command.json')).write_text(json.dumps(dict(argv=command, exit_code=result.returncode), indent=2)+'\n')
            assert result.returncode == 0, result.stderr
        assert 'ERROR' not in result.stdout and 'Correct operation validated.' in result.stdout
        values = [re.findall(r'^'+re.escape(label)+r'\s*:\s*0x([0-9a-f]{4})$', result.stdout, re.M)
                  for label in ['seedcrc','[0]crclist','[0]crcmatrix','[0]crcstate','[0]crcfinal']]
        assert all(len(v)==1 for v in values)
        values = [v[0] for v in values]
        from zmmul_software import legacy
        assert tuple(values[:4]) == legacy.EXPECTED[mode]
        crc[name] = dict(values=values, clock_is_dummy=True, performance_evidence=False,
                         output_sha256=sha(host/(name+'_run.log')))
        namespace['build'](name, BUILD_DIR.name)
        out = BUILD_DIR/name
        old_info = json.loads((OLD/(mode+'_120')/'manifest.json').read_text())
        info = require_manifest(out/'manifest.json')
        assert info['symbols'] == old_info['symbols'] and info['sections'] == old_info['sections']
        assert info['multiply_sites'] == old_info['multiply_sites'] and len(info['multiply_sites']) == 28
        old_bin = (ROOT/old_info['bin_path']).read_bytes(); new_bin = (ROOT/info['bin_path']).read_bytes()
        offset = info['symbols']['seed4_volatile']-info['base']
        assert len(new_bin)==len(old_bin) and old_bin[:offset]==new_bin[:offset] and old_bin[offset+4:]==new_bin[offset+4:]
        assert int.from_bytes(new_bin[offset:offset+4], 'little') == 300
        assert (out/'core_portme.c').read_bytes() == (OLD/(mode+'_120')/'core_portme.c').read_bytes()
        template = (OLD/(mode+'_120')/'reference.txt').read_text()
        template = template.replace('Iterations       : 120', 'Iterations       : 300').replace('iterations=120','iterations=300')
        template = re.sub(r'(^\[0\]crcfinal\s*:\s*0x)[0-9a-f]{4}', lambda m:m[1]+values[4], template, flags=re.M)
        (out/'reference.txt').write_text(template, encoding='utf-8')
        outputs[name] = dict(bin_sha256=info['bin_sha256'], elf_sha256=info['elf_sha256'], bytes=info['bytes'],
                             iterations=300, static_MUL=28, crcfinal=values[4], seed_offset=offset,
                             difference_from_frozen_120_BIN='Only 4 bytes seed4_volatile 120 -> 300')
    assert all(sha(ROOT/n)==h for n,h in protected.items())
    report = dict(status='ZMMUL300_BUILD_ISA_AND_NATIVE_CRC_PASS_REAL_CPU_V1_PENDING', outputs=outputs,
                  compiler_flags=FLAGS, crc_reference=crc, protected_sha256=protected,
                  algorithm_and_port_unchanged=True, previous_outputs_unchanged=True,
                  HDL_started=False, PDS_started=False, serial_opened=False,
                  source_sha256={p.relative_to(ROOT).as_posix():sha(p) for p in
                                 [Path(__file__), HERE/'zmmul300_software.py', HERE/'build.py', *sources]})
    (BUILD_DIR/'build_review.json').write_text(json.dumps(report, indent=2)+'\n')
    print(report['status'], json.dumps(outputs, indent=2))


if __name__ == '__main__': main()
