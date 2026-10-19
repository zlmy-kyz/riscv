"""Record restored live mode; no firmware build, HDL, PDS or serial."""
import hashlib,json
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    out=HERE/'hardware.json';assert not out.exists()
    prior=json.loads((ROOT/'sim/camera/dvp_photo_20261017_a/hardware.json').read_text())
    receipt=ROOT/'sim/camera/restore_live_20261017_a/review.json';r=json.loads(receipt.read_text())
    assert r['status']=='LIVE_MODE_RESTORED_IN_RTL_PENDING_USER_NEW_BITSTREAM'
    assert r['parameters']=={'CAMERA_COLORBAR_ENABLE':0,'CAMERA_DVP_TEST_ENABLE':0}
    expected=dict(prior['design_sha256']);expected['myriscv/board_top.v']=r['board_top_sha256']
    for n,h in expected.items():assert sha(ROOT/n)==h,n
    base=json.loads((ROOT/'sim/cnn/board_diag_20261016_a/ready_review.json').read_text())['design_sha256']
    h=dict(version='OV5640_LIVE_RESTORED_J10_20261017_A',mode='OV5640_LIVE_SCENE',connector='J10',camera_connector='CAM1/J4',
        requires_new_bitstream=True,parameters=r['parameters'],registers_expected={'503d':'00'},
        register_4741=dict(expected_after_sensor_reset='00',explicitly_written=False,explicitly_read_back=False),
        config_writes_expected=244,config_readbacks_expected=8,design_sha256=expected,
        changed_vs_photo_design={n:d for n,d in expected.items() if base[n]!=d},
        design_snapshot_base=prior['design_snapshot_base'],
        constraint_sha256={n:sha(ROOT/n) for n in prior['constraint_sha256']},
        astra_static_review=receipt.relative_to(ROOT).as_posix(),astra_static_review_sha256=sha(receipt),
        firmware_sha256='2f72e829b3044e1ce8f5996d6b9ddb39877c3c6f15048cf9a040b64bd78d7bd4',
        status='EXPECTED_SOURCE_IDENTITY_NOT_DOWNLOADED_BITSTREAM_PROOF',timing='NEW_LIVE_PHOTO_IMPLEMENTATION_NOT_REVIEWED',board='NOT_RUN')
    out.write_text(json.dumps(h,indent=2)+'\n',encoding='utf-8');print('RESTORED_LIVE_IDENTITY_READY_FIXED_BIN_UNCHANGED')
if __name__=='__main__':main()
