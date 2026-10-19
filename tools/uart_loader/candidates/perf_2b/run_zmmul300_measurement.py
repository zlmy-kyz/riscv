"""User-operated Zmmul300 transport; require the V1 continuation gate for board use."""
from pathlib import Path
import inspect
import json
import sys

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0,str(ROOT/'tests/cpu_performance_2b'))
from zmmul300_software import BUILD_DIR, require_manifest, parse_measurement, measurement, sha

GATE = ROOT/'sim/cpu_zmmul/build/ds_cpu_zmmul_coremark_v1_resume_20261013_a/software_gate.json'


def manifest_for(name):
    assert name in ('performance_300','validation_300')
    return BUILD_DIR/name/'manifest.json'


source = inspect.getsource(measurement.upload.execute)
guard = r"b'PORT_DONE ticks=' in output and output.endswith(b'\n')"
assert source.count(guard)==1
source = source.replace(guard,r"output.endswith(b'PERF2B_DONE\n')",1)
transport_namespace = dict(measurement.upload.__dict__,parse_output=parse_measurement)
exec(compile(source,'<Zmmul300_same_RVLD_transport>','exec'),transport_namespace)
namespace = dict(measurement.__dict__,manifest_for=manifest_for,require_manifest=require_manifest,
                 parse_measurement=parse_measurement,execute=transport_namespace['execute'],
                 APPLICATIONS=('performance_300','validation_300'),FORMAL_APPLICATIONS=())
for name in ['verify_record','verify','main']:
    exec(compile(inspect.getsource(getattr(measurement,name)),'<Zmmul300_'+name+'>','exec'),namespace)
verify = namespace['verify']


def require_gate():
    assert GATE.exists(), 'V1 validation/closure pending: wait for Codex raw evidence review before board run'
    gate = json.loads(GATE.read_text())
    assert gate['status']=='ZMMUL_P_V_SHORT_CRC_GATE_PASS_300_READY_FOR_USER_BOARD'
    review_path = GATE.with_name('codex_review.json')
    assert review_path.exists(), 'Wait for Codex independent raw-evidence review of V1'
    review = json.loads(review_path.read_text())
    assert review['status']=='ZMMUL_P_V_SHORT_CRC_AND_300_HANDOFF_RAW_EVIDENCE_REVIEW_PASS'
    assert review['software_gate_sha256']==sha(GATE)
    assert sha(ROOT/'generate_bitstream/board_top.sbit')==gate['bitstream_sha256']
    for name,digest in {**gate['registered_input_sha256'],**gate['continuation_input_sha256'],**gate['software_sha256'],
                        **gate['P1']['evidence_sha256'],**gate['V1']['evidence_sha256']}.items():
        assert sha(ROOT/name)==digest, name
    return gate


def main():
    if '--plan-only' not in sys.argv and '--verify-log' not in sys.argv: require_gate()
    namespace['main']()


if __name__=='__main__': main()
