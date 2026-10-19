"""Create one immutable-by-contract input copy; no simulator/PDS/serial execution."""
import ast
import hashlib
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
TAG='ds_camera_key_20261015_a'
SEAL=HERE/'sealed_20261015_a'
MS=Path('D:/modelsim/win64pe')
VENDOR=Path('C:/pango/PDS_2022.2-SP6.4/arch/vendor/pango/verilog/simulation')
INCDIRS=['myriscv','ipcore/inst_rom/rtl','ipcore/data_ram/rtl','sim/camera/key']
TOPS={'sccb':'tb_camera_sccb','faults':'tb_camera_faults','soc':'tb_camera_soc'}
TIMEOUTS={'vlib':60,'compile':180,'sccb':120,'faults':180,'soc':7200,'check':180}

def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def source_list():
    prior=json.loads((ROOT/'sim/data_bus_turnover/inputs.json').read_text())
    base=[s for s in prior['compile_sources'] if not s.startswith('sim/')]
    camera=['ov5640_sccb.v','ov5640_config_rom.v','ov5640_config.v','ov5640_capture.v',
            'afifo_16i_64o_512.v','ipm2l_fifo_v1_10_afifo_16i_64o_512.v',
            'ipm2l_fifo_ctrl_v1_1_afifo_16i_64o_512.v','ipm2l_sdpram_v1_10_afifo_16i_64o_512.v',
            'camera_mmio.v','camera_ddr_write_arbiter.v','soc_ddr3_top.v']
    test=['sensor.sv','ddr_model.sv','arbiter_unit.sv','aperture_unit.sv','tb_sccb.sv','tb_faults.sv','tb_soc.sv']
    return base+['myriscv/'+p for p in camera]+['sim/camera/key/'+p for p in test]

def closure(root,sources):
    root=Path(root).resolve();todo=[root/p for p in sources];seen=set();result={}
    while todo:
        source=todo.pop().resolve()
        if source in seen:continue
        assert source.is_file(),source
        seen.add(source)
        # Includes may live inside conditional branches: archive all literal dependencies.
        for name in re.findall(r'^\s*`include\s+"([^"]+)"',source.read_text(encoding='utf-8'),re.M):
            candidates=[source.parent/name,*[root/d/name for d in INCDIRS]]
            found=next((p.resolve() for p in candidates if p.is_file()),None)
            assert found and found.is_relative_to(root),(source,name)
            result[source.relative_to(root).as_posix()+':'+name]=found.relative_to(root).as_posix()
            todo.append(found)
    return dict(sorted(result.items()))

def git_snapshot():
    def git(*args):return subprocess.check_output(['git',*args],cwd=ROOT).decode('utf-8',errors='replace')
    return dict(head=git('rev-parse','HEAD').strip(),branch=git('branch','--show-current').strip(),
                status=git('-c','core.quotepath=false','status','--short','--untracked-files=all'),
                diff=git('diff','--binary','--','myriscv','ipcore','RISCV.pds','constraint_check/temp_constraint_file.fdc'))

