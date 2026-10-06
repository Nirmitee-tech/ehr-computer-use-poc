"""Opt-in local vision test restricted to the synthetic app's Reset test button."""
import os
import sys
import unittest
from pathlib import Path
from openclerk.driver import MacDriver
from openclerk.engine import Engine
from openclerk.planner import OllamaPlanner


@unittest.skipUnless(sys.platform=='darwin' and os.environ.get('OPENCLERK_LIVE_MODEL_TESTS')=='1','Requires macOS, the synthetic clinic and the installed local vision model')
class LocalVisionIntegrationTests(unittest.TestCase):
    def test_model_proposes_reviewed_native_reset_and_result_is_visible(self):
        driver=MacDriver(Path(__file__).resolve().parents[1]/'build'/'desktop-bridge')
        self.addCleanup(driver.close)
        planner=OllamaPlanner('qwen3-vl:2b')
        engine=Engine(driver,planner,{'io.openclerk.clinicdemo'})
        engine.start('Click the Reset test button once in this synthetic app. Your next action must be a click on Reset test. Do not click any other control.','io.openclerk.clinicdemo','qwen3-vl:2b')
        state=engine.propose();action=state['pending']['action']
        self.assertEqual(action['kind'],'click')
        self.assertGreaterEqual(action['x'],744);self.assertLessEqual(action['x'],874)
        self.assertGreaterEqual(action['y'],510);self.assertLessEqual(action['y'],545)
        self.assertEqual(state['steps'],0)
        engine.approve(state['pending']['id'])
        self.assertEqual(engine.steps,1)
        self.assertIn('Ready to schedule',engine.observation.text)
        self.assertIn('No appointment has been saved',engine.observation.text)


if __name__=='__main__':unittest.main()
