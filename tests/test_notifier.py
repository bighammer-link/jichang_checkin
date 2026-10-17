import base64
import hashlib
import hmac
import os
import sys
import unittest
from unittest.mock import patch
from urllib.parse import parse_qs, urlsplit

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
import notifier

WEBHOOK = 'https://oapi.dingtalk.com/robot/send?access_token=example-token'


class Response:
    def __init__(self, code=0):
        self.code = code

    def raise_for_status(self):
        pass

    def json(self):
        return {'errcode': self.code, 'code': 0, 'errmsg': 'ok' if self.code == 0 else 'invalid signature'}


class NotifierTests(unittest.TestCase):
    def test_signed_url_preserves_token_and_has_expected_hmac(self):
        secret = 'SEC-test-secret'
        url = notifier.signed_dingtalk_webhook(WEBHOOK, secret, timestamp='1710000000000')
        q = parse_qs(urlsplit(url).query)
        digest = hmac.new(secret.encode(), b'1710000000000\nSEC-test-secret', hashlib.sha256).digest()
        self.assertEqual(q['sign'], [base64.b64encode(digest).decode()])
        self.assertEqual(q['timestamp'], ['1710000000000'])
        self.assertEqual(q['access_token'], ['example-token'])

    @patch.dict(os.environ, {'DINGTALK_WEBHOOK': WEBHOOK, 'DINGTALK_SECRET': 'SEC-test-secret'}, clear=True)
    @patch('notifier.requests.post', return_value=Response())
    def test_sent_as_text_and_with_timeout(self, post):
        notifier.send_dingtalk('机场签到成功', '消息')
        self.assertEqual(post.call_count, 1)
        args, kwargs = post.call_args
        self.assertEqual(kwargs['json']['msgtype'], 'text')
        self.assertIn('消息', kwargs['json']['text']['content'])
        self.assertEqual(kwargs['timeout'], 10)
        self.assertIn('sign=', args[0])

    @patch.dict(os.environ, {'DINGTALK_WEBHOOK': WEBHOOK}, clear=True)
    @patch('notifier.requests.post')
    def test_missing_secret_does_not_send(self, post):
        notifier.send_dingtalk('标题', '内容')
        post.assert_not_called()

    @patch.dict(os.environ, {}, clear=True)
    @patch('notifier.requests.post')
    def test_no_secrets_does_not_send(self, post):
        notifier.notify('标题', '内容')
        post.assert_not_called()

    @patch.dict(os.environ, {'DINGTALK_WEBHOOK': 'http://evil.com/robot/send?access_token=x', 'DINGTALK_SECRET': 'SEC-test-secret'}, clear=True)
    @patch('notifier.requests.post')
    def test_invalid_url_does_not_send(self, post):
        notifier.send_dingtalk('标题', '内容')
        post.assert_not_called()

    @patch.dict(os.environ, {'SCKEY': 'test-server-key', 'DINGTALK_WEBHOOK': WEBHOOK, 'DINGTALK_SECRET': 'SEC-test-secret'}, clear=True)
    @patch('notifier.requests.post')
    def test_notifier_uses_both_channels(self, post):
        post.side_effect = [Response(), Response()]
        notifier.notify('签到', '消息')
        self.assertEqual(post.call_count, 2)
        self.assertIn('sctapi.ftqq.com', post.call_args_list[0].args[0])
        self.assertIn('oapi.dingtalk.com', post.call_args_list[1].args[0])


if __name__ == '__main__':
    unittest.main()
