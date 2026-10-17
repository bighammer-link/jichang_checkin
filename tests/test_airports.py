"""Configuration and isolation tests for multi-airport check-in."""

import importlib.util
import json
import os
import sys
import types
import unittest
from unittest.mock import Mock, patch

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
sys.modules.setdefault('geeked', types.SimpleNamespace(Geeked=Mock()))
spec = importlib.util.spec_from_file_location(
    'multi_airport_main', os.path.join(os.path.dirname(os.path.dirname(__file__)), 'main.py')
)
main = importlib.util.module_from_spec(spec)
spec.loader.exec_module(main)


class AirportConfigurationTests(unittest.TestCase):
    def setUp(self):
        self.airports = [
            {
                'name': '机场A',
                'url': 'https://a.example.com/',
                'captcha_id': 'site-a-geetest-id',
                'accounts': [
                    {'email': 'alice@example.com', 'password': 'a-password'},
                    {'email': 'bob@example.com', 'password': 'b-password'},
                ],
            },
            {
                'name': '机场B',
                'url': 'https://b.example.com',
                'captcha_id': 'site-b-geetest-id',
                'accounts': [{'email': 'charlie@example.com', 'password': 'c-password'}],
            },
        ]

    def test_two_airports_three_accounts(self):
        result = main.load_airports({'AIRPORTS': json.dumps(self.airports)})
        self.assertEqual(len(result), 2)
        self.assertEqual(len(result[0]['accounts']), 2)
        self.assertEqual(len(result[1]['accounts']), 1)
        self.assertEqual(result[0]['url'], 'https://a.example.com')
        self.assertEqual(result[1]['captcha_id'], 'site-b-geetest-id')

    def test_json_config_takes_precedence_over_legacy(self):
        result = main.load_airports({
            'AIRPORTS': json.dumps(self.airports),
            'URL': 'https://legacy.example.com',
            'CONFIG': 'old@example.com\noldpass',
        })
        self.assertEqual(len(result), 2)
        self.assertNotIn('legacy', str(result))

    def test_legacy_multi_account_is_preserved(self):
        result = main.load_airports({
            'URL': 'https://legacy.example.com/',
            'CONFIG': 'alice@example.com\na-pass\nbob@example.com\nb-pass',
        })
        self.assertEqual(len(result), 1)
        self.assertEqual(len(result[0]['accounts']), 2)
        self.assertEqual(result[0]['url'], 'https://legacy.example.com')
        self.assertEqual(result[0]['captcha_id'], main.CAPTCHA_ID)

    def test_invalid_json_rejected_without_credentials_in_error(self):
        with self.assertRaisesRegex(ValueError, 'JSON'):
            main.load_airports({'AIRPORTS': '[invalid-secret]'})

    def test_invalid_account_or_airport_skipped(self):
        bad = [
            {'name': '坏机场', 'url': 'javascript:bad', 'accounts': []},
            {'name': '好机场', 'url': 'https://good.example.com', 'accounts': [
                {'email': 'alice@example.com', 'password': 'pass'},
                {'email': 'missing-password@example.com'},
            ]},
        ]
        result = main.load_airports({'AIRPORTS': json.dumps(bad)})
        self.assertEqual(len(result), 1)
        self.assertEqual(len(result[0]['accounts']), 1)
        self.assertEqual(result[0]['captcha_id'], main.CAPTCHA_ID)

    def test_empty_usable_accounts_error(self):
        with self.assertRaisesRegex(ValueError, '没有可运行'):
            main.load_airports({'AIRPORTS': '[{"url":"https://ok.example.com","accounts":[]}]'})

    def test_legacy_odd_line_count_error(self):
        with self.assertRaisesRegex(ValueError, 'CONFIG'):
            main.load_airports({'URL': 'https://test.example.com', 'CONFIG': 'a@example.com'})

    def test_url_query_or_credentials_not_allowed(self):
        self.assertIsNone(main.validate_url('https://u:pwd@a.example.com'))
        self.assertIsNone(main.validate_url('https://a.example.com/path'))
        self.assertIsNone(main.validate_url('https://a.example.com/?query=x'))


class MultiAirportRuntimeTests(unittest.TestCase):
    def test_run_all_continues_after_one_account_exception(self):
        data = json.dumps([
            {'name': '机场 A', 'url': 'https://a.example.com', 'captcha_id': 'A', 'accounts': [
                {'email': 'a@example.com', 'password': '1'},
                {'email': 'b@example.com', 'password': '2'},
            ]},
            {'name': '机场 B', 'url': 'https://b.example.com', 'captcha_id': 'B', 'accounts': [
                {'email': 'c@example.com', 'password': '3'},
            ]},
        ])
        with patch.object(main, 'sign', side_effect=[RuntimeError('failed'), None, None]) as checkin, \
             patch.object(main, 'notify') as notify:
            main.run_all({'AIRPORTS': data})
        self.assertEqual(checkin.call_count, 3)
        self.assertEqual(checkin.call_args_list[0].kwargs['captcha_id'], 'A')
        self.assertEqual(checkin.call_args_list[2].kwargs['captcha_id'], 'B')
        self.assertEqual(checkin.call_args_list[2].kwargs['airport_name'], '机场 B')
        notify.assert_called_once()

    def test_site_specific_captcha_and_notification_label(self):
        session = Mock()
        session.post.side_effect = [
            Mock(**{'json.return_value': {'ret': 1, 'msg': 'login ok'}}),
            Mock(**{'json.return_value': {'ret': 1, 'msg': 'checkin ok'}}),
        ]
        with patch.object(main.requests, 'session', return_value=session), \
             patch.object(main, 'solve_captcha', return_value={
                 'lot_number': 'a', 'captcha_output': 'b', 'pass_token': 'c', 'gen_time': 'd',
             }) as solver, \
             patch.object(main, 'notify') as notifier:
            main.sign(0, 'user@example.com', 'password',
                      airport_url='https://site.example.com',
                      captcha_id='site-captcha-id', airport_name='机场 B')
        solver.assert_called_once_with('site-captcha-id')
        self.assertEqual(session.post.call_args_list[0].args[0], 'https://site.example.com/auth/login')
        self.assertEqual(session.post.call_args_list[1].args[0], 'https://site.example.com/user/checkin')
        self.assertIn('机场 B', notifier.call_args.args[1])
        self.assertNotIn('user@example.com', notifier.call_args.args[1])


if __name__ == '__main__':
    unittest.main()
