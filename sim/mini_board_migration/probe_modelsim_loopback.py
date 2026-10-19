"""Local TCP loopback-only preflight; never runs ModelSim or changes host settings."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import socket


def probe(family,address):
    stage='create_listener';port=None
    try:
        with socket.socket(family,socket.SOCK_STREAM) as listener:
            listener.settimeout(2)
            stage='bind_loopback';listener.bind((address,0));port=listener.getsockname()[1]
            stage='listen';listener.listen(1)
            with socket.socket(family,socket.SOCK_STREAM) as client:
                client.settimeout(2)
                stage='connect_loopback';client.connect((address,port))
                stage='accept';peer,_=listener.accept()
                with peer:
                    peer.settimeout(2)
                    stage='send_receive';client.sendall(b'LOCAL_RPC_PREFLIGHT')
                    assert peer.recv(64)==b'LOCAL_RPC_PREFLIGHT'
        return dict(address=address,port=port,status='PASS',stage='send_receive_complete')
    except Exception as exc:
        return dict(address=address,port=port,status='FAIL',stage=stage,
                    error_type=type(exc).__name__,errno=getattr(exc,'errno',None),
                    winerror=getattr(exc,'winerror',None),message=str(exc))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--context',required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    assert not args.output.exists(),'Preserve previous probe evidence'
    results=[probe(socket.AF_INET,'127.0.0.1'),probe(socket.AF_INET6,'::1')]
    report=dict(context_label=args.context,time_utc=datetime.now(timezone.utc).isoformat(),
        scope='IPv4/IPv6 TCP loopback only; ephemeral ports; 2-second socket limits',
        host_settings_changed=False,ModelSim_started=False,results=results)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(report,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    print(json.dumps(report,indent=2,ensure_ascii=False))


if __name__=='__main__':main()
