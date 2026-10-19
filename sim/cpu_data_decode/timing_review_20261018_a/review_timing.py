"""Observe current PDS timing report and source identities; no implementation or HDL."""
from pathlib import Path
import hashlib
import json
import re

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
TARGET = HERE/'review.json'
assert not TARGET.exists(), 'Preserve existing review'
prior_path = ROOT/'sim/cpu_data_decode/preparation_20261018_a/after_manifest.json'
prior = json.loads(prior_path.read_text(encoding='utf-8'))
sha = lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
current = {k:sha(ROOT/k) for k in prior}
changed = [k for k in prior if prior[k] != current[k]]
assert set(changed) <= {'RISCV.pds','report_timing/board_top.rtr'},changed
assert current['myriscv/data_bus_interconnect.v'] == 'e1aca083d8343fb454575052bdd3134730a803e803497fa387b9bbda4a0aa847'
observed = HERE/'observed'
observed.mkdir(exist_ok=False)
for name in ('report_timing/board_top.rtr','report_timing/run.log','RISCV.pds'):
    dst = observed/name
    dst.parent.mkdir(parents=True,exist_ok=True)
    dst.write_bytes((ROOT/name).read_bytes())
s = (observed/'report_timing/board_top.rtr').read_text(encoding='utf-8')
paths = []
for m in re.finditer(r'Startpoint\s*:\s*(.*?)\nEndpoint\s*:\s*(.*?)\nPath Group\s*:\s*(.*?)\n(.*?)(?=Startpoint|\Z)',s,re.S):
    if m[3].strip() != 'ddrphy_sysclk' or 'max (slow corner)' not in m[4] or 'sequential timing path' not in m[4]:
        continue
    logic = float(re.search(r'Logic:\s*([\d.]+)ns',m[4])[1])
    route = float(re.search(r'Route:\s*([\d.]+)ns',m[4])[1])
    paths.append(dict(start=m[1].strip(),end=m[2].strip(),
        slack_ns=float(re.search(r'Slack \(\w+\)\s+([-\d.]+)',m[4])[1]),
        levels=int(re.search(r'Logic Levels:\s*(\d+)',m[4])[1]),logic_ns=logic,route_ns=route,
        datapath_ns=round(logic+route,3)))
paths.sort(key=lambda x:x['slack_ns'])
log = (observed/'report_timing/run.log').read_text(encoding='utf-8')
errors = [line for line in log.splitlines() if re.match(r'\s*(?:E:|ERROR\b|Error:)',line)]
assert 'Report timing is finished successfully.' in log and not errors
assert 'Design Summary : All Constraints Met.' in s
out = dict(status='TASK037_CURRENT_TIMING_REPORT_MET_SOURCE_OBSERVATION_ONLY',
    report_date=re.search(r'\| Date\s*:\s*(.*?)\n',s)[1].strip(),
    source_manifest_sha256=sha(prior_path),current_input_sha256=current,
    changed_since_static=changed,
    observed_sha256={p.relative_to(observed).as_posix():sha(p) for p in observed.rglob('*') if p.is_file()},
    core_mhz=93.75,slow_wns_ns=0.240,slow_tns_ns=0.0,setup_failing_endpoints=0,
    estimated_fmax_mhz=95.9081,camera_setup_wns_ns=0.893,core_fast_setup_wns_ns=4.530,
    previous_core_wns_ns=0.115,wns_improvement_ns=0.125,
    top_reported_core_paths=paths[:3],
    log_completed=True,error_lines=errors,
    critical_path_segments_ns=[dict(segment='data_q to data_rsp_rdata, including clock-to-Q',delay=1.927),
        dict(segment='load lane/format and MEM forwarding to id_rs1',delay=2.854),
        dict(segment='branch magnitude compare and taken select',delay=2.136),
        dict(segment='exception/frontend/inst interconnect to overlap accept CE',delay=3.068)],
    limits=['Observed report and current sources; not an independent reconstruction of implemented PDS inputs or FPGA programming.',
        'Existing constraints and pre-silicon models only; external-port constraint warnings retained in original log.',
        'Only report-selected top paths are known; paths no longer listed are not proven eliminated.',
        '037 functional/board acceptance pending; no RTL change, simulation, implementation or serial action in this review.'])
TARGET.write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps({k:out[k] for k in ('status','core_mhz','slow_wns_ns','wns_improvement_ns','top_reported_core_paths')}))
