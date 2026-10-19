"""ABI2 immutable input copy with recursive include/initializer/vendor closure. Sol prepares, DeepSeek executes."""
import ast,hashlib,json,re,shutil,subprocess,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2]
TAG='ds_abi2_key_20261016_a';SEAL=HERE/'sealed_20261016_a'
MS=Path('D:/modelsim/win64pe');VENDOR=Path('C:/pango/PDS_2022.2-SP6.4/arch/vendor/pango/verilog/simulation')
INCDIRS=['myriscv','ipcore/inst_rom/rtl','ipcore/data_ram/rtl','sim/camera/key','sim/camera_double/key_20261016_a']
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(p,obj):Path(p).write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def sources():
    prior=json.loads((ROOT/'sim/camera/key/inputs.json').read_text(encoding='utf-8'))
    return [s for s in prior['compile_sources'] if not s.startswith('sim/')]+['sim/camera/key/sensor.sv']+[f'sim/camera_double/key_20261016_a/{n}' for n in ['ddr_model.sv','dvp.sv','aperture.sv','tb_unit.sv','tb_soc.sv']]
def closure(root,src):
    root=Path(root).resolve();todo=[root/n for n in src];seen=set();edges={}
    while todo:
        p=todo.pop().resolve()
        if p in seen:continue
        seen.add(p);assert p.is_file(),p
        for name in re.findall(r'^\s*`include\s+"([^"]+)"',p.read_text(encoding='utf-8'),re.M):
            q=next((c.resolve() for c in [p.parent/name,*[root/d/name for d in INCDIRS]] if c.is_file()),None)
            assert q and q.is_relative_to(root),(p,name)
            edges[p.relative_to(root).as_posix()+':'+name]=q.relative_to(root).as_posix();todo.append(q)
    return dict(sorted(edges.items()))
def git():
    def g(*a):return subprocess.check_output(['git',*a],cwd=ROOT).decode('utf-8',errors='replace')
    return dict(head=g('rev-parse','HEAD').strip(),status=g('-c','core.quotepath=false','status','--short'),
                diff=g('diff','--binary','--','myriscv','ipcore','RISCV.pds'))
