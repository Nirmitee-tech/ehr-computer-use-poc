import threading
from openclerk.types import Observation, ClerkError


def screen(png=b'png-before', text='Ready to schedule'):
    return Observation('io.openclerk.clinicdemo', 42, {'x': 100, 'y': 100, 'width': 960, 'height': 650}, 960, 650, png, text)


def click():
    return {'kind': 'click', 'x': 400, 'y': 300, 'reason': 'Open the provider menu', 'expected': 'Provider choices appear'}


class Driver:
    def __init__(self):
        self.current = screen(); self.inputs = []; self.fail_after_input = False
    def observe(self, bundle):
        if self.fail_after_input and self.inputs:
            raise ClerkError('Capture failed after input')
        return self.current
    def execute(self, bundle, observation, action, stopped):
        if stopped(): raise ClerkError('Stopped')
        self.inputs.append(action)
        self.current = screen(b'png-after', 'Provider choices')
        return {'input_posted': True}
    def doctor(self): return {'ok': True, 'screen_recording': True, 'accessibility': True}
    def apps(self): return [{'name': 'Synthetic Clinic', 'bundle_id': 'io.openclerk.clinicdemo'}]


class Planner:
    model = 'test-vision'
    action = None
    def propose(self, task, observation, history): return self.action or click()
    def models(self): return ['test-vision']


class BlockingPlanner(Planner):
    def __init__(self): self.entered = threading.Event(); self.release = threading.Event()
    def propose(self, *args):
        self.entered.set(); self.release.wait(5)
        return click()
