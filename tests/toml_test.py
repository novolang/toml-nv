#!/usr/bin/env python3
"""Compare toml-nv with the toml-test corpus.

Run by tests/toml_test.sh with the built harness and a toml-test
checkout.  For every file its `files-toml-1.0.0` list names:

- a valid document must parse, and its tree must equal the upstream
  `.json` file, numbers compared as numbers and date-times as instants;
  the canonical writer, in both styles, must write a document that reads
  back equal, and the editing document must render the text unchanged;
- an invalid document must be refused.

Python's `tomllib`, where the interpreter has it, is a second reader:
every document it accepts must be accepted here, every document it
refuses refused here, and its tree must equal this package's.

The harness is run on batches of files.  A batch whose process fails is
run again one file at a time, so a crash is charged to its file.
"""
import datetime
import json
import math
import os
import subprocess
import sys
import tempfile

try:
    import tomllib
except ImportError:  # Python older than 3.11
    tomllib = None


def run(harness, base, paths):
    with tempfile.NamedTemporaryFile('w', delete=False) as f:
        f.write('\n'.join(os.path.join(base, p) for p in paths) + '\n')
        listing = f.name
    r = subprocess.run([harness, listing], capture_output=True, text=True,
                       errors='replace', timeout=300)
    os.unlink(listing)
    out, cur = {}, None
    for line in r.stdout.splitlines():
        if line.startswith('=== '):
            cur = os.path.relpath(line[4:], base)
            out[cur] = []
        elif cur is not None:
            out[cur].append(line)
    return out, r.returncode


def norm(v):
    if isinstance(v, dict) and set(v) == {'type', 'value'} and isinstance(v['value'], str):
        t, s = v['type'], v['value']
        if t == 'float':
            if s.lstrip('+-') == 'nan':
                return ('float', 'nan')
            if s.lstrip('+') == 'inf':
                return ('float', math.inf)
            if s == '-inf':
                return ('float', -math.inf)
            return ('float', float(s))
        if t == 'integer':
            return (t, int(s))
        if t in ('datetime', 'datetime-local'):
            return (t, datetime.datetime.fromisoformat(s.replace('z', 'Z').replace(' ', 'T')))
        if t == 'date-local':
            return (t, datetime.date.fromisoformat(s))
        if t == 'time-local':
            return (t, datetime.time.fromisoformat(s))
        return (t, s)
    if isinstance(v, dict):
        return {k: norm(x) for k, x in v.items()}
    if isinstance(v, list):
        return [norm(x) for x in v]
    return v


def plain(v):
    """A tagged tree as the plain values tomllib answers."""
    if isinstance(v, dict) and set(v) == {'type', 'value'} and isinstance(v['value'], str):
        return norm(v)[1]
    if isinstance(v, dict):
        return {k: plain(x) for k, x in v.items()}
    if isinstance(v, list):
        return [plain(x) for x in v]
    return v


def plain_py(v):
    """tomllib's tree with every float that is not a number made equal."""
    if isinstance(v, float) and math.isnan(v):
        return 'nan'
    if isinstance(v, bool):
        return 'true' if v else 'false'
    if isinstance(v, dict):
        return {k: plain_py(x) for k, x in v.items()}
    if isinstance(v, list):
        return [plain_py(x) for x in v]
    return v


def main(harness, toml_test):
    base = os.path.join(toml_test, 'tests')
    files = [l.strip() for l in open(os.path.join(base, 'files-toml-1.0.0'))
             if l.strip().endswith('.toml')]
    results = {}
    for i in range(0, len(files), 25):
        part = files[i:i + 25]
        out, rc = run(harness, base, part)
        if rc == 0 and all(p in out for p in part):
            results.update(out)
            continue
        for p in part:
            one, rc1 = run(harness, base, [p])
            results[p] = one.get(p, []) if rc1 == 0 else ['CRASH %d' % rc1]
    fails = []
    for p in files:
        got = results.get(p) or ['']
        if p.startswith('valid/'):
            if not got[0].startswith('OK '):
                fails.append((p, 'refused: ' + got[0]))
                continue
            want = json.load(open(os.path.join(base, p[:-5] + '.json')))
            if norm(json.loads(got[0][3:])) != norm(want):
                fails.append((p, 'the tree differs from the upstream JSON'))
            if len(got) < 2 or got[1] != 'RT standard=ok compact=ok edit-ok':
                fails.append((p, 'round trip: ' + (got[1] if len(got) > 1 else 'missing')))
        elif not got[0].startswith('ERR '):
            fails.append((p, 'accepted: ' + got[0][:80]))
    if tomllib is not None:
        for p in files:
            got = results.get(p) or ['']
            raw = open(os.path.join(base, p), 'rb').read()
            try:
                theirs = tomllib.loads(raw.decode('utf-8'))
            except (UnicodeDecodeError, tomllib.TOMLDecodeError, ValueError):
                theirs = None
            if (theirs is None) != (not got[0].startswith('OK ')):
                fails.append((p, 'tomllib %s it' % ('refuses' if theirs is None else 'accepts')))
            elif theirs is not None and plain(json.loads(got[0][3:])) != plain_py(theirs):
                fails.append((p, 'the tree differs from tomllib\'s'))
    valid = sum(1 for p in files if p.startswith('valid/'))
    print('toml-test: %d valid and %d invalid documents, %d failure(s)'
          % (valid, len(files) - valid, len(fails)))
    for p, why in fails:
        print('  ✗ %s: %s' % (p, why))
    return 0 if not fails else 1


if __name__ == '__main__':
    sys.exit(main(sys.argv[1], sys.argv[2]))
