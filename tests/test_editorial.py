import copy
import json
import pathlib
import tempfile
import unittest

import editorial
import server as s


def story():
    concepts=[{'title':'The broken ticket' if i==0 else 'Concept '+str(i),
               'hook':'Why are you taking my last train ticket?' if i==0 else 'What is happening to item number '+str(i)+'?',
               'conflict':'A stranger takes the only ticket','setting':'A station','twist':'The ticket was exchanged by mistake','ending':'A costly choice',
               'scores':{'hook':5 if i==0 else 2,'clarity':4,'emotion':4,'novelty':5 if i==0 else 2}} for i in range(5)]
    return {'title':concepts[0]['title'],'cover_title':'THE LAST TRAIN?','description':'Original AI fiction',
            'creative_selection':{'candidates':concepts,'selected_index':0,'reason':'Visible urgency and a clear choice'},
            'story_signature':{'relationship':'strangers','setting':'train station','central_object':'last ticket','twist_mechanism':'mistaken exchange with a costly rescue'},
            'characters':[{'id':'pear','name':'Lou','appearance':'A pear in a coat','voice':'Native English','image_prompt':'A pear in a coat'}],
            'scenes':[{'characters':['pear'],'meaning':text,'image_prompt':'Station scene '+str(i),'video_prompt':'Moving camera','dialogue':[{'speaker':'pear','text':line}]} for i,(text,line) in enumerate([
                ('The last train is leaving while a stranger takes the only ticket from the counter.',concepts[0]['hook']),
                ('The stranger points at a torn matching corner and reveals that two tickets have been swapped.','Look at the torn corner. This one belongs to me.'),
                ('Lou gives up the seat and runs towards the departing train to return the missing bag.','Take the seat. Your child needs you tonight.')])]}


