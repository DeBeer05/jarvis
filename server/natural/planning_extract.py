"""Dutch user-sourced planning facts, independent of model output and tool schemas."""
import re
from datetime import datetime,timedelta
from zoneinfo import ZoneInfo
from server.natural.temporal import resolve,normalize_dayparts,daypart,AmbiguousTime,NUMBER,number
from server.natural.planning_models import Fact,Cost

ACTIVITIES={'dierentuin':'dierentuin','pretpark':'pretpark','museum':'museum','bioscoop':'bioscoop','restaurant':'restaurant','diner':'restaurant','wandeling':'wandeling','wandelen':'wandeling','natuur':'wandeling','escape room':'escape room','bowlen':'bowlen','stad':'stedentrip','stedentrip':'stedentrip','date':'date','sport':'sport'}
TOPIC=re.compile(r'\b(?:uitjes?|activiteit\w*|dagtrip\w*|dagtocht\w*|uitstap\w*|date|dierentuin\w*|pretpark\w*|museum|bioscoop|wandeling|restaurant|bowlen|sport|weekend|iets (?:leuks|romantisch)|vriend verrassen)\b',re.I)
FOLLOW=re.compile(r"\s*(?:maak het|het regent|er komt regen|dat klinkt|die (?:lijkt|klinkt)|een .+ klinkt|doe toch|liever|niet te|het moet|maakt (?:me|mij)|verras|bedenk jij|een uur|een uurtje|iets later|haal|verwijder|voeg|zonder|tickets?|entree|parkeren|brandstof|vervoer|eten|drinken|kunnen we|laten we|ik wil eerst|we gaan|toch met|maximaal|budget|met |zaterdag|zondag|morgen|terug naar|ga terug|hoe staat|werk .+ uit)",re.I)
CANCEL=re.compile(r'\b(?:vergeet|annuleer|stop|laat)\b.*\b(?:uitje|planning|dagtrip|hele plan)\b|^\s*(?:laat maar|stop maar|annuleer maar|vergeet het maar)[.!\s]*$',re.I)
COMMIT=re.compile(r'\b(?:zet|zetten|plaats|voeg|inplannen)\b.*\b(?:agenda|kalender)\b|\b(?:agenda|kalender)\b.*\b(?:zet|zetten|toevoegen)\b',re.I)


def amount(text):
    text=text.casefold().strip().replace(',','.')
    try:return float(text)
    except ValueError:pass
    values={'vijfentwintig':25,'dertig':30,'veertig':40,'vijftig':50,'zestig':60,'zeventig':70,'tachtig':80,'negentig':90,'honderd':100,'duizend':1000}
    if text in values:return float(values[text])
    if text in ('een half','anderhalf'):return .5 if text=='een half' else 1.5
    try:return float(number(text))
    except (ValueError,KeyError):return None


MONEY=r'(?:\d+(?:[.,]\d{1,2})?|vijfentwintig|dertig|veertig|vijftig|zestig|zeventig|tachtig|negentig|honderd|duizend|'+NUMBER+r')'


