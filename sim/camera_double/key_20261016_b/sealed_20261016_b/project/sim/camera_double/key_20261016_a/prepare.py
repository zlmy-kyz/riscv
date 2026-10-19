"""Independent input-pattern reference and fixed C image conversion. No HDL execution."""
import functools,json,struct,zlib
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2]
@functools.lru_cache(maxsize=None)
def frame(p,w,h):
    return b''.join(struct.pack('<H',((x*73+y*151+(x^(y*3))*19)^((p*0x3d79+0x1357)&0xffff))&0xffff) for y in range(h) for x in range(w))
def main():
    out=HERE/'generated';out.mkdir(exist_ok=False)
    info={}
    for kind,h,patterns in [('soc',8,range(1,6)),('unit',128,range(1,13))]:
        for p in patterns:
            raw=frame(p,64,h);name=f'{kind}_{p}.bin';(out/name).write_bytes(raw)
            info[f'{kind}:{p}']=dict(bytes=len(raw),CRC=f'{zlib.crc32(raw)&0xffffffff:08x}')
    (out/'golden.json').write_text(json.dumps(info,indent=2)+'\n')
    raw=(ROOT/'tests/camera_double100/build/abi2_small_20261016_d/program.bin').read_bytes();assert len(raw)<16384
    raw+=bytes(16384-len(raw))
    (out/'cpu.dat').write_text(''.join(f'{int.from_bytes(raw[i:i+4],"little"):08x}\n' for i in range(0,len(raw),4)),encoding='ascii')
    print(json.dumps(dict(status='ABI2_INPUT_PATTERNS_GENERATED_NO_HDL',patterns=len(info))))
if __name__=='__main__':main()
