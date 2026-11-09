import time
import unittest

import flow_credits
import robot


def iso(t):
    import datetime as dt
    return dt.datetime.fromtimestamp(t, dt.timezone.utc).isoformat()


class RobotTest(unittest.TestCase):
    def setUp(self):
        self.now = time.time()

    def job(self, **kw):
        base = {'id': 'j', 'status': 'running', 'stage': 'script', 'created': iso(self.now - 7200),
                'events': [{'at': iso(self.now - 3600), 'text': 'x'}]}
        base.update(kw)
        return base

    def test_stalled_running_episode_is_scheduled(self):
        d = robot.inspect(self.job(), [], self.now, flow_credits.seconds)
        self.assertEqual(d['action'], 'schedule')

    def test_live_task_is_left_alone(self):
        d = robot.inspect(self.job(), [{'status': 'claimed', 'slot': 'script'}], self.now, flow_credits.seconds)
        self.assertIsNone(d)

    def test_recent_news_is_left_alone(self):
        j = self.job(events=[{'at': iso(self.now - 60), 'text': 'x'}])
        self.assertIsNone(robot.inspect(j, [], self.now, flow_credits.seconds))

    def test_technical_chat_failure_is_resumed(self):
        j = self.job(status='attention', events=[{'at': iso(self.now - 300), 'text': 'Réponse JSON complète non détectée'}])
        t = {'status': 'failed', 'slot': 'script', 'kind': 'chat_text', 'created': iso(self.now - 600), 'error': 'Réponse JSON complète non détectée'}
        self.assertEqual(robot.inspect(j, [t], self.now, flow_credits.seconds)['action'], 'resume')

    def test_clip_failure_is_never_touched(self):
        j = self.job(status='attention', stage='clips', events=[{'at': iso(self.now - 300), 'text': 'timeout'}])
        t = {'status': 'failed', 'slot': 'clip:3', 'kind': 'flow_video', 'created': iso(self.now - 600), 'error': 'timeout'}
        self.assertIsNone(robot.inspect(j, [t], self.now, flow_credits.seconds))

    def test_other_failure_waits_for_owner(self):
        j = self.job(status='attention', events=[{'at': iso(self.now - 300), 'text': 'Contenu refusé'}])
        t = {'status': 'failed', 'slot': 'script', 'kind': 'chat_text', 'created': iso(self.now - 600), 'error': 'Contenu refusé'}
        self.assertIsNone(robot.inspect(j, [t], self.now, flow_credits.seconds))

    def test_fix_budget(self):
        j = self.job()
        for _ in range(robot.MAX_FIXES):
            robot.note(j, {'action': 'schedule', 'why': 'x'}, self.now, iso(self.now))
        self.assertIsNone(robot.inspect(j, [], self.now, flow_credits.seconds))

    def test_waiting_credit_and_paused_untouched(self):
        for status in ('paused', 'waiting_credit', 'done'):
            self.assertIsNone(robot.inspect(self.job(status=status), [], self.now, flow_credits.seconds))

    def test_failed_filon_retried(self):
        j = self.job(status='attention', filon_only=True, stage='research')
        self.assertEqual(robot.inspect(j, [], self.now, flow_credits.seconds)['action'], 'refresh_filon')


if __name__ == '__main__':
    unittest.main()
