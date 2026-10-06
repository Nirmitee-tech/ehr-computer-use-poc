#!/usr/bin/env python3
"""Save scoped test measurements; do not treat them as healthcare readiness evidence."""
import argparse
import datetime
import json
import os
import platform
import sys
import unittest
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
parser=argparse.ArgumentParser()
parser.add_argument('--native',action='store_true')
parser.add_argument('--x11',action='store_true')
parser.add_argument('--windows',action='store_true')
parser.add_argument('--vision',action='store_true')
parser.add_argument('--output',default='docs/evidence/validation.json')
args=parser.parse_args()
suites=[('unit',['tests.test_unit','tests.test_planner_unit','tests.test_platform_unit','tests.test_driver_unit']),('http_integration',['tests.test_integration'])]
if args.native:
    os.environ['OPENCLERK_NATIVE_TESTS']='1';suites.append(('macos_native',['tests.test_native_integration']))
if args.x11:
    os.environ['OPENCLERK_X11_TESTS']='1';suites.append(('linux_x11_native',['tests.test_linux_native_integration']))
if args.windows:
    os.environ['OPENCLERK_WINDOWS_TESTS']='1';suites.append(('windows_native',['tests.test_windows_native_integration']))
if args.vision:
    os.environ['OPENCLERK_LIVE_MODEL_TESTS']='1';suites.append(('live_local_vision',['tests.test_live_model_integration']))
report={'measured_at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'source':'scripts/verify.py','scope':'Local synthetic desktop and HTTP behavior; no real EHR, patient or payer data',
        'counting_unit':'unittest test cases; skipped cases excluded from passed count',
        'platform':platform.system(),'architecture':platform.machine(),'python':platform.python_version(),'suites':[]}
success=True
for name,modules in suites:
    result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromNames(modules))
    failures=len(result.failures);errors=len(result.errors);skipped=len(result.skipped)
    report['suites'].append({'name':name,'source_modules':modules,'run':result.testsRun,
                            'passed':result.testsRun-failures-errors-skipped,'failures':failures,'errors':errors,'skipped':skipped})
    success=success and result.wasSuccessful()
report['all_selected_checks_passed']=success
path=Path(args.output);path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
sys.exit(0 if success else 1)
