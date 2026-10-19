"""037: prepare decoder timing change; static identity/elaboration only."""
from pathlib import Path
import difflib
import hashlib
import json
import re
import subprocess
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
PRIOR = ROOT/'sim/cpu_request_presample/timing_repair_20261018_a'
TARGET = 'myriscv/data_bus_interconnect.v'
BOARD = 'sim/cpu_request_presample/board/review_20261018_01/board_review.json'

def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()

def save(name,value):
    (HERE/name).write_text(json.dumps(value,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')

def git(name,args):
    r = subprocess.run(['git',*args],cwd=ROOT,capture_output=True,check=True)
    (HERE/name).write_bytes(r.stdout+r.stderr)

def snapshot():
    prior = json.loads((PRIOR/'after_manifest.json').read_text(encoding='utf-8'))
    current = {k:sha(ROOT/k) for k in prior}
    changed = [k for k in prior if current[k] != prior[k]]
    assert set(changed) <= {'RISCV.pds','report_timing/board_top.rtr'},changed
    current[BOARD] = sha(ROOT/BOARD)
    assert json.loads((ROOT/BOARD).read_text(encoding='utf-8'))['status'] == 'TASK036_FIXED_P300_V300_APPLICATION_BOARD_RAW_PASS_HDL_NOT_RUN'
    (HERE/'before').mkdir(exist_ok=False)
    copied = sorted(set(changed)|{TARGET})
    for k in copied:
        p = HERE/'before'/k
        p.parent.mkdir(parents=True,exist_ok=True)
        p.write_bytes((ROOT/k).read_bytes())
    save('before_manifest.json',current)
    save('snapshot_index.json',{'prior_manifest':str(PRIOR/'after_manifest.json'),
        'copied_inputs':copied,'reused_inputs':'Unchanged sources reuse prior snapshots; new board review remains at its immutable evidence path.'})
    text = (ROOT/'report_timing/board_top.rtr').read_text(encoding='utf-8')
    paths = []
    for m in re.finditer(r'Startpoint\s*:\s*(.*?)\nEndpoint\s*:\s*(.*?)\nPath Group\s*:\s*(.*?)\n(.*?)(?=Startpoint|\Z)',text,re.S):
        if m[3].strip() != 'ddrphy_sysclk' or 'max (slow corner)' not in m[4] or 'sequential timing path' not in m[4]:
            continue
        slack = re.search(r'Slack \(\w+\)\s+([-\d.]+)',m[4])
        detail = re.search(r'Logic Levels:.*?Route:.*?\)',m[4],re.S)
        paths.append(dict(start=m[1].strip(),end=m[2].strip(),slack_ns=float(slack[1]),detail=detail[0] if detail else None))
    paths.sort(key=lambda x:x['slack_ns'])
    save('timing_observation.json',{'report_sha256':current['report_timing/board_top.rtr'],
        'report_date':'Sun Oct 18 02:07:14 2026','design_summary':'All Constraints Met',
        'clock_mhz':93.75,'wns_ns':0.115,'tns_ns':0.0,'estimated_fmax_mhz':94.7718,
        'top_reported_core_paths':paths[:3],
        'limits':'Report/current sources observed; not independent reconstruction of PDS implementation inputs.'})
    git('git_before.txt',['status','--porcelain=v1','-uall'])
    git('decoder_before_head.diff',['diff','--',TARGET])
    print(json.dumps({'status':'SNAPSHOT_ONLY','inputs':len(current),'copied':copied}))

def review():
    if (HERE/'review.json').exists():
        raise RuntimeError('preserve existing receipt')
    before = json.loads((HERE/'before_manifest.json').read_text(encoding='utf-8'))
    after = {k:sha(ROOT/k) for k in before}
    changed = [k for k in before if before[k] != after[k]]
    assert changed == [TARGET],changed
    for k in json.loads((HERE/'snapshot_index.json').read_text(encoding='utf-8'))['copied_inputs']:
        assert sha(HERE/'before'/k) == before[k]
    old = (HERE/'before'/TARGET).read_text(encoding='utf-8')
    new = (ROOT/TARGET).read_text(encoding='utf-8')
    # All outputs except combinational selection/ready and declarations are untouched.
    assert old[old.index('    assign req_fire ='):]==new[new.index('    assign req_fire ='):]
    assert old[:old.index('    wire ram_select;')]==new[:new.index('    wire ram_select;')]
    save('after_manifest.json',after)
    (HERE/'decoder.patch').write_text(''.join(difflib.unified_diff(old.splitlines(True),new.splitlines(True),
        'before/'+TARGET,'after/'+TARGET)),encoding='utf-8')
    src = [p.relative_to(ROOT).as_posix() for p in sorted((ROOT/'myriscv').glob('*.v'))]
    src += ['ipcore/icache/icache.v','ipcore/dcache/dcache.v']
    top = 'data_bus_interconnect'
    enabled = {'ENABLE_DDR':1,'ENABLE_UART':1,'ENABLE_CAMERA':1,'ENABLE_PREPROCESS':1,'ENABLE_CNN':1,
               'DDR_WRITE_ORDER_ENABLE':1}
    configs = [('board','board_top',{}),('default',top,{}),('all_enabled',top,enabled),
        ('ram_overlaps_peripherals',top,dict(enabled,RAM_BASE="32'h10000000",RAM_ADDR_MASK="32'hffff0000")),
        ('mmio_overlaps_all',top,dict(enabled,MMIO_ADDR_MASK="32'hf0000000",DDR_BASE="32'h10000000",DDR_ADDR_MASK="32'hf0000000")),
        ('uart_overlaps_camera',top,dict(enabled,UART_BASE="32'h10002000")),
        ('turnover_off',top,dict(enabled,RESPONSE_TURNOVER_ENABLE=0)),
        ('ram_covers_all',top,dict(enabled,RAM_ADDR_MASK=0))]
    (HERE/'checks_01').mkdir(exist_ok=False)
    checks = []
    for name,module,params in configs:
        argv = ['D:/iverilog/bin/iverilog.exe','-g2005','-tnull','-i','-I','myriscv','-s',module]
        for k,v in params.items():
            argv += ['-P',f'{module}.{k}={v}']
        argv += src
        r = subprocess.run(argv,cwd=ROOT,capture_output=True,timeout=60)
        output = (r.stdout+r.stderr).decode('utf-8',errors='replace')
        (HERE/'checks_01'/(name+'.log')).write_text(output,encoding='utf-8')
        checks.append(dict(name=name,cwd=str(ROOT),argv=argv,exit_code=r.returncode,output=output))
        if r.returncode:
            save('static_failure.json',checks)
            raise RuntimeError(name)
    subprocess.run(['git','diff','--check','--',TARGET],cwd=ROOT,check=True)
    git('git_after.txt',['status','--porcelain=v1','-uall'])
    save('review.json',{'status':'TASK037_DATA_DECODE_STATIC_ONLY_PENDING_USER_PDS','changed':changed,
        'before_sha256':before[TARGET],'after_sha256':after[TARGET],'unchanged_inputs':len(after)-1,
        'scope_check':'Interface/parameters and all RTL from req_fire through sequential response ownership identical.',
        'checks':checks,'dynamic_simulation':'NOT_RUN','pds':'NOT_RUN','board':'NOT_RUN',
        'limits':'Null-target with vendor internals blackboxed; no functional/timing/performance PASS.'})
    print(json.dumps({'status':'TASK037_STATIC_ONLY_PENDING_USER_PDS','checks':len(checks),'decoder':after[TARGET]}))

if __name__ == '__main__':
    {'snapshot':snapshot,'review':review}[sys.argv[1]]()
