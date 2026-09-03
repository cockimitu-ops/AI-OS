"""Offline shared-chat regressions. No provider, account, or service calls."""
import concurrent.futures
import importlib.util
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE / 'scripts'))
sys.path.insert(0, str(HERE))
# Codex's module import probes its account; never do that from these tests.
with patch('subprocess.Popen', side_effect=OSError('offline test')):
    import conversation_store as store
    import shared_briefing
    spec = importlib.util.spec_from_file_location('shared_test_engines', HERE / 'scripts' / 'engines.py')
    en = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(en)


class SharedMemoryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.calls, self.results = [], {}
        replacements = [
            (store, 'CONVERSATIONS_DIR', self.tmp.name + '/conversations'),
            (en, 'JOBS_DIR', self.tmp.name + '/jobs'),
            (en.claude_chat, 'JOBS_DIR', self.tmp.name + '/claude'),
            (en, 'INBOX', self.tmp.name + '/inbox'), (en, 'LOGS', self.tmp.name + '/logs'),
            (en, 'LIMIT_STATE', self.tmp.name + '/limits.json'),
            (en, 'limited', lambda engine: None),
            (en, '_tell_felix', lambda text: None),
            (en.safety_controls, 'dispatch_guard', lambda *a, **kw: None),
            (shared_briefing, 'system_instruction', lambda **kw: 'STANDING CORE'),
            (en, '_raw_result', lambda engine, job: dict(self.results[job])),
            (en, '_spawn', self.spawn),
            (en.claude_chat, 'send', self.claude_send),
        ]
        for obj, key, value in replacements:
            mock = patch.object(obj, key, value)
            mock.start()
            self.addCleanup(mock.stop)
        for name in en.ENGINES:
            mock = patch.dict(en.ENGINES[name], {'available': lambda: (True, '')})
            mock.start()
            self.addCleanup(mock.stop)
        # Auto knowledge extraction is outside this test and may write the vault.
        import knowledge_store
        mock = patch.object(knowledge_store, 'save', return_value=None)
        mock.start()
        self.addCleanup(mock.stop)
        self.cid = store.create('claude')

    def spawn(self, prefix, argv, message, **kw):
        job = f'{prefix}_test{len(self.calls)}'
        self.calls.append({'job': job, 'message': message,
                           'argv': argv('/tmp/prompt', message), 'meta': kw.get('meta')})
        return job

    def claude_send(self, session, message, **kw):
        job = f'cc_test{len(self.calls)}'
        self.calls.append({'job': job, 'message': message, 'session': session})
        return job

    def complete(self, ticket, text='answer', session='session-native'):
        self.results[ticket['job']] = {'ready': True, 'ok': True, 'reply': text, 'session_id': session}
        return en.result(ticket['engine'], ticket['job'], notify=False)

    def test_manual_switch_and_return_use_separate_sessions_and_deltas(self):
        first = en.send('claude', 'first question', conversation_id=self.cid)
        self.complete(first, 'Claude answer', 'claude-native')
        second = en.send('google-pro', 'second question', conversation_id=self.cid)
        self.assertIn('first question', self.calls[-1]['message'])
        self.assertIn('Claude answer', self.calls[-1]['message'])
        self.assertNotIn('--conversation', self.calls[-1]['argv'])
        self.assertIn('--no-briefing', self.calls[-1]['argv'])
        self.complete(second, 'Google answer', 'google-native')
        third = en.send('claude', 'third question', conversation_id=self.cid)
        prompt = self.calls[-1]['message']
        self.assertEqual(self.calls[-1]['session'], 'claude-native')
        self.assertIn('second question', prompt)
        self.assertIn('Google answer', prompt)
        self.assertNotIn('first question', prompt)
        self.assertNotIn('Claude answer', prompt)
        self.assertNotIn('STANDING CORE', prompt)
        self.assertEqual(prompt.count('third question'), 1)
        self.complete(third, 'third answer', 'claude-native')
        en.send('google-pro', 'fourth question', conversation_id=self.cid)
        self.assertIn('google-native', self.calls[-1]['argv'])
        self.assertNotIn('--continue', self.calls[-1]['argv'])
        self.assertNotIn('second question', self.calls[-1]['message'])

    def test_all_four_engines_get_the_same_bounded_prior_conversation(self):
        store.append(self.cid, 'user', 'remember this marker')
        for engine in en.ENGINES:
            with self.subTest(engine=engine):
                ticket = en.send(engine, 'new request', conversation_id=self.cid)
                prompt = ((Path(en.INBOX) / ticket['job']).read_text() if engine == 'aios'
                          else self.calls[-1]['message'])
                self.assertIn('remember this marker', prompt)
                if engine == 'aios':
                    self.assertIn('<!-- shared-history -->', prompt)
                    self.assertIn('web_' + self.cid, prompt)
                    self.assertNotIn('STANDING CORE', prompt)

    def test_handoff_remembers_full_question_context_and_ticket_once(self):
        store.append(self.cid, 'assistant', 'prior Google context', engine='google-pro')
        question = 'original ' + 'x' * 2400 + ' IMPORTANT TAIL'
        ticket = en.send('claude', question, conversation_id=self.cid)
        self.results[ticket['job']] = {'ready': True, 'ok': False, 'error': 'session limit'}
        one = en.result('claude', ticket['job'], notify=False)
        two = en.result('claude', ticket['job'], notify=False)
        self.assertEqual(one, two)
        self.assertEqual(one['conversation_id'], self.cid)
        self.assertEqual(len(self.calls), 2)
        self.assertIn('prior Google context', self.calls[-1]['message'])
        self.assertIn('IMPORTANT TAIL', self.calls[-1]['message'])
        self.assertEqual(sum(m['role'] == 'user' for m in store.read(self.cid)['messages']), 1)
        self.complete(one, 'Codex reply', 'codex-native')
        self.assertEqual(store.native_session(self.cid, 'codex')['id'], 'codex-native')

    def test_known_limit_records_the_user_exactly_once(self):
        with patch.object(en, 'limited', side_effect=lambda name: {'message': 'quota'} if name == 'claude' else None):
            ticket = en.send('claude', 'one user question', conversation_id=self.cid)
        self.assertEqual(ticket['engine'], 'codex')
        messages = store.read(self.cid)['messages']
        self.assertEqual(len(messages), 1)
        self.assertEqual(messages[0]['text'], 'one user question')
        self.assertEqual(self.calls[-1]['message'].count('one user question'), 1)

    def test_result_without_browser_id_records_once_and_rejects_mismatch(self):
        ticket = en.send('codex', 'hello', conversation_id=self.cid)
        self.complete(ticket)
        self.complete(ticket)
        self.assertEqual(len(store.read(self.cid)['messages']), 2)
        with self.assertRaises(ValueError):
            en.result('codex', ticket['job'], conversation_id=store.create('codex'))

    def test_failure_does_not_advance_native_cursor(self):
        ticket = en.send('google-pro', 'question', conversation_id=self.cid)
        self.results[ticket['job']] = {'ready': True, 'ok': False, 'error': 'network failure'}
        en.result('google-pro', ticket['job'], notify=False)
        self.assertEqual(store.native_session(self.cid, 'google-pro'), {})
        self.assertEqual(len(store.read(self.cid)['messages']), 1)

    def test_updated_briefing_is_injected_once_per_native_session(self):
        self.complete(en.send('codex', 'one', conversation_id=self.cid), session='codex-native')
        with patch.object(shared_briefing, 'system_instruction', return_value='UPDATED CORE'):
            second = en.send('codex', 'two', conversation_id=self.cid)
            self.assertIn('UPDATED CORE', self.calls[-1]['message'])
            self.complete(second, session='codex-native')
            en.send('codex', 'three', conversation_id=self.cid)
            self.assertNotIn('UPDATED CORE', self.calls[-1]['message'])

    def test_old_single_session_is_never_given_to_another_provider(self):
        path = Path(store._path(self.cid))
        path.write_text(json.dumps({'id': self.cid, 'engine': 'claude', 'session_id': 'old-claude',
                                    'messages': [{'role': 'user', 'text': 'legacy'}]}))
        en.send('codex', 'new', conversation_id=self.cid)
        self.assertNotIn('--resume', self.calls[-1]['argv'])
        self.assertIn('legacy', self.calls[-1]['message'])
        en.send('claude', 'back', conversation_id=self.cid)
        self.assertEqual(self.calls[-1]['session'], 'old-claude')

    def test_storage_context_and_sequence_stay_bounded(self):
        for i in range(410):
            store.append(self.cid, 'user', f'message {i}: ' + 'x' * 8100)
        record = store.read(self.cid)
        self.assertEqual(len(record['messages']), 400)
        self.assertEqual(record['next_seq'], 411)
        self.assertLessEqual(max(len(m['text']) for m in record['messages']), 8000)
        self.assertLessEqual(len(store.format_context(self.cid)), 6000)
        self.assertLessEqual(len(store.history_context(self.cid)), 24)
        self.assertEqual(store.history_context(self.cid, max_messages=0), [])

    def test_concurrent_append_and_collect_are_idempotent(self):
        ticket = en.send('claude', 'question', conversation_id=self.cid)
        self.results[ticket['job']] = {'ready': True, 'ok': True, 'reply': 'once', 'session_id': 'native'}
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
            list(pool.map(lambda _: en.result('claude', ticket['job'], notify=False), range(8)))
        self.assertEqual([m['text'] for m in store.read(self.cid)['messages']], ['question', 'once'])

    def test_late_reply_does_not_skip_other_engine_input_after_dispatch(self):
        ticket = en.send('claude', 'original', conversation_id=self.cid)
        store.append(self.cid, 'user', 'concurrent Google question')
        store.append(self.cid, 'assistant', 'concurrent Google answer', engine='google-pro')
        self.complete(ticket, 'late Claude answer', 'native')
        en.send('claude', 'next', conversation_id=self.cid)
        self.assertIn('concurrent Google question', self.calls[-1]['message'])
        self.assertIn('concurrent Google answer', self.calls[-1]['message'])

    def test_read_only_handoff_never_escalates_capabilities(self):
        ticket = en.send('google-pro', 'review only', conversation_id=self.cid, read_only=True)
        self.results[ticket['job']] = {'ready': True, 'ok': False, 'error': 'quota'}
        result = en.result('google-pro', ticket['job'], notify=False)
        self.assertEqual(result['engine'], 'codex')
        self.assertIn('--read-only', self.calls[-1]['argv'])

    def test_worker_metadata_never_appears_as_an_immortal_cli_job(self):
        en.send('aios', 'question', conversation_id=self.cid)
        self.assertEqual(en.in_flight(), [])

    def test_worker_error_is_not_successful_shared_memory(self):
        ticket = en.send('aios', 'question', conversation_id=self.cid)
        log = Path(en.LOGS) / (ticket['job'] + '.log')
        log.write_text('ERROR during execution: provider failed')
        reply = en._aios_result(ticket['job'])
        self.assertFalse(reply['ok'])

    def test_newest_turn_survives_rendered_label_overhead(self):
        for i in range(24):
            store.append(self.cid, 'assistant', f'entry {i} ' + 'x' * 240, engine='google-pro')
        prompt = store.format_context(self.cid)
        self.assertLessEqual(len(prompt), 6000)
        self.assertIn('entry 23 ' + 'x' * 240, prompt)

    def test_late_reply_from_discarded_native_session_is_shared(self):
        first = en.send('claude', 'old parallel question', conversation_id=self.cid)
        second = en.send('claude', 'new parallel question', conversation_id=self.cid)
        self.complete(second, 'new reply', 'retained-native')
        self.complete(first, 'late reply from other native', 'discarded-native')
        en.send('claude', 'continue', conversation_id=self.cid)
        self.assertEqual(self.calls[-1]['session'], 'retained-native')
        self.assertIn('late reply from other native', self.calls[-1]['message'])
        self.assertNotIn('new reply', self.calls[-1]['message'])


if __name__ == '__main__':
    unittest.main()
