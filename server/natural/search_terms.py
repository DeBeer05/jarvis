"""Small opt-in Dutch vocabulary expansion; no embeddings or extra inference."""
GROUPS=(
    ("agenda","afspraak","afspraken","planning","kalender"),
    ("programmeren","programmeertaal","coderen","python","kotlin","rust","javascript","typescript"),
    ("fietsen","fiets","wielrennen","rijwiel"),
    ("wandelen","wandeling","hiken"),
    ("voorkeur","voorkeuren","liever","liefst"),
)


def expand(words):
    result=set(words)
    for group in GROUPS:
        if result.intersection(group):result.update(group)
    return sorted(result)[:24]
