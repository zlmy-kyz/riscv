"""Deterministic nontrained diagnostic package; only writes a new package and C header."""
import hashlib,json,struct,zlib
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2]
def sha(b):return hashlib.sha256(b).hexdigest()
def main():
    out=ROOT/'tests/cnn_digits_diag/model/diag_20261016_a';header=ROOT/'tests/cnn_digits_diag/model_data.h'
    assert not out.exists() and not header.exists();out.mkdir(parents=True)
    state=0x16d10a01;weights=[]
    for _ in range(6152):
        state=(1664525*state+1013904223)&0xffffffff
        weights.append((-3,-2,-1,1,2,3)[(state>>16)%6])
    biases=[]
    for i in range(66):biases.append((1 if i%3 else -1)*(17+(i*29)%197))
    shifts=[5,5,4,0]
    compact=bytes(v&255 for v in weights);bias=struct.pack('<66i',*biases)
    words=[v&255 for v in weights]+[v&0xffffffff for v in biases]+shifts
    packed=struct.pack('<6222I',*words)
    identity=hashlib.sha256(b'digits10_int8_v1\0DIAGNOSTIC_NONTRAINED\0'+packed).digest()
    model_id=int.from_bytes(identity[:4],'little') or 1
    files={'weights.bin':compact,'bias.bin':bias,'load_words.bin':packed}
    for n,b in files.items():(out/n).write_bytes(b)
    meta=dict(contract='digits10_int8_v1',purpose='DETERMINISTIC_NONTRAINED_HARDWARE_DIAGNOSTIC',
        seed='16d10a01',weight_rule='LCG(1664525,1013904223), high16 modulo6 selects [-3,-2,-1,1,2,3]',
        bias_rule='(i%3 ? 1 : -1)*(17+(i*29)%197)',model_id=model_id,model_id_hex=f'{model_id:08x}',
        shifts=shifts,scales=[dict(Fin=7,Fw=1,Fout=3),dict(Fin=3,Fw=3,Fout=1),dict(Fin=1,Fw=4,Fout=1),dict(Fin=1,Fw=0,Fout=1)],
        load_words=6222,load_bytes=24888,load_crc32=zlib.crc32(packed)&0xffffffff,
        sha256={n:sha(b) for n,b in files.items()},trained=False,
        contract_sha256=sha((ROOT/'doc/cnn/digits10_int8_v1.json').read_bytes()),
        labels=[str(i) for i in range(10)],weights_nonzero=6152,weights_negative=sum(v<0 for v in weights),
        weights_positive=sum(v>0 for v in weights),biases_nonzero=66)
    (out/'model.json').write_text(json.dumps(meta,indent=2)+'\n')
    header.write_text('#include <stdint.h>\n#define MODEL_ID 0x%08xu\n#define MODEL_CRC 0x%08xu\n#define MODEL_WORDS 6222u\nstatic const uint32_t model_words[6222]={\n'%(model_id,meta['load_crc32'])+
        ''.join('0x%08xu,%s'%(v,'\n' if i%8==7 else '') for i,v in enumerate(words))+'\n};\n')
    print(json.dumps({k:meta[k] for k in ('model_id_hex','load_words','load_crc32','weights_negative','weights_positive')},indent=2))
if __name__=='__main__':main()
