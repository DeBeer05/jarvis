"""Style presets; backend permissions and action truth remain authoritative."""
PROFILES={
    "classic":("Klassieke JARVIS",{"formality":70,"humor":35,"sarcasm":20,"friendliness":60,"brevity":65}),
    "professional":("Professioneel",{"formality":85,"humor":10,"sarcasm":0,"friendliness":60,"brevity":70}),
    "friendly":("Vriendelijk",{"formality":35,"humor":35,"sarcasm":5,"friendliness":85,"brevity":65}),
    "informal":("Informeel",{"formality":10,"humor":45,"sarcasm":10,"friendliness":80,"brevity":65}),
    "humorous":("Humoristisch",{"formality":20,"humor":80,"sarcasm":20,"friendliness":80,"brevity":60}),
    "concise":("Kort en zakelijk",{"formality":55,"humor":5,"sarcasm":0,"friendliness":50,"brevity":100}),
    "informative":("Uitgebreid en informatief",{"formality":50,"humor":15,"sarcasm":0,"friendliness":65,"brevity":10}),
    "custom":("Aangepast profiel",{}),
}


def describe(settings):
    profile=settings["profile"];name=PROFILES[profile][0]
    return {"profile":name,**{k:v for k,v in settings.items() if k!="profile"}}
