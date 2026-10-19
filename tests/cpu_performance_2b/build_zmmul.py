"""Build independent Zmmul 1/120-iteration P/V BINs, leaving all RV32I inputs untouched."""
from pathlib import Path
import inspect
import json
import re
import subprocess
from zmmul_software import ROOT, HERE, BUILD_DIR, FLAGS, audit, load, sha


def main():
    assert not BUILD_DIR.exists(),'Preserve existing Zmmul outputs; no automatic rebuild'
    old=HERE/'build/measure_20261011_120'
    receipt=json.loads((old/'performance_120/build_receipt.json').read_text())
    protected={n:h for n,h in receipt['source_sha256'].items() if n!='tests/cpu_performance_2b/build/measure_20261011_120/performance_120/core_portme.c'}
    for p in old.rglob('*'):
        if p.is_file():protected[p.relative_to(ROOT).as_posix()]=sha(p)
    assert all(sha(ROOT/n)==h for n,h in protected.items()),'Old sources/binaries changed'
    builder=load('zmmul_reference_builder',HERE/'build.py')
    build_code=inspect.getsource(builder.build)
    assert build_code.count('-march=rv32i')==2
    build_code=build_code.replace('-march=rv32i','-march=rv32i_zmmul')
    namespace=dict(builder.__dict__,audit=audit,__file__=str(Path(__file__).resolve()))
    exec(compile(build_code,'<same_build_recipe_except_Zmmul_ISA>','exec'),namespace)
    tools=ROOT/'xpack-riscv-none-elf-gcc-15.2.0-1/bin'
    compiler=tools/'riscv-none-elf-gcc.exe'
    libraries={}
    for march in ['rv32i','rv32i_zmmul']:
        p=subprocess.run([str(compiler),'-march='+march,'-mabi=ilp32','-print-libgcc-file-name'],capture_output=True,text=True,check=True,timeout=20)
        libraries[march]=p.stdout.strip()
    assert libraries['rv32i']==libraries['rv32i_zmmul'],'Keep the same RV32I libgcc implementation'
    outputs={}
    for mode in ['performance','validation']:
        for iterations in [1,120]:
            name=f'{mode}_{iterations}';namespace['build'](name,BUILD_DIR.name)
            out=BUILD_DIR/name;info=json.loads((out/'manifest.json').read_text())
            ref=old/f'{mode}_120/reference.txt' if iterations==120 else ROOT/f'tools/uart_loader/candidates/bsp_workflow/references/{mode}_1.txt'
            reference=ref.read_text().replace('-march=rv32i ','-march=rv32i_zmmul ')
            (out/'reference.txt').write_text(reference,encoding='utf-8')
            # Decode disassembly regions independently of the compiler's source claims.
            region='';hot={};all_counts={}
            for line in (out/'program.dis').read_text().splitlines():
                label=re.fullmatch(r'[0-9a-f]+ <(.+)>:',line)
                if label:region=label[1]
                inst=re.search(r'^\s*([0-9a-f]+):\s+[0-9a-f]{8}\s+(mul|mulh|mulhsu|mulhu)\s',line)
                if inst:
                    all_counts[inst[2]]=all_counts.get(inst[2],0)+1
                    if region.startswith('matrix_mul_'):hot[region]=hot.get(region,0)+1
            assert sum(hot.values())>0 and sum(all_counts.values())==len(info['multiply_sites'])
            assert (out/'core_portme.c').read_bytes()==(old/f'{mode}_120/core_portme.c').read_bytes()
            outputs[name]=dict(bin_sha256=info['bin_sha256'],elf_sha256=info['elf_sha256'],bytes=info['bytes'],
                               multiply_static_counts=all_counts,matrix_static_multiply_sites=hot,CRC='PENDING_REAL_CPU_SIMULATION')
        one=BUILD_DIR/f'{mode}_1';fixed=BUILD_DIR/f'{mode}_120'
        a=json.loads((one/'manifest.json').read_text());b=json.loads((fixed/'manifest.json').read_text())
        assert a['sections']==b['sections'] and a['symbols']==b['symbols']
        raw=(one/'program.bin').read_bytes();new=(fixed/'program.bin').read_bytes();offset=a['symbols']['seed4_volatile']-a['base']
        assert len(raw)==len(new) and raw[:offset]==new[:offset] and raw[offset+4:]==new[offset+4:]
    assert all(sha(ROOT/n)==h for n,h in protected.items())
    final=dict(status='ZMMUL_SOFTWARE_BUILD_AND_ISA_AUDIT_PASS_CRC_SIM_PENDING',compiler_flags=FLAGS,
               algorithm_and_port_unchanged=True,old_protected_sha256=protected,outputs=outputs,
               short_vs_fixed_BIN_difference='Only seed4_volatile 1->120; same code/sections/symbols',
               source_sha256={n:sha(ROOT/n) for n in protected if '/build/' not in n},libgcc=libraries,
               old_native_CRC_reference_reused=True,HDL_started=False,PDS_started=False,serial_opened=False)
    (BUILD_DIR/'build_review.json').write_text(json.dumps(final,indent=2)+'\n',encoding='utf-8')
    print('ZMMUL_SOFTWARE_BUILT_CRC_PENDING',json.dumps(outputs,indent=2))


if __name__=='__main__':main()
