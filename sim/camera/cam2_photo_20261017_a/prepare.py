"""Record CAM2/J5 pin switch; reuse live RTL and fixed BIN without hardware execution."""
import hashlib,json,re
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    out=HERE/'hardware.json';assert not out.exists()
    prior=json.loads((ROOT/'sim/camera/live_photo_20261017_a/hardware.json').read_text())
    receipt=ROOT/'sim/camera/cam2_switch_20261017_a/review.json';r=json.loads(receipt.read_text())
    assert r['status']=='CAM2_J5_J10_CONSTRAINT_MAPPING_READY_PENDING_USER_PDS_BOARD' and r['only_14_LOC_replacements']
    assert not r['other_port_conflicts'] and not r['rtl_changed']
    for n,h in prior['design_sha256'].items():assert sha(ROOT/n)==h,('RTL changed',n)
    fdc=ROOT/'constraint_check/temp_constraint_file.fdc';assert sha(fdc)==r['after_sha256']
    actual=dict(re.findall(r'define_attribute \{p:(camera_[^}]+)\} \{PAP_IO_LOC\} \{([^}]+)\}',fdc.read_text()))
    expected={c['port']:c['CAM2_pad'] for c in r['changes']};assert len(expected)==14 and actual==expected
    h=dict(prior);h.update(version='OV5640_LIVE_CAM2_J5_ON_J10_20261017_A',camera_connector='CAM2/J5',
        camera_count=1,DDR_frame_buffers=2,buffer_meaning='A/B are two DDR buffers of the same CAM2 camera, not two cameras',
        camera_pad_map=expected,constraint_sha256={'constraint_check/temp_constraint_file.fdc':r['after_sha256']},
        astra_static_review=receipt.relative_to(ROOT).as_posix(),astra_static_review_sha256=sha(receipt),
        inactive_legacy_CAM1_FDC='fdc/camera_single.fdc (not active PDS input; do not apply to CAM2)',
        prior_live_RTL_review='sim/camera/restore_live_20261017_a/review.json',
        prior_CAM1_hardware_identity='sim/camera/live_photo_20261017_a/hardware.json',
        timing='NEW_CAM2_PHOTO_IMPLEMENTATION_NOT_REVIEWED',board='NOT_RUN')
    out.write_text(json.dumps(h,indent=2)+'\n',encoding='utf-8');print('CAM2_J5_ON_J10_IDENTITY_READY; SAME_RTL_SAME_FIXED_BIN')
if __name__=='__main__':main()
