"""digits10_int8_v1 wide-integer reference, written from the contract, independent of RTL."""
import hashlib,json,struct,zlib
from pathlib import Path
CONTRACT='digits10_int8_v1'
SHAPES=[(32,1,8),(16,8,16),(8,16,32)]
def rha(a,s):
    if not 0<=s<=31:raise ValueError('shift')
    return a if s==0 else (-1 if a<0 else 1)*((abs(a)+(1<<(s-1)))>>s)
def gray(rgb):
    if len(rgb)!=27648:raise ValueError('RGB96 length')
    out=[]
    for y in range(32):
        for x in range(32):
            i=3*(96*(3*y+1)+3*x+1);r,g,b=rgb[i:i+3]
            out.append(((77*r+150*g+29*b+128)>>8)-128)
    return out
def load(folder):
    folder=Path(folder);m=json.loads((folder/'model.json').read_text())
    if m['contract']!=CONTRACT or m['purpose']!='DETERMINISTIC_NONTRAINED_HARDWARE_DIAGNOSTIC' or m['trained'] is not False:raise ValueError('wrong model contract/purpose')
    if m['load_words']!=6222 or m['load_bytes']!=24888 or m['labels']!=[str(i) for i in range(10)] or len(m['scales'])!=4:raise ValueError('model layout')
    for n,d in m['sha256'].items():
        if hashlib.sha256((folder/n).read_bytes()).hexdigest()!=d:raise ValueError('model hash '+n)
    w=[x if x<128 else x-256 for x in (folder/'weights.bin').read_bytes()]
    b=list(struct.unpack('<66i',(folder/'bias.bin').read_bytes()));s=m['shifts']
    if len(w)!=6152 or len(b)!=66 or any(x==-128 for x in w) or len(s)!=4:raise ValueError('parameter encoding')
    words=[v&255 for v in w]+[v&0xffffffff for v in b]+s
    packed=struct.pack('<6222I',*words)
    if packed!=(folder/'load_words.bin').read_bytes() or zlib.crc32(packed)&0xffffffff!=m['load_crc32']:raise ValueError('load encoding/CRC')
    identity=int.from_bytes(hashlib.sha256(b'digits10_int8_v1\0DIAGNOSTIC_NONTRAINED\0'+packed).digest()[:4],'little') or 1
    if m['model_id']!=identity or m['model_id_hex']!=f'{identity:08x}':raise ValueError('model ID')
    wi=bi=0;bounds=[]
    for layer,(n,ci,co) in enumerate(SHAPES+[(1,32,10)]):
        terms=9*ci if layer<3 else ci
        for oc in range(co):
            bound=abs(b[bi+oc])+128*sum(abs(v) for v in w[wi+oc*terms:wi+(oc+1)*terms])
            if bound>2147483647 or abs(b[bi+oc])>2145142783:raise ValueError('accumulator/bias overflow')
            bounds.append(bound)
        wi+=co*terms;bi+=co
    assert wi==6152 and bi==66
    for f,sft in zip(m['scales'],s):
        if not all(0<=f[k]<=15 for k in ('Fin','Fw','Fout')) or f['Fin']+f['Fw']-f['Fout']!=sft or not 0<=sft<=31:raise ValueError('scale/shift')
    if m['scales'][0]['Fin']!=7 or any(m['scales'][i]['Fin']!=m['scales'][i-1]['Fout'] for i in range(1,4)):raise ValueError('scale continuity')
    return dict(meta=m,weights=w,biases=b,shifts=s,words=words,max_bound=max(bounds))
def infer(rgb,model):
    a=gray(rgb);layers={'gray32':a.copy()};wi=bi=0;stats=[]
    weights=model['weights'];bias=model['biases'];shifts=model['shifts']
    for layer,(n,ci,co) in enumerate(SHAPES):
        no=n//2;out=[];zeros=clips=0;minacc=2**63;maxacc=-2**63
        for y in range(no):
            for x in range(no):
                for oc in range(co):
                    acc=bias[bi+oc];base=wi+oc*9*ci
                    for ky in range(3):
                        iy=2*y+ky-1
                        for kx in range(3):
                            ix=2*x+kx-1
                            for ic in range(ci):
                                q=a[(iy*n+ix)*ci+ic] if 0<=iy<n and 0<=ix<n else 0
                                acc+=q*weights[base+(ky*3+kx)*ci+ic]
                    if not -2**31<=acc<2**31:raise ValueError('int32 accumulator overflow')
                    minacc=min(minacc,acc);maxacc=max(maxacc,acc)
                    q=rha(acc,shifts[layer]);zeros+=q<=0;clips+=q>127;out.append(min(127,max(0,q)))
        a=out;layers[f'conv{layer+1}']=out.copy();stats.append(dict(min_acc=minacc,max_acc=maxacc,zero=zeros,saturated=clips,elements=len(out)))
        wi+=co*9*ci;bi+=co
    gap=[(sum(a[p*32+c] for p in range(16))+8)//16 for c in range(32)];layers['gap']=gap
    scores=[rha(bias[bi+c]+sum(gap[i]*weights[wi+32*c+i] for i in range(32)),shifts[3]) for c in range(10)]
    if any(not -2**31<=s<2**31 for s in scores):raise ValueError('score overflow')
    return dict(layers=layers,scores=scores,prediction=max(range(10),key=lambda c:scores[c]),stats=stats)
def save_trace(folder,result):
    folder=Path(folder);folder.mkdir(exist_ok=True)
    for name,values in result['layers'].items():(folder/(name+'.bin')).write_bytes(bytes(v&255 for v in values))
    (folder/'scores.bin').write_bytes(struct.pack('<10i',*result['scores']))
    (folder/'reference.json').write_text(json.dumps({k:v for k,v in result.items() if k!='layers'},indent=2)+'\n')
