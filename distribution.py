"""First-use terms acceptance for the shared local edition. No network calls."""
import datetime
import hashlib
import json
import pathlib

ROOT = pathlib.Path(__file__).resolve().parent


def accept_terms():
    terms = ROOT / 'CONDITIONS-UTILISATION.txt'
    digest = hashlib.sha256(terms.read_bytes()).hexdigest()
    receipt = ROOT / 'data' / 'conditions-acceptees.json'
    try:
        if json.loads(receipt.read_text('utf-8')).get('sha256') == digest:
            return
    except (OSError, ValueError, AttributeError):
        pass
    print(terms.read_text('utf-8'))
    if input('\nTapez ACCEPTER pour continuer, ou Entree pour quitter : ').strip() != 'ACCEPTER':
        raise SystemExit('Installation annulee. Aucune acceptation enregistree.')
    receipt.parent.mkdir(exist_ok=True)
    receipt.write_text(json.dumps({'sha256': digest, 'accepted_at': datetime.datetime.now(datetime.timezone.utc).isoformat()}, indent=2), 'utf-8')
