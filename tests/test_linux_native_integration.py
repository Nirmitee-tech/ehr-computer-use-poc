"""Run inside the isolated X11 desktop fixture, never against a real clinic."""
import json
import os
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path
from openclerk.engine import Engine
from openclerk.platform_driver import PlatformDriver
from tests.support import Planner


@unittest.skipUnless(os.environ.get('OPENCLERK_X11_TESTS')=='1','Requires the isolated X11 test desktop')
class LinuxNativeIntegrationTests(unittest.TestCase):
    def setUp(self):
        from openclerk.linux import X11Backend
        self.directory=tempfile.TemporaryDirectory();self.result=Path(self.directory.name)/'synthetic-result.json'
        self.process=subprocess.Popen([sys.executable,'-m','openclerk.demo'],env={**os.environ,'OPENCLERK_DEMO_RESULT':str(self.result)})
        self.addCleanup(self.cleanup_fixture)
        self.backend=X11Backend();self.driver=PlatformDriver(self.backend)
        self.app_id=os.path.realpath(sys.executable)
        deadline=time.time()+5
        while time.time()<deadline:
            if any(w.app_id==self.app_id for w in self.backend.windows()):break
            time.sleep(.1)
        else:raise AssertionError('Synthetic X11 target did not become visible')
    def cleanup_fixture(self):
        if hasattr(self,'driver'):self.driver.close()
        if self.process.poll() is None:self.process.terminate()
        self.process.wait(timeout=3);self.directory.cleanup()
    def test_native_x11_capture_and_reviewed_booking(self):
        observation=self.driver.observe(self.app_id)
        self.assertEqual((observation.width,observation.height),(960,650))
        self.assertTrue(observation.png.startswith(b'\x89PNG'))
        planner=Planner();engine=Engine(self.driver,planner,{self.app_id})
        engine.start('Synthetic X11 booking test',self.app_id,'test-vision')
        actions=[{'kind':'click','x':460,'y':292},{'kind':'click','x':465,'y':376},
                 {'kind':'click','x':500,'y':465},{'kind':'type','text':'Native X11 test'},
                 {'kind':'key','key':'tab'},{'kind':'click','x':450,'y':526}]
        for action in actions:
            planner.action={**action,'reason':'Synthetic native X11 test','expected':'Inspect native result'}
            proposal=engine.propose()['pending']['id'];engine.approve(proposal)
        deadline=time.time()+2
        while not self.result.exists() and time.time()<deadline:time.sleep(.05)
        self.assertTrue(self.result.exists(),'The native app did not save an appointment')
        result=json.loads(self.result.read_text())
        self.assertEqual(result['appointment_id'],'SYN-APT-001');self.assertTrue(result['synthetic'])
        self.assertEqual(result['provider'],1);self.assertEqual(result['slot'],1)
        self.assertEqual(result['note'],'Native X11 test')
    def test_stale_x11_capture_is_rejected(self):
        observation=self.driver.observe(self.app_id)
        from dataclasses import replace
        from openclerk.types import ClerkError
        stale=replace(observation,png=b'invalid')
        with self.assertRaises(ClerkError):self.driver.execute(self.app_id,stale,{'kind':'click','x':450,'y':292,'reason':'Test','expected':'Test'},lambda:False)


if __name__=='__main__':unittest.main()
