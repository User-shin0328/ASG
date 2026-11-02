"""Open the retained fictional PostgreSQL lab; never takes corporate connection options."""
import argparse
import os
from pathlib import Path
import time
from unittest.mock import patch

from scripts.testbed_launcher import LocalLab
from testing.validation_database import start_and_wait

ROOT=Path(__file__).resolve().parents[1]


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data-dir',type=Path,default=ROOT/'testing/.runtime/postgresql-validation')
    parser.add_argument('--dashboard-port',type=int,default=18863)
    args=parser.parse_args()
    folder=args.data_dir.resolve()
    state=start_and_wait(folder)
    env={'PROTECTED_DB_BACKEND':'postgresql','PROTECTED_DB_TARGET_ID':state['target_id'],
         'PROTECTED_DB_SCHEMA':'asg_access','PROTECTED_DB_DSN_FILE':str(folder/'protected-dsn.txt'),'PROTECTED_DB_LOCAL_TEST':'1'}
    lab=None
    try:
        with patch.dict(os.environ,env):
            lab=LocalLab(folder/'lab',dashboard_port=args.dashboard_port,gateway_database=(folder/'gateway-dsn.txt').read_text(encoding='utf-8')).start()
            print('FICTIONAL PostgreSQL validation dashboard: '+lab.url,flush=True)
            print('Ctrl+C closes the dashboard. The dedicated DB and its data remain available.',flush=True)
            while True:time.sleep(.25)
    except KeyboardInterrupt:pass
    finally:
        if lab:lab.stop()


if __name__=='__main__':main()
