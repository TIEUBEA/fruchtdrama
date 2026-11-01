import copy
import pathlib
import tempfile
import unittest
from unittest.mock import patch

import server as s
import flow_accounts as accounts


def profile(name, balance, client='browser'):
    return {'id': name, 'label': name+'@example.com', 'balance': balance,
            'flow_email': name+'@example.com', 'flow_client': client,
            'flow_url': 'https://flow.google.com/u/'+('0' if name=='a' else '1')+'/project/'+name,
            'auto_enabled': True}


class FlowAccountsTests(unittest.TestCase):
    def setUp(self):
        self.old_state,self.old_data=s.STATE,s.DATA
        self.temp=tempfile.TemporaryDirectory();s.DATA=pathlib.Path(self.temp.name)
        s.STATE=s.fresh();s.STATE['settings']['flow_auto']=True
        s.STATE['clients']={'browser':{'id':'browser','role':'flow','seen':s.now()}}
        s.STATE['profiles']=[profile('a',0),profile('b',50)]
        self.job={'id':'1234567890abcdef','stage':'clips','status':'running','events':[],
                  'config':{'flow_cost':10},'flow_profile':'a','characters':[],
                  'scenes':[{'image':'image.png','dialogue':[],'video_prompt':'a new scene'}]}
        s.STATE['jobs']=[self.job]

    def tearDown(self):
        s.STATE,s.DATA=self.old_state,self.old_data;self.temp.cleanup()

    def schedule(self):
        with patch.object(s,'flow_reference',return_value='reference.jpg'):
            s.schedule(self.job)

    def test_switch_routes_next_scene_to_registered_account(self):
        self.schedule();t=s.STATE['tasks'][0]
        self.assertEqual(t['profile'],'b');self.assertTrue(t['payload']['flow_route']['new_project'])
        self.assertTrue(s.client_accepts(s.STATE['clients']['browser'],t))
        self.assertFalse(s.client_accepts({'id':'unrelated','role':'flow','flow_profile':'b'},t))
        self.assertFalse(s.client_accepts({'id':'browser','role':'creation'},t))

    def test_preserves_received_clips_and_reuses_production_project(self):
        self.job['scenes'].insert(0,{'clip':'already_received.mp4'})
        self.job['flow_projects']={'b':'https://flow.google.com/u/1/project/new-production'}
        self.schedule();t=s.STATE['tasks'][0]
        self.assertEqual(t['slot'],'clip:1');self.assertNotIn('new_project',t['payload']['flow_route'])
        self.assertEqual(t['payload']['flow_route']['url'],self.job['flow_projects']['b'])
        self.assertEqual(self.job['scenes'][0]['clip'],'already_received.mp4')

    def test_no_switch_or_browser_launch_while_task_is_claimed(self):
        s.STATE['tasks']=[{'id':'active','job':self.job['id'],'slot':'clip:0','kind':'flow_video','status':'claimed','profile':'a'}]
        with patch.object(accounts,'launch') as launch:
            self.schedule();s.flow_dispatch_tick();launch.assert_not_called()
        self.assertEqual(len(s.STATE['tasks']),1)

    def test_only_explicit_credit_failure_before_submission_can_switch(self):
        s.STATE['profiles'][0]['balance']=10
        self.schedule();t=s.STATE['tasks'][0];t['status']='claimed'
        t['reservation']={'profile':'a','amount':10,'refunded':False};s.STATE['profiles'][0]['balance']=0
        with patch.object(s,'flow_reference',return_value='reference.jpg'):
            s.accept_task_result(t,{'ok':False,'generation_submitted':False,'flow_blocked':'credits','error':'credits'})
        self.assertEqual(self.job['flow_profile'],'b');self.assertEqual(len(s.STATE['tasks']),2)
        self.assertEqual(s.STATE['profiles'][0]['balance'],10)
        self.assertEqual(s.STATE['profiles'][0]['blocked'],'credits')

    def test_uncertain_submission_never_switches_or_refunds(self):
        s.STATE['profiles'][0]['balance']=10;self.schedule();t=s.STATE['tasks'][0]
        t['reservation']={'profile':'a','amount':10,'refunded':False};s.STATE['profiles'][0]['balance']=0
        s.accept_task_result(t,{'ok':False,'generation_submitted':True,'flow_blocked':'credits','error':'uncertain'})
        self.assertEqual(self.job['status'],'attention');self.assertEqual(len(s.STATE['tasks']),1)
        self.assertEqual(s.STATE['profiles'][0]['balance'],0)

    def test_unregistered_disabled_or_exhausted_profiles_are_not_used(self):
        for change in ({'flow_client':'missing'},{'auto_enabled':False},{'blocked':'credits'},{'balance':0}):
            s.STATE['profiles'][1]=dict(profile('b',50),**change)
            self.assertIsNone(accounts.choose(s.STATE,'a',10))
        s.STATE['settings']['flow_auto']=False;s.STATE['profiles'][1]=profile('b',50)
        self.assertIsNone(accounts.choose(s.STATE,'a',10))

    def test_one_browser_wakeup_for_100_accounts_and_no_repeated_open(self):
        s.STATE['profiles']=[profile('a',0)]+[profile('b'+str(i),50) for i in range(99)]
        s.STATE['clients']['browser']['seen']='2000-01-01T00:00:00+00:00'
        self.schedule()
        with patch.object(accounts,'launch') as launch:
            s.flow_dispatch_tick();s.flow_dispatch_tick()
            launch.assert_called_once()

    def test_online_browser_does_not_need_external_launch(self):
        self.schedule()
        with patch.object(accounts,'launch') as launch:
            s.flow_dispatch_tick();launch.assert_not_called()

    def test_disabled_automation_does_not_create_or_open_projects(self):
        s.STATE['settings']['flow_auto']=False;self.job['flow_profile']='b'
        self.schedule();self.assertNotIn('flow_route',s.STATE['tasks'][0]['payload'])

    def test_ai_only_client_is_not_selected_for_flow(self):
        s.STATE['clients']['browser']['role']='creation'
        self.assertIsNone(accounts.choose(s.STATE,'b',10))

    def test_rejects_external_urls_and_invalid_chrome_directories(self):
        for url in ('https://evil.example/project/id','http://flow.google.com/project/id','https://flow.google.com@evil.example/project/id','https://flow.google.com/project/id?authuser=0'):
            with self.assertRaises(ValueError):accounts.project_url(url)
        with self.assertRaises(ValueError):accounts.chrome_profile('../Profile 1')
        self.assertEqual(accounts.chrome_profile('Profile 1'),'Profile 1')
        self.assertEqual(accounts.account_home('https://flow.google.com/u/3/project/p/edit/v'),'https://flow.google.com/u/3/')

    def test_delete_profile_keeps_media_and_pauses_queued_production(self):
        self.job['flow_profile']='b';self.job['scenes'].insert(0,{'clip':'received.mp4'})
        self.job['flow_projects']={'b':'https://flow.google.com/u/1/project/old'}
        media=s.job_dir(self.job)/'received.mp4';media.write_bytes(b'preserved')
        s.STATE['clients']['browser'].update(flow_profile='b',ai_provider='chatgpt')
        self.schedule();deleted_task=copy.deepcopy(s.STATE['tasks'][0]);s.delete_profile('b')
        self.assertIsNone(s.profile_by('b'));self.assertEqual(self.job['status'],'paused')
        self.assertIsNone(self.job['flow_profile']);self.assertNotIn('b',self.job['flow_projects'])
        self.assertEqual(s.STATE['tasks'][0]['status'],'cancelled')
        self.assertEqual(media.read_bytes(),b'preserved');self.assertEqual(self.job['scenes'][0]['clip'],'received.mp4')
        self.assertEqual(s.STATE['clients']['browser']['ai_provider'],'chatgpt')
        self.assertIsNone(s.STATE['clients']['browser']['flow_profile'])
        self.assertFalse(s.client_accepts(s.STATE['clients']['browser'],deleted_task))

    def test_delete_profile_in_use_is_rejected_atomically(self):
        self.schedule();s.STATE['tasks'][0]['status']='claimed';before=copy.deepcopy(s.STATE)
        with self.assertRaisesRegex(ValueError,'en cours'):s.delete_profile('b')
        self.assertEqual(s.STATE,before)

    def test_delete_uncertain_profile_requires_receiving_the_clip_first(self):
        t={'job':self.job['id'],'profile':'a','slot':'clip:0','status':'failed','reservation':{'refunded':False}}
        s.STATE['tasks']=[t]
        with self.assertRaisesRegex(ValueError,'reste à vérifier'):s.delete_profile('a')
        self.job['scenes'][0]['clip']='recovered.mp4';self.job['status']='done'
        s.delete_profile('a');self.assertEqual(self.job['status'],'done')
        self.assertEqual(self.job['scenes'][0]['clip'],'recovered.mp4')

    def test_delete_unknown_profile_does_not_change_state(self):
        before=copy.deepcopy(s.STATE)
        with self.assertRaisesRegex(ValueError,'introuvable'):s.delete_profile('missing')
        self.assertEqual(s.STATE,before)


if __name__=='__main__':unittest.main()
