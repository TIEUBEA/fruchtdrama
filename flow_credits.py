"""Visible Flow balance checks; never synthesize renewed credits."""
import datetime as dt
import secrets
import flow_accounts

UTC=dt.timezone.utc
def stamp(time):return dt.datetime.fromtimestamp(time,UTC).isoformat()
def seconds(value):
    try:return dt.datetime.fromisoformat(value).timestamp()
    except (ValueError,TypeError):return 0

def route(profile):
    copy=dict(profile)
    if copy.get('blocked')=='credits':copy.pop('blocked')
    return flow_accounts.route(copy)

def busy(state):
    return any(t.get('kind') in ('flow_video','flow_collect') and t.get('status') in ('claimed','queued') for t in state['tasks'])

def prepare(state,time):
    if not state.get('settings',{}).get('flow_auto'):return None
    if busy(state):return None
    for p in state['profiles']:
        check=p.get('credit_probe')
        if check and check['status'] in ('queued','claimed'):
            if seconds(check['expires'])>time:return p
            check['status']='expired';p['credit_next_check']=stamp(time+900)
    needs_funds=any(j.get('stage')=='clips' and j.get('status')=='waiting_credit' for j in state['jobs'])
    for p in state['profiles']:
        target=route(p)
        if not target or state['clients'].get(target['client'],{}).get('role') not in ('all','flow'):continue
        if seconds(p.get('credit_next_check'))>time:continue
        # Bootstrap depleted accounts even without an active production. Once
        # observed, follow the provider reset time. Never open all accounts at once.
        if not needs_funds and p.get('balance',0)>0 and p.get('credit_source')!='flow':continue
        p['credit_probe']={'id':secrets.token_hex(8),'status':'queued','client':target['client'],'target':target,'created':stamp(time),'expires':stamp(time+180)}
        return p
    return None

def claim(state,client,time):
    profile=prepare(state,time)
    if not profile:return None
    probe=profile['credit_probe']
    if probe['client']!=client or probe['status']!='queued':return None
    probe['status']='claimed';probe['expires']=stamp(time+180)
    return {'id':probe['id'],'profile':profile['id'],'target':probe['target']}

def report(state,client,body,time):
    p=next((p for p in state['profiles'] if p['id']==body.get('profile')),None)
    probe=p.get('credit_probe') if p else None
    if not probe or probe['id']!=body.get('id') or probe['status']!='claimed' or probe['client']!=client or seconds(probe['expires'])<time:raise ValueError('Vérification de crédits expirée ou non associée')
    target=route(p)
    if not target or target!=probe['target'] or busy(state):raise ValueError('Compte ou production modifié pendant la vérification')
    result=body.get('result',{})
    if result.get('ok'):
        value=result.get('balance')
        if type(value) is not int or not 0<=value<=100000:raise ValueError('Solde Flow invalide')
        if result.get('email','').lower()!=target['email'].lower() or flow_accounts.project_url(result.get('url'))!=target['url']:raise ValueError('Identité du solde Flow non confirmée')
        p.update(balance=value,checked=stamp(time),credit_source='flow',credit_error='')
        if p.get('blocked')=='credits':p.pop('blocked')
        reset=result.get('reset_at')
        reset=reset if type(reset) in (int,float) and time+60<=reset<=time+26*3600 else time+3600
        p['credit_next_check']=stamp(reset)
        p['credit_reset_label']=str(result.get('reset_label',''))[:160]
        if value==0:p.setdefault('exhausted_at',stamp(time))
        else:p.pop('exhausted_at',None)
    else:
        p['credit_error']=str(result.get('error','Solde non lisible ; ancienne valeur conservée.'))[:300]
        p['credit_next_check']=stamp(time+900)
    probe['status']='done' if result.get('ok') else 'failed'
    return p

def request(state,profile,time):
    if busy(state):raise ValueError('Attendez la fin de la tâche Flow en cours')
    if any(p.get('credit_probe',{}).get('status') in ('queued','claimed') and seconds(p['credit_probe']['expires'])>time for p in state['profiles']):raise ValueError('Une vérification de solde est déjà en cours')
    p=next((p for p in state['profiles'] if p['id']==profile),None)
    target=route(p) if p else None
    if not target:raise ValueError('Compte Flow non enregistré ou non autorisé')
    p['credit_probe']={'id':secrets.token_hex(8),'status':'queued','client':target['client'],'target':target,'created':stamp(time),'expires':stamp(time+180)}
    return p
