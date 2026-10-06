import json
import tempfile
import threading
import time
import unittest
from pathlib import Path
from openclerk.engine import Engine
from openclerk.types import ClerkError, validate_action
from tests.support import Driver, Planner, BlockingPlanner, click, screen


class ActionTests(unittest.TestCase):
    def test_valid_coordinates(self):
        self.assertEqual(validate_action(click(), screen())['x'], 400)
    def test_outside_window(self):
        action=click(); action['x']=960
        with self.assertRaises(ClerkError): validate_action(action, screen())
    def test_nan_and_boolean_coordinates(self):
        for value in (float('nan'), float('inf'), True):
            with self.subTest(value=value):
                action=click(); action['x']=value
                with self.assertRaises(ClerkError): validate_action(action, screen())
    def test_shell_and_shortcuts_are_not_actions(self):
        for action in ({'kind':'shell','text':'anything'}, {'kind':'key','key':'cmd+q'}):
            action.update(reason='test',expected='test')
            with self.assertRaises(ClerkError): validate_action(action,screen())
    def test_type_rejects_control_characters(self):
        for text in ('hello\nworld','\x00','\t','x'*1001):
            with self.subTest(text=text[:12]):
                with self.assertRaises(ClerkError): validate_action({'kind':'type','text':text,'reason':'test','expected':'test'},screen())
    def test_action_field_smuggling(self):
        action=click(); action['key']='enter'
        with self.assertRaises(ClerkError): validate_action(action,screen())
    def test_done_requires_visible_evidence(self):
        with self.assertRaises(ClerkError): validate_action({'kind':'done','reason':'Saved','expected':'Complete'},screen())
    def test_geometry_changes_fingerprint(self):
        old=screen(); new=screen(); new.bounds['x']=200
        self.assertNotEqual(old.fingerprint,new.fingerprint)
    def test_reason_is_required(self):
        action=click(); action.pop('reason')
        with self.assertRaises(ClerkError):validate_action(action,screen())


class EngineTests(unittest.TestCase):
    def setUp(self):
        self.driver=Driver();self.planner=Planner();self.engine=Engine(self.driver,self.planner,{'io.openclerk.clinicdemo'})
        self.engine.start('Schedule synthetic referral','io.openclerk.clinicdemo','test-vision')
    def proposal(self): return self.engine.propose()['pending']['id']
    def test_proposal_does_not_execute(self):
        self.proposal();self.assertEqual(self.driver.inputs,[]);self.assertEqual(self.engine.state,'review')
    def test_approval_executes_one_action_and_observes(self):
        self.engine.approve(self.proposal());self.assertEqual(len(self.driver.inputs),1)
        self.assertEqual(self.engine.observation.png,b'png-after');self.assertEqual(self.engine.state,'ready')
    def test_approval_is_single_use(self):
        proposal=self.proposal();self.engine.approve(proposal)
        with self.assertRaises(ClerkError): self.engine.approve(proposal)
        self.assertEqual(len(self.driver.inputs),1)
    def test_reject_has_no_input(self):
        self.engine.reject(self.proposal());self.assertEqual(self.driver.inputs,[])
    def test_stale_screen_blocks_input(self):
        proposal=self.proposal();self.driver.current=screen(b'changed')
        with self.assertRaises(ClerkError):self.engine.approve(proposal)
        self.assertEqual(self.driver.inputs,[]);self.assertEqual(self.engine.state,'error')
    def test_review_expiry_blocks_input(self):
        proposal=self.proposal();self.engine.pending['created_at']-=121
        with self.assertRaises(ClerkError):self.engine.approve(proposal)
        self.assertEqual(self.driver.inputs,[])
    def test_stop_invalidates_pending(self):
        proposal=self.proposal();self.engine.stop()
        with self.assertRaises(ClerkError):self.engine.approve(proposal)
        self.assertEqual(self.driver.inputs,[])
    def test_stop_during_model_call_discards_result(self):
        planner=BlockingPlanner();self.engine.planner=planner
        thread=threading.Thread(target=self.engine.propose);thread.start();self.assertTrue(planner.entered.wait(2))
        self.engine.stop();planner.release.set();thread.join(2)
        self.assertIsNone(self.engine.pending);self.assertEqual(self.engine.state,'stopped');self.assertFalse(self.engine.busy)
    def test_failed_post_input_capture_needs_inspection(self):
        self.driver.fail_after_input=True
        with self.assertRaises(ClerkError):self.engine.approve(self.proposal())
        self.assertEqual(self.engine.state,'uncertain')
        with self.assertRaises(ClerkError):self.engine.propose()
        self.assertEqual(len(self.driver.inputs),1)
    def test_target_allowlist(self):
        with self.assertRaises(ClerkError):self.engine.start('Task','com.apple.Terminal','test-vision')
    def test_cloud_model_rejected(self):
        with self.assertRaises(ClerkError):self.engine.start('Task','io.openclerk.clinicdemo','model:cloud')
    def test_step_budget(self):
        self.engine.steps=30
        with self.assertRaises(ClerkError):self.engine.propose()
    def test_completion_waits_for_operator(self):
        self.planner.action={'kind':'done','reason':'Saved result visible','expected':'Operator confirms','evidence':'SYN-APT-001'}
        proposal=self.proposal();self.assertEqual(self.engine.state,'review')
        self.engine.approve(proposal);self.assertEqual(self.engine.state,'completed');self.assertEqual(self.driver.inputs,[])
    def test_handoff_posts_no_input(self):
        self.planner.action={'kind':'handoff','reason':'Ambiguous record','expected':'Staff checks identifiers'}
        self.engine.approve(self.proposal());self.assertEqual(self.engine.state,'handoff');self.assertEqual(self.driver.inputs,[])
    def test_new_run_clears_previous_screenshot(self):
        self.proposal();self.engine.start('New task','io.openclerk.clinicdemo','test-vision')
        self.assertIsNone(self.engine.observation);self.assertIsNone(self.engine.pending)
    def test_journal_excludes_task_and_action_text(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'events.jsonl'
            engine=Engine(self.driver,self.planner,{'io.openclerk.clinicdemo'},path)
            engine.start('private-task-marker','io.openclerk.clinicdemo','test-vision')
            self.planner.action={'kind':'type','text':'private-action-marker','reason':'private-reason-marker','expected':'private-result-marker'}
            engine.propose();body=path.read_text()
            self.assertNotIn('private-',body);self.assertNotIn('png',body)
            self.assertEqual(path.stat().st_mode & 0o777,0o600)


if __name__=='__main__':unittest.main()
