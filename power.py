"""Keep the computer awake while the night queue runs (P2-12): Windows API, macOS « caffeinate » (11/11/2026).

SetThreadExecutionState is per thread: it must be called from the long-lived dispatch thread, never from
a short-lived HTTP handler thread (the state would vanish with that thread).
"""
import os
import subprocess
import sys

ES_CONTINUOUS = 0x80000000
ES_SYSTEM_REQUIRED = 0x00000001
_applied = None
_caffeinate = None


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
    elif sys.platform == 'darwin':
        mac_awake(active)
    _applied = active
    return True


def mac_awake(active, popen=subprocess.Popen):
    """macOS: « caffeinate -i -w <studio pid> » prevents idle sleep and ends by itself with the studio."""
    global _caffeinate
    if active and (_caffeinate is None or _caffeinate.poll() is not None):
        try:
            _caffeinate = popen(['caffeinate', '-i', '-w', str(os.getpid())], stdin=subprocess.DEVNULL,
                                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except OSError:
            _caffeinate = None
    elif not active and _caffeinate is not None:
        try:
            _caffeinate.terminate()
        except OSError:
            pass
        _caffeinate = None
