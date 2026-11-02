"""Ownership checks and endpoint refresh for a retained fictional DB only."""
import json
from pathlib import Path
import subprocess
import time

import psycopg
from psycopg.conninfo import conninfo_to_dict, make_conninfo


def owned_state(folder):
    state=json.loads((Path(folder)/'session.json').read_text(encoding='utf-8'))
    if state.get('fictional') is not True or state.get('host')!='127.0.0.1' or not state.get('container','').startswith('asg-validation-'):
        raise ValueError('Only the dedicated fictional validation DB is supported')
    if (state.get('gateway_database'),state.get('protected_database'))!=('asg_validation_gateway','asg_validation_business'):
        raise ValueError('Unexpected validation database names')
    if state.get('target_id')!=state['container']:
        raise ValueError('Unexpected validation target ID')
    inspected=json.loads(subprocess.check_output(['docker','inspect',state['container']],stderr=subprocess.PIPE))[0]
    if inspected['Config'].get('Labels',{}).get('asg.validation')!='fictional':
        raise ValueError('Missing fictional DB ownership marker')
    if not any(m.get('Name')==state['container']+'-data'==state.get('volume') for m in inspected['Mounts']):
        raise ValueError('Validation volume does not match')
    return state


def refresh_connections(folder,state):
    folder=Path(folder)
    endpoint=subprocess.check_output(['docker','port',state['container'],'5432/tcp'],stderr=subprocess.PIPE).decode().strip()
    if not endpoint.startswith('127.0.0.1:') or '\n' in endpoint:
        raise ValueError('The validation DB must publish a loopback endpoint only')
    port=int(endpoint.rsplit(':',1)[1])
    for file,db,user in [('admin-dsn.txt','asg_validation_gateway','postgres'),('gateway-dsn.txt','asg_validation_gateway','gateway_app'),('protected-dsn.txt','asg_validation_business','asg_reader')]:
        path=folder/file
        opts=conninfo_to_dict(path.read_text(encoding='utf-8'))
        if opts.get('host')!='127.0.0.1' or opts.get('dbname')!=db or opts.get('user')!=user:
            raise ValueError('Connection does not match the fictional DB')
        path.write_text(make_conninfo(**(opts|{'port':port})),encoding='utf-8')
    state=state|{'port':port}
    (folder/'session.json').write_text(json.dumps(state,indent=2),encoding='utf-8')
    return state


def start_and_wait(folder):
    folder=Path(folder)
    state=owned_state(folder)
    subprocess.run(['docker','start',state['container']],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE)
    state=refresh_connections(folder,state)
    deadline=time.monotonic()+30
    while True:
        try:
            with psycopg.connect((folder/'admin-dsn.txt').read_text(encoding='utf-8')) as c:
                c.execute('SELECT 1').fetchone()
            return state
        except psycopg.OperationalError:
            if time.monotonic()>deadline:raise RuntimeError('Fictional PostgreSQL did not become ready') from None
            time.sleep(.3)