def main():
    assert not SEAL.exists() and not (HERE/'inputs.json').exists()
    src=sources();inc=closure(ROOT,src);names=set(src)|set(inc.values())
    # Bind design and original IP inputs without changing or compiling physical DDR.
    names.update(p.relative_to(ROOT).as_posix() for p in (ROOT/'myriscv').iterdir() if p.suffix in ('.v','.vh','.svh'))
    names.update(p.relative_to(ROOT).as_posix() for p in (ROOT/'ipcore').rglob('*') if p.is_file() and p.suffix in ('.v','.vp','.vh','.svh','.idf'))
    names.update(p.relative_to(ROOT).as_posix() for p in HERE.iterdir() if p.is_file() and p.suffix in ('.py','.sv','.md'))
    names.update(p.relative_to(ROOT).as_posix() for p in (HERE/'generated').iterdir() if p.is_file())
    # Bind preparation receipts without duplicating compiler libraries or synthetic fixtures.
    for folder in ('preparation/static_f','preparation/offline_b'):
        names.update(p.relative_to(ROOT).as_posix() for p in (HERE/folder).iterdir() if p.is_file())
    names.add('sim/camera_double/key_20261016_a/preparation/ready_review.json')
    for tag in ('abi2_20261016_d','abi2_small_20261016_d'):
        manifest=ROOT/f'tests/camera_double100/build/{tag}/manifest.json';m=json.loads(manifest.read_text(encoding='utf-8'))
        for n,d in m['source_sha256'].items():assert sha(ROOT/n)==d;names.add(n)
        names.update(p.relative_to(ROOT).as_posix() for p in manifest.parent.iterdir() if p.is_file())
    for n in ('AGENTS.md','RISCV.pds','sim/camera/key/generated/config.hex','sim/camera/key/generated/ddr_header.svh',
              'sim/camera/key/inputs.json','sim/camera_double/static_20261015_a/review.json',
              'tests/camera_double100/README.md','DeepSeek/双缓冲ABI2_精简关键测试_2026-10-16.md'):
        names.add(n)
    names.update(['doc/camera/OV5640双缓冲所有权与CPU并发读取_2026-10-15.md','sim/camera/key/review_soc_bootmap_20261015_a/review.json','sim/camera/key/review_timeout_20261015_a/review.json'])
    review=json.loads((ROOT/'sim/camera_double/static_20261015_a/review.json').read_text(encoding='utf-8'))
    for row in review['source_after']:
        if row['path'].startswith('myriscv/'):assert sha(ROOT/row['path'])==row['sha256'],row['path']
    protected={}
    for folder in ('sim/camera/board/loop100_20261015_01','sim/camera/board/uart_frames_20261015_01',
                   'tests/camera_loop100/build/camera_loop100_20261015_a','tests/camera_uart/build/camera_uart_20261015_a'):
        for p in (ROOT/folder).iterdir():
            if p.is_file():protected[p.relative_to(ROOT).as_posix()]=sha(p)
    for directory in ('ipcore/inst_rom','ipcore/data_ram'):
        for raw in re.findall(r'INIT_FILE\s*=\s*"([^"]+)"',(ROOT/directory/(Path(directory).name+'.v')).read_text(encoding='utf-8')):
            p=Path(raw).resolve();assert p.is_relative_to(ROOT);names.add(p.relative_to(ROOT).as_posix())
    vendor={str(VENDOR/n):sha(VENDOR/n) for n in ('GTP_GRS.v','GTP_DRM36K_E1.v','GTP_APM_E2.v')};todo=list(vendor)
    while todo:
        p=Path(todo.pop())
        for n in re.findall(r'^\s*`include\s+"([^"]+)"',p.read_text(encoding='utf-8'),re.M):
            q=(p.parent/n).resolve();assert q.is_relative_to(VENDOR.resolve()) and q.is_file()
            if str(q) not in vendor:vendor[str(q)]=sha(q);todo.append(str(q))
    for p in HERE.glob('*.py'):ast.parse(p.read_text(encoding='utf-8'))
    tools={str(MS/(n+'.exe')):sha(MS/(n+'.exe')) for n in ('vlib','vlog','vsim')};tools[sys.executable]=sha(sys.executable)
    m=dict(status='ABI2_KEY_SEALED_NOT_EXECUTED',date='2026-10-16',tag=TAG,ABI='43414d02',
           timing='USER_CONFIRMED_BITSTREAM_GENERATED_TIMING_CORRECT_NO_PDS_OR_BITSTREAM_REAUDIT',
           project_sha256={n:sha(ROOT/n) for n in sorted(names)},protected_history_sha256=protected,
           vendor_sha256=vendor,vendor_compile_sources=[str(VENDOR/n) for n in ('GTP_GRS.v','GTP_DRM36K_E1.v','GTP_APM_E2.v')],
           tool_sha256=tools,include_dirs=INCDIRS,include_dependencies=inc,compile_sources=src,
           modelsim_ini=dict(path=str(MS.parent/'modelsim.ini'),sha256=sha(MS.parent/'modelsim.ini')),
           jobs=dict(unit='tb_double_unit',soc='tb_double_soc'),timeouts=dict(vlib=60,compile=180,unit=300,soc=300,check=120),
           substitutions=['DDR3 at native x32/256bit user port replaced by model, not PHY',
               'unit geometry64x128, hardware timeout CLK_HZ100000/config1600000, DROP10',
               'real CPU geometry64x8, config CLK_HZ1600000, DROP10, physical core/PCLK unchanged',
               'CPU SIM from sealed DDR preload, ROM/RAM base0 PC40000000, same C with real UART input/stress',
               'unit tests direct MMIO; permissions use real decoders; no claim of real CPU illegal-instruction trap coverage'],
           board='NOT_RUN',HDL='NOT_EXECUTED',CoreMark='NOT_RUN',ISA='NOT_RUN',DDR_PHY='NOT_RUN')
    m['modules']=sorted(set(n for p in set(src)|set(inc.values()) for n in re.findall(r'^\s*module\s+(\w+)',(ROOT/p).read_text(encoding='utf-8'),re.M)))
    SEAL.mkdir(exist_ok=False);save(SEAL/'worktree.json',git())
    for n,d in m['project_sha256'].items():
        p=SEAL/'project'/n;p.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(ROOT/n,p);assert sha(p)==d
    for n,d in vendor.items():
        p=SEAL/'vendor'/Path(n).relative_to(VENDOR);p.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(n,p);assert sha(p)==d
    (SEAL/'tools').mkdir();shutil.copyfile(m['modelsim_ini']['path'],SEAL/'tools/modelsim.ini')
    assert closure(SEAL/'project',src)==inc
    save(HERE/'inputs.json',m);save(SEAL/'inputs.json',m)
    print(json.dumps(dict(status=m['status'],manifest_sha256=sha(HERE/'inputs.json'),inputs=len(names),include_edges=len(inc),modules=len(m['modules']))))
if __name__=='__main__':main()
