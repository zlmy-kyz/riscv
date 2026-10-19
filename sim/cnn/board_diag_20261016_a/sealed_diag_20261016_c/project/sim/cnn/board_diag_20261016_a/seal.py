"""Seal software-only board-first diagnostic after offline checks. No hardware tools."""
import hashlib,json,re,shutil,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2]
sys.path.insert(0,str(ROOT/'tools/cnn_digits_diag'))
import reference,run as pc
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def save(p,v):p.write_text(json.dumps(v,indent=2)+'\n',encoding='utf-8')
def main():
    frozen=HERE/'sealed_diag_20261016_c';ready=HERE/'ready_review.json';release=pc.RELEASE
    assert not frozen.exists() and not ready.exists() and not release.exists(),'new seal identity required'
    m=pc.image(pc.DEFAULT);model=reference.load(pc.MODEL);checked=HERE/'checks_02/review.json';r=read(checked)
    assert r['status']=='SOFTWARE_OFFLINE_CHECKS_PASS_NOT_HDL_NOT_BOARD'
    for n,h in r['input_sha256'].items():assert sha(ROOT/n)==h,('changed checked input',n)
    for n,h in r['artifact_sha256'].items():assert sha(checked.parent/n)==h,('changed raw check evidence',n)
    parent=read(HERE/'parent_identity.json')
    for n,h in parent.items():assert sha(ROOT/n)==h,('historical scaffold changed',n)
    photo=read(ROOT/'tests/camera_preprocess_photo/build/photo_20261015_d/manifest.json')
    for k in ('bin','elf'):assert sha(ROOT/photo[k+'_path'])==photo[k+'_sha256']
    for n,h in photo['source_sha256'].items():assert sha(ROOT/n)==h,('historical successful software changed',n)
    prior=ROOT/'sim/camera_preprocess/board/photo_20261015_01'
    previous=read(prior/'result.json')
    for n,h in previous.get('file_sha256',{}).items():assert sha(prior/n)==h,('historical board evidence changed',n)
    timing=read(ROOT/'sim/cnn/timing_20261016_a/review.json')
    baseline=read(ROOT/'sim/cnn/timing_20261016_a/before_manifest.json')
    expected={n:h for n,h in baseline.items() if n.startswith('myriscv')}
    expected.update(timing['after_sha256']);assert len(expected)==39
    design={n.replace('\\','/'):sha(ROOT/n) for n in expected}
    for n,h in expected.items():assert sha(ROOT/n)==h,('design differs from latest timing repair',n)
    # Snapshot the source include closure, but do not present this as a vendor HDL run package.
    queue=[ROOT/n for n in design];seen=set()
    while queue:
        p=queue.pop()
        if p in seen:continue
        seen.add(p)
        for n in re.findall(r'`include\s+"([^"]+)"',p.read_text(encoding='utf-8')):
            q=p.parent/n;assert q.exists(),('unclosed design include',q);queue.append(q)
    design={p.relative_to(ROOT).as_posix():sha(p) for p in sorted(seen)}
    inputs={ROOT/n for n in m['source_sha256']}
    inputs.update(ROOT/n for n in design)
    inputs.update([pc.DEFAULT,checked,HERE/'parent_identity.json',ROOT/'sim/cnn/timing_20261016_a/review.json',
        ROOT/'sim/cnn/timing_20261016_a/before_manifest.json',ROOT/'doc/cnn/digits10_int8_v1.json',
        ROOT/'doc/cnn/数字CNN整网与SoC_ABI1_2026-10-16.md',ROOT/'doc/cnn/单字符数字识别_INT8首版合同_2026-10-16.md',
        ROOT/'tests/cnn_digits_diag/README.md',Path(__file__)])
    inputs.update(HERE.glob('*.py'));inputs.update((ROOT/'tests/cnn_digits_diag/build/diag_20261016_c').glob('*'))
    project=frozen/'project';project.mkdir(parents=True)
    hashes={}
    for p in sorted(inputs):
        if not p.is_file():continue
        name=p.relative_to(ROOT).as_posix();target=project/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,target);hashes[name]=sha(p)
        assert sha(target)==hashes[name]
    save(frozen/'manifest.json',dict(status='SEALED_SOFTWARE_INPUT_NOT_FULL_HDL_PACKAGE',sha256=hashes,
        firmware_sha256=m['bin_sha256'],model_id=model['meta']['model_id_hex'],model_load_sha256=sha(pc.MODEL/'load_words.bin')))
    receipt=dict(status='SOFTWARE_READY_USER_BOARD_FIRST_TIMING_PENDING_NOT_HW_PASS',
        user_authorization='用户授权板优先诊断、关键HDL未完成、时序待确认',
        firmware_manifest=pc.DEFAULT.relative_to(ROOT).as_posix(),firmware_sha256=m['bin_sha256'],firmware_bytes=m['bytes'],
        model_id=model['meta']['model_id_hex'],model_crc=f"{model['meta']['load_crc32']:08x}",model_load_words=6222,
        model_load_sha256=sha(pc.MODEL/'load_words.bin'),offline_review=checked.relative_to(ROOT).as_posix(),offline_review_sha256=sha(checked),
        offline_scope='7 patterns C int64/Python wide all reference tensors; actual firmware C/native device; no RISC-V CPU execution',
        source_snapshot=frozen.relative_to(ROOT).as_posix(),source_manifest_sha256=sha(frozen/'manifest.json'),design_sha256=design,
        latest_repairs_match_original_receipt=True,design_modified_by_this_step=False,IP_PDS_modified_by_this_step=False,
        historical_success_bin_unchanged=photo['bin_sha256'],historical_board_result_sha256=sha(prior/'result.json'),
        HDL='NOT_COMPLETED',Full_Boot='NOT_RUN',timing='PENDING_USER_CONFIRMATION',board='NOT_RUN',PDS_started=False,
        retries=0,success_scope='One actual RGB96 input and this nontrained package, 10 signed scores plus argmax only',
        excluded=['hardware layer-by-layer','all exceptions/concurrency','trained digit accuracy','timing signoff'])
    save(ready,receipt)
    gate=dict(status='USER_AUTHORIZED_BOARD_DIAGNOSTIC_TIMING_PENDING',firmware_sha256=m['bin_sha256'],
        firmware_manifest=pc.DEFAULT.relative_to(ROOT).as_posix(),model_id=model['meta']['model_id_hex'],model_crc=receipt['model_crc'],
        ready_review=ready.relative_to(ROOT).as_posix(),ready_review_sha256=sha(ready),
        user_must_generate_and_download_latest_RAM_plus1_DVP_IO_repaired_bitstream=True,
        PDS_or_bitstream_receipt_required=False,key_HDL='NOT_COMPLETED',timing='PENDING_USER_CONFIRMATION',board='NOT_RUN',
        input_lock='software/package SHA only; no claim of hardware functional PASS')
    save(release,gate)
    print(json.dumps(dict(status=receipt['status'],firmware_sha256=m['bin_sha256'],model_id=receipt['model_id'],model_crc=receipt['model_crc'],sealed_inputs=len(hashes),design_sources_with_includes=len(design)),indent=2))
if __name__=='__main__':main()
