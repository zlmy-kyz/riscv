"""Record task040 input requirements; does not implement or run tests."""
from pathlib import Path
import hashlib
import json

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
assert not (HERE / 'requirements_identity.json').exists(), 'Preserve requirements receipt'
cpu_hash = '5c26df0229ab00365b2eca1412499f988981fdfe1d1b7292e43a8317f0d47745'
cpu = ROOT / 'myriscv/mycpu_sync.v'
frozen = ROOT / 'sim/cpu_ex_redirect/target_fetch_20261018_a/after/myriscv/mycpu_sync.v'
assert sha(cpu) == sha(frozen) == cpu_hash
baseline = ROOT / 'sim/cpu_ex_redirect/board/review_task039_20261018_01/board_review.json'
review = json.loads(baseline.read_text(encoding='utf-8'))
for rel, digest in review['evidence_sha256'].items():
    assert sha(ROOT / rel) == digest, rel
rels = ['DeepSeek/任务040_ID到EX重定向与错路取指占用归因.md',
        'myriscv/mycpu_sync.v', 'myriscv/csr_defs.vh', 'myriscv/regfile.v',
        'myriscv/alu.v', 'myriscv/br_alu.v', 'myriscv/l_alu.v', 'myriscv/csr_file.v',
        'myriscv/simple_mmio.v', 'sim/br_ex_redirect/mul_behavioral.v',
        'sim/br_ex_redirect/asm.py', 'sim/br_ex_redirect/tb_br_ex_redirect.v',
        'sim/br_ex_redirect/serial_drain_20261018_a/tb_serial_drain.v',
        frozen.relative_to(ROOT).as_posix(), baseline.relative_to(ROOT).as_posix()]
result = dict(status='TASK040_REQUIREMENTS_READY_FOR_DEEPSEEK_IMPLEMENTATION_NOT_RUN',
    input_requirement_sha256={rel: sha(ROOT / rel) for rel in rels},
    baseline_evidence_hashes_verified=len(review['evidence_sha256']),
    existing_trace_limits=['Ordinary bench DELAY=1 has two-edge CPU-visible response.',
        'Serial trace idex group logs live ID taken/target, not registered EX fields.',
        'Existing traces omit full response identity and only print first 40 cycles.'],
    scope='Current039 stage/wrong-path attribution only; no new RTL or board trial.',
    final_test_input_manifest='DeepSeek must create after implementing TB/model/reference and recursively closing includes.',
    dynamic_simulation='NOT_RUN', RTL_modified=False, PDS_started=False, serial_opened=False)
(HERE / 'requirements_identity.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
print(result['status'])
