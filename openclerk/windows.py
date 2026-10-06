"""Native Win32 window capture and input. No browser automation dependency."""
import ctypes
import multiprocessing
import os
import sys
import time
from pathlib import Path
from .platform_driver import DesktopWindow
from .png import encode_bgra
from .types import ClerkError


def _capture_worker(window, connection):
    try:
        backend=WindowsBackend()
        if backend.process_id(window.window_id)!=window.process_id:
            raise ClerkError('Target process changed before capture')
        connection.send((True,backend._capture_window(window)))
    except Exception as exc:connection.send((False,str(exc)))
    finally:connection.close()


class WindowsBackend:
    def __init__(self):
        if sys.platform!='win32':raise ClerkError('Win32 desktop backend requires Windows')
        from ctypes import wintypes as w
        self.w=w;self.user=ctypes.WinDLL('user32',use_last_error=True)
        self.gdi=ctypes.WinDLL('gdi32',use_last_error=True);self.kernel=ctypes.WinDLL('kernel32',use_last_error=True)
        self.user.GetForegroundWindow.restype=w.HWND
        self.user.GetWindowRect.argtypes=[w.HWND,ctypes.POINTER(w.RECT)]
        self.user.GetWindowThreadProcessId.argtypes=[w.HWND,ctypes.POINTER(w.DWORD)]
        self.user.IsWindowVisible.argtypes=[w.HWND];self.user.IsIconic.argtypes=[w.HWND]
        self.user.GetWindowTextLengthW.argtypes=[w.HWND]
        self.user.GetWindowTextW.argtypes=[w.HWND,w.LPWSTR,ctypes.c_int]
        self.user.SetForegroundWindow.argtypes=[w.HWND]
        self.user.ShowWindow.argtypes=[w.HWND,ctypes.c_int]
        self.user.GetWindowDC.argtypes=[w.HWND];self.user.GetWindowDC.restype=w.HDC
        self.user.ReleaseDC.argtypes=[w.HWND,w.HDC]
        self.user.PrintWindow.argtypes=[w.HWND,w.HDC,w.UINT]
        self.kernel.OpenProcess.argtypes=[w.DWORD,w.BOOL,w.DWORD];self.kernel.OpenProcess.restype=w.HANDLE
        self.kernel.QueryFullProcessImageNameW.argtypes=[w.HANDLE,w.DWORD,w.LPWSTR,ctypes.POINTER(w.DWORD)]
        self.kernel.CloseHandle.argtypes=[w.HANDLE]
        self.gdi.CreateCompatibleDC.argtypes=[w.HDC];self.gdi.CreateCompatibleDC.restype=w.HDC
        self.gdi.DeleteDC.argtypes=[w.HDC]
        self.gdi.SelectObject.argtypes=[w.HDC,w.HGDIOBJ];self.gdi.SelectObject.restype=w.HGDIOBJ
        self.gdi.DeleteObject.argtypes=[w.HGDIOBJ]
        class Header(ctypes.Structure):
            _fields_=[('size',w.DWORD),('width',w.LONG),('height',w.LONG),('planes',w.WORD),('bits',w.WORD),('compression',w.DWORD),('image_size',w.DWORD),('xppm',w.LONG),('yppm',w.LONG),('used',w.DWORD),('important',w.DWORD)]
        class Info(ctypes.Structure):_fields_=[('header',Header),('colors',w.DWORD*3)]
        self.Header=Header;self.Info=Info
        self.gdi.CreateDIBSection.argtypes=[w.HDC,ctypes.POINTER(Info),w.UINT,ctypes.POINTER(ctypes.c_void_p),w.HANDLE,w.DWORD]
        self.gdi.CreateDIBSection.restype=w.HBITMAP
        class Mouse(ctypes.Structure):_fields_=[('dx',w.LONG),('dy',w.LONG),('data',w.DWORD),('flags',w.DWORD),('time',w.DWORD),('extra',ctypes.c_size_t)]
        class Keyboard(ctypes.Structure):_fields_=[('vk',w.WORD),('scan',w.WORD),('flags',w.DWORD),('time',w.DWORD),('extra',ctypes.c_size_t)]
        class Hardware(ctypes.Structure):_fields_=[('message',w.DWORD),('low',w.WORD),('high',w.WORD)]
        class Payload(ctypes.Union):_fields_=[('mouse',Mouse),('keyboard',Keyboard),('hardware',Hardware)]
        class Input(ctypes.Structure):_fields_=[('kind',w.DWORD),('payload',Payload)]
        self.Mouse=Mouse;self.Keyboard=Keyboard;self.Payload=Payload;self.Input=Input
        self.user.SendInput.argtypes=[w.UINT,ctypes.POINTER(Input),ctypes.c_int];self.user.SendInput.restype=w.UINT
        self.callback=ctypes.WINFUNCTYPE(w.BOOL,w.HWND,ctypes.c_ssize_t)
        self.user.EnumWindows.argtypes=[self.callback,ctypes.c_ssize_t]
        try:
            self.user.SetProcessDpiAwarenessContext.argtypes=[ctypes.c_void_p]
            self.user.SetProcessDpiAwarenessContext(ctypes.c_void_p(-4))
        except AttributeError:self.user.SetProcessDPIAware()

    def process_id(self, hwnd):
        pid=self.w.DWORD();self.user.GetWindowThreadProcessId(hwnd,ctypes.byref(pid));return pid.value

    def process_path(self,pid):
        handle=self.kernel.OpenProcess(0x1000,False,pid)
        if not handle:return ''
        try:
            buffer=ctypes.create_unicode_buffer(32768);size=self.w.DWORD(len(buffer))
            if not self.kernel.QueryFullProcessImageNameW(handle,0,buffer,ctypes.byref(size)):return ''
            return os.path.normcase(os.path.realpath(buffer.value))
        finally:self.kernel.CloseHandle(handle)

    def windows(self):
        result=[]
        def visit(hwnd,_):
            if not self.user.IsWindowVisible(hwnd) or self.user.IsIconic(hwnd):return True
            rect=self.w.RECT()
            if not self.user.GetWindowRect(hwnd,ctypes.byref(rect)):return True
            width,height=rect.right-rect.left,rect.bottom-rect.top
            length=self.user.GetWindowTextLengthW(hwnd)
            if width<=100 or height<=100 or not length:return True
            title=ctypes.create_unicode_buffer(length+1);self.user.GetWindowTextW(hwnd,title,len(title))
            pid=self.process_id(hwnd);path=self.process_path(pid)
            if path:result.append(DesktopWindow(path,int(hwnd),pid,title.value,{'x':rect.left,'y':rect.top,'width':width,'height':height}))
            return True
        self.user.EnumWindows(self.callback(visit),0)
        return result

    def foreground(self):return int(self.user.GetForegroundWindow() or 0)

    def focus(self,window):
        if self.foreground()!=window.window_id:
            self.user.SetForegroundWindow(window.window_id)
            for _ in range(10):
                if self.foreground()==window.window_id:return
                time.sleep(0.05)
            raise ClerkError('Windows refused target activation. Bring the approved window forward and retry.')

    def capture(self,window):
        # PrintWindow is synchronous. Isolate it so an unresponsive app cannot hang the runner.
        context=multiprocessing.get_context('spawn');parent,child=context.Pipe(duplex=False)
        process=context.Process(target=_capture_worker,args=(window,child),daemon=True)
        process.start();child.close()
        try:
            if not parent.poll(8):raise ClerkError('Native window capture timed out')
            ok,value=parent.recv()
            if not ok:raise ClerkError(value)
            return value
        finally:
            parent.close();process.join(timeout=1)
            if process.is_alive():process.terminate();process.join(timeout=2)

    def _capture_window(self,window):
        width,height=int(window.bounds['width']),int(window.bounds['height'])
        source=self.user.GetWindowDC(window.window_id);dc=self.gdi.CreateCompatibleDC(source)
        info=self.Info();info.header=self.Header(ctypes.sizeof(self.Header),width,-height,1,32,0,width*height*4,0,0,0,0)
        bits=ctypes.c_void_p();bitmap=self.gdi.CreateDIBSection(dc,ctypes.byref(info),0,ctypes.byref(bits),None,0)
        old=None
        try:
            if not source or not dc or not bitmap or not bits.value:raise ClerkError('Native capture allocation failed')
            old=self.gdi.SelectObject(dc,bitmap)
            if not self.user.PrintWindow(window.window_id,dc,2):raise ClerkError('Application refused native window capture')
            data=ctypes.string_at(bits,width*height*4)
            if not any(data[i] for i in range(0,len(data),4)):raise ClerkError('Native capture returned an empty image; this application needs a different capture adapter')
            return encode_bgra(data,width,height)
        finally:
            if old:self.gdi.SelectObject(dc,old)
            if bitmap:self.gdi.DeleteObject(bitmap)
            if dc:self.gdi.DeleteDC(dc)
            if source:self.user.ReleaseDC(window.window_id,source)

    def send(self,window,events):
        if self.foreground()!=window.window_id or self.process_id(window.window_id)!=window.process_id:
            raise ClerkError('Foreground or target process changed before input')
        if any(self.user.GetAsyncKeyState(key)&0x8000 for key in (0x10,0x11,0x12,0x5b,0x5c)):
            raise ClerkError('Release modifier keys before approving input')
        inputs=(self.Input*len(events))(*events)
        if self.user.SendInput(len(events),inputs,ctypes.sizeof(self.Input))!=len(events):
            raise ClerkError('Windows did not accept all input events. Inspect the target; do not retry blindly.')

    def mouse_event(self,flags,data=0):return self.Input(0,self.Payload(mouse=self.Mouse(0,0,data & 0xffffffff,flags,0,0)))
    def key_event(self,vk,scan,flags):return self.Input(1,self.Payload(keyboard=self.Keyboard(vk,scan,flags,0,0)))

    def input(self,window,action):
        name=Path(window.app_id).name.lower()
        if any(part in name for part in ('cmd.exe','powershell','pwsh','windowsterminal','code.exe','idea')):raise ClerkError('Terminal and editor targets are disabled')
        point=self.w.POINT();self.user.GetCursorPos(ctypes.byref(point))
        if point.x<=2 and point.y<=2:raise ClerkError('Emergency stop: pointer is at the upper-left corner')
        kind=action['kind']
        if kind in ('click','double_click','scroll'):
            if not self.user.SetCursorPos(int(window.bounds['x']+action['x']),int(window.bounds['y']+action['y'])):raise ClerkError('Windows refused pointer movement')
            if kind=='scroll':self.send(window,[self.mouse_event(0x0800,int(action['delta']))])
            else:
                for _ in range(2 if kind=='double_click' else 1):
                    self.send(window,[self.mouse_event(0x0002),self.mouse_event(0x0004)])
                    time.sleep(0.08)
        elif kind=='type':
            data=action['text'].encode('utf-16-le');events=[]
            for i in range(0,len(data),2):
                value=int.from_bytes(data[i:i+2],'little');events.extend([self.key_event(0,value,4),self.key_event(0,value,6)])
            self.send(window,events)
        elif kind=='key':
            keys={'tab':9,'enter':13,'escape':27,'backspace':8,'space':32,'left':37,'up':38,'right':39,'down':40,'home':36,'end':35}
            value=keys[action['key']];extended=1 if action['key'] in ('left','right','up','down','home','end') else 0
            self.send(window,[self.key_event(value,0,extended),self.key_event(value,0,extended|2)])
        elif kind=='wait':time.sleep(action['seconds'])
        else:raise ClerkError('Unsupported Windows action')

    def doctor(self):
        return {'ok':True,'platform':'Windows','screen_recording':bool(self.foreground()),'accessibility':bool(self.foreground()),
                'capture':'Win32 PrintWindow; application support varies','input':'Win32 SendInput; elevated applications are not supported',
                'verification':'Native Windows host testing required'}
