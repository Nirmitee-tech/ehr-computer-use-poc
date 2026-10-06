import unittest
from unittest.mock import patch
from openclerk.platform_driver import DesktopWindow, PlatformDriver, make_driver
from openclerk.types import ClerkError
from openclerk.png import encode_bgra
from tests.support import click


class Backend:
    def __init__(self):
        self.window=DesktopWindow('/test/app',42,123,'Synthetic native app',{'x':10,'y':20,'width':960,'height':650})
        self.active=42;self.png=b'unchanged';self.inputs=[];self.extra=False
    def windows(self):return [self.window,self.window] if self.extra else [self.window]
    def focus(self,window):pass
    def foreground(self):return self.active
    def capture(self,window):return self.png
    def input(self,window,action):self.inputs.append(action)
    def doctor(self):return {'ok':True,'platform':'test'}


class PlatformTests(unittest.TestCase):
    def setUp(self):self.backend=Backend();self.driver=PlatformDriver(self.backend)
    def test_valid_input_posts_once(self):
        observation=self.driver.observe('/test/app');self.driver.execute('/test/app',observation,click(),lambda:False)
        self.assertEqual(len(self.backend.inputs),1)
    def test_unknown_app_is_rejected(self):
        with self.assertRaises(ClerkError):self.driver.observe('/other/app')
    def test_ambiguous_windows_rejected(self):
        self.backend.extra=True
        with self.assertRaises(ClerkError):self.driver.observe('/test/app')
    def test_foreground_refusal_blocks_capture(self):
        self.backend.active=99
        with self.assertRaises(ClerkError):self.driver.observe('/test/app')
    def test_stale_pixels_block_input(self):
        observation=self.driver.observe('/test/app');self.backend.png=b'changed'
        with self.assertRaises(ClerkError):self.driver.execute('/test/app',observation,click(),lambda:False)
        self.assertEqual(self.backend.inputs,[])
    def test_process_change_blocks_input(self):
        observation=self.driver.observe('/test/app')
        self.backend.window=DesktopWindow('/test/app',42,999,'Synthetic native app',self.backend.window.bounds)
        with self.assertRaises(ClerkError):self.driver.execute('/test/app',observation,click(),lambda:False)
    def test_stopped_run_blocks_input(self):
        observation=self.driver.observe('/test/app')
        with self.assertRaises(ClerkError):self.driver.execute('/test/app',observation,click(),lambda:True)
    def test_result_claim_cannot_reach_native_input(self):
        observation=self.driver.observe('/test/app')
        with self.assertRaises(ClerkError):self.driver.execute('/test/app',observation,{'kind':'done','reason':'Saved','expected':'Review','evidence':'Visible result'},lambda:False)
    def test_unknown_platform_rejected(self):
        with self.assertRaises(ClerkError):make_driver('unsupported','unused')
    def test_win32_module_can_be_imported_on_other_platforms(self):
        from openclerk.windows import WindowsBackend
        with patch('openclerk.windows.sys.platform','darwin'):
            with self.assertRaises(ClerkError):WindowsBackend()
    def test_wayland_fails_explicitly(self):
        from openclerk.linux import X11Backend
        with patch.dict('os.environ',{'XDG_SESSION_TYPE':'wayland','DISPLAY':':1'}):
            with self.assertRaisesRegex(ClerkError,'Wayland'):X11Backend()
    def test_bgra_encoder_outputs_png(self):
        png=encode_bgra(bytes([0,0,255,255]),1,1)
        self.assertTrue(png.startswith(b'\x89PNG'));self.assertIn(b'IHDR',png);self.assertIn(b'IEND',png)
    def test_invalid_image_dimensions_rejected(self):
        with self.assertRaises(ValueError):encode_bgra(b'',1,1)


if __name__=='__main__':unittest.main()
