import json
import unittest
from openclerk.planner import OllamaPlanner, SCHEMA
from openclerk.types import ClerkError
from tests.support import screen, click


class StubPlanner(OllamaPlanner):
    def __init__(self):
        super().__init__('test-vision');self.calls=[];self.metadata={'capabilities':['vision']};self.content=json.dumps(click())
    def request(self,path,body=None):
        self.calls.append((path,body))
        if path=='/api/show':return self.metadata
        return {'message':{'content':self.content}}


class PlannerTests(unittest.TestCase):
    def test_schema_requires_coordinates_for_click_and_evidence_for_done(self):
        variants={variant['properties']['kind']['const']:variant for variant in SCHEMA['oneOf']}
        self.assertIn('x',variants['click']['required']);self.assertIn('y',variants['click']['required'])
        self.assertIn('evidence',variants['done']['required'])
        self.assertFalse(variants['click']['additionalProperties'])

    def test_normalized_coordinates_convert_to_logical_pixels(self):
        planner=StubPlanner();planner.content=json.dumps({'kind':'click','x':500,'y':1000,'reason':'test','expected':'test'})
        result=planner.propose('Task',screen(),[])
        self.assertEqual(result['x'],480);self.assertEqual(result['y'],649)
    def test_out_of_range_normalized_coordinates_are_rejected(self):
        planner=StubPlanner();planner.content=json.dumps({'kind':'click','x':1500,'y':500,'reason':'test','expected':'test'})
        with self.assertRaises(ClerkError):planner.propose('Task',screen(),[])
    def test_non_object_model_response_rejected(self):
        planner=StubPlanner();planner.content='[]'
        with self.assertRaises(ClerkError):planner.propose('Task',screen(),[])

    def test_screenshot_is_sent_to_local_vision_request(self):
        planner=StubPlanner();self.assertEqual(planner.propose('Task',screen(),[])['kind'],'click')
        path,body=planner.calls[-1];self.assertEqual(path,'/api/chat');self.assertFalse(body['stream'])
        self.assertEqual(body['messages'][1]['images'],['cG5nLWJlZm9yZQ=='])
        self.assertEqual(planner.endpoint,'http://127.0.0.1:11434')
    def test_nonvision_model_rejected(self):
        planner=StubPlanner();planner.metadata={'capabilities':['completion']}
        with self.assertRaises(ClerkError):planner.propose('Task',screen(),[])
    def test_invalid_model_json_rejected(self):
        planner=StubPlanner();planner.content='not JSON'
        with self.assertRaises(ClerkError):planner.propose('Task',screen(),[])
    def test_cloud_alias_metadata_rejected(self):
        planner=StubPlanner();planner.metadata={'capabilities':['vision'],'remote_model':'remote-name','remote_host':'https://ollama.com'}
        with self.assertRaises(ClerkError):planner.propose('Task',screen(),[])
    def test_cloud_tag_rejected(self):
        planner=StubPlanner();planner.model='qwen3-vl:235b-cloud'
        with self.assertRaises(ClerkError):planner.propose('Task',screen(),[])


if __name__=='__main__':unittest.main()
