from pathlib import Path
import hashlib,json
ROOT=Path('D:/riscv/RISCV')
B=ROOT/'sim/uart_loader/build/ack_nack_stage8'
A=B/'attempt1_sources';A.mkdir(exist_ok=True)
report=json.loads((B/'full/results.json').read_text())
entries=[]
for key,digest in report['input_sha256'].items():
    p=Path(key); assert hashlib.sha256(p.read_bytes()).hexdigest()==digest
    q=A/p.relative_to(ROOT);q.parent.mkdir(parents=True,exist_ok=True)
    if q.exists():assert q.read_bytes()==p.read_bytes()
    else:q.write_bytes(p.read_bytes())
    entries.append(dict(source=key,archive=str(q),sha256=digest))
(A/'receipt.json').write_text(json.dumps(dict(status='ATTEMPT1_INPUT_ARCHIVE_PASS',entries=entries),indent=2)+'\n',encoding='utf8')
p=ROOT/'sim/uart_loader/stage8/prepare.py'
s=p.read_text(encoding='utf-8-sig')
s=s.replace("# No change to production sources, timing, or successful ELF/DAT.", "# A FIFO-overflow drop consumes wire input but has no LBU retirement.\ns=s.replace('cpu_lbu>=frame_end', 'lbu_index>=frame_end')\n# No change to production sources, timing, or successful ELF/DAT.")
p.write_text(s,encoding='utf8')
p=ROOT/'sim/uart_loader/stage8/run.py'
s=p.read_text(encoding='utf-8-sig').replace("choices=['full','native']", "choices=['full','native','uart']")
s=s.replace('selected=cases(native=native)', "selected=cases(native=native)\n    if args.suite=='uart': selected=[c for c in selected if c['name'].startswith(('seed_', 'uart_'))]")
p.write_text(s,encoding='utf8')
print('Archived original checker inputs; fix raw wire index after deliberate drop')
