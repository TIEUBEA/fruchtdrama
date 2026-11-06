"""Daily Flow credit refill tracking (owner, 03/11/2026: each Google account gets its credits back every day).

When an account first spends credits, its refill time is noted (spend time + 24 h). When that time comes,
the studio asks the FruchtDrama window to read the real balances again; if the credits are not back yet,
it retries every hour. Pure functions on profiles; times are epoch seconds.
"""
PERIOD = 24 * 3600
RETRY = 3600
DAILY = 50


def spent(profile, at, period=PERIOD):
    """First spend since the last full balance starts the 24 h clock; later spends do not move it."""
    if not profile.get('refill_at'):
        profile['refill_at'] = at + period


def read(profile, balance, at, daily=DAILY, period=PERIOD):
    """Real balance read from Flow: full means nothing to wait for, below full keeps or starts the clock."""
    if balance >= daily:
        profile.pop('refill_at', None)
    elif not profile.get('refill_at'):
        # Spent outside the studio, time unknown: assume the worst case, a full day from now.
        profile['refill_at'] = at + period
    elif profile['refill_at'] <= at:
        # Due but not back yet: look again in an hour.
        profile['refill_at'] = at + RETRY


def due(profiles, at):
    return [p for p in profiles if p.get('refill_at') and p['refill_at'] <= at and p.get('slot') is not None]


def order(profiles):
    """Spend first the accounts whose clock already runs (soonest refill), keep full ones for later."""
    return sorted(profiles, key=lambda p: (0, p['refill_at']) if p.get('refill_at') else (1, 0))
