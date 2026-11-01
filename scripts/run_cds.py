#!/usr/bin/env python3
"""Build and run finite CDSChecker harnesses; never interpret a crash as a pass."""
from __future__ import annotations
import argparse, hashlib, json, os, platform, re, subprocess, sys, time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
VENDOR=ROOT/'vendor/cdschecker'
OUT=ROOT/'results/cds'
EXPECTED_REV='5c4efe5cd8bdfe1e85138396109876a121ca61d1'
TESTS={
 'peterson_entry_relaxed': ('entry assertion', 'two threads; one entry guard observation each; no unlock'),
 'peterson_entry_acqrel': ('entry assertion', 'two threads; one entry guard observation each; no unlock'),
 'peterson_entry_seqcst': ('entry assertion', 'two threads; one entry guard observation each; no unlock'),
 'peterson_race_relaxed': ('instrumented payload race', 'two threads; one acquisition each; at most two guard observations; bounded withdrawal'),
 'peterson_race_acqrel': ('instrumented payload race', 'two threads; one acquisition each; at most two guard observations; bounded withdrawal'),
 'peterson_race_seqcst': ('instrumented payload race', 'two threads; one acquisition each; at most two guard observations; bounded withdrawal'),
 'spinlock_acqrel': ('payload race and increment assertion', 'two threads; one test-and-set try-lock each'),
 'ticket_acqrel': ('payload race and increment assertion', 'two threads; one ticket each; at most three serving polls'),
 'spsc_queue_ra': ('payload race and publication assertion', 'two threads; one slot; one item; one consumer observation; no slot reuse'),
}
COUNTERS={
 'complete_bug_free':'Number of complete, bug-free executions',
 'redundant':'Number of redundant executions',
 'buggy':'Number of buggy executions',
 'infeasible':'Number of infeasible executions',
 'total':'Total executions',
}
def run(cmd, log, *, cwd=ROOT, timeout=120, env=None):
    start=time.monotonic()
    try:
        result=subprocess.run([str(x) for x in cmd],cwd=cwd,env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,timeout=timeout)
        content=result.stdout; code=result.returncode; timed_out=False
    except subprocess.TimeoutExpired as exc:
        content=exc.stdout or b''
        if isinstance(content,bytes): content=content.decode(errors='replace')
        content+='\nRUNNER: TIMEOUT; NO VERIFICATION RESULT\n';code=None;timed_out=True
    log.write_text(content)
    return content,code,timed_out,round(time.monotonic()-start,6)
