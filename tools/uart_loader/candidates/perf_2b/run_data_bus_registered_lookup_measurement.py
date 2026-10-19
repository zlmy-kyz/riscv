"""User-operated Task032 registered lookup: frozen P300/V300, reviewed functional gate."""
import json
import sys
import run_write_buffer_turnover_measurement as original

sys.path.insert(0,str(original.ROOT/'sim/data_bus_turnover'))
import run_inst_lookup_triple as simulation

original.GATE=original.ROOT/'sim/data_bus_turnover/build/registered_lookup_final_review_20261014_a/codex_review.json'
verify=original.verify


_read_exact=original.software.transport_namespace['read_exact']


def read_exact_with_evidence(port,n,timeout=5):
    """Keep the frozen reader/timeout; retain bytes it consumed before a short read."""
    received=bytearray()
    class ObservedPort:
        def read(self,size):
            part=port.read(size)
            received.extend(part)
            return part
        def __getattr__(self,name):
            return getattr(port,name)
    try:
        return _read_exact(ObservedPort(),n,timeout)
    except ValueError as error:
        raise ValueError(f'{error}; received={len(received)}/{n}; partial_rx_hex={received.hex()}') from error


# execute() keeps this namespace as its globals. Only improve failure evidence;
# no changes to packets, the five-second deadline, retry policy or FPGA code.
original.software.transport_namespace['read_exact']=read_exact_with_evidence


def require_gate():
    data=simulation.require_inputs()
    gate=json.loads(original.GATE.read_text(encoding='utf-8'))
    if gate['status']!='DATA_BUS_RESPONSE_TURNOVER_RAW_EVIDENCE_REVIEW_PASS':
        raise ValueError('Task032 registered lookup functional review has not passed')
    if gate['review_kind']!='TASK032_REGISTERED_INST_LOOKUP_RAW_REVIEW':
        raise ValueError('Wrong Task032 functional review')
    if gate['manifest_sha256']!=simulation.base.sha(simulation.MANIFEST):
        raise ValueError('Task032 inputs changed')
    if gate['bridge_sha256']!=data['bridge_sha256']:
        raise ValueError('Task032 RTL identity changed')
    if not gate['evidence_sha256']:
        raise ValueError('Task032 raw evidence missing')
    for name,digest in gate['evidence_sha256'].items():
        if simulation.base.sha(original.ROOT/name)!=digest:
            raise ValueError('Task032 evidence changed: '+name)
    return gate


original.require_gate=require_gate


if __name__=='__main__':
    if sys.argv[1:]==['--check-gate']:
        require_gate()
        print('Task032 raw functional gate verified; serial/PDS/board NOT_RUN')
    else:
        original.main()
