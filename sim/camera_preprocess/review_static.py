"""Source integration and identity review only; does not simulate or run PDS."""
from pathlib import Path
import hashlib,json
root=Path(__file__).resolve().parents[2]
base=root/'sim/camera_preprocess/baseline_double_20261015'
out=root/'sim/camera_preprocess/static_20261015_a'
sha=lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
baseline=json.loads((base/'manifest.json').read_text())
allowed={'myriscv/camera_mmio.v','myriscv/camera_ddr_write_arbiter.v',
         'myriscv/data_bus_interconnect.v','myriscv/inst_bus_interconnect.v',
         'myriscv/dual_sram_to_pango_ddr_bridge.v','myriscv/soc_top.v',
         'myriscv/soc_ddr3_top.v','myriscv/board_top.v','RISCV.pds'}
rows=[]; unchanged=[]
for old in baseline['files']:
 n=old['path']; assert sha(base/n)==old['sha256'],n
 current=sha(root/n)
 if n in allowed:
  assert current!=old['sha256'],n
  rows.append(dict(path=n,before_sha256=old['sha256'],sha256=current))
 else:
  assert current==old['sha256'],n
  unchanged.append(n)
assert len(rows)==len(allowed)
assert sha(root/baseline['reference'])==baseline['reference_sha256']
pds=(root/'RISCV.pds').read_text()
for n in ['preprocess_mmio','preprocess_ddr_read_arbiter']:
 entry=f'                (_file "myriscv/{n}.v"\n                    (_format verilog)\n                )\n'
 assert pds.count(entry)==2
 pds=pds.replace(entry,'')
 rows.append(dict(path=f'myriscv/{n}.v',sha256=sha(root/f'myriscv/{n}.v')))
assert pds==(base/'RISCV.pds').read_text(), 'Only two added source entries per source group allowed'
assert '(_file "constraint_check/temp_constraint_file.fdc"' in pds
for log in ['syntax_board_final.log','syntax_disabled.log']:
 assert (out/log).read_text().strip().endswith('exit_code=0'),log
# Arithmetic audit of the fixed contract (not a DUT or functional simulation).
coords=[(2*i+1)*15//4 for i in range(96)]
assert coords[0]==3 and coords[-1]==716
assert all(coords[i+1]-coords[i]==(8 if i%2==0 else 7) for i in range(95))
assert 3*1280*2+283*2==0x2036
assert 96*96*3==864*32==27648
report=dict(status='PREPROCESS_RTL_STATIC_PREPARED_PENDING_PDS_AND_FUNCTIONAL_VALIDATION',
 date='2026-10-15',inputs=rows,unchanged_baseline_files=unchanged,
 successful_double_buffer_receipt_unchanged=True,
 preprocessing=dict(crop=[280,0,720,720],output=[96,96,3],
    sample_first=[283,3],sample_last=[996,716],output_base='42000000',
    read_beats=9216,write_beats=864,bytes=27648),
 syntax_scope='Icarus -tnull -i, missing vendor/IP modules ignored; two configurations exit 0',
 pds_run=False,hdl_simulation_run=False,board_run=False,
 review_points=['Camera RELEASE blocked by external hold while job busy',
 'Active source and sequence frozen independently of software selectors',
 'Read owner stable from AR presentation through counted last R; supports immediate R',
 'Full 32-byte native output writes including RGB cross-beat boundaries',
 'ABORT/timeout drain exposed AR/AW; fatal read protocol error quarantines until global reset',
 'DONE after final W, exact counts; output protected/no-hit/no-fill/no-execute',
 'No new clock domain, no DDR IP or constraint relaxation',
 'These are static review points, not observed functional or timing coverage'])
(out/'review.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps(dict(status=report['status'],existing_changed=len(allowed),new_sources=2,
                     unchanged_baseline=len(unchanged),syntax_exits=[0,0]),ensure_ascii=False))
