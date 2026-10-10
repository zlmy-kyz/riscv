"""Clone active PDS inputs into an isolated build; never alter main IP/PDS."""
from pathlib import Path
import hashlib,json,re,shutil,xml.etree.ElementTree as ET
ROOT=Path(__file__).resolve().parents[3]
DEST=ROOT/'sim/uart_loader/build/verify_run_hello/pds_candidate'
assert not DEST.exists(), 'preserve existing candidate PDS build'
DEST.mkdir()
source=ROOT/'RISCV.pds'
tokens=re.findall(r'"(?:\\.|[^"\\])*"|[()]|[^\s()]+',source.read_text())
position=0


def parse():
    global position
    token=tokens[position];position+=1
    if token!='(':return token
    result=[]
    while tokens[position]!=')':result.append(parse())
    position+=1;return result


tree=parse();assert position==len(tokens)
for name in ('inst_rom','data_ram','ddr3'):
    src=ROOT/'ipcore'/name;dst=DEST/'ipcore'/name;dst.mkdir(parents=True)
    for f in src.iterdir():
        if f.is_file():shutil.copy2(f,dst/f.name)
    for folder in ('rtl','sim_lib'):
        if (src/folder).is_dir():shutil.copytree(src/folder,dst/folder)
    if name!='ddr3':
        path=dst/(name+'.idf');idf=ET.parse(path)
        for param in idf.iter():
            if param.findtext('name')=='INIT_FILE':
                kind='rom' if name=='inst_rom' else 'ram'
                param.find('value').text=(ROOT/f'tests/uart_loader/candidates/verify_run_hello/build/loader_{kind}.dat').as_posix()
        idf.write(path,encoding='UTF-8',xml_declaration=True)
input_files={}


def mutate(node):
    if not isinstance(node,list):return
    if node and node[0] in ('_file','_ip','_ip_source_item'):
        rel=node[1].strip('"');old=ROOT/rel
        if rel.startswith(('myriscv/','source/','sim/board_main_selftest/','constraint_check/')):
            new=old
        elif rel.startswith('ipcore/'):
            new=DEST/rel
            if not new.exists():
                assert node[0]=='_file' and rel.endswith('/ddr3.v'),rel
                new=old
        else:new=DEST/rel
        if new==old:
            assert old.is_file(),old
            input_files[rel]=hashlib.sha256(old.read_bytes()).hexdigest()
        node[1]='"'+new.resolve().as_posix()+'"'
    if node and node[0]=='_gci_state':node[1]=['_integer','0']
    for child in node:mutate(child)


mutate(tree)

# This is a static DebugCore input selected by the successful main project;
# synthesis does not generate it. Preserve its settings and relocate only
# the designInputFile reference into the new implementation directory.
fic_source=ROOT/'synthesize/board_top_syn.fic'
fic_target=DEST/'synthesize/board_top_syn.fic'
fic_target.parent.mkdir(parents=True,exist_ok=True)
fic_text=fic_source.read_text()
fic_old='Project.device.designInputFile=D:/riscv/RISCV/synthesize/board_top_syn.adf'
fic_new='Project.device.designInputFile='+(DEST/'synthesize/board_top_syn.adf').resolve().as_posix()
assert fic_old in fic_text
fic_target.write_text(fic_text.replace(fic_old,fic_new))
input_files[fic_source.relative_to(ROOT).as_posix()]=hashlib.sha256(fic_source.read_bytes()).hexdigest()


def render(node,depth=0):
    if not isinstance(node,list):return node
    if not any(isinstance(x,list) for x in node):return '('+' '.join(node)+')'
    pieces=[x for x in node if not isinstance(x,list)]
    children=[x for x in node if isinstance(x,list)]
    return '('+' '.join(pieces)+'\n'+'\n'.join(' '*(depth+4)+render(x,depth+4) for x in children)+'\n'+' '*depth+')'


project=DEST/'combined.pds';project.write_text(render(tree)+'\n')
(DEST/'source_receipt.json').write_text(json.dumps(dict(status='ISOLATED_PDS_INPUTS_PREPARED',
    main_project_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),main_project_unchanged=True,
    original_read_only_inputs=input_files,project=project.relative_to(ROOT).as_posix()),indent=2)+'\n')
print('RESULT: PASS isolated PDS prepared',project,'; main PDS/IP unchanged')
