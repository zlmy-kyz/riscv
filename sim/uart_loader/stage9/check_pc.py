"""Adversarial PC transport and independent board verifier tests; no real serial."""
from pathlib import Path
import hashlib,importlib.util,json,struct,sys
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).resolve().parent
TOOLS=ROOT/'tools/uart_loader/candidates/random_stage9';sys.path.insert(0,str(TOOLS))
from acceptance import board_cases,run_cases
from protocol import response,crc32
from check_board import verify
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
OUT=ROOT/'sim/uart_loader/build/random_stage9/pc'

class Fake:
    def __init__(self,cases,mode='ok'):self.cases=cases;self.mode=mode;self.index=0;self.buffer=b'';self.writes=0
    @property
    def in_waiting(self):
        if self.mode=='startup':return 1
        if self.mode=='extra' and self.writes and not self.buffer:return 1
        return 0
    def write(self,raw):
        assert raw==bytes.fromhex(self.cases[self.index]['tx_hex']);self.writes+=1
        rx=response(self.cases[self.index]);self.index+=1
        if self.mode=='bad_crc':rx=rx[:-1]+bytes([rx[-1]^1])
        elif self.mode=='pseudo_ddr_ack':
            rx=bytearray(rx);struct.pack_into('<I',rx,44,struct.unpack_from('<I',rx,44)[0]^1);struct.pack_into('<I',rx,56,crc32(rx[32:56]));rx=bytes(rx)
        elif self.mode=='wrong_seq':
            rx=bytearray(rx);struct.pack_into('<I',rx,8,9999);struct.pack_into('<I',rx,28,crc32(rx[:28]));rx=bytes(rx)
        elif self.mode=='nack':
            rx=bytearray(rx);struct.pack_into('<I',rx,32,0x8005);struct.pack_into('<I',rx,56,crc32(rx[32:56]));rx=bytes(rx)
        elif self.mode=='partial':rx=rx[:59]
        self.buffer=rx
        return len(raw)-1 if self.mode=='short_write' else len(raw)
    def read(self,n):
        if not self.buffer and self.mode=='extra':return b'!'
        out=self.buffer[:min(n,7)];self.buffer=self.buffer[len(out):];return out

def main():
    assert not OUT.exists();OUT.mkdir(parents=True)
    plan,cases=board_cases(ROOT/'sim/uart_loader/build/random_stage9/corpus/board')
    checks=[];records=[];fake=Fake(cases)
    images,payload=run_cases(fake,cases,records,quiet=lambda _:None)
    assert images==1000 and payload==plan['payload_bytes'] and fake.writes==len(cases)
    checks.append('1000_image_complete_corpus_fragmented_reads_zero_retry')
    for mode in ('startup','bad_crc','pseudo_ddr_ack','wrong_seq','nack','partial','short_write','extra'):
        collected=[];fake=Fake(cases[:4],mode)
        try:run_cases(fake,cases[:4],collected,quiet=lambda _:None)
        except (ValueError,AssertionError):pass
        else:raise AssertionError('accepted '+mode)
        assert fake.writes<=1;checks.append('reject_'+mode+'_without_retry')
    identity=json.loads((ROOT/'tests/uart_loader/candidates/random_stage9/build/manifest.json').read_text())['sha256']
    fixture=dict(status='STAGE9_DIAGNOSTIC_BOARD_PASS',board_result='PASS_RANDOM_DIAGNOSTIC_ONLY',evidence_origin='OFFLINE_FIXTURE_NOT_BOARD',
                 port='COM11',baud=115200,no_automatic_retry=True,retry_count=0,formal_load_verify_run_implemented=False,random_execute=False,
                 crc_errors=0,uart_errors=0,corpus_sha256=sha(ROOT/'sim/uart_loader/build/random_stage9/corpus/board/manifest.json'),seed=plan['seed'],
                 planned_images=1000,completed_images=1000,planned_payload_bytes=payload,payload_bytes=payload,planned_frames=len(cases),frames=len(cases),
                 image_sha256=identity,pc_input_sha256={p.name:sha(p) for p in sorted(TOOLS.glob('*.py'))},records=records,seconds=1000,bytes_per_second=payload/1000)
    path=OUT/'fixture_not_board.json';path.write_text(json.dumps(fixture,indent=2)+'\n')
    assert verify(path,check_gate=False)['images']==1000;checks.append('independent_raw_1000_image_verifier')
    try:verify(path)
    except AssertionError:checks.append('reject_fixture_as_actual_board_before_gate')
    else:raise AssertionError('fixture passed board gate')
    # Mutate one response's actual DDR CRC and recompute packet CRC: must still reject.
    altered=json.loads(json.dumps(fixture));r=altered['records'][1];wire=bytearray.fromhex(r['rx_hex']);struct.pack_into('<I',wire,44,struct.unpack_from('<I',wire,44)[0]^1);struct.pack_into('<I',wire,56,crc32(wire[32:56]));r['rx_hex']=wire.hex()
    bad=OUT/'pseudo_ack_fixture.json';bad.write_text(json.dumps(altered))
    try:verify(bad,check_gate=False)
    except AssertionError:checks.append('independent_reject_valid_packet_crc_wrong_ddr_crc')
    else:raise AssertionError('pseudo ACK passed independent verifier')
    for key,value in [('completed_images',999),('retry_count',1),('random_execute',True),('crc_errors',1),('seed',0)]:
        altered=dict(fixture);altered[key]=value;bad=OUT/f'bad_{key}.json';bad.write_text(json.dumps(altered))
        try:verify(bad,check_gate=False)
        except AssertionError:checks.append('independent_reject_'+key)
        else:raise AssertionError(key)
    result=dict(status='STAGE9_PC_OFFLINE_PASS',checks=checks,serial_opened=False,fixture_is_board_evidence=False,
                image_count=1000,payload_bytes=payload,frames=len(cases))
    (OUT/'results.json').write_text(json.dumps(result,indent=2)+'\n');print('RESULT: PASS stage9 PC/offline verifier',len(checks),'checks; no serial opened')

if __name__=='__main__':main()
