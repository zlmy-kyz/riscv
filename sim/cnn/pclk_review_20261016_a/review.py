"""Read existing PDS evidence only; never launch implementation or change inputs."""
import hashlib,json,re,shutil
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    receipt=HERE/'review.json';assert not receipt.exists(),'preserve original review identity'
    snapshot=HERE/'evidence';snapshot.mkdir(exist_ok=False)
    files=['report_timing/board_top.rtr','report_timing/run.log','device_map/run.log','device_map/board_top.dmr',
           'place_route/board_top.prr','constraint_check/temp_constraint_file.fdc','fdc/camera_single.fdc',
           'myriscv/ov5640_capture.v','myriscv/ov5640_config_rom.v','place_route/multiseed_result.csv']
    identities={}
    for n in files:
        p=ROOT/n;q=snapshot/n;q.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,q);identities[n]=sha(q);assert sha(p)==identities[n]
    text=(snapshot/files[0]).read_text();mapping=(snapshot/'device_map/run.log').read_text();prr=(snapshot/'place_route/board_top.prr').read_text()
    fdc=(snapshot/'constraint_check/temp_constraint_file.fdc').read_text()
    expected=json.loads((ROOT/'sim/cnn/board_diag_20261016_a/ready_review.json').read_text())['design_sha256']
    assert all(sha(ROOT/n)==h for n,h in expected.items()),'RTL no longer matches sealed latest repair'
    metrics={}
    for kind,corner in [('Setup','Slow'),('Setup','Fast'),('Hold','Slow'),('Hold','Fast')]:
        section=text.split(f'{kind} Summary({corner} Corner):',1)[1].split('====',1)[0]
        row=re.search(r'^\s*camera_pclk\s+camera_pclk\s+(-?\d+\.\d+)\s+(-?\d+\.\d+)\s+(\d+)\s+(\d+)\s*$',section,re.M);assert row
        slack,total,failing,endpoints=map(float,row.groups());assert slack>0 and total==0 and failing==0
        metrics[kind.lower()+'_'+corner.lower()]=dict(slack_ns=slack,total_negative_slack_ns=total,failing_endpoints=int(failing),endpoints=int(endpoints))
    assert 'Design Summary : All Constraints Met.' in text
    packed=[]
    for line in mapping.splitlines():
        if 'u_capture/' in line and 'has been packed in "IFF"' in line and line.endswith('success.'):packed.append(line)
    assert len(packed)==10
    ports=[]
    for line in prr.splitlines():
        if re.search(r'\| camera_(data\[\d\]|href|vsync)\s',line):
            fields=[x.strip() for x in line.split('|')[1:]];assert fields[-1]=='IREGIS'
            ports.append(dict(port=fields[0],pin=fields[2],bank=fields[3],io_register=fields[-1]))
    assert len(ports)==10
    assert '-clock_fall -max 3.000' in fdc and '-clock_fall -min 0.000' in fdc
    m=re.search(r'Startpoint\s*:\s*camera_data\[2\] \(port\).*?Slack \(MET\)\s+(\d+\.\d+)',text,re.S);assert m
    d2=m.group();assert 'IOLHR_16_828/DI' in d2 and 'max (fast corner)' in d2 and float(m[1])==3.072
    (HERE/'d2_detailed_path.txt').write_text(d2+'\n')
    result=dict(status='EXISTING_PDS_PCLK_STA_MET_AND_ALL_10_DVP_IFF_PACKED',
        report_tool_date=re.search(r'\| Date\s*:\s*(.*?)\s*\|',text)[1],
        design='board_top PG2L200H FBB676 -6',metrics=metrics,ports=ports,mapper_success_lines=packed,
        D2=dict(pin='K26',site='IOLHR_16_828',setup_fast_slack_ns=3.072,input_external_delay_ns=3.0,data_arrival_ns=8.580,data_required_ns=11.652),
        clock_contract=dict(period_ns=10,launch='falling',capture='rising',input_delay_min_ns=0,input_delay_max_ns=3,
                            status='implementation target; sensor launch polarity and board skew not measured'),
        all_40_sealed_RTL_and_include_identities_match=True,
        detailed_report_limit='Existing selected worst paths; not all 10 individual input setup/hold paths are printed',
        conclusion='No reported PCLK setup/hold violation and no missed DVP IO packing. Color-dot cause unresolved; physical input timing/phase/voltage and source DDR path not excluded.',
        actual_downloaded_bitstream_identity='not independently established by these on-disk reports',
        source_sha256=identities,RTL_modified=False,FDC_modified=False,PDS_started=False,HDL_run=False,
        key_HDL='NOT_COMPLETED',raw_board_logs_modified=False)
    receipt.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:result[k] for k in ('status','metrics','all_40_sealed_RTL_and_include_identities_match')},indent=2))
if __name__=='__main__':main()