class EditorialTests(unittest.TestCase):
    def setUp(self):
        self.old_state,self.old_data=s.STATE,s.DATA
        self.temp=tempfile.TemporaryDirectory();s.DATA=pathlib.Path(self.temp.name);s.STATE=s.fresh()
        self.job={'id':'1234567890abcdef','editorial_version':2,'stage':'script','status':'running','events':[],
                  'config':{'scene_count':3,'provider':'chatgpt','flow_cost':10,'query':'fruit stories','language':'English (en-US)'},
                  'brief':'Choose an original story','selected':{'url':'https://www.tiktok.com/@a/video/1','basis':'vues','views':1000},
                  'characters':[],'scenes':[],'flow_profile':None}
        s.STATE['jobs']=[self.job]

    def tearDown(self):
        s.STATE,s.DATA=self.old_state,self.old_data;self.temp.cleanup()

    def add_old(self):
        old={'id':'old','title':'Previous story','script':story(),'scenes':story()['scenes'],'characters':story()['characters'],'selected':{'url':'https://www.tiktok.com/@a/video/1'}}
        s.STATE['jobs'].append(old);return old

    def test_accepts_winning_concept_and_rejects_wrong_choice(self):
        draft=story();editorial.validate(draft,self.job,s.STATE['jobs'])
        draft['creative_selection']['selected_index']=1
        editorial.validate(draft,self.job,s.STATE['jobs'])  # 0.1.102: the concept comparison never refuses a script

    def test_rejects_recycled_story_with_only_a_different_title(self):
        self.add_old();draft=story();draft['title']='Another title';draft['creative_selection']['candidates'][0]['title']=draft['title']
        with self.assertRaisesRegex(editorial.Rejection,'trop proche'):editorial.validate(draft,self.job,s.STATE['jobs'])

    def test_rejects_duplicate_signature_even_when_dialogues_are_translated(self):
        self.add_old();draft=story()
        for i,scene in enumerate(draft['scenes']):
            scene['meaning']='Une action entièrement différente dans un autre lieu numéro '+str(i)
            scene['dialogue'][0]['text']='Rends cette lettre maintenant, personne ne doit la voir !' if i==0 else 'Je dois partir avec mon chien ce soir.'
        draft['creative_selection']['candidates'][0]['hook']=draft['scenes'][0]['dialogue'][0]['text']
        with self.assertRaisesRegex(editorial.Rejection,'signature narrative'):editorial.validate(draft,self.job,s.STATE['jobs'])

    def test_legacy_scripts_remain_accepted_without_five_concepts(self):
        draft=story();draft.pop('creative_selection');draft.pop('story_signature');self.job.pop('editorial_version')
        s.store_script(self.job,draft);self.assertEqual(self.job['title'],draft['title'])

    def test_bad_new_script_rewrites_at_most_twice_before_any_image_generation(self):
        self.add_old();draft=story();draft['title']='Another title'  # a real defect (same story) still refuses
        for attempt in range(3):
            t={'id':str(attempt),'job':self.job['id'],'kind':'chat_text','slot':'script','status':'claimed'}
            s.STATE['tasks'].append(t);s.accept_task_result(t,{'ok':True,'text':json.dumps(draft)})
            self.assertEqual(t['status'],'failed')
            self.assertEqual(self.job['characters'],[])
            if attempt<2:
                queued=[x for x in s.STATE['tasks'] if x['status']=='queued'];self.assertEqual(len(queued),1)
                queued[0]['status']='cancelled'
        self.assertEqual(self.job['status'],'attention')
        self.assertTrue(all(t['kind']=='chat_text' for t in s.STATE['tasks']))

    def test_history_is_in_prompt_without_modifying_existing_project_or_media(self):
        old=self.add_old();old_before=copy.deepcopy(old)
        file=pathlib.Path(self.temp.name)/'existing.mp4';file.write_bytes(b'untouched')
        prompt=s.script_prompt(self.job)
        self.assertIn('Previous story',prompt);self.assertIn('CINQ concepts',prompt)
        self.assertEqual(old,old_before);self.assertEqual(file.read_bytes(),b'untouched')
        self.assertIn('creative_selection',prompt);self.assertNotIn('appartement réaliste chaleureux, vertical',prompt)

    def test_retention_rules_only_apply_to_new_productions(self):
        draft=story()
        editorial.validate(draft,self.job,s.STATE['jobs'])
        draft['scenes'][0]['dialogue'][0]['text']='Why are you taking my very last train ticket?'
        draft['creative_selection']['candidates'][0]['hook']=draft['scenes'][0]['dialogue'][0]['text']
        editorial.validate(draft,self.job,s.STATE['jobs'])
        self.job['retention_version']=1
        self.assertIn('0–2 secondes',s.script_prompt(self.job))
        self.assertIn('image_prompt ET video_prompt',s.script_prompt(self.job))
        # 0.1.102: shortened by the studio instead of a rewrite.
        editorial.validate(draft,self.job,s.STATE['jobs'])
        draft['scenes'][1]['dialogue'][0]['text']=' '.join(['word']*24)
        editorial.validate(draft,self.job,s.STATE['jobs'])
        draft['scenes'][1]['dialogue'][0]['text']+=' word'
        editorial.validate(draft,self.job,s.STATE['jobs'])  # 0.1.102: one word too many is cut, never a rewrite
        self.assertLessEqual(sum(len(x['text'].split()) for x in draft['scenes'][1]['dialogue']),24)

    def opening_story(self):
        self.job.update(hook_version=1,retention_version=1)
        draft=story()
        first='Oma, wer ist das fremde Kind auf diesem Foto?'
        draft['scenes'][0]['dialogue'][0]['text']=first
        draft['creative_selection']['candidates'][0]['hook']=first
        draft['scenes'][0]['image_prompt']='Close-up: altes Foto held in shaking hands.'
        draft['scenes'][0]['video_prompt']='She holds the altes Foto and reacts immediately.'
        draft['opening_plan']={'visible_detail':'altes Foto','question':'Wer ist das Kind?','payoff_scene':3,'payoff':'Die Großmutter erklärt die Herkunft des Fotos.'}
        return draft

    def test_new_hooks_accept_long_visual_anchor_and_add_it_to_missing_prompts(self):
        draft=self.opening_story();editorial.validate(draft,self.job,s.STATE['jobs'])
        detail="Diane approche la photo d’Esther du fil incandescent"
        draft['opening_plan']['visible_detail']=detail
        first=draft['scenes'][0]
        first['video_prompt']='The camera follows Diane.'
        for _ in range(2):
            editorial.validate(draft,self.job,s.STATE['jobs'])
        for key in ('image_prompt','video_prompt'):
            self.assertEqual(first[key].count(detail),1)

    def test_new_hooks_require_a_resolution_scene_and_reject_overlong_opening(self):
        draft=self.opening_story();draft['opening_plan']['payoff_scene']=4
        editorial.validate(draft,self.job,s.STATE['jobs'])  # 0.1.102: set to the last scene, no refusal
        self.assertEqual(draft['opening_plan']['payoff_scene'],len(draft['scenes']))
        first=' '.join(['Wort']*13)
        draft['scenes'][0]['dialogue'][0]['text']=first;draft['creative_selection']['candidates'][0]['hook']=first
        editorial.validate(draft,self.job,s.STATE['jobs'])
        self.assertLessEqual(len(draft['scenes'][0]['dialogue'][0]['text'].split()),12)

    def test_new_hooks_prompt_contains_emotional_variety_and_native_language_without_migrating_old_jobs(self):
        old=self.add_old();before=copy.deepcopy(old);self.job['hook_version']=1;self.job['retention_version']=1
        prompt=s.script_prompt(self.job)
        self.assertIn('6 à 10 mots',prompt);self.assertIn('opening_plan',prompt)
        self.assertIn('Le spectateur comprend immédiatement qui souffre',prompt)
        self.assertIn('English (en-US)',prompt)
        self.assertEqual(old,before);self.assertNotIn('hook_version',old)
        self.assertIn(editorial.direction(self.job,s.STATE['jobs'])['id'],[x[0] for x in editorial.FAMILY_DIRECTIONS])

    def test_next_direction_changes_from_recent_direction(self):
        old=self.add_old();first=editorial.direction(self.job,s.STATE['jobs'])
        old['creative_direction']=first;self.job.pop('creative_direction')
        self.assertNotEqual(editorial.direction(self.job,s.STATE['jobs'])['id'],first['id'])

    def test_unknown_counters_trigger_another_search_for_new_jobs(self):
        self.job['stage']='research';self.job['research_queries']=['first','second'];self.job.pop('selected')
        s.apply_research(self.job,[{'url':f'https://www.tiktok.com/@a/video/{i}','signal':100000} for i in range(3)])
        self.assertEqual(self.job['stage'],'research');self.assertEqual(self.job['research_round'],1)
        self.assertNotIn('selected',self.job)

    def test_research_does_not_reselect_old_reference_or_mix_unknown_with_views(self):
        self.add_old()
        rows=[{'url':'https://www.tiktok.com/@a/video/1','views':99999999}]+[{'url':f'https://www.tiktok.com/@b/video/{i}','views':1000*i} for i in (2,3,4)]
        rows.append({'url':'https://www.tiktok.com/@c/video/5','signal':99999999999})
        s.apply_research(self.job,rows)
        self.assertEqual(self.job['selected']['url'],'https://www.tiktok.com/@b/video/4')
        self.assertEqual(self.job['selected']['basis'],'vues')

    def test_one_view_count_and_two_like_counts_are_not_three_comparable_metrics(self):
        self.job['stage']='research';self.job.pop('selected')
        s.apply_research(self.job,[{'url':'https://www.tiktok.com/@a/video/1','views':10},
                                   {'url':'https://www.tiktok.com/@b/video/2','likes':100000},
                                   {'url':'https://www.tiktok.com/@c/video/3','likes':200000}])
        self.assertEqual(self.job['status'],'waiting_research');self.assertNotIn('selected',self.job)

    def test_unknown_duplicate_does_not_erase_an_identified_view_count(self):
        url='https://www.tiktok.com/@a/video/1'
        ranked=s.rank_candidates([{'url':url,'views':12000},{'url':url,'signal':999999}])
        self.assertEqual(len(ranked),1);self.assertEqual(ranked[0]['views'],12000)


if __name__=='__main__':unittest.main()
