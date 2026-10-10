"""LOAD handshake failures and independent board-audit rejection; no serial."""
from pathlib import Path
import copy,hashlib,importlib.util,json,struct,sys,zlib
ROOT=Path(__file__).resolve().parents[3];TOOLS=ROOT/'tools/uart_loader/candidates/load_stage10';sys.path.insert(0,str(TOOLS))
import acceptance
from cases import cases,PROGRAM
from protocol import decode
from check_board import verify
OUT=ROOT/'sim/uart_loader/build/load_stage10/pc';sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()

class Fake:
    def __init__(self,selected,mutate=None,extra=False,short=False,startup=False):
        self.selected=selected;self.mutate=mutate;self.extra=extra;self.short=short;self.writes=[];self.buffer=b'X' if startup else b''
    @property
    def in_waiting(self):return len(self.buffer)
    def write(self,raw):
        i=len(self.writes);assert not self.buffer,'DATA/next header sent before previous READY/ACK drained'
        assert raw==bytes.fromhex(self.selected[i]['tx_hex']);self.writes.append(raw)
        self.buffer=bytes.fromhex(self.selected[i]['expected_hex'])
        if self.mutate:self.buffer=self.mutate(i,self.buffer)
        if self.extra:self.buffer+=b'Hello'
        return len(raw)-1 if self.short else len(raw)
    def read(self,n):
        part=self.buffer[:min(7,n)];self.buffer=self.buffer[len(part):];return part

def repaired(raw,offset,value):
    b=bytearray(raw);struct.pack_into('<I',b,offset,value)
    struct.pack_into('<I',b,28,zlib.crc32(b[:28]));struct.pack_into('<I',b,56,zlib.crc32(b[32:56]));return bytes(b)

def main():
    assert not OUT.exists();OUT.mkdir(parents=True)
    selected=cases('native');rows=[]
    good=[];port=Fake(selected);count=acceptance.run_cases(port,selected,good,quiet=lambda _:None)
    assert count==8 and len(port.writes)==8 and sum(c['status']==1 for c in selected)==2
    rows.append('full_REAL_BIN_fragmented_READY_DATA_ACK_PASS')
    for name,mutate,extra,short,startup,expected_writes in [
        ('early_ACK_instead_READY',lambda i,r:repaired(r,32,0) if i==1 else r,False,False,False,2),
        ('wrong_SEQ',lambda i,r:repaired(r,8,999),False,False,False,1),
        ('bad_response_CRC',lambda i,r:r[:-1]+bytes([r[-1]^1]),False,False,False,1),
        ('wrong_final_accepted',lambda i,r:repaired(r,40,255) if i==2 else r,False,False,False,3),
        ('VERIFIED_bit_forgery',lambda i,r:repaired(r,48,0x30003) if i==4 else r,False,False,False,5),
        ('wrong_image_CRC_identity',lambda i,r:repaired(r,24,123) if i==1 else r,False,False,False,2),
        ('Hello_extra_RX',None,True,False,False,1),('short_write',None,False,True,False,1),
        ('startup_RX',None,False,False,True,0),
        ('short_59_byte_response',lambda i,r:r[:-1],False,False,False,1),
        ('NACK_at_READY',lambda i,r:repaired(r,32,0x8005) if i==1 else r,False,False,False,2),
    ]:
        failed=[];port=Fake(selected,mutate,extra,short,startup)
        try:acceptance.run_cases(port,selected,failed,quiet=lambda _:None)
        except (ValueError,AssertionError):pass
        else:raise AssertionError('accepted fault: '+name)
        assert len(port.writes)==expected_writes,name
        rows.append(name+'_REJECT_NO_RETRY')
    info=json.loads((PROGRAM.parent/'manifest.json').read_text());log=dict(
        evidence_origin='OFFLINE_FIXTURE_NOT_BOARD',status='STAGE10_REAL_PROGRAM_BOARD_PASS',board_result='PASS_LOAD_ONLY_UNVERIFIED',
        port='COM11',baud=115200,no_automatic_retry=True,retry_count=0,formal_load_implemented=True,
        formal_verify_implemented=False,run_implemented=False,program_execute=False,state='LOADED_UNVERIFIED',
        frames=8,planned_frames=8,crc_errors=0,uart_errors=0,seconds=1.0,program_bytes=info['bytes'],
        program_crc32=info['crc32'],program_sha256=sha(PROGRAM),program_manifest_sha256=sha(PROGRAM.parent/'manifest.json'),
        image_sha256=json.loads((ROOT/'tests/uart_loader/candidates/load_stage10/build/manifest.json').read_text())['sha256'],
        pc_input_sha256={p.name:sha(p) for p in sorted(TOOLS.glob('*.py'))},records=good)
    fixture=OUT/'fixture_OFFLINE_NOT_BOARD.json';fixture.write_text(json.dumps(log,indent=2)+'\n')
    assert verify(fixture,gate_check=False,offline=True)['responses']==8;rows.append('independent_struct_zlib_fixture_PASS')
    try:verify(fixture,gate_check=False)
    except ValueError:rows.append('fixture_REJECT_actual_board_mode')
    else:raise AssertionError('fixture accepted as board')
    for name,change in [
        ('retries',lambda d:d.update(retry_count=1)),('execution',lambda d:d.update(program_execute=True)),
        ('missing_final',lambda d:d['records'].pop()),
        ('payload_changed',lambda d:d['records'][2].update(tx_hex='00')),
        ('valid_packet_forged_DDR_CRC',lambda d:d['records'][6].update(rx_hex=repaired(bytes.fromhex(d['records'][6]['rx_hex']),44,1).hex())),
    ]:
        bad=copy.deepcopy(log);change(bad);p=OUT/(name+'.json');p.write_text(json.dumps(bad))
        try:verify(p,gate_check=False,offline=True)
        except (AssertionError,ValueError):rows.append('audit_'+name+'_REJECT')
        else:raise AssertionError('bad fixture accepted '+name)
    report=dict(status='STAGE10_PC_OFFLINE_PASS',checks=rows,check_count=len(rows),board_result='NOT_TESTED',serial_opened=False)
    (OUT/'results.json').write_text(json.dumps(report,indent=2)+'\n');print('RESULT: PASS stage10 PC offline',len(rows),'checks; no serial')

if __name__=='__main__':main()
