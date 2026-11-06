"""Test helper (0.1.91): since « Préparer mes comptes », nothing starts before ChatGPT and a clip engine have a ready
account. Tests written before that rule start from a studio whose services were just checked ready; tests of the
rule itself (test_readiness.py) use the plain fresh state."""
import datetime as dt


def ready_state(state):
    at = dt.datetime.now(dt.timezone.utc).isoformat()
    state['readiness'] = {'sites': {name: {'state': 'ready', 'reason': '', 'at': at} for name in ('chatgpt', 'claude', 'grok', 'arena')}, 'pending': []}
    return state


def install(server):
    """server.fresh() now returns a studio with every service ready."""
    plain = server.fresh
    server.fresh = lambda: ready_state(plain())
    return server
