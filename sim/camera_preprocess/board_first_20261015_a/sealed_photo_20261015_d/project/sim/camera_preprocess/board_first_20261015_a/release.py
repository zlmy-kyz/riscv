"""Freeze reviewed single-photo software for explicit user-authorized board-first bringup."""
import hashlib,json,shutil,sys,datetime
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2]
sys.path.insert(0,str(ROOT/'tools/camera_preprocess_photo'))
import run as photo
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def load(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def main():
    gate=HERE/'board_release.json';receipt=HERE/'ready_review.json';sealed=HERE/'sealed_photo_20261015_d'
    assert not any(p.exists() for p in (gate,receipt,sealed))
    m=photo.image(photo.DEFAULT)
    assert m['bytes']==19780 and m['bin_sha256']=='8a7b1c57cce723753ff73fd6c62dd8f8a099d4f1522902bbb3bb0b4a933bb7b3'
    review=HERE/'checks_d/review.json';assert sha(review)=='afce2d6b0dc5b1a8cbb7cae4c82cb2c04a944e10d3d61112e960e6669302ee37'
    r=load(review);assert r['status']=='PHOTO_SOFTWARE_NATIVE_AND_WIRE_PASS_NOT_BOARD' and r['manifest_sha256']==sha(photo.DEFAULT)
    assert r['firmware_sha256']==m['bin_sha256'] and r['native_C_source_sha256']==sha(ROOT/'tests/camera_preprocess_photo/main.c')
    assert r['script_sha256']==sha(HERE/'check_software.py') and len(r['native_cases'])==13 and len(r['rejected'])==11
    design_path=ROOT/'sim/camera_preprocess/plan_20261015_a/design_inputs.json';design=load(design_path)
    assert sha(design_path)=='a21f061174e2e0bb1a56a25177c96e6de274d68455f273a7e8adfba6eeed5125'
    for group in ('design_sha256','protected_sha256'):
        for n,d in design[group].items():assert sha(ROOT/n)==d,n
    parent=load(HERE/'parent_software_identity.json')
    for n,d in parent.items():assert sha(ROOT/n)==d,('parent preparation changed',n)
    inputs=dict(m['source_sha256'])
    for p in (photo.DEFAULT,ROOT/m['bin_path'],ROOT/m['elf_path'],photo.DEFAULT.with_name('program.dat'),
              photo.DEFAULT.with_name('stack_depth.json'),HERE/'check_software.py',HERE/'prepare.py',Path(__file__),
              ROOT/'tests/camera_preprocess_photo/README.md',design_path,review,HERE/'parent_software_identity.json'):
        inputs[p.relative_to(ROOT).as_posix()]=sha(p)
    evidence={p.relative_to(HERE/'checks_d').as_posix():sha(p) for p in (HERE/'checks_d').rglob('*') if p.is_file()}
    sealed.mkdir()
    for n,d in inputs.items():
        dst=sealed/'project'/n;dst.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(ROOT/n,dst);assert sha(dst)==d
    ready=dict(status='PHOTO_SOFTWARE_REVIEW_PASS_BOARD_FIRST_READY_NOT_HARDWARE_PASS',
        reviewed_at_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        user_authorization=['先上板吧','可以新拍一张吗','执行,准备上板'],
        input_sha256=inputs,software_check_evidence_sha256=evidence,
        fixed_firmware=dict(bytes=m['bytes'],sha256=m['bin_sha256'],crc32=f"{m['crc32']:08x}",manifest_sha256=sha(photo.DEFAULT),path=m['bin_path']),
        design_manifest_sha256=sha(design_path),design_files_checked=len(design['design_sha256']),
        protected_files_checked=len(design['protected_sha256']),parent_preparation_files_unchanged=len(parent),
        native_cases=13,negative_cases=11,native_is_not_RTL=True,real_CPU_HDL='NOT_RUN',
        board='NOT_RUN',PDS='USER_CONFIRMED_TIMING_NO_REAUDIT',RTL_modified=False,serial_opened=False,
        deferred='Key HDL/fault/concurrency qualification deferred by explicit user board-first instruction; no key PASS invented',
        earlier_failures_preserved=['build/photo_20261015_a stack analysis rejected guarded error recursion',
            'checks_a MinGW host harness compilation','checks_b expected reason string mismatch'],
        board_command='python tools/camera_preprocess_photo/run.py --port COM9 --log-dir sim/camera_preprocess/board/photo_20261015_01')
    receipt.write_text(json.dumps(ready,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    g=dict(status='SOL_SOFTWARE_REVIEWED_USER_AUTHORIZED_BOARD_FIRST',firmware_sha256=m['bin_sha256'],
        firmware_manifest_sha256=sha(photo.DEFAULT),review_path=receipt.relative_to(ROOT).as_posix(),review_sha256=sha(receipt),
        HDL_key_status='NOT_RUN_DEFERRED_BY_USER',board='NOT_RUN',release_is_not_hardware_PASS=True)
    gate.write_text(json.dumps(g,indent=2)+'\n',encoding='utf-8')
    (sealed/'ready_review.json').write_bytes(receipt.read_bytes());(sealed/'board_release.json').write_bytes(gate.read_bytes())
    assert not (ROOT/'sim/camera_preprocess/board/photo_20261015_01').exists()
    print(json.dumps(dict(status=ready['status'],ready_sha256=sha(receipt),manifest_sha256=sha(photo.DEFAULT),
        input_files=len(inputs),software_evidence_files=len(evidence),gate_sha256=sha(gate)),indent=2))
if __name__=='__main__':main()
