import importlib.util
import os
import sys
import types
import unittest
from unittest.mock import Mock, patch

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
sys.modules.setdefault('geeked', types.SimpleNamespace(Geeked=Mock()))
spec = importlib.util.spec_from_file_location('checkin_main', os.path.join(os.path.dirname(os.path.dirname(__file__)), 'main.py'))
checkin_main = importlib.util.module_from_spec(spec)
spec.loader.exec_module(checkin_main)
checkin_main.url = 'https://example.com'


class CheckinNotificationTests(unittest.TestCase):
    def test_captcha_failure_notifies_and_closes_session(self):
        session = Mock()
        with patch.object(checkin_main.requests, 'session', return_value=session), \
             patch.object(checkin_main, 'solve_captcha', return_value=None), \
             patch.object(checkin_main, 'notify') as notify:
            checkin_main.sign(0, 'alice@example.com', 'password')
        notify.assert_called_once()
        self.assertIn('验证码求解失败', notify.call_args.args[1])
        self.assertNotIn('alice@example.com', notify.call_args.args[1])
        session.close.assert_called_once()

    def test_login_failure_notifies(self):
        session = Mock()
        session.post.return_value.json.return_value = {'ret': 0, 'msg': '登录失败'}
        with patch.object(checkin_main.requests, 'session', return_value=session), \
             patch.object(checkin_main, 'solve_captcha', return_value={'lot_number': 'a', 'captcha_output': 'b', 'pass_token': 'c', 'gen_time': 'd'}), \
             patch.object(checkin_main, 'notify') as notify:
            checkin_main.sign(0, 'alice@example.com', 'password')
        self.assertIn('签到失败', notify.call_args.args[0])
        self.assertEqual(session.post.call_count, 1)

    def test_success_notifies(self):
        session = Mock()
        session.post.side_effect = [Mock(**{'json.return_value': {'ret': 1, 'msg': '登录成功'}}), Mock(**{'json.return_value': {'ret': 1, 'msg': '签到成功，获得1G'}})]
        with patch.object(checkin_main.requests, 'session', return_value=session), \
             patch.object(checkin_main, 'solve_captcha', return_value={'lot_number': 'a', 'captcha_output': 'b', 'pass_token': 'c', 'gen_time': 'd'}), \
             patch.object(checkin_main, 'notify') as notify:
            checkin_main.sign(0, 'alice@example.com', 'password')
        self.assertEqual(notify.call_args.args[0], '机场签到成功')
        self.assertIn('1G', notify.call_args.args[1])
        self.assertEqual(session.post.call_count, 2)

    def test_checkin_rejected_notifies_failure(self):
        session = Mock()
        session.post.side_effect = [Mock(**{'json.return_value': {'ret': 1, 'msg': '登录成功'}}), Mock(**{'json.return_value': {'ret': 0, 'msg': '今日已经签到'}})]
        with patch.object(checkin_main.requests, 'session', return_value=session), \
             patch.object(checkin_main, 'solve_captcha', return_value={'lot_number': 'a', 'captcha_output': 'b', 'pass_token': 'c', 'gen_time': 'd'}), \
             patch.object(checkin_main, 'notify') as notify:
            checkin_main.sign(0, 'alice@example.com', 'password')
        self.assertEqual(notify.call_args.args[0], '机场签到失败')
        self.assertIn('已经签到', notify.call_args.args[1])

    def test_exception_notifies_and_closes(self):
        session = Mock()
        session.post.side_effect = RuntimeError('connection failed')
        with patch.object(checkin_main.requests, 'session', return_value=session), \
             patch.object(checkin_main, 'solve_captcha', return_value={'lot_number': 'a', 'captcha_output': 'b', 'pass_token': 'c', 'gen_time': 'd'}), \
             patch.object(checkin_main, 'notify') as notify:
            checkin_main.sign(0, 'alice@example.com', 'password')
        self.assertIn('签到失败', notify.call_args.args[0])
        session.close.assert_called_once()


if __name__ == '__main__':
    unittest.main()
