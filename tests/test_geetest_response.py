"""Safe parsing tests for the upstream GeeTest JSONP response."""

import importlib.util
import os
import sys
import types
import unittest
from unittest.mock import Mock, patch

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
sys.modules.setdefault('geeked', types.SimpleNamespace(Geeked=Mock()))

spec = importlib.util.spec_from_file_location(
    'geetest_parser_main',
    os.path.join(os.path.dirname(os.path.dirname(__file__)), 'main.py'),
)
main = importlib.util.module_from_spec(spec)
spec.loader.exec_module(main)


class GeetestResponseTests(unittest.TestCase):
    def test_valid_jsonp(self):
        raw = 'cb123({"status":"success","data":{"lot_number":"public-demo"}})'
        self.assertEqual(main.parse_geetest_response(raw, 'cb123'),
                         {'lot_number': 'public-demo'})

    def test_missing_data_gives_only_status_and_code(self):
        raw = 'cb123({"status":"fail","code":"60100","msg":"token-sensitive-example"})'
        with self.assertRaises(main.GeetestResponseError) as ctx:
            main.parse_geetest_response(raw, 'cb123')
        self.assertIn('status=fail', str(ctx.exception))
        self.assertIn('code=60100', str(ctx.exception))
        self.assertNotIn('token-sensitive-example', str(ctx.exception))

    def test_nested_error_code(self):
        raw = 'cb123({"status":"error","error":{"code":"-50005","msg":"secret"}});'
        with self.assertRaises(main.GeetestResponseError) as ctx:
            main.parse_geetest_response(raw, 'cb123')
        self.assertIn('code=-50005', str(ctx.exception))
        self.assertNotIn('secret', str(ctx.exception))

    def test_unknown_code_not_leaked(self):
        raw = 'cb123({"status":"fail","code":"abc-user-token-sensitive"})'
        with self.assertRaises(main.GeetestResponseError) as ctx:
            main.parse_geetest_response(raw, 'cb123')
        self.assertIn('code=unknown', str(ctx.exception))
        self.assertNotIn('abc-user-token-sensitive', str(ctx.exception))

    def test_html_or_wrong_callback_rejected(self):
        with self.assertRaisesRegex(main.GeetestResponseError, 'JSONP'):
            main.parse_geetest_response('<html>denied</html>', 'cb123')

    def test_solver_uses_safe_parser_and_does_not_log_raw_response(self):
        class FakeGeeked:
            def __init__(self, *args, **kwargs):
                self.callback = 'cb123'

            def solve(self):
                return self.format_response(
                    'cb123({"status":"fail","code":"60100","msg":"hidden-token"})'
                )

        with patch.object(main, 'Geeked', FakeGeeked), \
             patch.object(main.time, 'sleep'), \
             patch('builtins.print') as printer:
            self.assertIsNone(main.solve_captcha('example-id'))
        logs = ' '.join(str(call) for call in printer.call_args_list)
        self.assertIn('code=60100', logs)
        self.assertNotIn('hidden-token', logs)


if __name__ == '__main__':
    unittest.main()
