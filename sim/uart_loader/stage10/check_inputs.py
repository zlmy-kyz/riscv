"""Read-only pre-deployment proof of baseline, real BIN, and staged LOAD plan."""
from pathlib import Path
import hashlib,json,struct,sys,zlib
ROOT=Path(__file__).resolve().parents[3];BUILD=ROOT/'sim/uart_loader/build/load_stage10'
sys.path.insert(0,str(ROOT/'tools/uart_loader/candidates/load_stage10'))
from cases import cases,PROGRAM
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    old=json.loads((BUILD/'protected_before.json').read_text())
    assert all(sha(ROOT/p)==h for p,h in old.items())
    info=json.loads((PROGRAM.parent/'manifest.json').read_text())
    for p,h in info['sha256'].items():assert sha(ROOT/p)==h,p
    raw=PROGRAM.read_bytes();assert len(raw)==383 and info['crc32']==zlib.crc32(raw)
    selected=cases('native');loaded=bytearray();last=None
    assert len(selected)==8
    for c in selected:
        tx=bytes.fromhex(c['tx_hex'])
        if c['status']==1:
            assert c['cmd']==2 and len(tx)==32
            h=struct.unpack('<4sBBH6I',tx)
            assert h[:3]==(b'RVLD',1,2) and h[-1]==zlib.crc32(tx[:28])
            assert h[5]==0x40000000+len(loaded) and h[7]==len(raw) and h[8]==info['crc32']
            assert h[3]==(1 if not loaded else 2)
            last=h
        elif c['cmd']==2:
            assert last and c['seq']==last[4] and len(tx)==last[6]+4
            assert zlib.crc32(tx[:-4])==struct.unpack_from('<I',tx,len(tx)-4)[0]
            loaded+=tx[:-4];last=None
        h=struct.unpack('<4sBBH6I',bytes.fromhex(c['expected_hex'])[:32])
        p=struct.unpack('<6I',bytes.fromhex(c['expected_hex'])[32:56])
        assert not p[4]&((1<<17)|4)
    assert loaded==raw and last is None
    checked=[]
    for name in ('v1/positive','v1/negative','v1/native','extended_v1/negative','window_v1/positive','unverified_v1/positive'):
        p=BUILD/name/'results.json';d=json.loads(p.read_text())
        assert d['status'].endswith('_SIM_PASS') and d['protected_unchanged'] and d['image_unchanged'] and d['inputs_unchanged']
        assert all(sha(ROOT/p)==h for p,h in d['input_sha256'].items())
        checked.append(dict(suite=name,status=d['status']))
    proof=dict(status='STAGE10_READ_ONLY_INPUTS_PASS',baseline_files_unchanged=len(old),
               program_bytes=383,program_crc32=info['crc32'],planned_responses=8,
               exact_BIN_reconstructed_from_LOAD_stages=True,VERIFIED_RUN_bits_clear=True,reports=checked,
               serial_opened=False,board_result='NOT_TESTED')
    p=BUILD/'input_check.json';assert not p.exists()
    p.write_text(json.dumps(proof,indent=2)+'\n')
    print('RESULT: PASS',len(old),'baseline files unchanged; same 383-byte BIN reconstructed from Header/READY/DATA/ACK plan; six completed suites frozen inputs unchanged')

if __name__=='__main__':main()
