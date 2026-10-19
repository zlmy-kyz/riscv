"""Prepare expected colorbar hardware identity without HDL/PDS/serial or rebuilding firmware."""
import hashlib,json
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    out=HERE/'hardware.json';assert not out.exists()
    old=json.loads((ROOT/'sim/cnn/board_diag_20261016_a/ready_review.json').read_text())['design_sha256']
    receipt=ROOT/'sim/camera/colorbar_20261016_a/review.json';new=json.loads(receipt.read_text())
    assert new['status']=='COLORBAR_RTL_STATIC_READY_PENDING_PDS_AND_BOARD'
    updates={n.replace('\\','/'):h for n,h in new['after_sha256'].items()};assert len(updates)==5
    expected=dict(old);expected.update(updates)
    for n,h in expected.items():assert sha(ROOT/n)==h,('unexpected current design',n)
    record=dict(version='OV5640_COLORBAR_J10_20261016_A',mode='OV5640_INTERNAL_COLOR_BARS',connector='J10',camera_connector='CAM1/J4',
        requires_new_bitstream=True,parameter='board_top.CAMERA_COLORBAR_ENABLE=1 (soc_ddr3_top instance)',
        registers_expected={'503d':'80','4741':'00'},config_writes_expected=245,config_readbacks_expected=10,
        unchanged_ABI=dict(camera='43414d02',preprocess='50525001',CNN='434e4e01'),
        source=dict(width=1280,height=720,format='RGB565 little endian',bytes=1843200),
        firmware_sha256='2f72e829b3044e1ce8f5996d6b9ddb39877c3c6f15048cf9a040b64bd78d7bd4',
        astra_static_review=receipt.relative_to(ROOT).as_posix(),astra_static_review_sha256=sha(receipt),
        design_sha256=expected,changed_vs_photo_design=updates,
        design_snapshot_base='sim/cnn/board_diag_20261016_a/sealed_diag_20261016_c',
        constraint_sha256={n:sha(ROOT/n) for n in ('constraint_check/temp_constraint_file.fdc','fdc/camera_single.fdc')},
        status='EXPECTED_SOURCE_IDENTITY_NOT_DOWNLOADED_BITSTREAM_PROOF',PDS='USER_MUST_REBUILD_AND_DOWNLOAD',
        timing='NEW_COLORBAR_IMPLEMENTATION_NOT_REVIEWED',key_HDL='NOT_COMPLETED',board='NOT_RUN')
    out.write_text(json.dumps(record,indent=2)+'\n',encoding='utf-8');print('EXPECTED_HARDWARE_IDENTITY_READY; 40 design/include files; no firmware rebuild/PDS/serial')
if __name__=='__main__':main()