def extract(state,message,settings,*,now=None,source_turn=''):
    text=normalize_dayparts(message)
    text=re.sub(r'\b(maandag|dinsdag|woensdag|donderdag|vrijdag|zaterdag|zondag)(ochtend|middag|avond)\b',r'\1 \2',text,flags=re.I)
    folded=text.casefold();facts=state.facts
    # Short cost/weather/correction turns remain part of the active draft.
    old_activity=facts.get('activity',Fact()).value
    def put(key,value,origin='user',evidence=message):
        if value is not None:facts[key]=Fact(value=value,origin=origin,evidence=evidence[:400],source_turn=source_turn)
    if CANCEL.search(text):
        state.status='cancelled';state.facts={};state.alternatives=[];state.costs=[];state.timeline=[];state.route=[];state.calendar={}
        return state
    if state.status=='cancelled':state.status='brainstorm'
    if re.match(r'\s*(?:maak het|het regent|er komt regen)',folded):state.mode='budget' if 'goedkoper' in folded else state.mode
    if 'goal' not in facts:put('goal',message[:300])
    selected=re.search(r'\b(?:de |het )?(eerste|tweede|derde|vierde)(?: optie| voorstel| activiteit)?\b',folded)
    if selected:
        index=('eerste','tweede','derde','vierde').index(selected[1])
        if index<len(state.alternatives):put('activity',state.alternatives[index].title)
    if re.search(r'\b(?:verras|verrassing)\w*\b',folded):state.mode='surprise'
    elif re.search(r'\b(?:ontspannen|rustig|relaxed)\b',folded):state.mode='relaxed'
    elif re.search(r'\b(?:gedetailleerd|precies tijdschema|volledig tijdschema)\b',folded):state.mode='detailed'
    elif re.search(r'\b(?:niet te duur|goedkoper|budgetmodus|betaalbaar)\b',folded):state.mode='budget';put('preference','betaalbaar')
    if re.search(r'\b(?:dichterbij|niet te ver)\b',folded):put('preference','dichterbij; voorkom onnodig reizen')
    for keyword,activity in ACTIVITIES.items():
        if not re.search(r'\b'+re.escape(keyword)+r'\b',folded):continue
        if re.search(r'\b(?:haal|zonder|geen|niet|niks|niets)\b',folded) and re.search(r'eruit|zonder|geen|lijkt.+(?:niks|niets)',folded):
            state.excluded=list(dict.fromkeys([*state.excluded,activity]))[-20:]
            if facts.get('activity',Fact()).value==activity:facts.pop('activity',None)
            if activity=='restaurant':facts.pop('meal',None)
            extra=facts.get('extra_activities',Fact()).value
            if isinstance(extra,list):put('extra_activities',[item for item in extra if item!=activity])
        elif activity=='restaurant' and re.search(r'\b(?:daarna|ook|nog|ergens|dineren|eten)\b',folded):put('meal','restaurant')
        elif old_activity and activity!=old_activity and re.search(r'\b(?:ook|daarna|vervolgens)\b',folded):
            extra=facts.get('extra_activities',Fact()).value
            put('extra_activities',list(dict.fromkeys([*(extra if isinstance(extra,list) else []),activity]))[:6])
        else:put('activity',activity)
    if re.search(r'\b(?:daarna|nog|ook).*(?:eten|lunchen|dineren)\b',folded):put('meal','eten')
    if facts.get('activity',Fact()).value!=old_activity:
        state.costs=[cost for cost in state.costs if cost.name not in ('entree','ticket','tickets','parkeren')]
    people=re.search(r'\bmet\s+(.+?)(?=\s+(?:naar|op|voor|om|rond|een|de |het |in |en daarna|maar|maximaal|zaterdag|zondag)|[,.;!?]|$)',text,re.I)
    if people:
        value=people[1].strip()
        if not re.match(r'(?:de trein|een trein|trein|auto|fiets|een budget|een klein budget|budget|maximaal)',value,re.I):
            put('participants',[name.strip() for name in re.split(r'\s+en\s+|,',value) if name.strip()][:10])
    addition=re.search(r'\bvoeg\s+(.+?)\s+(?:ook\s+)?toe(?:\s+als deelnemer)?[.!]?$',text,re.I)
    removal=re.search(r'\b(?:zonder|verwijder)\s+([\wÀ-ÿ-]+)(?:\s+als deelnemer)?[.!]?$',text,re.I)
    names=facts.get('participants',Fact()).value
    if addition:put('participants',list(dict.fromkeys([*(names if isinstance(names,list) else []),addition[1].strip()]))[:10])
    if removal and isinstance(names,list):put('participants',[name for name in names if name.casefold()!=removal[1].casefold()])
    pickup=re.search(r'\b(?:eerst\s+)?([A-ZÀ-Ý][\wÀ-ÿ-]*(?:\s+[A-ZÀ-Ý][\wÀ-ÿ-]*)?)\s+ophalen\b',text)
    if pickup:put('pickup',pickup[1])
    destination=re.search(r'\bnaar\s+(?:de |een |het )?(.+?)(?=\s+(?:daar|en daarna|met|voor|maximaal|om|rond|gaan)|[,.;!?]|$)',text,re.I)
    if destination and destination[1].casefold() not in ACTIVITIES:put('destination',destination[1].strip()[:120])
    origin=re.search(r'\b(?:vanaf|vanuit)\s+(.+?)(?=\s+(?:naar|met|om)|[,.;!?]|$)',text,re.I)
    if origin:put('origin',origin[1].strip()[:120])
    for transport,pattern in [('car',r'\b(?:auto|rijden)\b'),('train',r'\b(?:trein|openbaar vervoer|ov)\b'),('bike',r'\b(?:fiets|fietsen)\b'),('walk',r'\bte voet\b')]:
        if re.search(pattern,folded):
            if facts.get('transport',Fact()).value!=transport:
                facts.pop('travel_minutes',None);facts.pop('distance_km',None)
                state.costs=[c for c in state.costs if c.name not in ('brandstof','berekende brandstof','parkeren','vervoer')]
            put('transport',transport)
    budget=re.search(r'\b(?:maximaal|max\.?|budget(?: van)?)\s*€?\s*('+MONEY+r')\b',folded)
    if budget:
        value=amount(budget[1])
        if value is not None and 0<=value<=100000:put('budget',value);put('budget_scope','person' if 'per persoon' in re.split(r'[.;!?]',folded[budget.end():],maxsplit=1)[0] else 'total')
    if 'budget' not in facts and settings['default_budget']>0:put('budget',settings['default_budget'],'preference','instelling: voorlopig budget')
    for match in re.finditer(r'\b(entree|tickets?|parkeren|brandstof|vervoer|eten|drinken|overnachting)\s*(?:kost\w*|is|:)??\s*€?\s*('+MONEY+r')\s*(?:euro)?(?:\s*(per persoon|totaal|samen))?',folded):
        value=amount(match[2])
        if value is not None:
            name=match[1]
            people=facts.get('participants',Fact()).value
            per_person=match[3]=='per persoon'
            quantity=len(people)+1 if per_person and isinstance(people,list) and people else 1
            state.costs=[cost for cost in state.costs if cost.name!=name]+[Cost(name=name,amount=value,basis='person' if per_person else 'total',quantity=quantity,quantity_known=not per_person or bool(isinstance(people,list) and people))]
    if re.search(r'\b(?:uur|uurtje)\s+(?:later|eerder)\b',folded) or 'iets later' in folded:
        old_clock=facts.get('clock',Fact()).value
        if isinstance(old_clock,str):
            h,m=map(int,old_clock.split(':'));minutes=h*60+m+(-60 if 'eerder' in folded else 60)
            if 0<=minutes<1440:put('clock',f'{minutes//60:02}:{minutes%60:02}','proposal' if 'iets later' in folded else 'user')
        # A single correction may change both the day and relative clock.
        day_text=re.sub(r'\b(?:een uur|een uurtje|iets)\s+(?:later|eerder)\b','',text,flags=re.I)
        try:changed_day=resolve(day_text,now=now,timezone=settings.get('timezone','Europe/Amsterdam'))
        except AmbiguousTime:changed_day=None
        if changed_day and changed_day.date:
            put('date',changed_day.date);facts.pop('date_end',None);state.calendar={}
    else:
        clock_text=re.sub(r'\b(?:rond|ongeveer|ergens rond)\s+(?='+NUMBER+r'\b)','om ',text,flags=re.I)
        try:hint=resolve(clock_text,now=now,timezone=settings.get('timezone','Europe/Amsterdam'))
        except AmbiguousTime:hint=None
        if hint:
            if hint.date:
                if facts.get('date',Fact()).value!=hint.date:facts.pop('date_end',None);state.calendar={}
                put('date',hint.date)
            if hint.clock:put('clock',hint.clock)
            if hint.duration_minutes:put('duration_minutes',hint.duration_minutes)
        if re.search(r'\b(?:dit |komend |het )?weekend\b',folded):
            zone=ZoneInfo(settings.get('timezone','Europe/Amsterdam'));today=(now or datetime.now(zone)).date()
            saturday=today+timedelta(days=(5-today.weekday())%7)
            put('date',saturday.isoformat(),'proposal','voorlopige dag binnen gevraagd weekend');put('date_end',(saturday+timedelta(days=2)).isoformat())
        part=daypart(text)
        if part:
            put('daypart',part)
            if not (hint and hint.clock):put('clock',{'ochtend':'10:00','middag':'13:00','avond':'18:00','nacht':'00:00'}[part],'proposal','voorlopig dagdeelvoorstel')
    if re.search(r'\b(?:rond|ongeveer|ergens|flexibel)\b',folded):put('flexible',True)
    consumption=re.search(r'\b(?:verbruik\w*\s*)?('+MONEY+r')\s+liter\s+per\s+100\s*(?:km|kilometer)\b',folded)
    price=re.search(r'\b('+MONEY+r')\s*euro\s+per\s+liter\b',folded)
    if consumption:put('fuel_consumption',amount(consumption[1]))
    if price:put('fuel_price',amount(price[1]))
    for key,pattern in [('distance_km',r'\b('+MONEY+r')\s*(?:km|kilometer)\b'),('travel_minutes',r'\b('+MONEY+r')\s+minuten?\s+(?:reizen|rijden|reistijd)\b')]:
        distance_match=next((match for match in re.finditer(pattern,folded) if not folded[:match.start()].rstrip().endswith('per')),None)
        if distance_match:
            value=amount(distance_match[1])
            if value is not None:put(key,value)
    if settings['consider_weather'] and re.search(r'\b(?:regent|regenachtig)\b',folded):put('environment','inside','proposal','binnenalternatief bij door gebruiker gemelde regen')
    if re.search(r'\b(?:binnen|indoor)\b',folded):put('environment','inside')
    if re.search(r'\b(?:maakt (?:me|mij) niet uit|bedenk jij)\b',folded):state.mode='automatic'
    if re.search(r'\b(?:buiten|outdoor)\b',folded):put('environment','outside')
    for key,default in [('transport',settings['transport']),('maximum_distance_km',settings['maximum_distance_km']),('maximum_travel_minutes',settings['maximum_travel_minutes'])]:
        if key not in facts:put(key,default,'preference','instelling')
    if facts.get('activity',Fact()).value!=old_activity:
        if facts.get('duration_minutes',Fact()).origin=='proposal':facts.pop('duration_minutes',None)
    if 'duration_minutes' not in facts and facts.get('activity'):
        activity=facts['activity'].value
        put('duration_minutes',{'dierentuin':240,'museum':120,'restaurant':90}.get(str(activity),settings['duration_minutes']),'proposal','activiteitvoorstel; openingstijden niet gecontroleerd')
    if facts.get('activity'):state.status='draft'
    if 'date' in facts and 'clock' not in facts:put('clock','13:00','proposal','voorlopig middagvoorstel; nog afstemmen')
    names=facts.get('participants',Fact()).value
    for cost in state.costs:
        if cost.basis=='person':cost.quantity=len(names)+1 if isinstance(names,list) else 1;cost.quantity_known=isinstance(names,list)
    return state
