"""Run the generated x32 DDR3 IP's two-device physical-model training bench."""
from pathlib import Path
import argparse
import hashlib
import json
import re
import subprocess

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
FACTORY = ROOT/'ipcore/ddr3/sim/modelsim'
MS = Path('D:/modelsim/win64pe')
LIB = Path('C:/pango/PDS_2022.2-SP6.4/arch/vendor/pango/verilog/simulation')


def command(args, cwd, log, timeout=1200):
    with log.open('w', encoding='utf-8') as stream:
        process = subprocess.run(list(map(str, args)), cwd=cwd,
                                 stdout=stream, stderr=subprocess.STDOUT,
                                 timeout=timeout)
    output = log.read_text(encoding='utf-8', errors='replace')
    if process.returncode or re.search(r'\*\* (?:Error|Fatal):', output):
        raise RuntimeError(f'{log}: exit={process.returncode}\n{output[-2500:]}')
    return output


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--tag', required=True)
    args = parser.parse_args()
    if not re.fullmatch(r'[a-zA-Z0-9_-]+', args.tag):
        parser.error('invalid tag')
    out = HERE/'build'/args.tag
    out.mkdir(parents=True, exist_ok=False)
    work = out/'work'
    command([MS/'vlib.exe', work], out, out/'vlib.log', 120)
    primitives = sorted((LIB/'modelsim10.2c/adc_e2_source_codes').glob('*.vp'))
    if not primitives:
        raise FileNotFoundError('Pango simulation primitives')
    primitive_log = command([MS/'vlog.exe', '-work', work, *primitives],
                            out, out/'primitives_compile.log', 180)
    model = ROOT/'ipcore/ddr3/example_design/bench/mem/ddr3.v'
    bench = ROOT/'ipcore/ddr3/example_design/bench/ddr3_tb/ddr3_test_top_tb.v'
    model_text, model_changes = re.subn(r'\bmodule\s+ddr3\b',
                                       'module mini_ddr3_mem', model.read_text(), count=1)
    bench_text, bench_changes = re.subn(r'\bddr3\s+mem_core\s*\(',
                                       'mini_ddr3_mem mem_core (', bench.read_text())
    if model_changes != 1 or bench_changes != 1:
        raise RuntimeError('unexpected generated physical bench/model structure')
    bench_text = bench_text.replace('mini_ddr3_mem mem_core (',
                                    'mini_ddr3_mem #(.DEBUG(0)) mem_core (', 1)
    # Vendor bench disables the model's max refresh-interval check throughout
    # training, then immediately re-enables it with a stale pre-training
    # timestamp. Wait for the controller's first real post-training REFRESH;
    # this preserves both the model's minimum and maximum interval checks.
    group_header = 'for(gen_mem=0; gen_mem<(MEM_DQS_WIDTH/2); gen_mem=gen_mem+1) begin   : i_mem'
    if bench_text.count(group_header) != 1:
        raise RuntimeError('unexpected DDR model group structure')
    bench_text = bench_text.replace(group_header,
                                    group_header + '\ntime refresh_before;', 1)
    refresh_enable = 'force ddr3_test_top_tb.i_mem[gen_mem].mem_core.disable_trfc_max = 1\'b0;'
    if bench_text.count(refresh_enable) != 1:
        raise RuntimeError('unexpected vendor refresh-check enable')
    bench_text = bench_text.replace(
        refresh_enable,
        'refresh_before = ddr3_test_top_tb.i_mem[gen_mem].mem_core.tm_refresh;\n'
        'wait (ddr3_test_top_tb.i_mem[gen_mem].mem_core.tm_refresh != refresh_before);\n'
        + refresh_enable + '\n'
        '$display("CHECK: post-training REFRESH observed rank=%0d", gen_mem);',
        1)
    # Vendor example requests FSDB tasks; local ModelSim has no FSDB plugin.
    bench_text, fsdb_changes = re.subn(r'(?m)^\s*\$fsdbDump(?:file|vars)\([^;]*;',
                                      '', bench_text)
    if fsdb_changes != 2:
        raise RuntimeError('unexpected FSDB commands in vendor bench')
    derived_model = out/'mini_ddr3_mem.v'
    derived_bench = out/'mini_ddr3_test_top_tb.v'
    derived_model.write_text(model_text)
    derived_bench.write_text(bench_text)
    original_list = (FACTORY/'sim_file_list.f').read_text().splitlines()
    if not original_list[0].endswith('ddr3_test_top_tb.v') or not original_list[1].endswith('mem/ddr3.v'):
        raise RuntimeError('unexpected generated simulation file list')
    file_list = out/'mini_sim_file_list.f'
    file_list.write_text('\n'.join([derived_bench.as_posix(), derived_model.as_posix(),
                                    *original_list[2:]])+'\n')
    compile_log = command([MS/'vlog.exe', '-sv', '-work', work, '-mfcu', '-incr',
                           '-suppress', '2902', '+define+den4096Mb',
                           '+define+x16', '+define+sg25E', '-f', file_list,
                           '-y', LIB, '+libext+.v',
                           '+incdir+../../example_design/bench/mem/'],
                          FACTORY, out/'ip_compile.log', 600)
    if 'Errors: 0' not in primitive_log or 'Errors: 0' not in compile_log:
        raise RuntimeError('DDR IP compile did not confirm Errors: 0')
    log = command([MS/'vsim.exe', '-c', '-sva', '-lib', work,
                   'ddr3_test_top_tb', '-do', 'run 450us; quit -f'],
                  out, out/'simulation.log', 2400)
    if (re.search(r'\bERROR:', log) or 'TRAINING ERROR' in log or 'simulation finish' not in log or
            'Mem training complete' not in log or
            log.count('CHECK: post-training REFRESH observed rank=') != 2 or
            'Errors: 0' not in log):
        raise RuntimeError('DDR PHY training acceptance failed: '+str(out/'simulation.log'))
    inputs = [ROOT/'ipcore/ddr3/ddr3.v', ROOT/'ipcore/ddr3/ddr3_ddrphy_top.v',
              ROOT/'ipcore/ddr3/ddr3.idf', FACTORY/'sim_file_list.f',
              ROOT/'ipcore/ddr3/example_design/bench/ddr3_tb/ddr3_test_top_tb.v']
    result = {'status': 'DDR_IP_PHY_TRAINING_PASS',
              'scope': 'generated IP example bench, two x16 DDR3 models; no SoC traffic',
              'inputs_sha256': {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
                                for p in inputs}}
    (out/'result.json').write_text(json.dumps(result, indent=2)+'\n')
    print('RESULT: PASS DDR_IP_PHY_TRAINING_PASS', out, flush=True)


if __name__ == '__main__':
    main()
