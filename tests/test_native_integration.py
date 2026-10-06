"""Opt-in tests post real desktop input only to io.openclerk.clinicdemo."""
import os
import unittest
from pathlib import Path
from openclerk.driver import MacDriver
from openclerk.engine import Engine
from openclerk.types import ClerkError
from tests.support import Planner


@unittest.skipUnless(os.environ.get('OPENCLERK_NATIVE_TESTS')=='1','Opt in with OPENCLERK_NATIVE_TESTS=1; requires the synthetic native app')
class NativeIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.driver=MacDriver(Path(__file__).resolve().parents[1]/'build'/'desktop-bridge')
    def tearDown(self):
        self.driver.close()
    def test_window_capture_has_only_synthetic_target(self):
        observation=self.driver.observe('io.openclerk.clinicdemo')
        self.assertTrue(observation.png.startswith(b'\x89PNG'))
        self.assertIn('SYNTHETIC DATA ONLY',observation.text)
        self.assertIn('TEST-REF-001',observation.text)
        self.assertEqual(observation.width,960)
    def test_native_bridge_blocks_stale_image(self):
        observation=self.driver.observe('io.openclerk.clinicdemo')
        with self.assertRaises(ClerkError):
            self.driver.call({'command':'execute','bundle_id':observation.bundle_id,'window_id':observation.window_id,'process_id':observation.process_id,
                              'bounds':observation.bounds,'fingerprint_png':'invalid',
                              'action':{'kind':'click','x':800,'y':510}})
    def test_native_bridge_blocks_unsupported_application(self):
        with self.assertRaises(ClerkError):self.driver.observe('com.apple.Terminal')
    def test_native_keyboard_and_click_save_synthetic_appointment(self):
        # These coordinates belong to the fixed synthetic app, not a production EHR.
        planner=Planner();engine=Engine(self.driver,planner,{'io.openclerk.clinicdemo'})
        engine.start('Native integration test','io.openclerk.clinicdemo','test-vision')
        actions=[{'kind':'click','x':800,'y':525},
                 {'kind':'click','x':352,'y':295},
                 {'kind':'click','x':352,'y':378},
                 {'kind':'click','x':520,'y':465},
                 {'kind':'type','text':'Native integration test'},
                 {'kind':'key','key':'tab'},
                 {'kind':'click','x':450,'y':525}]
        for index, action in enumerate(actions):
            print("Synthetic desktop step", index + 1, action["kind"], flush=True)
            planner.action={**action,'reason':'Synthetic test step','expected':'Inspect the resulting native screenshot'}
            pending=engine.propose()['pending']['id']
            engine.approve(pending)
        observed=self.driver.observe('io.openclerk.clinicdemo')
        self.assertIn('Appointment booked',observed.text)
        self.assertIn('SYN-APT-001',observed.text)
        self.assertIn('Test Provider A',observed.text)
        self.assertIn('Synthetic slot A',observed.text)
        self.assertIn('Native integration test',observed.text)


if __name__=='__main__':unittest.main()
