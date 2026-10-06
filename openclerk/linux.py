import os
import shutil
import subprocess
import time
from pathlib import Path
from .platform_driver import DesktopWindow
from .types import ClerkError


class X11Backend:
    def __init__(self):
        if os.environ.get('XDG_SESSION_TYPE') == 'wayland' or not os.environ.get('DISPLAY'):
            raise ClerkError('Linux desktop execution needs an X11 session. Wayland is not supported in this release.')
        if not shutil.which('xdotool'):
            raise ClerkError('Install xdotool before running the Linux desktop backend.')
        try:
            from Xlib import display, X, protocol
            import mss
            import mss.tools
        except ImportError as exc:
            raise ClerkError('Install the Linux extras: python3 -m pip install -e ".[linux]"') from exc
        self.X=X;self.protocol=protocol;self.mss=mss
        self.display=display.Display();self.root=self.display.screen().root
        self.active_atom=self.display.intern_atom('_NET_ACTIVE_WINDOW')

    def close(self): self.display.close()

    def command(self, *arguments):
        try:
            result=subprocess.run(['xdotool',*map(str,arguments)],capture_output=True,text=True,timeout=5)
        except (OSError,subprocess.TimeoutExpired) as exc:
            raise ClerkError('Native X11 command failed or timed out. Inspect the target.') from exc
        if result.returncode:
            raise ClerkError('Native X11 command rejected the input. Inspect the target.')
        return result.stdout.strip()

    def windows(self):
        prop=self.root.get_full_property(self.display.intern_atom('_NET_CLIENT_LIST'),self.X.AnyPropertyType)
        result=[]
        for window_id in ([] if prop is None else prop.value):
            try:
                window=self.display.create_resource_object('window',int(window_id))
                if window.get_attributes().map_state != self.X.IsViewable: continue
                geometry=window.get_geometry();position=self.root.translate_coords(window,0,0)
                if geometry.width <=100 or geometry.height <=100:continue
                pid_property=window.get_full_property(self.display.intern_atom('_NET_WM_PID'),self.X.AnyPropertyType)
                if pid_property is None:continue
                pid=int(pid_property.value[0]);executable=str(Path('/proc')/str(pid)/'exe')
                app_id=os.path.realpath(executable)
                if not os.path.isabs(app_id) or app_id==executable:continue
                name=window.get_wm_name() or Path(app_id).name
                result.append(DesktopWindow(app_id,int(window_id),pid,name,
                              {'x':position.x,'y':position.y,'width':geometry.width,'height':geometry.height}))
            except Exception:
                continue
        return result

    def foreground(self):
        prop=self.root.get_full_property(self.active_atom,self.X.AnyPropertyType)
        return int(prop.value[0]) if prop is not None and len(prop.value) else 0

    def focus(self, window):
        if self.foreground()!=window.window_id:self.command('windowactivate','--sync',window.window_id)
        if self.foreground()!=window.window_id:raise ClerkError('Window manager refused target activation')

    def capture(self, window):
        # X11 captures the visible client rectangle. Desktop overlays can appear in this region.
        with self.mss.mss() as capture:
            image=capture.grab({'left':int(window.bounds['x']),'top':int(window.bounds['y']),
                                'width':int(window.bounds['width']),'height':int(window.bounds['height'])})
            return self.mss.tools.to_png(image.rgb,image.size)

    def input(self, window, action):
        if self.foreground()!=window.window_id:raise ClerkError('Foreground changed before native input')
        pointer=self.command('getmouselocation','--shell')
        values=dict(line.split('=',1) for line in pointer.splitlines() if '=' in line)
        if int(values.get('X','100'))<=2 and int(values.get('Y','100'))<=2:raise ClerkError('Emergency stop: pointer is at the upper-left corner')
        name=Path(window.app_id).name.lower()
        if any(part in name for part in ('terminal','xterm','konsole','code','idea')):
            raise ClerkError('Terminal and editor targets are disabled')
        kind=action['kind']
        if kind in ('click','double_click','scroll'):
            self.command('mousemove','--sync',int(window.bounds['x']+action['x']),int(window.bounds['y']+action['y']))
            if self.foreground()!=window.window_id:raise ClerkError('Foreground changed before click')
            if kind=='scroll':
                delta=action['delta']
                if delta:self.command('click','--repeat',max(1,int(abs(delta)/60)), '--delay',20,4 if delta>0 else 5)
            else:self.command('click','--repeat',2 if kind=='double_click' else 1,'--delay',80,1)
        elif kind=='type':self.command('type','--clearmodifiers','--delay',1,'--',action['text'])
        elif kind=='key':
            keys={'enter':'Return','escape':'Escape','backspace':'BackSpace','tab':'Tab','space':'space','left':'Left','right':'Right','up':'Up','down':'Down','home':'Home','end':'End'}
            self.command('key','--clearmodifiers',keys[action['key']])
        elif kind=='wait':time.sleep(action['seconds'])
        else:raise ClerkError('Unsupported X11 action')

    def doctor(self):
        return {'ok':True,'platform':'Linux / X11','screen_recording':True,'accessibility':True,
                'capture':'Visible target client rectangle; may include desktop overlays','input':'X11 / xdotool',
                'verification':'Native host testing required'}
