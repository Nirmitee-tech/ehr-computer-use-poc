import json
import threading
import unittest
import urllib.error
import urllib.request
from openclerk.engine import Engine
from openclerk.server import LocalServer
from tests.support import Driver, Planner


class ConsoleIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.driver=Driver();self.engine=Engine(self.driver,Planner(),{'io.openclerk.clinicdemo'})
        self.server=LocalServer(('127.0.0.1',0),self.engine)
        self.thread=threading.Thread(target=self.server.serve_forever,daemon=True);self.thread.start()
        self.url='http://127.0.0.1:'+str(self.server.server_port)
    def tearDown(self):
        self.server.shutdown();self.server.server_close();self.thread.join()
    def request(self,path,body=None,token=True,extra=None):
        headers={'Content-Type':'application/json'}
        if token:headers['Authorization']='Bearer '+self.server.token
        headers.update(extra or {})
        req=urllib.request.Request(self.url+path,data=None if body is None else json.dumps(body).encode(),headers=headers)
        try:
            with urllib.request.urlopen(req) as response:return response.status,response.read(),response.headers
        except urllib.error.HTTPError as exc:return exc.code,exc.read(),exc.headers
    def start(self):
        return self.request('/api/start',{'task':'Book synthetic referral','bundle_id':'io.openclerk.clinicdemo','model':'test-vision'})
    def test_console_exposes_review_controls_and_local_token(self):
        code,body,headers=self.request('/',token=False)
        self.assertEqual(code,200);self.assertIn(b'Approve this action',body);self.assertIn(b'Stop run',body)
        self.assertNotIn(b'__SESSION_TOKEN__',body);self.assertEqual(headers['Cache-Control'],'no-store')
    def test_console_to_desktop_review_cycle(self):
        self.assertEqual(self.start()[0],200)
        _,body,_=self.request('/api/propose',{});proposal=json.loads(body)
        self.assertEqual(proposal['state'],'review');self.assertEqual(self.driver.inputs,[])
        self.assertTrue(proposal['observation']['image'].startswith('data:image/png;base64,'))
        code,body,_=self.request('/api/approve',{'proposal_id':proposal['pending']['id']})
        self.assertEqual(code,200);self.assertEqual(json.loads(body)['state'],'ready')
        self.assertEqual(len(self.driver.inputs),1)
    def test_console_rejection_does_not_execute(self):
        self.start();_,body,_=self.request('/api/propose',{})
        proposal=json.loads(body)['pending']['id']
        self.assertEqual(self.request('/api/reject',{'proposal_id':proposal})[0],200)
        self.assertEqual(self.driver.inputs,[])
    def test_unauthenticated_requests_cannot_read_screens_or_start(self):
        self.assertEqual(self.request('/api/status',token=False)[0],401)
        self.assertEqual(self.request('/api/start',{},token=False)[0],403)
    def test_cross_origin_write_blocked(self):
        self.assertEqual(self.request('/api/start',{},extra={'Origin':'https://untrusted.example'})[0],403)
    def test_dns_rebinding_host_blocked(self):
        self.assertEqual(self.request('/',extra={'Host':'untrusted.example'})[0],403)
    def test_stop_makes_pending_approval_invalid(self):
        self.start();_,body,_=self.request('/api/propose',{});proposal=json.loads(body)['pending']['id']
        self.assertEqual(self.request('/api/stop',{})[0],200)
        self.assertEqual(self.request('/api/approve',{'proposal_id':proposal})[0],422)
        self.assertEqual(self.driver.inputs,[])
    def test_unknown_target_is_rejected_in_api(self):
        code,_,_=self.request('/api/start',{'task':'Task','bundle_id':'com.apple.Terminal','model':'test-vision'})
        self.assertEqual(code,422)
    def test_static_path_traversal_rejected(self):
        self.assertEqual(self.request('/../engine.py')[0],404)
    def test_unknown_endpoint_is_404(self):
        self.assertEqual(self.request('/api/anything',{})[0],404)
    def test_script_renders_untrusted_text_as_text(self):
        code,body,_=self.request('/app.js')
        self.assertEqual(code,200);self.assertNotIn(b'innerHTML',body)
        self.assertIn(b'.textContent = action.reason',body)


if __name__=='__main__':unittest.main()
