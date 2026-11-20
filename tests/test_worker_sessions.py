import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import unittest
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
os.environ.setdefault('FM27_ENGINE_ROOT',str(ROOT/'build/test-temp'))
sys.path.insert(0,str(ROOT/'src'))
from desktop_warm_batch import DesktopWarmRunner, match_importance_receipt


class MatchImportanceReceiptTests(unittest.TestCase):
 def test_resume_requires_exact_starter_readbacks(self):
  scenario={'match_importance':7}
  receipt={'event':'native_match_importance_readback','requested':7,'verified':True,
           'starters':[[7]*11,[7]*11]}
  self.assertIsNone(match_importance_receipt([],{}))
  self.assertEqual(match_importance_receipt([receipt],scenario),7)
  for rows in ([], [receipt,receipt], [{**receipt,'starters':[[7]*11,[7]*10+[13]]}]):
   with self.subTest(rows=rows),self.assertRaises(ValueError):
    match_importance_receipt(rows,scenario)

class WorkerSessionTests(unittest.TestCase):
 def setUp(self):
  root=ROOT/'build/test-temp';root.mkdir(parents=True,exist_ok=True)
  self.temp=tempfile.TemporaryDirectory(dir=root);self.addCleanup(self.temp.cleanup)
  self.root=Path(self.temp.name);(self.root/'fm27_native').mkdir()
  (self.root/'fm27_native/FM27Simulator.exe').write_bytes(b'worker-capability-fixture')
  DesktopWarmRunner._capabilities_cache.clear()
 def runner(self,body,code=0):
  result=subprocess.CompletedProcess([],code,json.dumps(body).encode(),b'')
  with patch('desktop_warm_batch.subprocess.run',return_value=result):return DesktopWarmRunner(self.root)
 def test_new_host_keeps_entire_lane_with_or_without_execution(self):
  runner=self.runner(dict(protocol=2,max_jobs=1000000,execution_context_reset=True,per_match_resource_release=True))
  lanes=[list(range(200)),list(range(199))]
  self.assertEqual(runner.session_size(lanes,True),200)
  self.assertEqual(runner.session_size(lanes,False),200)
 def test_legacy_host_preserves_execution_isolation(self):
  runner=self.runner({},79)
  self.assertEqual(runner.session_size([list(range(200))],True),1)
  self.assertEqual(runner.session_size([list(range(200))],False),64)
 def test_missing_cleanup_capability_cannot_enable_reuse(self):
  runner=self.runner(dict(protocol=2,max_jobs=1000000,execution_context_reset=True))
  self.assertFalse(runner.counted_sessions)
  self.assertEqual(runner.session_size([[1,2]],True),1)
 def test_invalid_job_limit_cannot_enable_reuse(self):
  for limit in (0,-1,'1000',True,1000001):
   DesktopWarmRunner._capabilities_cache.clear()
   runner=self.runner(dict(protocol=2,max_jobs=limit,execution_context_reset=True,per_match_resource_release=True))
   self.assertFalse(runner.counted_sessions,limit)
 def test_host_change_invalidates_capability_cache(self):
  self.runner({},79)
  (self.root/'fm27_native/FM27Simulator.exe').write_bytes(b'upgraded-worker')
  runner=self.runner(dict(protocol=2,max_jobs=1000,execution_context_reset=True,per_match_resource_release=True))
  self.assertTrue(runner.counted_sessions)

 def test_serial_startup_still_allows_eight_simultaneous_matches(self):
  runner=self.runner(dict(protocol=2,max_jobs=64,execution_context_reset=True,per_match_resource_release=True))
  runner.workers=8
  matches=threading.Barrier(runner.workers,timeout=8)
  lock=threading.Lock()
  starting=set()
  overlaps=[]
  threads=[]

  class Process:
   def __init__(self,command,**kwargs):
    manifest=Path(command[2]).read_text(encoding='utf8').splitlines()
    self.log=Path(manifest[4])
    self.startup=Path(command[4])
    self.pid=int(manifest[5])+1000
    self.stdout=io.BytesIO()
    self.returncode=None
    self.started=threading.Event()
    with lock:
     if starting:overlaps.append(self.pid)
     starting.add(self.pid)
    thread=threading.Thread(target=self.simulate)
    threads.append(thread)
    thread.start()

   def simulate(self):
    self.started.wait(.05)
    with lock:starting.remove(self.pid)
    self.startup.write_text('{"event":"native_activation_completed"}\n'
                            '{"event":"native_interface_created"}\n'
                            '{"event":"native_engine_compatibility","compatible":true}\n'
                            '{"event":"native_image_fingerprint","sha256":"test"}\n'
                            '{"event":"steam_session_cleanup","ok":true}\n',encoding='utf8')
    try:
     matches.wait()
    except threading.BrokenBarrierError:
     self.returncode=82
     return
    self.log.write_text('{"event":"host_icu_data_initialized"}\n'
                        '{"event":"native_engine_bootstrap_returned"}\n',encoding='utf8')
    ack=Path(str(self.log)+'.worker_done')
    pending=Path(str(ack)+'.tmp')
    pending.write_text(json.dumps(dict(released=True,exit_code=0,index=1,pid=self.pid)),encoding='utf8')
    pending.replace(ack)
    self.returncode=0

   def poll(self):
    return self.returncode

   def communicate(self):
    return b'',None

  tasks=[dict(path=self.root/f'{seed}.jsonl',config=self.root/'input.bin',seed=seed,
              scenario={},variant='B',event_details=False) for seed in range(8)]
  checked=[]
  with patch('desktop_warm_batch.subprocess.Popen',side_effect=Process),\
       patch('desktop_warm_batch.own_child_processes'),\
       patch('desktop_warm_batch.require_space'),\
       patch.object(runner,'postprocess',side_effect=lambda task,*_:task['seed']):
   try:runner.run(tasks,checked.append)
   finally:
    for thread in threads:thread.join()
  self.assertEqual(overlaps,[])
  self.assertEqual(sorted(checked),list(range(8)))

class WorkerResourceTests(unittest.TestCase):
 def test_high_core_machine_has_headroom_and_conservative_default(self):
  from fm27_batch import resource_limits
  result=resource_limits(24,14*1024**3)
  self.assertEqual(result['maximum'],256)
  self.assertEqual(result['resource_suggested_maximum'],8)
  self.assertEqual(result['recommended'],4)
 def test_cpu_and_current_free_memory_both_limit_parallelism(self):
  from fm27_batch import resource_limits
  self.assertEqual(resource_limits(24,5*1024**3)['resource_suggested_maximum'],3)
  self.assertEqual(resource_limits(8,32*1024**3)['resource_suggested_maximum'],4)
  self.assertEqual(resource_limits(2,1*1024**3)['resource_suggested_maximum'],1)

 def test_manual_limit_does_not_shrink_on_a_low_memory_machine(self):
  from fm27_batch import resource_limits
  result=resource_limits(2,1024**3)
  self.assertEqual(result['maximum'],256)
  self.assertEqual(result['recommended'],1)
