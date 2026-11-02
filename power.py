"""Keep Windows awake while the night queue runs (P2-12). No effect elsewhere.

SetThreadExecutionState is per thread: it must be called from the long-lived dispatch thread, never from
a short-lived HTTP handler thread (the state would vanish with that thread).
"""
import sys

ES_CONTINUOUS = 0x80000000
ES_SYSTEM_REQUIRED = 0x00000001
_applied = None


def kernel32():
    if sys.platform != 'win32':
        return None
    import ctypes
    return ctypes.windll.kernel32


def sync(active, k=None):
    """Apply the wanted state once; returns True when a change was applied."""
    global _applied
    active = bool(active)
    if _applied is active:
        return False
    k = k if k is not None else kernel32()
    if k is not None:
        k.SetThreadExecutionState(ES_CONTINUOUS | (ES_SYSTEM_REQUIRED if active else 0))
    _applied = active
    return True
