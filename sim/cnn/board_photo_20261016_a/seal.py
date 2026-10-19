"""New software seal, preserving all prior successful inputs and board evidence."""
import hashlib,json,shutil,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2]
sys.path.insert(0,str(ROOT/'tools/cnn_digits_photo'))
import run as pc,reference
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_text(encoding='utf-8'))
def save(p,v):p.write_text(json.dumps(v,indent=2)+'\n',encoding='utf-8')
def main():
    frozen=HERE/'sealed_photo_20261016_a';ready=HERE/'ready_review.json';gate=pc.RELEASE
    assert not frozen.exists() and not ready.exists() and not gate.exists()
    m=pc.image(pc.DEFAULT);model=reference.load(pc.MODEL);checked=HERE/'checks_01/review.json';review=read(checked)
    assert review['status']=='SOURCE_EXPORT_SOFTWARE_CHECKS_PASS_NOT_HDL_NOT_BOARD'
    for n,h in review['input_sha256'].items():assert sha(ROOT/n)==h,n
    for n,h in review['artifact_sha256'].items():assert sha(checked.parent/n)==h,n
    for n,h in read(HERE/'parent_identity.json').items():assert sha(ROOT/n)==h,('changed parent',n)
    historical={}
    for manifest in [ROOT/'tests/cnn_digits_diag/build/diag_20261016_c/manifest.json',ROOT/'tests/camera_preprocess_photo/build/photo_20261015_d/manifest.json']:
        old=read(manifest)
        for n,h in old['source_sha256'].items():assert sha(ROOT/n)==h,('historical source changed',n)
        for k in ('bin','elf'):assert sha(ROOT/old[k+'_path'])==old[k+'_sha256']
        historical[manifest.relative_to(ROOT).as_posix()]=sha(manifest)
    for folder in sorted((ROOT/'sim/cnn/board').glob('diag_20261016_*')):
        r=read(folder/'result.json')
        for n,h in r['file_sha256'].items():assert sha(folder/n)==h,('historical evidence changed',n)
        historical[(folder/'result.json').relative_to(ROOT).as_posix()]=sha(folder/'result.json')
    pclk=ROOT/'sim/cnn/pclk_review_20261016_a/review.json';pclk_info=read(pclk)
    assert pclk_info['status']=='EXISTING_PDS_PCLK_STA_MET_AND_ALL_10_DVP_IFF_PACKED'
    original=ROOT/'sim/cnn/board_diag_20261016_a/ready_review.json';design=read(original)['design_sha256']
    for n,h in design.items():assert sha(ROOT/n)==h,('RTL changed',n)
    inputs={ROOT/n for n in m['source_sha256']}
    inputs.update([pc.DEFAULT,checked,pclk,original,HERE/'parent_identity.json',Path(__file__),ROOT/'tests/cnn_digits_photo/README.md'])
    inputs.update(HERE.glob('*.py'));inputs.update((ROOT/'tests/cnn_digits_photo/build/photo_20261016_a').glob('*'))
    project=frozen/'project';project.mkdir(parents=True);hashes={}
    for p in sorted(inputs):
        if not p.is_file():continue
        n=p.relative_to(ROOT).as_posix();q=project/n;q.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,q);hashes[n]=sha(q);assert sha(p)==hashes[n]
    save(frozen/'manifest.json',dict(status='SEALED_SOFTWARE_ONLY_NOT_FULL_HDL_PACKAGE',sha256=hashes,
        design_snapshot_reused='sim/cnn/board_diag_20261016_a/sealed_diag_20261016_c',design_sha256=design))
    r=dict(status='SOURCE_PHOTO_SOFTWARE_READY_USER_BOARD_FIRST_NOT_BOARD_PASS',firmware_sha256=m['bin_sha256'],
        firmware_bytes=m['bytes'],firmware_manifest=pc.DEFAULT.relative_to(ROOT).as_posix(),model_id=model['meta']['model_id_hex'],
        model_crc=f"{model['meta']['load_crc32']:08x}",model_load_sha256=sha(pc.MODEL/'load_words.bin'),
        source_bytes=1843200,RGB96_bytes=27648,same_frame_held_until_both_exports=True,
        offline_review_sha256=sha(checked),offline_review=checked.relative_to(ROOT).as_posix(),
        frozen_manifest_sha256=sha(frozen/'manifest.json'),timing_review_sha256=sha(pclk),historical_unchanged=historical,
        design_unchanged=True,IP_PDS_unchanged=True,PDS_started=False,HDL_run=False,key_HDL='NOT_COMPLETED',board='NOT_RUN',
        timing='EXISTING_REPORT_MET_BOARD_PHASE_UNMEASURED',scope='One same-frame source/PP all-byte check and diagnostic CNN 10-score comparison only')
    save(ready,r)
    save(gate,dict(status='USER_AUTHORIZED_BOARD_PHOTO_DIAGNOSTIC_EXISTING_STA_MET',firmware_sha256=m['bin_sha256'],
        ready_review=ready.relative_to(ROOT).as_posix(),ready_review_sha256=sha(ready),source_bytes=1843200,
        model_id=model['meta']['model_id_hex'],PDS_or_new_bitstream_required=False,board='NOT_RUN',key_HDL='NOT_COMPLETED'))
    assert not (ROOT/'sim/cnn/board/photo_20261016_01').exists()
    print(json.dumps(dict(status=r['status'],firmware_sha256=m['bin_sha256'],inputs=len(hashes),old_inputs_unchanged=True),indent=2))
if __name__=='__main__':main()
