"""Opt-in Win32 integration test. Requires an interactive Windows desktop."""
import ctypes
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


@unittest.skipUnless(sys.platform=='win32' and os.environ.get('OPENCLERK_WINDOWS_TESTS')=='1','Requires an interactive Windows host and explicit test opt-in')
class WindowsNativeIntegrationTests(unittest.TestCase):
    def setUp(self):
        from openclerk.windows import WindowsBackend
        self.directory=tempfile.TemporaryDirectory();self.result=Path(self.directory.name)/'synthetic-result.json'
        self.process=subprocess.Popen([sys.executable,'-m','openclerk.demo'],env={**os.environ,'OPENCLERK_DEMO_RESULT':str(self.result)})
        self.backend=WindowsBackend();self.driver=PlatformDriver(self.backend)
        self.app_id=os.path.normcase(os.path.realpath(sys.executable))
        deadline=time.time()+5
        while time.time()<deadline:
            windows=[w for w in self.backend.windows() if w.process_id==self.process.pid]
            if windows:self.window=windows[0];break
            time.sleep(.1)
        else:raise AssertionError('Synthetic Win32 target did not become visible')
    def tearDown(self):
        self.process.terminate();self.process.wait(timeout=3);self.directory.cleanup()
    def test_native_win32_capture_and_reviewed_booking(self):
        from ctypes import wintypes as w
        observation=self.driver.observe(self.app_id)
        self.assertTrue(observation.png.startswith(b'\x89PNG'))
        point=w.POINT(0,0)
        self.backend.user.ClientToScreen.argtypes=[w.HWND,ctypes.POINTER(w.POINT)]
        self.backend.user.ClientToScreen(self.window.window_id,ctypes.byref(point))
        dx,dy=point.x-self.window.bounds['x'],point.y-self.window.bounds['y']
        planner=Planner();engine=Engine(self.driver,planner,{self.app_id})
        engine.start('Synthetic Win32 booking test',self.app_id,'test-vision')
        actions=[{'kind':'click','x':460+dx,'y':292+dy},{'kind':'click','x':465+dx,'y':376+dy},
                 {'kind':'click','x':500+dx,'y':465+dy},{'kind':'type','text':'Native Win32 test'},
                 {'kind':'key','key':'tab'},{'kind':'click','x':450+dx,'y':526+dy}]
        for action in actions:
            planner.action={**action,'reason':'Synthetic native Win32 test','expected':'Inspect native result'}
            proposal=engine.propose()['pending']['id'];engine.approve(proposal)
        deadline=time.time()+2
        while not self.result.exists() and time.time()<deadline:time.sleep(.05)
        self.assertTrue(self.result.exists(),'The native app did not save an appointment')
        result=json.loads(self.result.read_text())
        self.assertEqual(result['appointment_id'],'SYN-APT-001');self.assertTrue(result['synthetic'])
        self.assertEqual(result['provider'],1);self.assertEqual(result['slot'],1)
        self.assertEqual(result['note'],'Native Win32 test')


if __name__=='__main__':unittest.main()
