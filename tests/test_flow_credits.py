import copy,unittest
import flow_credits as c

def state():
 return {'settings':{'flow_auto':True},'jobs':[{'stage':'clips','status':'waiting_credit'}],'tasks':[],'clients':{'client':{'role':'flow'}},'profiles':[{'id':'p','balance':0,'auto_enabled':True,'blocked':'credits','flow_client':'client','flow_email':'owner@example.com','flow_url':'https://flow.google.com/project/registered'}]}
class CreditTests(unittest.TestCase):
 def test_no_time_based_credit_reset(self):
  s=state();c.prepare(s,1000);c.prepare(s,1000+86400);self.assertEqual(s['profiles'][0]['balance'],0)
 def test_single_claim_and_identity(self):
  s=state();self.assertIsNone(c.claim(s,'other',1000));lease=c.claim(s,'client',1001);self.assertIsNotNone(lease);self.assertIn('background',lease);self.assertIsNone(c.claim(s,'client',1002))
  with self.assertRaises(ValueError):c.report(s,'other',{**lease,'result':{}},1003)
 def test_real_balance_unblocks_and_remembers_reset(self):
  s=state();lease=c.claim(s,'client',1000)
  c.report(s,'client',{**lease,'result':{'ok':True,'balance':50,'email':'owner@example.com','url':lease['target']['url'],'reset_at':90000}},1001)
  p=s['profiles'][0];self.assertEqual(p['balance'],50);self.assertNotIn('blocked',p);self.assertEqual(c.seconds(p['credit_next_check']),90000)
 def test_zero_read_waits_without_synthetic_refill(self):
  s=state();lease=c.claim(s,'client',1000);c.report(s,'client',{**lease,'result':{'ok':True,'balance':0,'email':'owner@example.com','url':lease['target']['url']}},1001)
  self.assertIsNone(c.prepare(s,2000));self.assertEqual(s['profiles'][0]['balance'],0);self.assertIsNotNone(c.prepare(s,4602))
 def test_wrong_account_or_changed_binding_never_updates(self):
  for changed in [False,True]:
   s=state();lease=c.claim(s,'client',1000)
   if changed:s['profiles'][0]['flow_email']='changed@example.com'
   with self.assertRaises(ValueError):c.report(s,'client',{**lease,'result':{'ok':True,'balance':50,'email':'wrong@example.com','url':lease['target']['url']}},1001)
   self.assertEqual(s['profiles'][0]['balance'],0)
 def test_error_retains_last_balance(self):
  s=state();lease=c.claim(s,'client',1000);c.report(s,'client',{**lease,'result':{'ok':False,'error':'Connexion requise'}},1001)
  self.assertEqual(s['profiles'][0]['balance'],0);self.assertEqual(s['profiles'][0]['credit_error'],'Connexion requise');self.assertIsNone(c.prepare(s,1100))
 def test_no_probe_during_generation_and_idle_depleted_probe(self):
  s=state();s['tasks']=[{'kind':'flow_video','status':'claimed'}];self.assertIsNone(c.prepare(s,1000));s['tasks']=[];s['jobs']=[];self.assertIsNotNone(c.prepare(s,1000));self.assertIsNotNone(c.claim(s,'client',1001))
 def test_positive_manual_balance_is_not_polled_without_need(self):
  s=state();s['jobs']=[];s['profiles'][0]['balance']=50;self.assertIsNone(c.prepare(s,1000))
 def test_observed_balance_is_rechecked_after_reset_while_idle(self):
  s=state();s['jobs']=[];p=s['profiles'][0];p.update(balance=20,credit_source='flow',credit_next_check=c.stamp(2000))
  self.assertIsNone(c.prepare(s,1900));self.assertIsNotNone(c.prepare(s,2001));self.assertEqual(p['balance'],20)
 def test_expired_deleted_and_disabled_checks_rejected(self):
  for mode in ['expired','deleted','disabled']:
   s=state();lease=c.claim(s,'client',1000)
   if mode=='deleted':s['profiles']=[]
   if mode=='disabled':s['profiles'][0]['auto_enabled']=False
   with self.assertRaises(ValueError):c.report(s,'client',{**lease,'result':{}},2000 if mode=='expired' else 1001)
if __name__=='__main__':unittest.main()
