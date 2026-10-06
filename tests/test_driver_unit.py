import unittest
from unittest.mock import patch, Mock
from openclerk.driver import MacDriver
from openclerk.types import ClerkError


class MacDriverTests(unittest.TestCase):
    def test_activation_uses_literal_bundle_argument_without_shell(self):
        driver=MacDriver('/unused/bridge')
        with patch('openclerk.driver.subprocess.run',return_value=Mock(returncode=0)) as run:
            driver.activate('io.openclerk.clinicdemo')
            args,kwargs=run.call_args
            self.assertEqual(args[0],['/usr/bin/open','-b','io.openclerk.clinicdemo'])
            self.assertNotIn('shell',kwargs);self.assertEqual(kwargs['timeout'],5)
    def test_blocked_target_is_not_launched(self):
        with patch('openclerk.driver.subprocess.run') as run:
            with self.assertRaises(ClerkError):MacDriver('/unused/bridge').activate('com.apple.Terminal')
            run.assert_not_called()
    def test_failed_activation_is_reported(self):
        with patch('openclerk.driver.subprocess.run',return_value=Mock(returncode=1)):
            with self.assertRaises(ClerkError):MacDriver('/unused/bridge').activate('io.openclerk.missing')
    def test_missing_bridge_is_reported(self):
        with self.assertRaises(ClerkError):MacDriver('/definitely/not/a/bridge').doctor()


if __name__=='__main__':unittest.main()
