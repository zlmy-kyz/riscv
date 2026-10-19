"""Preserve frozen CoreMark bytes/addresses; link only the post-ROI reader at 0x40008000."""
from pathlib import Path
import argparse
import json
import re
import subprocess
from perf27_fixed_software import ROOT,HERE,DEFAULT_FIXED_TAG,EXTENSION_BASE,elf_sections,audit,require_manifest,sha
from zmmul300_software import require_manifest as require_frozen_manifest

TOOL = ROOT/'xpack-riscv-none-elf-gcc-15.2.0-1/bin'
def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--tag',default=DEFAULT_FIXED_TAG)
    a = p.parse_args()
    assert re.fullmatch('[a-z0-9_-]+',a.tag)
    folder = HERE/'build'/a.tag
    assert not folder.exists(), 'Preserve old output; choose a new tag'
    protected = {p.relative_to(ROOT).as_posix():sha(p)
        for tag in ['measure_zmmul300_20261013_a','measure_perf27_20261018_a']
        for p in (HERE/'build'/tag).rglob('*') if p.is_file()}
    for n in ['mycpu_sync','dual_sram_to_pango_ddr_bridge','simple_mmio','soc_top']:
        p = ROOT/f'myriscv/{n}.v'; protected[p.relative_to(ROOT).as_posix()] = sha(p)
    outputs = {}
    for mode in ['performance','validation']:
        name = mode+'_300'
        frozen_path = HERE/f'build/measure_zmmul300_20261013_a/{name}/manifest.json'
        old = require_frozen_manifest(frozen_path)
        old_elf = ROOT/old['elf_path']
        sections = elf_sections(old_elf)
        out = folder/name; out.mkdir(parents=True)
        patch = old['symbols']['perf_dump']-old['sections']['.text']['address']
        assembly = ['.option norelax', '.section .baseline_text,"ax",@progbits',
            f'.incbin "baseline_text.bin",0,{patch}',
            'lui t0,%hi(perf27_dump)', 'jalr zero,%lo(perf27_dump)(t0)',
            f'.incbin "baseline_text.bin",{patch+8},{sections[".text"]["size"]-patch-8}']
        for section,blob in [('.text','text'),('.rodata','rodata'),('.data','data')]:
            (out/f'baseline_{blob}.bin').write_bytes(sections[section]['data'])
            if blob != 'text':
                assembly += [f'.section .baseline_{blob},"a{("w" if blob=="data" else "")}",@progbits',
                             f'.incbin "baseline_{blob}.bin"']
        assembly += ['.section .baseline_bss,"aw",@nobits',f'.space {sections[".bss"]["size"]}']
        (out/'baseline.S').write_text('\n'.join(assembly)+'\n',encoding='utf-8')
        # Absolute aliases retain local as well as global baseline names in the
        # final ELF. The measured instructions/data are the original incbins.
        aliases = '\n'.join(f'{n} = 0x{v:08x};' for n,v in old['symbols'].items())
        script = f'''OUTPUT_ARCH(riscv)
ENTRY(_start)
{aliases}
SECTIONS {{
  .text 0x{sections['.text']['address']:08x} : {{ KEEP(*(.baseline_text)) }}
  .rodata 0x{sections['.rodata']['address']:08x} : {{ KEEP(*(.baseline_rodata)) }}
  .data 0x{sections['.data']['address']:08x} : {{ KEEP(*(.baseline_data)) }}
  .bss 0x{sections['.bss']['address']:08x} (NOLOAD) : {{ KEEP(*(.baseline_bss)) }}
  .perf27_text 0x{EXTENSION_BASE:08x} : {{ *(.text .text.*) }}
  .perf27_rodata : ALIGN(8) {{ *(.rodata .rodata.* .srodata .srodata.*) }}
  .perf27_data : ALIGN(8) {{ BYTE(0); . = ALIGN(8); *(.data .data.* .sdata .sdata.*) *(.bss .bss.* .sbss .sbss.* COMMON) }}
  __perf27_end = .;
  ASSERT(__perf27_end <= 0x4000f000,"Reader overlaps the frozen 4KiB stack")
  ASSERT(ADDR(.bss)+SIZEOF(.bss) <= 0x{EXTENSION_BASE:08x},"Reader overlaps frozen workspace")
  /DISCARD/ : {{ *(.comment) *(.eh_frame .eh_frame.*) }}
}}
'''
        (out/'linker_fixed.ld').write_text(script,encoding='utf-8')
        commands = []
        def run(tool,args,log):
            argv = [str(TOOL/f'riscv-none-elf-{tool}.exe'),*map(str,args)]
            result = subprocess.run(argv,cwd=out,capture_output=True,text=True,timeout=60)
            (out/log).write_text(result.stdout+result.stderr,encoding='utf-8')
            commands.append(dict(argv=argv,cwd=str(out),exit_code=result.returncode,log=log))
            (out/'commands.json').write_text(json.dumps(commands,indent=2)+'\n',encoding='utf-8')
            assert result.returncode == 0, result.stdout+result.stderr
        flags = ['-march=rv32i_zmmul','-mabi=ilp32','-Os','-g','-Wall','-Wextra','-ffreestanding',
            '-fno-builtin','-fno-pic','-fno-pie','-msmall-data-limit=0','-ffunction-sections',
            '-fdata-sections','-fstack-usage','-I',str(ROOT/'tests/bsp_workflow'),'-I',str(HERE),
            '-DCLOCKS_PER_SEC=93750000','-Dperf_dump=perf27_dump']
        inputs = [HERE/'perf27.c',HERE/'perf.h',ROOT/'tests/bsp_workflow/bsp.h',
            HERE/'perf27_fixed_software.py',Path(__file__),frozen_path,old_elf,ROOT/old['bin_path'],
            out/'baseline.S',out/'linker_fixed.ld',*[out/f'baseline_{n}.bin' for n in ['text','rodata','data']]]
        before = {p.relative_to(ROOT).as_posix():sha(p) for p in inputs}
        run('gcc',flags+['-c',HERE/'perf27.c','-o','reader.o'],'reader_compile.log')
        run('gcc',['-march=rv32i_zmmul','-mabi=ilp32','-g','-c','baseline.S','-o','baseline.o'],'baseline_compile.log')
        elf = out/'program.elf'; binary = out/'program.bin'
        run('gcc',['-march=rv32i_zmmul','-mabi=ilp32','-nostdlib','-nostartfiles',
            '-Wl,--no-relax','-Wl,--build-id=none','-Wl,--gc-sections','-T','linker_fixed.ld',
            '-Wl,-Map=program.map','baseline.o','reader.o','-o',elf,'-lgcc'],'link.log')
        for tool,args,log in [('objcopy',['-O','binary',elf,binary],'objcopy.log'),
            ('readelf',['-h','-A','-l','-S',elf],'program.readelf.txt'),
            ('objdump',['-d',elf],'program.dis'),('nm',['-n',elf],'symbols.txt'),('size',[elf],'size.txt')]:
            run(tool,args,log)
        info = audit(elf,binary,'coremark',mode,300)
        assert all(sha(ROOT/n)==h for n,h in before.items())
        (out/'manifest.json').write_text(json.dumps(info,indent=2)+'\n',encoding='utf-8')
        (out/'build_receipt.json').write_text(json.dumps(dict(
            status='PERF27_FIXED_LAYOUT_BUILD_AND_STATIC_IDENTITY_PASS',source_sha256=before,info=info),indent=2)+'\n',encoding='utf-8')
        require_manifest(out/'manifest.json')
        outputs[name] = info
        print('FIXED_LAYOUT_STATIC_PASS',name,info['bytes'],info['layout_proof'])
    assert all(sha(ROOT/n)==h for n,h in protected.items())
    (folder/'build_review.json').write_text(json.dumps(dict(
        status='PERF27_FIXED_LAYOUT_STATIC_PASS_PENDING_RUNTIME',outputs=outputs,
        protected_sha256=protected,all_original_symbols_and_sections_preserved=True,
        original_loaded_bytes_changed_only_at_post_ROI_perf_dump_entry=8,
        extension_base=EXTENSION_BASE,HDL_started=False,PDS_started=False,serial_opened=False),indent=2)+'\n',encoding='utf-8')
if __name__ == '__main__': main()
