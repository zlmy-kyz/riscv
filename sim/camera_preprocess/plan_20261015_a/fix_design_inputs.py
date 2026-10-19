"""Sol fixes design/contract/protected evidence identity for DeepSeek test development.
This is not the final test seal and does not run HDL, build firmware, PDS or serial.
"""
import hashlib
import json
import shutil
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
TASK = 'DeepSeek/预处理96RGB888_逐字节参考与串口导图测试_2026-10-15.md'
CONTRACT = 'doc/camera/OV5640预处理96RGB888与DDR接口_2026-10-15.md'


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def read(p):
    return json.loads(Path(p).read_text(encoding='utf-8'))


def main():
    target = HERE/'design_inputs.json'
    assert not target.exists() and not (HERE/'design_snapshot').exists()
    prior = read(ROOT/'sim/camera_double/key_20261016_b/inputs.json')
    static = read(ROOT/'sim/camera_preprocess/static_20261015_a/review.json')
    for item in static['inputs']:
        if item['path'].startswith('myriscv/'):
            assert sha(ROOT/item['path']) == item['sha256'], item['path']
    names = {n for n in prior['project_sha256'] if n.startswith(('ipcore/','MyCpu_test/'))}
    names.update(p.relative_to(ROOT).as_posix() for p in (ROOT/'myriscv').iterdir()
                 if p.is_file() and p.suffix in ('.v','.vh','.sv','.svh'))
    design = {n:sha(ROOT/n) for n in sorted(names)}
    protected = dict(prior['protected_history_sha256'])
    board = ROOT/'sim/camera_double/board/abi2_100_20261015_01'
    receipt = board/'sol_review.json'
    assert sha(receipt) == '538ddaaa51acffd68c2dc2dd4f743857c5a9ecf0aa83b589faeca3a58a26e5c9'
    for n,d in read(receipt)['original_evidence_sha256'].items():
        assert sha(board/n) == d
    for p in board.iterdir():
        if p.is_file():
            protected[p.relative_to(ROOT).as_posix()] = sha(p)
    # Preserve the previous design snapshot, not its now intentionally changed live sources.
    base = ROOT/'sim/camera_preprocess/baseline_double_20261015'
    for f in read(base/'manifest.json')['files']:
        assert sha(base/f['path']) == f['sha256'], f['path']
        protected[(base/f['path']).relative_to(ROOT).as_posix()] = f['sha256']
    protected[(base/'manifest.json').relative_to(ROOT).as_posix()] = sha(base/'manifest.json')
    for n,d in protected.items():
        assert sha(ROOT/n) == d, n
    refs = {n:sha(ROOT/n) for n in (TASK,CONTRACT,'AGENTS.md',
        'sim/camera_preprocess/static_20261015_a/review.json',
        'sim/camera_double/key_20261016_b/inputs.json',
        'sim/camera_double/key_20261016_b/review_b/review.json',
        'tests/camera_uart/startup.S','tests/camera_uart/linker.ld',
        'tests/camera_uart/crc32.c','tests/camera_uart/crc32.h',
        'tools/camera_uart/capture.py','tools/camera_uart/protocol.py',
        'tools/uart_loader/candidates/bsp_workflow/plan.py',
        'tools/uart_loader/candidates/bsp_workflow/application.py',
        'tools/uart_loader/candidates/verify_run_hello/protocol.py')}
    for n in design:
        dst = HERE/'design_snapshot'/n
        dst.parent.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(ROOT/n,dst)
        assert sha(dst) == design[n]
    m = dict(status='DESIGN_INPUTS_FIXED_TEST_IMPLEMENTATION_AUTHORIZED_NOT_RUN',
        date='2026-10-15',timezone='America/Denver',
        timing=dict(source='Human reply in current conversation',confirmation='已通过，可准备封存与执行',PDS_independently_reaudited=False),
        task_path=TASK,contract_path=CONTRACT,
        design_sha256=design,reference_dependencies_sha256=refs,protected_sha256=protected,
        snapshot='sim/camera_preprocess/plan_20261015_a/design_snapshot',
        prep_script_sha256=sha(__file__),
        final_test_manifest='NOT_CREATED_DEEPSEEK_MUST_REGISTER_FINAL_TEST_CODE_AND_RECURSIVE_DEPENDENCIES',
        planned_jobs=['unit','soc'],wall_timeout_seconds=dict(unit=300,soc=600,checker=120),
        planned_run='sim/camera_preprocess/key_20261015_a/build/ds_pp_key_20261015_a',
        roles=dict(Sol='Requirements, acceptance, identity and raw review',DeepSeek='Implement tests/models/software/tools/seal; execute frozen key group',user='PDS, download, KEY0 and actual serial'),
        HDL='NOT_RUN',board='NOT_RUN',firmware='NOT_BUILT',serial_opened=False,
        scope='No RTL/IP changes, PDS implementation or bitstream re-audit; no legacy full regression; final test seal remains required')
    target.write_text(json.dumps(m,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(dict(status=m['status'],manifest_sha256=sha(target),design_files=len(design),protected_files=len(protected),reference_files=len(refs)),indent=2))


if __name__ == '__main__':
    main()
