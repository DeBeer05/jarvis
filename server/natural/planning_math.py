"""Decimal costs and verified calendar intervals; no invented routes or prices."""
from datetime import datetime,timedelta,date,UTC
from decimal import Decimal,ROUND_HALF_UP
from zoneinfo import ZoneInfo
from server.natural.temporal import local_time,AmbiguousTime
from server.natural.planning_models import Fact,Cost


def money(value):return float(Decimal(str(value)).quantize(Decimal('.01'),rounding=ROUND_HALF_UP))


def fuel_cost(distance_km,litres_per_100km,price_per_litre):
    if any(value<0 for value in (distance_km,litres_per_100km,price_per_litre)):raise ValueError('Negatieve routewaarde')
    return money(Decimal(str(distance_km))*Decimal(str(litres_per_100km))*Decimal(str(price_per_litre))/100)


def cost_summary(state):
    subtotal=sum((Decimal(str(c.amount))*c.quantity for c in state.costs if c.quantity_known),Decimal(0))
    budget=state.facts.get('budget',Fact()).value
    per_person=state.facts.get('budget_scope',Fact()).value=='person'
    names=state.facts.get('participants',Fact()).value
    quantity=len(names)+1 if isinstance(names,list) else None
    comparable=subtotal/quantity if per_person and quantity else subtotal if not per_person else None
    return {'known_subtotal':money(subtotal),'total':None,'complete':False,
            'known_per_person':money(subtotal/quantity) if quantity else None,
            'budget':budget,'budget_scope':'person' if per_person else 'total',
            'over_budget':bool(isinstance(budget,(int,float)) and comparable is not None and comparable>Decimal(str(budget))),
            'unknown':['entree, vervoer, parkeren en eten voor zover niet expliciet opgegeven'],
            'items':[c.model_dump() for c in state.costs]}


def free_blocks(items,start,end,*,incomplete=False,buffer_minutes=15):
    if incomplete:return {'status':'incomplete','blocks':[],'checked_start':start.isoformat(),'checked_end':end.isoformat()}
    busy=[]
    try:
        for item in items:
            if item.get('status')=='cancelled' or item.get('transparency')=='transparent':continue
            def parse(value):
                if 'dateTime' in value:
                    parsed=datetime.fromisoformat(value['dateTime'].replace('Z','+00:00'))
                    if parsed.utcoffset() is None:raise ValueError('Tijdzone ontbreekt')
                    return parsed.astimezone(start.tzinfo)
                if 'date' in value:return local_time(date.fromisoformat(value['date']),0,0,start.tzinfo)
                raise ValueError('Ontbrekend tijdstip')
            begin,finish=parse(item['start']),parse(item['end'])
            if begin.tzinfo is None or finish<=begin:raise ValueError('Ongeldige afspraak')
            margin=timedelta(minutes=buffer_minutes)
            busy.append((max(start,begin-margin),min(end,finish+margin)))
    except (ValueError,KeyError,TypeError,AmbiguousTime):return {'status':'incomplete','blocks':[]}
    cursor=start;free=[]
    for begin,finish in sorted(busy):
        if finish<=start or begin>=end:continue
        if begin>cursor:free.append({'start':cursor.isoformat(),'end':begin.isoformat()})
        cursor=max(cursor,finish)
    if cursor<end:free.append({'start':cursor.isoformat(),'end':end.isoformat()})
    return {'status':'verified','blocks':free,'checked_start':start.isoformat(),'checked_end':end.isoformat(),'participants':'Alleen de agenda van de eigenaar is gecontroleerd.'}


def suggest_free_time(state,config):
    if state.calendar.get('status')!='verified':return
    facts=state.facts;clock=facts.get('clock',Fact())
    if clock.origin=='user' and not facts.get('flexible',Fact()).value:return
    if 'date' not in facts:return
    zone=ZoneInfo(config['timezone']);day=date.fromisoformat(str(facts['date'].value))
    last=date.fromisoformat(str(facts['date_end'].value)) if 'date_end' in facts else day+timedelta(days=1)
    duration=timedelta(minutes=int(facts.get('duration_minutes',Fact(value=config['duration_minutes'])).value))
    preferred=str(clock.value or '13:00');h,m=map(int,preferred.split(':'))
    for index in range(min(7,max(1,(last-day).days))):
        chosen=day+timedelta(days=index);minimum=local_time(chosen,9,0,zone);maximum=local_time(chosen,22,0,zone)
        wanted=local_time(chosen,h,m,zone)
        for block in state.calendar.get('blocks',[]):
            begin=max(datetime.fromisoformat(block['start']),minimum)
            end=min(datetime.fromisoformat(block['end']),maximum)
            start=max(begin,wanted)
            if start+duration>end:start=begin
            if start+duration<=end:
                facts['date']=Fact(value=start.date().isoformat(),origin=facts['date'].origin if start.date()==day else 'proposal',evidence='binnen gecontroleerd eigen agendablok; andere deelnemers onbekend')
                facts['clock']=Fact(value=start.strftime('%H:%M'),origin='proposal',evidence='voorstel binnen eigen agenda; openingstijden nog onbekend')
                return


