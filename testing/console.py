"""Compatibility console for the local dashboard simulator. No tokens on the command line."""
from scripts.traffic_generator import send_request
import argparse
import json


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--dashboard',default='http://127.0.0.1:18511')
    args=parser.parse_args()
    modes=['normal','cross-tenant','injection','obfuscation','unapproved','audit-verify','custom']
    while True:
        print('\nASG: 1 Read / 2 Cross-tenant / 3 Injection / 4 Unicode / 5 Approval / 6 Audit / 7 Custom / 0 Exit')
        try:
            choice=input('Select: ').strip()
            if choice=='0':return
            if choice not in [str(n) for n in range(1,8)]:continue
            mode=modes[int(choice)-1]
            data={'text':input('Text: ')} if mode=='custom' else {}
            code,result=send_request(args.dashboard+'/api/generate?mode='+mode,'POST',{'X-ASG-Request':'1'},data)
            print(code,json.dumps(result,ensure_ascii=False,indent=2))
        except (EOFError,KeyboardInterrupt):return


if __name__=='__main__':main()
