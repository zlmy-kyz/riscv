"""Check the independent board validator with explicitly offline fixtures."""
from pathlib import Path
import importlib.util,json,sys,tempfile
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
sys.path.insert(0,str(ROOT/'tools/uart_loader/candidates/ack_nack_stage8'))
from cases import cases,CRC
from protocol import expected_response,decode_response
spec=importlib.util.spec_from_file_location('board_validator',HERE/'check_board.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
records=[]
for c in cases(uart_faults=False):
    raw=expected_response(c['seq'],c['cmd'],c['status'],CRC if c.get('crc_read') else 0)
    records.append(dict(**c,result='PASS',rx_hex=raw.hex(),seconds=.3,decoded=decode_response(raw,c['seq'],c['cmd'],expected_crc=c.get('expected_crc',CRC))))
log=dict(status='STAGE8_HOST_INJECTABLE_BOARD_PASS',board_result='PASS_HOST_INJECTABLE_ONLY',image_sha256=m.EXPECTED_IMAGE,records=records,
    fixture_notice='OFFLINE FIXTURE ONLY; THIS IS NOT BOARD EVIDENCE')
folder=ROOT/'sim/uart_loader/build/ack_nack_stage8/validator_offline';folder.mkdir(exist_ok=True)
path=folder/'fixture.json';path.write_text(json.dumps(log),encoding='utf8')
result=m.verify(path);assert (result['ack_count'],result['nack_count'],result['crc_ack_count'])==(73,35,37)
tests=[dict(name='complete offline fixture',result='PASS')]
for name,mutate in [('missing final recovery',lambda x:x['records'].pop()),('tampered raw response',lambda x:x['records'][1].update(rx_hex='00'*60)),
                     ('wrong expected request',lambda x:x['records'][2].update(tx_hex='00')),('false decoder metadata',lambda x:x['records'][1]['decoded'].update(actual_ddr_crc=0))]:
    broken=json.loads(json.dumps(log));mutate(broken);path.write_text(json.dumps(broken),encoding='utf8')
    try:m.verify(path)
    except (AssertionError,ValueError):tests.append(dict(name=name,result='PASS'))
    else:raise AssertionError(f'tampering accepted: {name}')
path.write_text(json.dumps(log),encoding='utf8')
(folder/'results.json').write_text(json.dumps(dict(status='OFFLINE_VALIDATOR_CHECK_PASS',board_result='NOT_TESTED',tests=tests),indent=2)+'\n',encoding='utf8')
print('RESULT: PASS',len(tests),'offline validator checks; no board evidence produced')