def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--test',choices=list(TESTS),action='append',help='run selected harness(es), default all')
    ap.add_argument('--timeout',type=int,default=120,help='per harness seconds (timeouts are errors)')
    args=ap.parse_args()
    OUT.mkdir(parents=True,exist_ok=True);(OUT/'bin').mkdir(exist_ok=True)
    if not (VENDOR/'Makefile').exists():
        print('Missing vendor/cdschecker. Obtain verified public upstream computersforpeace/model-checker; see docs/CDSCHECKER.md.',file=sys.stderr);return 2
    # The sole source compatibility patch raises pre-main allocator capacity;
    # it does not change the checker memory-model algorithms.
    mem=VENDOR/'mymemory.cc'
    source=mem.read_text()
    if '#define BOOTSTRAPBYTES 4096' in source:
        mem.write_text(source.replace('#define BOOTSTRAPBYTES 4096','#define BOOTSTRAPBYTES (1024 * 1024)'))
    patch_path=ROOT/'scripts/patches/cdschecker-bootstrap.patch'
    (OUT/'bootstrap.patch').write_text(patch_path.read_text())
    build=['make','-j2','libmodel.so','CXX=g++ -std=c++11','CPPFLAGS=-Wall -g -O0 -Iinclude -I.']
    stamp=VENDOR/'.cs554-build-flags'
    desired='c++11 O0 bootstrap-1MiB v1\n'
    if not stamp.exists() or stamp.read_text()!=desired:
        _,clean_code,_,_=run(['make','clean'],OUT/'clean.log',cwd=VENDOR)
        if clean_code!=0:return 2
    build_output,build_code,_,_=run(build,OUT/'build.log',cwd=VENDOR)
    if build_code!=0:
        print('Checker build failed; see results/cds/build.log',file=sys.stderr);return 2
    stamp.write_text(desired)
    metadata=json.loads((VENDOR/'CS554_UPSTREAM.json').read_text())
    revision=metadata['revision']
    if (VENDOR/'.git').exists():
        revision=subprocess.run(['git','rev-parse','HEAD'],cwd=VENDOR,capture_output=True,text=True,check=True).stdout.strip()
    if revision!=EXPECTED_REV:
        print('Unexpected checker revision; refusing to mix versions.',file=sys.stderr);return 2
    compiler=subprocess.run(['g++','--version'],capture_output=True,text=True).stdout.splitlines()[0]
    summary={'schema_version':1,'checker':'CDSChecker','upstream':'https://github.com/computersforpeace/model-checker','revision':revision,
        'expected_revision':EXPECTED_REV,'platform':platform.platform(),'compiler':compiler,'checker_build_command':build,
        'compatibility_patch':'results/cds/bootstrap.patch','checker_options':'No CLI overrides; defaults saved in results/cds/checker-help.log',
        'model':'historical CDSChecker C11/C++11 implementation; not formal RA/SRA',
        'scope_note':'Finite harness safety checks only. Total includes infeasible/redundant candidates. Race reports are not overlap witnesses. No liveness or unbounded correctness claim.',
        'tests':[]}
    env=dict(os.environ);env['LD_LIBRARY_PATH']=str(VENDOR)
    failure=False
    for name in args.test or TESTS:
        src=ROOT/'cdschecker_tests'/f'{name}.cc';binary=OUT/'bin'/name
        command=['g++','-std=c++11','-O0','-g','-no-pie','-Wl,-z,now','-I'+str(VENDOR/'include'),'-I'+str(VENDOR),str(src),'-L'+str(VENDOR),'-lmodel','-o',str(binary)]
        _,code,_,_=run(command,OUT/f'{name}.build.log')
        row={'test':name,'property':TESTS[name][0],'bounds':TESTS[name][1],'compile_command':command,'command':[str(binary)],'log':str((OUT/f'{name}.log').relative_to(ROOT)),
             'source_sha256':hashlib.sha256(src.read_bytes()).hexdigest(),
             'source_files_sha256':{str(f.relative_to(ROOT)):hashlib.sha256(f.read_bytes()).hexdigest() for f in [src]+([ROOT/'cdschecker_tests/peterson_entry.h'] if name.startswith('peterson_entry') else [ROOT/'cdschecker_tests/peterson_race.h'] if name.startswith('peterson_race') else [])},
             'status':'compile_error'}
        if code==0:
            if not (OUT/'checker-help.log').exists():run([binary,'-h'],OUT/'checker-help.log',env=env)
            content,code,timed_out,elapsed=run([binary],OUT/f'{name}.log',env=env,timeout=args.timeout)
            row.update(returncode=code,timed_out=timed_out,seconds=elapsed)
            for key,label in COUNTERS.items():
                matches=re.findall(re.escape(label)+r':\s*(\d+)',content)
                row[key]=int(matches[-1]) if matches else None
            completed=(code==0 and 'Model-checking complete:' in content and all(row[k] is not None for k in COUNTERS))
            row['status']='completed' if completed else ('timeout' if timed_out else 'checker_error')
            row['race_report_mentions']=len(re.findall(r'Data race detected',content))
            row['assertion_report_mentions']=len(re.findall(r'Program has hit assertion',content))
            row['report_count_note']='Diagnostic mentions, not unique executions; a single 32-bit race may generate byte-address reports.'
            if completed and row['total']!=sum(row[k] for k in ['complete_bug_free','redundant','buggy','infeasible']):row['status']='counter_parse_error'
        if row['status']=='completed':
            expected_bug = name in {'peterson_entry_relaxed','peterson_entry_acqrel','peterson_race_relaxed','peterson_race_acqrel'}
            row['expected_bug_reachable']=expected_bug
            row['calibration_matches']=bool(row['buggy']>0)==expected_bug
            if name.startswith('peterson_entry') and expected_bug:
                row['calibration_matches'] &= row['assertion_report_mentions']>0 and row['race_report_mentions']==0
            if name.startswith('peterson_race') and expected_bug:
                row['calibration_matches'] &= row['race_report_mentions']>0 and row['assertion_report_mentions']==0
            if not expected_bug:
                row['calibration_matches'] &= row['race_report_mentions']==0 and row['assertion_report_mentions']==0
            if not row['calibration_matches']:row['status']='calibration_mismatch'
        summary['tests'].append(row)
        failure |= row['status']!='completed'
        print(f"{name}: {row['status']} total={row.get('total')} buggy={row.get('buggy')}")
    (ROOT/'results/cds_summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    return 1 if failure else 0
if __name__=='__main__':raise SystemExit(main())
