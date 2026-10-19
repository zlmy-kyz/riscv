"""Select latest committed EX CPU in the working tree; preserve the user's index."""
from pathlib import Path
import hashlib
import json
import subprocess

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
TARGET='myriscv/mycpu_sync.v'
sha=lambda b:hashlib.sha256(b).hexdigest()
def git(*args):
    return subprocess.run(['git',*args],cwd=ROOT,capture_output=True,check=True).stdout

assert not (HERE/'restore.json').exists(), 'Preserve existing restoration evidence'
before=(ROOT/TARGET).read_bytes()
candidate=git('show','HEAD:'+TARGET)
assert sha(before)=='b1114fa388b0da4a3c914da38f1b169d607b8ebed839dd018eab37fd0f4a41d3'
assert sha(candidate)=='ef6bfec7853f6b0e93f976c7038ad25cdb4f6e04b14251331fdbf79906cc87e6'
assert b'assign branch_redirect = ex_br_redirect;' in candidate and b'id_ex_br_taken' in candidate
index_before=git('ls-files','--stage','--',TARGET)
staged_before=git('diff','--cached','--',TARGET)
others={p.relative_to(ROOT).as_posix():sha(p.read_bytes()) for p in (ROOT/'myriscv').rglob('*')
        if p.is_file() and p.relative_to(ROOT).as_posix()!=TARGET}
(HERE/'cpu_before_restore.v.txt').write_bytes(before)
(HERE/'staged_before.patch').write_bytes(staged_before)
(HERE/'git_before.txt').write_bytes(git('status','--porcelain=v1','--',TARGET))
(ROOT/TARGET).write_bytes(candidate)
assert (ROOT/TARGET).read_bytes()==candidate
assert git('ls-files','--stage','--',TARGET)==index_before
assert git('diff','--cached','--',TARGET)==staged_before
assert all(sha((ROOT/p).read_bytes())==digest for p,digest in others.items())
(HERE/'git_after.txt').write_bytes(git('status','--porcelain=v1','--',TARGET))
receipt=dict(status='USER_SELECTED_LATEST_EX_CPU_WORKTREE_RESTORED_NOT_FUNCTIONAL_FIX',
    date='2026-10-18',target=TARGET,head=git('rev-parse','HEAD').decode().strip(),
    before_sha256=sha(before),after_sha256=sha(candidate),other_myriscv_files_unchanged=len(others),
    git_index_unchanged=True,staged_prior_revert_preserved=True,
    verification='Exact bytes equal HEAD and archived reviewed EX candidate',
    limits=['Restoration does not fix serial-drain suspect or resolve the failed P300 trial.',
        'Existing staged ID rollback remains in the Git index; PDS reads restored working-tree EX source.',
        'No simulation, PDS, bitstream generation, serial operation or Git commit performed.'])
(HERE/'restore.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps(receipt,ensure_ascii=False))
