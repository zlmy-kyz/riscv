"""Static source/constraint identity audit. Never runs HDL, PDS or a board tool."""
from pathlib import Path
import hashlib,json,re
root=Path(__file__).resolve().parents[2]
baseline=root/'sim/camera_double/baseline_single_20261015'
out=root/'sim/camera_double/static_20261015_a'
sha=lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
manifest=json.loads((baseline/'manifest.json').read_text(encoding='utf-8'))
changed={
    'myriscv/camera_mmio.v','myriscv/ov5640_capture.v',
    'myriscv/data_bus_interconnect.v','myriscv/inst_bus_interconnect.v',
    'myriscv/dual_sram_to_pango_ddr_bridge.v','myriscv/soc_top.v','myriscv/soc_ddr3_top.v',
    'constraint_check/temp_constraint_file.fdc','fdc/camera_single.fdc'}
before=[]; after=[]; unchanged=[]
for row in manifest['files']:
    n=row['path']; assert sha(baseline/n)==row['sha256'],n
    current=sha(root/n)
    if n in changed:
        assert current!=row['sha256'],n
        before.append(row); after.append(dict(path=n,sha256=current))
    else:
        assert current==row['sha256'],n
        unchanged.append(n)
assert len(after)==len(changed)
assert sha(root/manifest['reference'])==manifest['reference_sha256']
firmware={
 'tests/camera_loop100/build/camera_loop100_20261015_a/program.bin':
 '82f6698dfeb820219a698b5d752c9c0d033e734ecde52c99b33ad805ad3c7cc6',
 'tests/camera_uart/build/camera_uart_20261015_a/program.bin':
 '373940dab9b1c1a4e444d5fa4467580b490d4bdd288fc4c516c90f32aed9f529'}
for n,h in firmware.items(): assert sha(root/n)==h,n
def commands(p):
    return [x for x in p.read_text().splitlines() if x.startswith(('create_clock -name {camera_pclk}',
            'set_input_delay ','set_max_delay ','set_false_path '))]
active=commands(root/'constraint_check/temp_constraint_file.fdc')
reference=commands(root/'fdc/camera_single.fdc')
assert active==reference
assert len(active)==len(set(active))==15
assert sum('buffer_crc*' in c for c in active)==1
assert sum('skip_warmup_sync*' in c for c in active)==1
pds=(root/'RISCV.pds').read_text()
assert '(_file "constraint_check/temp_constraint_file.fdc"' in pds
assert '(_file "fdc/camera_single.fdc"' not in pds
logs=['syntax_board_final.log','syntax_camera_disabled.log']
for log in logs: assert (out/log).read_text().strip().endswith('exit_code=0'),log
result=dict(status='DOUBLE_BUFFER_RTL_STATIC_PREPARED_PENDING_PDS_AND_FUNCTIONAL_VALIDATION',
 date='2026-10-15',abi='43414d02',buffer_bases=['41000000','41200000'],
 native_addresses=['00400000','00480000'],per_frame_bytes=1843200,
 source_before=before,source_after=after,unchanged_baseline_files=unchanged,
 successful_firmware_unchanged=firmware,successful_single_buffer_receipt=manifest['reference'],
 camera_timing_commands=len(active),syntax_logs=logs,
 syntax_scope='Icarus null target with missing vendor/IP modules ignored; not simulation',
 pds_executed=False,hdl_simulation_executed=False,board_executed=False,
 review_points=['Only FREE is allocated; captured bank independent from software SELECT',
 'Claim/release require ownership and matching sequence token',
 'Both occupied waits with no automatic overwrite; no capture timeout while waiting',
 'STOP blocks further allocation and drains current frame; ABORT preserves other valid buffers',
 'Publication waits for exact W count, valid frame end and DMA idle',
 '4MiB no-hit/no-fill and instruction exclusion; only claimed slot readable in dual mode',
 'Warm-up bypass stable before synchronized run; FIFO resets between acquisitions',
 'Functional concurrency, response ordering, CDC endpoint matching and timing remain unverified'])
(out/'review.json').write_text(json.dumps(result,indent=2,ensure_ascii=False),encoding='utf-8')
print(json.dumps(dict(status=result['status'],changed_files=len(after),
 unchanged_baseline_files=len(unchanged),successful_bins_unchanged=2,
 timing_commands=len(active),syntax_exits=[0,0]),ensure_ascii=False))
