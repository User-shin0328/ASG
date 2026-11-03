"""Bind one acceptance run's reports, logs, source identity and binary evidence."""
from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import uuid


def file_hash(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def source_identity(root):
    root = Path(root)
    commit = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=root).decode().strip()
    names = subprocess.check_output(['git', 'ls-files', '--cached', '--others', '--exclude-standard', '-z'], cwd=root).decode('utf-8').split('\0')
    h = hashlib.sha256()
    prefixes = ('gateway/', 'security_agent/', 'tool_sandbox/', 'demo_agent/', 'dashboard/',
                'config/', 'fixtures/', 'migrations/', 'scripts/', 'testing/', 'tests/', 'launcher/')
    excluded = ('testing/results/', 'testing/screenshots/', 'testing/.runtime/')
    for name in sorted(set(names)):
        path = root / name
        if (name.startswith(prefixes) and not name.startswith(excluded) and path.is_file()
                and path.suffix in {'.py', '.js', '.css', '.html', '.json', '.yaml', '.sql', '.ps1', '.bat', '.lock'}):
            h.update(name.encode('utf-8') + b'\0' + path.read_bytes() + b'\0')
    dirty = bool(subprocess.check_output(['git', 'status', '--porcelain', '--untracked-files=normal'], cwd=root).strip())
    return {'commit': commit, 'source_sha256': h.hexdigest(), 'working_tree_modified': dirty}


@contextmanager
def report_lock(folder):
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    with (folder / '.acceptance.lock').open('a+b') as stream:
        stream.seek(0,os.SEEK_END)
        if stream.tell()==0:
            stream.write(b'0')
            stream.flush()
        stream.seek(0)
        try:
            if os.name == 'nt':
                import msvcrt
                msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            raise RuntimeError('Another acceptance run is writing reports; wait for it to finish.') from None
        yield


def seal(folder):
    folder = Path(folder)
    report = json.loads((folder / 'results.json').read_text(encoding='utf-8'))
    manifest = {'run_id': report['run_id'], 'source': report['source'],
                'executable': report['executable'],
                'files': {p.name: file_hash(p) for p in sorted(folder.iterdir()) if p.is_file() and p.name != 'manifest.json'}}
    (folder / 'manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding='utf-8')
    verify(folder)


def verify(folder):
    folder = Path(folder)
    manifest = json.loads((folder / 'manifest.json').read_text(encoding='utf-8'))
    actual_names = {p.name for p in folder.iterdir() if p.is_file() and p.name != 'manifest.json'}
    if actual_names != set(manifest['files']):
        raise ValueError('Unexpected or missing evidence file')
    for name, expected in manifest['files'].items():
        if Path(name).name != name or file_hash(folder / name) != expected:
            raise ValueError('Evidence file changed: ' + name)
    report = json.loads((folder / 'results.json').read_text(encoding='utf-8'))
    if any(report[key] != manifest[key] for key in ('run_id', 'source', 'executable')):
        raise ValueError('Report identity differs from manifest')
    log = (folder / 'unittest.log').read_text(encoding='utf-8')
    if not log.startswith('ASG_RUN_ID=' + report['run_id'] + '\n'):
        raise ValueError('Regression log belongs to another run')
    if ('ASG_COMMIT='+report['source']['commit']+'\n' not in log
            or 'ASG_SOURCE_SHA256='+report['source']['source_sha256']+'\n' not in log):
        raise ValueError('Regression source identity differs from report')
    match = re.search(r'Ran (\d+) tests', log)
    regression = report['checks'][0]
    if not match or int(match[1]) != regression['actual']['tests']:
        raise ValueError('Regression test count differs from report')
    log_passed = bool(re.search(r'^OK(?: \([^\n]*\))?\s*$', log, re.M)) and 'FAILED (' not in log
    if log_passed != (regression['status'] == 'PASS'):
        raise ValueError('Regression outcome differs from report')
    if report['result'] == 'PASS' and any(c['status'] != 'PASS' for c in report['checks']):
        raise ValueError('Overall outcome differs from checks')
    return {'run_id': report['run_id'], 'files': len(manifest['files']), 'status': 'VALID'}


def publish(folder, results_root):
    """Keep completed runs and previous latest evidence; do not delete reports."""
    folder, results_root = Path(folder).resolve(), Path(results_root).resolve()
    latest = results_root / 'latest'
    previous = results_root / 'history' / ('previous-latest-' + uuid.uuid4().hex)
    for path in (folder, latest, previous):
        if not path.resolve().is_relative_to(results_root):
            raise ValueError('Evidence path is outside the results directory')
    verify(folder)
    if latest.exists():
        previous.parent.mkdir(parents=True, exist_ok=True)
        latest.replace(previous)
    shutil.copytree(folder, latest)
    verify(latest)


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('folder', type=Path, nargs='?', default=Path(__file__).parent / 'results/latest')
    args = parser.parse_args()
    print(json.dumps(verify(args.folder), indent=2))
