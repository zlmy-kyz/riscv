"""Seal new PC-only colorbar entry, reusing fixed firmware and old design snapshot."""
import importlib.util,json,shutil
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2]
spec=importlib.util.spec_from_file_location('colorbar_seal_driver',ROOT/'tools/cnn_colorbar_photo/run.py')
pc=importlib.util.module_from_spec(spec);spec.loader.exec_module(pc)
def main():
    frozen=HERE/'sealed_20261017_a';ready=HERE/'ready_review.json';release=pc.RELEASE
    assert not frozen.exists() and not ready.exists() and not release.exists()
    m=pc.fixed_image();h=pc.expected_hardware();checked=HERE/'checks_01/review.json';r=pc.read(checked)
    assert r['status']=='COLORBAR_PC_TOOL_CHECKS_PASS_NOT_HDL_NOT_BOARD'
    for n,d in r['input_sha256'].items():assert pc.sha(ROOT/n)==d,n
    for n,d in r['artifact_sha256'].items():assert pc.sha(checked.parent/n)==d,n
    old=pc.read(ROOT/'sim/cnn/board_photo_20261016_a/ready_review.json')
    assert old['firmware_sha256']==m['bin_sha256']==pc.FIXED_BIN_SHA
    logs={}
    for folder in (ROOT/'sim/cnn/board').glob('*'):
        if not folder.is_dir() or not (folder/'result.json').exists():continue
        value=pc.read(folder/'result.json')
        for n,d in value.get('file_sha256',{}).items():assert pc.sha(folder/n)==d,('changed old evidence',folder.name,n)
        logs[(folder/'result.json').relative_to(ROOT).as_posix()]=pc.sha(folder/'result.json')
    paths={ROOT/'tools/cnn_colorbar_photo/run.py',ROOT/'tools/cnn_colorbar_photo/README.md',pc.HARDWARE,
        checked,pc.photo.DEFAULT,ROOT/h['astra_static_review'],ROOT/'sim/cnn/board_photo_20261016_a/ready_review.json'}
    paths.update(HERE.glob('*.py'));paths.update(ROOT/n for n in h['changed_vs_photo_design'])
    paths.update(ROOT/n for n in h['constraint_sha256'])
    paths.update(ROOT/n for n in m['source_sha256'])
    paths.update(ROOT/m[k+'_path'] for k in ('bin','elf'))
    project=frozen/'project';project.mkdir(parents=True);hashes={}
    for p in sorted(paths):
        n=p.relative_to(ROOT).as_posix();q=project/n;q.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,q);hashes[n]=pc.sha(q);assert pc.sha(p)==hashes[n]
    pc.save(frozen/'manifest.json',dict(status='COLORBAR_PC_SOFTWARE_INPUT_SEALED_NOT_HDL_PACKAGE',sha256=hashes,
        hardware_manifest_sha256=pc.sha(pc.HARDWARE),fixed_firmware_sha256=pc.FIXED_BIN_SHA,
        design_snapshot_base=h['design_snapshot_base'],current_design_sha256=h['design_sha256']))
    record=dict(status='COLORBAR_PC_READY_PENDING_USER_NEW_BITSTREAM_AND_BOARD',hardware_version=h['version'],
        fixed_firmware_sha256=pc.FIXED_BIN_SHA,firmware_rebuilt=False,hardware_manifest_sha256=pc.sha(pc.HARDWARE),
        tool_sha256=pc.sha(ROOT/'tools/cnn_colorbar_photo/run.py'),offline_review_sha256=pc.sha(checked),
        frozen_manifest_sha256=pc.sha(frozen/'manifest.json'),old_log_result_sha256=logs,
        RTL_modified=False,IP_FDC_PDS_modified=False,PDS_started=False,serial_opened=False,HDL_run=False,board='NOT_RUN',
        new_bitstream_required=True,connector='J10',timing='NEW_COLORBAR_IMPLEMENTATION_NOT_REVIEWED',
        colorbar_visual='PENDING',scene_independence='NOT_VERIFIED_BY_ONE_CAPTURE')
    pc.save(ready,record)
    pc.save(release,dict(status='USER_AUTHORIZED_NEW_COLORBAR_BOARD_DIAGNOSTIC',firmware_sha256=pc.FIXED_BIN_SHA,
        hardware_manifest_sha256=pc.sha(pc.HARDWARE),tool_sha256=record['tool_sha256'],
        ready_review=ready.relative_to(ROOT).as_posix(),ready_review_sha256=pc.sha(ready),
        new_bitstream_required=True,connector='J10',PDS_or_bitstream_receipt_required=False,
        key_HDL='NOT_COMPLETED',board='NOT_RUN'))
    assert not (ROOT/'sim/cnn/board/colorbar_20261017_01').exists()
    print(json.dumps(dict(status=record['status'],fixed_firmware_sha256=pc.FIXED_BIN_SHA,hardware_version=h['version'],sealed_inputs=len(hashes)),indent=2))
if __name__=='__main__':main()
