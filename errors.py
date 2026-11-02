"""Typed task failures (P2-01/P2-02). Pure functions: no state, no network."""
import re

KINDS = ('login', 'challenge', 'quota', 'refusal', 'credits', 'interface', 'timeout', 'restart', 'other')
# Only these can be retried without a human (still bounded by the night queue).
RETRYABLE = ('interface', 'timeout', 'restart', 'other')
HUMAN = ('login', 'challenge')

# Fallback for results sent by older extensions or by the background worker, which only carry a message.
PATTERNS = (
    ('challenge', r'Contrôle du fournisseur|captcha|verify you are human|vérifiez que vous êtes humain|anti-robot'),
    ('login', r'Connexion requise|session expirée|not logged in|sign in to|log in to|connectez-vous|anmelden'),
    ('credits', r'Crédits Flow insuffisants'),
    ('quota', r'Quota du fournisseur|limit reached|usage limit|you.ve (?:reached|hit)|quota atteint|limite atteinte|Limit erreicht'),
    ('refusal', r'refus de contenu|refuse de dessiner|content polic|politique de contenu|Inhaltsrichtlinie'),
    ('restart', r'^Redémarrage'),
    ('timeout', r'délai dépassé|trop longue|timed? ?out'),
    ('interface', r'Interface non reconnue|Envoi bloqué|indisponible|non lisible|non détecté|Extension reloaded|context invalidated'),
)

HELP = {
    'login': 'Connexion requise : ouvrez l’onglet du fournisseur, connectez-vous vous-même, puis cliquez sur Reprendre.',
    'challenge': 'Vérification anti-robot affichée : résolvez-la vous-même dans l’onglet, puis cliquez sur Reprendre. FruchtDrama ne contourne jamais ces contrôles.',
}


def classify(result, kind_hint=None):
    """Return the failure type of a task result. An explicit, known type sent by the extension wins."""
    kind = result.get('error_kind') if isinstance(result, dict) else None
    if kind in KINDS:
        return kind
    if isinstance(result, dict) and result.get('flow_blocked') == 'credits':
        return 'credits'
    message = str(result.get('error', '') if isinstance(result, dict) else result)
    for name, pattern in PATTERNS:
        if re.search(pattern, message, re.I):
            return name
    return kind_hint if kind_hint in KINDS else 'other'


def retry_after(result, lower=60, upper=48 * 3600):
    """Provider-announced renewal delay in seconds, bounded; None when absent or invalid."""
    try:
        value = int(result.get('retry_after'))
    except (TypeError, ValueError, AttributeError):
        return None
    return min(max(value, lower), upper) if value > 0 else None


def message(kind, raw):
    """Event text: the provider message, prefixed by the human action when one is required."""
    raw = str(raw or 'Connecteur interrompu')[:1200]
    return HELP[kind] + ' Détail : ' + raw if kind in HELP else raw
