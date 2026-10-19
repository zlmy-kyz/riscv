"""Audit frozen measured image plus an isolated post-ROI PERF27 reader."""
from pathlib import Path
import inspect
import json
import struct
from zmmul_software import ROOT, HERE, FLAGS, legacy, zmmul_legal, sha, multiply_sites
from zmmul300_software import require_manifest as require_frozen_manifest

DEFAULT_FIXED_TAG = 'measure_perf27_fixed_20261018_a'
EXTENSION_BASE = 0x40008000
LAYOUT_SCHEMA = 'FROZEN_LAYOUT_PLUS_PERF27_V1'

# Retain the original independent ELF/ISA checks. Only explicitly admit the
# three extra sections and the frozen BSS below the separately loaded reader.
code = inspect.getsource(legacy.audit)
guard = "for i in range(0,len(code),4):assert isa.legal_instruction(int.from_bytes(code[i:i+4],'little')),(name,i)"
sections = "assert name in ('.text','.rodata','.data','.image_tail','.bss'),name"
bss = "assert sections['.bss']['address']>=((BASE+len(payload)+3)&~3)"
assert code.count(guard) == code.count(sections) == code.count(bss) == code.count('iterations in (1,60)') == 1
code = code.replace(guard, "for i in range(0,len(code),4):assert (isa.legal_instruction(int.from_bytes(code[i:i+4],'little')) or zmmul_legal(int.from_bytes(code[i:i+4],'little'))),(name,i)")
code = code.replace(sections, "assert name in ('.text','.rodata','.data','.image_tail','.bss','.perf27_text','.perf27_rodata','.perf27_data'),name")
code = code.replace(bss, "assert sections['.bss']['address']+sections['.bss']['size']<=sections['.perf27_text']['address']")
code = code.replace('iterations in (1,60)', 'iterations == 300')
namespace = dict(legacy.__dict__, zmmul_legal=zmmul_legal)
exec(compile(code, '<frozen_image_plus_isolated_reader_ELF_ISA_audit>', 'exec'), namespace)
layout_audit = namespace['audit']

def elf_sections(path):
    raw = Path(path).read_bytes()
    offset = struct.unpack_from('<I',raw,32)[0]
    size,count,names_index = struct.unpack_from('<HHH',raw,46)
    headers = [struct.unpack_from('<10I',raw,offset+i*size) for i in range(count)]
    names = raw[headers[names_index][4]:headers[names_index][4]+headers[names_index][5]]
    result = {}
    for h in headers:
        name = names[h[0]:names.index(0,h[0])].decode()
        if h[2] & 2 and h[5]:
            result[name] = dict(address=h[3], size=h[5], type=h[1],
                data=raw[h[4]:h[4]+h[5]] if h[1] != 8 else None)
    return result

def audit(elf,binary,kind,mode=None,iterations=None):
    info = layout_audit(elf,binary,kind,mode,iterations)
    frozen_path = HERE/f'build/measure_zmmul300_20261013_a/{mode}_300/manifest.json'
    old = require_frozen_manifest(frozen_path)
    original = (ROOT/old['bin_path']).read_bytes()
    payload = Path(binary).read_bytes()
    patch = old['symbols']['perf_dump']-old['base']
    assert original[:patch] == payload[:patch]
    assert original[patch+8:] == payload[patch+8:len(original)]
    first,second = struct.unpack_from('<II',payload,patch)
    assert first & 0xfff == (5<<7)|0x37  # lui t0,hi(reader)
    assert second & 0xfffff == (5<<15)|0x67  # jalr zero,lo(reader)(t0)
    low = second>>20
    if low & 0x800: low -= 0x1000
    destination = ((first & 0xfffff000)+low) & 0xffffffff
    assert destination == info['symbols']['perf27_dump']
    assert destination >= EXTENSION_BASE
    for n,v in old['symbols'].items():
        assert info['symbols'].get(n) == v, ('Frozen symbol moved',n,v,info['symbols'].get(n))
    for n in ['.text','.rodata','.data','.bss']:
        assert info['sections'][n] == old['sections'][n], ('Frozen section moved',n)
    assert info['sections']['.perf27_text']['address'] == EXTENSION_BASE
    assert info['sections']['.perf27_data']['type'] == 1, 'Reader scratch must be loaded bytes, not uninitialized BSS'
    ordered = sorted(info['sections'].items(),key=lambda pair:pair[1]['address'])
    for (_,a),(_,b) in zip(ordered,ordered[1:]):
        assert a['address']+a['size'] <= b['address'], 'Sections overlap'
    assert max(s['address']+s['size'] for s in info['sections'].values()) <= old['symbols']['__stack_bottom']
    a = old['sections']['.bss']['address']-old['base']
    b = a+old['sections']['.bss']['size']
    assert payload[a:b] == bytes(b-a), 'Frozen BSS bytes in flat image must be zero'
    architecture = legacy.re.findall(r'Tag_RISCV_arch:\s*"([^"]+)"',Path(elf).with_name('program.readelf.txt').read_text())
    assert len(architecture)==1 and legacy.re.fullmatch(r'rv32i\d+p\d+_zmmul\d+p\d+',architecture[0])
    assert int.from_bytes(payload[old['symbols']['seed4_volatile']-old['base']:old['symbols']['seed4_volatile']-old['base']+4],'little') == iterations
    ref = frozen_path.with_name('reference.txt')
    return dict(info, isa='rv32i_zmmul', compiler_flags=FLAGS, elf_arch=architecture[0],
        multiply_sites=multiply_sites(elf), counter_schema='PERF27_V1',counter_count=27,
        layout_schema=LAYOUT_SCHEMA, frozen_manifest_path=frozen_path.relative_to(ROOT).as_posix(),
        frozen_manifest_sha256=sha(frozen_path), reference_path=ref.relative_to(ROOT).as_posix(), reference_sha256=sha(ref),
        comparison_kind='FROZEN_TIMED_CODE_AND_DATA_ADDRESSES_BYTES_PRESERVED_POST_ROI_TRAMPOLINE_ONLY',
        layout_proof=dict(frozen_symbols=len(old['symbols']),
            original_loaded_bytes=len(original), all_original_bytes_preserved_except=8,
            post_ROI_patch_address=old['symbols']['perf_dump'], reader_entry=destination,
            reader_segment_base=EXTENSION_BASE, frozen_BSS_zero_loaded=True),
        scope='All executable sections ISA-whitelisted; no CoreMark relink/recompile; post-ROI extension only')

def require_manifest(path):
    path = Path(path)
    info = json.loads(path.read_text(encoding='utf-8'))
    assert info['layout_schema'] == LAYOUT_SCHEMA
    assert sha(ROOT/info['elf_path']) == info['elf_sha256'] and sha(ROOT/info['bin_path']) == info['bin_sha256']
    assert audit(ROOT/info['elf_path'],ROOT/info['bin_path'],info['kind'],info['mode'],info['iterations']) == info
    receipt = json.loads(path.with_name('build_receipt.json').read_text(encoding='utf-8'))
    assert receipt['info'] == info
    assert all(sha(ROOT/n) == h for n,h in receipt['source_sha256'].items()), 'Build source changed; use a new fixed-layout build'
    return info