def rebuild(state,config):
    facts=state.facts
    value=lambda key:facts.get(key,Fact()).value
    state.warnings=['Prijzen, openingstijden, weer, route en reserveringsbeschikbaarheid zijn niet live gecontroleerd.']
    if state.calendar.get('status')!='verified' and config['consider_calendar']:state.warnings.append('Beschikbaarheid in uw agenda is niet bevestigd.')
    if value('participants'):state.warnings.append('Beschikbaarheid van andere deelnemers is onbekend.')
    if state.excluded:state.alternatives=[o for o in state.alternatives if not any(word in o.title.casefold() for word in state.excluded)]
    environment=value('environment') or config['environment']
    if environment!='any':state.alternatives=[o for o in state.alternatives if o.environment in ('any',environment)]
    state.route=[str(value('origin') or 'Vertrekpunt nog onbekend')]
    if value('pickup'):state.route.append(str(value('pickup'))+' ophalen')
    if value('activity') or value('destination'):state.route.append(str(value('destination') or value('activity')))
    if isinstance(value('extra_activities'),list):state.route.extend(value('extra_activities'))
    if value('meal'):state.route.append('Eten: locatie nog kiezen')
    state.route.append('Terug naar vertrekpunt')
    if config['include_travel'] and value('activity') and not value('travel_minutes'):state.warnings.append('Reistijd ontbreekt; vertrek en terugkomst kunnen nog niet betrouwbaar worden berekend.')
    if isinstance(value('travel_minutes'),(int,float)) and value('travel_minutes')>config['maximum_travel_minutes']:state.warnings.append('De opgegeven reistijd overschrijdt uw voorkeur.')
    if isinstance(value('distance_km'),(int,float)) and value('distance_km')>config['maximum_distance_km']:state.warnings.append('De opgegeven reisafstand overschrijdt uw voorkeur.')
    if value('transport')=='car' and all(isinstance(value(key),(int,float)) and value(key)>=0 for key in ('distance_km','fuel_consumption','fuel_price')):
        state.costs=[cost for cost in state.costs if cost.name!='berekende brandstof']
        state.costs.append(Cost(name='berekende brandstof',amount=fuel_cost(value('distance_km'),value('fuel_consumption'),value('fuel_price')),origin='estimate'))
    state.timeline=[]
    if value('date') and value('clock'):
        try:
            zone=ZoneInfo(config.get('timezone','Europe/Amsterdam'));h,m=map(int,str(value('clock')).split(':'))
            start=local_time(date.fromisoformat(str(value('date'))),h,m,zone)
            duration=int(value('duration_minutes') or config['duration_minutes'])
            end=(start.astimezone(UTC)+timedelta(minutes=duration)).astimezone(zone)
            if config['include_travel'] and isinstance(value('travel_minutes'),(int,float)):
                departure=(start.astimezone(UTC)-timedelta(minutes=float(value('travel_minutes')))).astimezone(zone)
                state.timeline.append({'activity':'Reis naar activiteit','start':departure.isoformat(),'end':start.isoformat(),'origin':'proposal'})
            state.timeline.append({'activity':str(value('activity') or 'Activiteit nog kiezen'),'start':start.isoformat(),'end':end.isoformat(),'origin':'proposal'})
            for activity in value('extra_activities') or []:
                following=end+timedelta(minutes=30 if state.mode=='relaxed' else 20)
                end=following+timedelta(minutes=90)
                state.timeline.append({'activity':activity+'; duur en verplaatsing nog afstemmen','start':following.isoformat(),'end':end.isoformat(),'origin':'proposal'})
            if value('meal'):
                meal=(end.astimezone(UTC)+timedelta(minutes=30 if state.mode=='relaxed' else 20)).astimezone(zone)
                state.timeline.append({'activity':'Samen eten, locatie en reistijd nog afstemmen','start':meal.isoformat(),'end':(meal+timedelta(minutes=90)).isoformat(),'origin':'proposal'})
                end=meal+timedelta(minutes=90)
            if config['include_travel'] and isinstance(value('travel_minutes'),(int,float)):
                state.timeline.append({'activity':'Terugreis (voorlopig dezelfde opgegeven reistijd)','start':end.isoformat(),'end':(end+timedelta(minutes=float(value('travel_minutes')))).isoformat(),'origin':'assumption'})
            if value('pickup'):state.warnings.append('Voor het ophalen ontbreken nog een tijdsduur en gecontroleerde route.')
            if state.calendar.get('status')=='verified':
                begin=datetime.fromisoformat(state.timeline[0]['start']);finish=datetime.fromisoformat(state.timeline[-1]['end'])
                covered=any(datetime.fromisoformat(block['start'])<=begin and datetime.fromisoformat(block['end'])>=finish for block in state.calendar['blocks'])
                if not covered:state.warnings.append('Dit voorgestelde tijdstip past niet volledig in het gecontroleerde vrije agendablok.')
        except (ValueError,TypeError,AmbiguousTime):state.warnings.append('De voorgestelde tijd moet nog worden verduidelijkt.')
    summary=cost_summary(state)
    if config['calculate_costs'] and summary['over_budget']:state.warnings.append('De bekende kosten overschrijden het opgegeven totale maximumbudget.')
    state.pending=['Openingstijden, volledige kosten, route en eventuele reserveringen controleren.']
    if not value('date'):state.pending.append('Dag nog kiezen; brainstormen kan gewoon doorgaan.')
    if not value('activity'):state.pending.append('Activiteit nog kiezen; geen verplichte vervolgvraag.')
    if state.model_status in ('invalid','unavailable'):state.warnings.append('Het model kon nog geen veilig bruikbaar vervolgvoorstel leveren.')
    return state
