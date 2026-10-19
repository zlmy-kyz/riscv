"""Read-only review of the INI-resume evidence; never executes a simulator."""
import collections
import hashlib
import importlib
import json
import re
import sys
from pathlib import Path

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[3]
KEY=ROOT/'sim/camera/key'
OUT=KEY/'build/ds_camera_ini_resume_20261015_a'
sys.path.insert(0,str(KEY))
from seal import sha,closure,VENDOR

def main():
    m=json.loads((OUT/'inputs.json').read_text(encoding='utf-8'))
    assert sha(OUT/'inputs.json')==sha(KEY/'inputs_ini_resume.json')=='0cadecef11c33d41d52b233a9aa629a51791843756f235c829c3fa32c08ce3f7'
    counts={}
    for label,folder in [('live',ROOT),('sealed',KEY/'sealed_ini_resume_20261015_a/project'),('run',OUT/'inputs/project')]:
        for name,d in m['project_sha256'].items():assert sha(folder/name)==d,(label,name)
        counts[label]=len(m['project_sha256'])
    for name,d in m['vendor_sha256'].items():
        for p in [Path(name),OUT/'inputs/vendor'/Path(name).relative_to(VENDOR),KEY/'sealed_ini_resume_20261015_a/vendor'/Path(name).relative_to(VENDOR)]:assert sha(p)==d
    for name,d in m['tool_sha256'].items():assert sha(name)==d,name
    for p in [Path(m['modelsim_ini']['path']),OUT/'modelsim.ini',OUT/'inputs/tools/modelsim.ini']:assert sha(p)==m['modelsim_ini']['sha256']
    assert closure(OUT/'inputs/project',m['compile_sources'])==m['include_dependencies']
    assert json.loads((OUT/'input_identity_after.json').read_text(encoding='utf-8'))==m['project_sha256']
    evidence=json.loads((OUT/'evidence_sha256.json').read_text(encoding='utf-8'))
    for n,d in evidence.items():assert sha(OUT/n)==d,n
    before=json.loads((OUT/'git_before.json').read_text(encoding='utf-8'))
    after=json.loads((OUT/'git_after.json').read_text(encoding='utf-8'))
    assert before==after
    commands={n:json.loads((OUT/(n+'.command.json')).read_text(encoding='utf-8')) for n in
              ['vlib','compile','sccb','sccb_check','faults','faults_check','soc']}
    assert all(c['returncode']==0 and not c['timed_out'] for c in commands.values())
    comp=(OUT/'compile.stdout.log').read_text(encoding='utf-8')
    modules=re.findall(r'-- Compiling module (\w+)',comp)
    assert sorted(modules)==sorted(m['compiled_module_names']+['GTP_GRS','GTP_DRM36K_E1','GTP_APM_E2'])
    assert 'Errors: 0, Warnings: 0' in comp
    # Import the *frozen execution* checker, disabling bytecode writes in the failed copy.
    sys.dont_write_bytecode=True
    sys.path.insert(0,str(OUT/'inputs/project/sim/camera/key'))
    checker=importlib.import_module('check_evidence')
    passed={}
    for name,fn in [('sccb',checker.check_sccb),('faults',checker.check_faults)]:
        actual=fn(OUT)
        assert actual==json.loads((OUT/(name+'.checked.json')).read_text(encoding='utf-8'))
        text=(OUT/(name+'.transcript')).read_text(encoding='utf-8')
        assert 'Errors: 0,' in text
        passed[name]=actual
    # Independently replay the raw synthetic arbiter AW/W records, not just its PASS count.
    text=(OUT/'faults.transcript').read_text(encoding='utf-8')
    pending=None;aw=[0,0];w=[0,0]
    for line in text.splitlines():
        r=line.lstrip('# ').split()
        if not r:continue
        if r[0]=='ARBAW':
            cycle,ident,length,address,cv,mv=int(r[1]),int(r[2]),int(r[3]),int(r[4],16),int(r[5]),int(r[6])
            owner=ident-1
            assert pending is None and owner in (0,1) and length==(0 if owner else 3)
            assert address==(0x400000+aw[1]*8 if owner else 0x100+aw[0]*32)
            pending=[owner,length+1,cycle];aw[owner]+=1
        elif r[0]=='ARBW':
            cycle,owner,value,mask=int(r[1]),int(r[2]),int(r[3],16),int(r[4],16)
            assert pending and pending[0]==owner and cycle>=pending[2]
            word=(0xd0000000 if owner else 0xc0000000)+w[owner]
            assert value==int.from_bytes(word.to_bytes(4,'little')*8,'little')
            assert mask==(0xffffffff if owner else 0x5555aaaa)
            w[owner]+=1;pending[1]-=1
            if not pending[1]:pending=None
    assert pending is None and aw==[6,6] and w==[24,6]
    soc=(OUT/'soc.transcript').read_text(encoding='utf-8')
    assert 'RESULT: FAIL CPU trap' in soc and 'Time: 3290461 ps' in soc
    assert not any(s in soc for s in ['CPU_CRC','DVP_FRAME_BEGIN','RESULT: PASS camera_soc'])
    assert not (OUT/'soc.checked.json').exists()
    assert all((OUT/n).stat().st_size==0 for n in ['bus.log','cpu.log','dvp.log'])
    # Static decode proof from sealed design, with the same configured top parameters.
    frozen=OUT/'inputs/project'
    top=(frozen/'sim/camera/key/tb_soc.sv').read_text(encoding='utf-8')
    soc_top=(frozen/'myriscv/soc_top.v').read_text(encoding='utf-8')
    board=(frozen/'myriscv/soc_ddr3_top.v').read_text(encoding='utf-8')
    inst=(frozen/'myriscv/inst_bus_interconnect.v').read_text(encoding='utf-8')
    assert '.RESET_PC(32\'h40000000)' in top
    assert 'parameter [31:0] INST_ROM_BASE = RESET_PC' in soc_top
    assert 'parameter [31:0] DATA_RAM_BASE = RESET_PC' in soc_top
    assert '.INST_ROM_BASE(' not in board and '.DATA_RAM_BASE(' not in board
    assert '&& !rom_select' in inst and '.ROM_BASE      (INST_ROM_BASE)' in soc_top
    assert 'defparam dut.u_soc.INST_ROM_BASE' not in top and 'defparam dut.u_soc.DATA_RAM_BASE' not in top
    pc=0x40000000;mask=0xffffc000
    def instruction_target(address,rom_base):
        if (address&mask)==(rom_base&mask):return 'ROM'
        if (address&0xc0000000)==0x40000000:return 'DDR'
        return 'FAULT'
    def table_target(address,ram_base):
        if (address&mask)==(ram_base&mask):return 'RAM'
        if (address&0xc0000000)==0x40000000:return 'DDR'
        return 'FAULT'
    assert instruction_target(pc,pc)=='ROM' and instruction_target(pc,0)=='DDR'
    assert table_target(0x1000,pc)=='FAULT' and table_target(0x1000,0)=='RAM'
    result=dict(status='CAMERA_SCCB_FAULTS_RAW_REVIEW_PASS_SOC_BLOCKED_BY_TEST_BOOT_MAP',date='2026-10-15',
        manifest_sha256=sha(OUT/'inputs.json'),inputs_verified=counts,vendor=3,tools=4,include_edges=5,
        compiled_modules=len(modules),git_before_after_identical=True,evidence_hashes_verified=len(evidence),
        commands={n:{k:c[k] for k in ['returncode','timed_out','elapsed_seconds']} for n,c in commands.items()},
        functional_pass=passed,independent_arbiter_raw_replay=dict(AW=aw,W=w),
        warning_counts={n:dict(collections.Counter(re.findall(r'\*\* Warning: \(([^)]+)\)',(OUT/(n+'.transcript')).read_text(encoding='utf-8')))) for n in ['sccb','faults','soc']},
        soc_failure=dict(time_ps=3290461,native_exit=0,raw_fatal=True,bus_bytes=0,cpu_bytes=0,dvp_bytes=0,
            trap_PC='NOT_RECORDED',trap_cause='NOT_RECORDED',trap_tval='NOT_RECORDED',
            classification='Definite TB address-map error invalidates intended DDR CPU program; exact historical trap instruction is unavailable',
            configured_reset_pc='40000000',effective_ROM_base='40000000',effective_RAM_base='40000000',
            intended_ROM_base='00000000',intended_RAM_base='00000000',first_instruction_target='ROM, not DDR',
            intended_CRC_table_address='00001000',old_CRC_table_address_mapped=False),
        next_step='TB-only override ROM/RAM bases to zero; add boot/trap diagnostics; reuse sccb/faults and execute only SoC in a new sealed directory',
        RTL_failure_demonstrated=False,RTL_modified=False,HDL_rerun_by_review=False,PDS='NOT_RUN',board='NOT_RUN',
        evidence_sha256={p.relative_to(ROOT).as_posix():sha(p) for p in OUT.iterdir() if p.is_file()})
    (HERE/'review.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:result[k] for k in ['status','inputs_verified','functional_pass','independent_arbiter_raw_replay','soc_failure']},ensure_ascii=False,indent=2))

if __name__=='__main__':main()