def main():
    assert not SEAL.exists(),'Sealed input identity is never overwritten'
    assert not (HERE/'inputs.json').exists(),'Manifest already exists'
    sources=source_list();includes=closure(ROOT,sources)
    repair=json.loads((ROOT/'sim/camera/timing_fix_20261015_a/repair_review.json').read_text())
    for row in repair['after']:assert sha(ROOT/row['path'])==row['sha256'],'Timing-repair input changed: '+row['path']
    names=set(sources)|set(includes.values())
    names.update(p.relative_to(ROOT).as_posix() for p in (ROOT/'myriscv').iterdir() if p.suffix in ('.v','.vh','.svh'))
    # Identity-only DDR inputs are preserved, but not compiled into this user-port-model run.
    names.update(p.relative_to(ROOT).as_posix() for p in (ROOT/'ipcore').rglob('*') if p.is_file() and p.suffix in ('.v','.vp','.vh','.svh','.idf'))
    names.update(p.relative_to(ROOT).as_posix() for p in HERE.iterdir() if p.is_file() and p.suffix in ('.py','.sv','.md'))
    names.update(p.relative_to(ROOT).as_posix() for p in (HERE/'generated').iterdir() if p.is_file())
    names.update(['AGENTS.md','RISCV.pds','constraint_check/temp_constraint_file.fdc','fdc/camera_single.fdc',
                  'difftest/golden/rvtool.py','sim/data_bus_turnover/inputs.json',
                  'sim/camera/static_20261015/source_review.json','sim/camera/timing_fix_20261015_a/repair_review.json',
                  'DeepSeek/相机首版_精简关键测试_2026-10-15.md'])
    # Record the successful prior evidence without rerunning it or promoting it to camera PASS.
    protected=['sim/data_bus_turnover/build/registered_board_final_review_20261015_a/board_review.json']
    prior=json.loads((ROOT/protected[0]).read_text())
    for key in ('files_sha256','evidence_sha256','input_sha256','source_sha256'):
        for name,digest in prior.get(key,{}).items():
            p=ROOT/name
            # Historic RTL hashes describe the old successful design. Protect its
            # evidence files, not an obsolete bridge identity at the live path.
            if name.startswith('sim/') and p.is_file():
                assert sha(p)==digest,name
                protected.append(name)
    names.update(protected)
    # Generated BRAM INIT_FILE paths are not changed; preserve their original images too.
    for directory in ('ipcore/inst_rom','ipcore/data_ram'):
        source=(ROOT/directory/(Path(directory).name+'.v')).read_text()
        for raw in re.findall(r'INIT_FILE\s*=\s*"([^"]+)"',source):
            p=Path(raw).resolve();assert p.is_relative_to(ROOT)
            names.add(p.relative_to(ROOT).as_posix())
    for p in HERE.glob('*.py'):ast.parse(p.read_text(encoding='utf-8'))
    vendor={str(VENDOR/n):sha(VENDOR/n) for n in ('GTP_GRS.v','GTP_DRM36K_E1.v','GTP_APM_E2.v')}
    # Check primitive includes too, and copy their recursively quoted dependencies.
    vendor_files=dict(vendor);todo=[Path(p) for p in vendor]
    while todo:
        p=todo.pop()
        for name in re.findall(r'^\s*`include\s+"([^"]+)"',p.read_text(),re.M):
            q=(p.parent/name).resolve();assert q.is_file() and q.is_relative_to(VENDOR.resolve())
            if str(q) not in vendor_files:vendor_files[str(q)]=sha(q);todo.append(q)
    tools={str(MS/(n+'.exe')):sha(MS/(n+'.exe')) for n in ('vlib','vlog','vsim')}
    tools[sys.executable]=sha(sys.executable)
    modelsim_ini=MS.parent/'modelsim.ini'
    manifest=dict(status='CAMERA_KEY_SEALED_HDL_NOT_RUN',date='2026-10-15',tag=TAG,
                  timing='USER_CONFIRMED_PASS_IN_CHAT_NOT_INDEPENDENTLY_AUDITED',
                  roles=dict(Sol='TB/model/CPU/reference/seal/review',DeepSeek='execute_only',user='PDS/board'),
                  project_sha256={n:sha(ROOT/n) for n in sorted(names)},vendor_sha256=vendor_files,
                  vendor_compile_sources=list(vendor),tool_sha256=tools,compile_sources=sources,include_dependencies=includes,
                  include_dirs=INCDIRS,tops=TOPS,timeouts=TIMEOUTS,modelsim_ini=dict(path=str(modelsim_ini),sha256=sha(modelsim_ini)),
                  protected_evidence_sha256={n:sha(ROOT/n) for n in sorted(set(protected))},
                  substitutions=['ddr3 PHY/controller replaced at native user port by sealed ddr_model.sv'],
                  test_overrides=['RESET_PC=40000000; test DDR preload only','config CLK_HZ=1600000; timing accelerated only',
                                  'fault module camera geometry=128x128 DROP_FRAMES=0; full SoC=1280x720 DROP_FRAMES=10'],
                  PDS='NOT_RUN',HDL='NOT_RUN',board='NOT_RUN',CoreMark='REUSED_NOT_RUN',ISA='NOT_RUN',DDR_PHY='NOT_RUN')
    module_files=set(sources)|set(includes.values())
    manifest['compiled_module_names']=sorted(set(n for p in module_files for n in
        re.findall(r'^\s*module\s+(\w+)',(ROOT/p).read_text(encoding='utf-8'),re.M)))
    SEAL.mkdir(exist_ok=False)
    (SEAL/'worktree_before.json').write_text(json.dumps(git_snapshot(),ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    for name,digest in manifest['project_sha256'].items():
        target=SEAL/'project'/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(ROOT/name,target)
        assert sha(target)==digest
    for name,digest in vendor_files.items():
        target=SEAL/'vendor'/Path(name).relative_to(VENDOR);target.parent.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(name,target);assert sha(target)==digest
    (SEAL/'tools').mkdir()
    shutil.copyfile(modelsim_ini,SEAL/'tools/modelsim.ini')
    assert closure(SEAL/'project',sources)==includes
    for path in (HERE/'inputs.json',SEAL/'inputs.json'):
        with path.open('x',encoding='utf-8') as f:json.dump(manifest,f,ensure_ascii=False,indent=2);f.write('\n')
    print(json.dumps(dict(status=manifest['status'],manifest_sha256=sha(HERE/'inputs.json'),
                         project=len(names),vendor=len(vendor_files),includes=len(includes),modules=len(manifest['compiled_module_names']))))

if __name__=='__main__':main()
