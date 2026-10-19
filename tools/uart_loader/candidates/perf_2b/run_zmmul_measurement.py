"""New Zmmul fixed120 board measurement; successful RV32I transport/tools untouched."""
from pathlib import Path
import inspect
import sys

ROOT=Path(__file__).resolve().parents[4]
sys.path.insert(0,str(ROOT/'tests/cpu_performance_2b'))
from zmmul_software import BUILD_DIR, require_manifest, parse_measurement, measurement, load


def manifest_for(name):
    assert name in ('performance_120','validation_120')
    return BUILD_DIR/name/'manifest.json'


# Reuse byte-for-byte successful RVLD transport behavior and its PERF2B tail wait.
upload=measurement.upload
source=inspect.getsource(upload.execute)
guard="b'PORT_DONE ticks=' in output and output.endswith(b'\\n')"
assert source.count(guard)==1
source=source.replace(guard,"output.endswith(b'PERF2B_DONE\\n')",1)
transport_namespace=dict(upload.__dict__,parse_output=parse_measurement)
exec(compile(source,'<zmmul_measurement_transport>','exec'),transport_namespace)

namespace=dict(measurement.__dict__,manifest_for=manifest_for,require_manifest=require_manifest,
               parse_measurement=parse_measurement,execute=transport_namespace['execute'],
               APPLICATIONS=('performance_120','validation_120'),FORMAL_APPLICATIONS=())
for name in ['verify_record','verify','main']:
    exec(compile(inspect.getsource(getattr(measurement,name)),'<zmmul_fixed120_'+name+'>','exec'),namespace)
verify=namespace['verify']
main=namespace['main']


if __name__=='__main__':main()
