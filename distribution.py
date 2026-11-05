"""First-use terms acceptance for the shared local edition. No network calls."""
import datetime
import hashlib
import json
import pathlib

ROOT = pathlib.Path(__file__).resolve().parent


def terms_accepted():
    """True when this copy's current terms were accepted (non-interactive check, used by the native host)."""
    digest = hashlib.sha256((ROOT / 'CONDITIONS-UTILISATION.txt').read_bytes()).hexdigest()
    try:
        return json.loads((ROOT / 'data' / 'conditions-acceptees.json').read_text('utf-8')).get('sha256') == digest
    except (OSError, ValueError, AttributeError):
        return False


def accept_terms():
    terms = ROOT / 'CONDITIONS-UTILISATION.txt'
    digest = hashlib.sha256(terms.read_bytes()).hexdigest()
    receipt = ROOT / 'data' / 'conditions-acceptees.json'
    if terms_accepted():
        return
    print(terms.read_text('utf-8'))
    if input('\nTapez ACCEPTER pour continuer, ou Entree pour quitter : ').strip() != 'ACCEPTER':
        raise SystemExit('Installation annulee. Aucune acceptation enregistree.')
    receipt.parent.mkdir(exist_ok=True)
    receipt.write_text(json.dumps({'sha256': digest, 'accepted_at': datetime.datetime.now(datetime.timezone.utc).isoformat()}, indent=2), 'utf-8')
