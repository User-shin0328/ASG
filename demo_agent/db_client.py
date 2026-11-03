"""Company-agent example: authenticated request -> wait for human -> one bounded DB read."""
import argparse
import json
import os
import time
import uuid
from scripts.traffic_generator import send_request


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--gateway',default=os.environ.get('GATEWAY_URL','http://127.0.0.1:8000'))
    parser.add_argument('--dataset',default='operations')
    parser.add_argument('--row-limit',type=int,default=25)
    parser.add_argument('--columns',nargs='+',default=['ticket_id','category','status'])
    parser.add_argument('--purpose',default='운영 지원 업무 현황을 조회하기 위한 사내 에이전트 요청입니다.')
    parser.add_argument('--wait-seconds',type=int,default=900)
    args=parser.parse_args()
    token=os.environ.get('AGENT_ALICE_TOKEN')
    if not token:raise SystemExit('Set AGENT_ALICE_TOKEN in the process environment; do not put tokens in command arguments.')
    headers={'Authorization':'Bearer '+token,'Content-Type':'application/json','Idempotency-Key':str(uuid.uuid4())}
    status,data=send_request(args.gateway+'/v1/db/requests','POST',headers,{'dataset_id':args.dataset,
        'columns':args.columns,'filters':{},'row_limit':args.row_limit,'purpose':args.purpose})
    print(json.dumps({'http':status,'request':data},ensure_ascii=False,indent=2))
    if status not in {200,202}:return 1
    endpoint=args.gateway+'/v1/db/requests/'+data['id']
    deadline=time.monotonic()+args.wait_seconds
    while time.monotonic()<deadline:
        code,detail=send_request(endpoint,headers=headers)
        if code!=200 or detail.get('state') in {'DENIED','REJECTED','EXPIRED'}:return 1
        if detail.get('state')=='APPROVED':
            code,result=send_request(endpoint+'/execute','POST',headers,{})
            print(json.dumps({'http':code,'result':result},ensure_ascii=False,indent=2))
            return 0 if code==200 else 1
        time.sleep(2)
    return 1


if __name__=='__main__':raise SystemExit(main())
