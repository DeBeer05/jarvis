"""Meaning-preserving Dutch pronunciation and markup removal, without inference."""
import html
import re
from datetime import datetime,date as calendar_date
from zoneinfo import ZoneInfo

ONES=['nul','een','twee','drie','vier','vijf','zes','zeven','acht','negen','tien','elf','twaalf','dertien','veertien','vijftien','zestien','zeventien','achttien','negentien']
TENS={20:'twintig',30:'dertig',40:'veertig',50:'vijftig',60:'zestig',70:'zeventig',80:'tachtig',90:'negentig'}
MONTHS=['januari','februari','maart','april','mei','juni','juli','augustus','september','oktober','november','december']


def number(n):
    if n<0:return 'min '+number(-n)
    if n<20:return ONES[n]
    if n<100:return TENS[n] if n%10==0 else ONES[n%10]+('ën' if n%10 in (2,3) else 'en')+TENS[n//10*10]
    if n<1000:return ('' if n//100==1 else number(n//100))+'honderd'+(' '+number(n%100) if n%100 else '')
    for divisor,label in ((1_000_000_000,'miljard'),(1_000_000,'miljoen'),(1000,'duizend')):
        if n>=divisor:return ('' if n//divisor==1 and divisor==1000 else number(n//divisor)+' ')+label+(' '+number(n%divisor) if n%divisor else '')
    return str(n)


def spoken_time(match):
    hour,minute=int(match[1]),int(match[2])
    if hour>23 or minute>59:return match[0]
    period="'s nachts" if hour<6 else "'s ochtends" if hour<12 else "'s middags" if hour<18 else "'s avonds"
    h=hour%12 or 12
    if minute==30:value='half '+number((hour+1)%12 or 12)
    elif minute==15:value='kwart over '+number(h)
    elif minute==45:value='kwart voor '+number((hour+1)%12 or 12)
    else:value=number(h)+' uur'+(' '+number(minute) if minute else '')
    return value+' '+period


def format_speech(text,timezone="Europe/Amsterdam"):
    text=html.unescape(text)
    text=re.sub(r'<(?:script|style)\b[^>]*>[\s\S]*?</(?:script|style)>','',text,flags=re.I)
    text=re.sub(r'</?(?:p|div|span|br|html|body|head|title|b|strong|i|em|a|table|tr|td|ul|ol|li|h[1-6])(?:\s[^>]*)?/?>','',text)
    text=re.sub(r'```[\s\S]*?```',' De code staat op het scherm. ',text)
    text=re.sub(r'```[\s\S]*',' De code staat op het scherm. ',text)
    text=re.sub(r'\[([^\]]+)\]\(https?://[^)]+\)',r'\1',text)
    text=re.sub(r'https?://\S+','de link op het scherm',text)
    if re.match(r'^\s*[\[{]\s*(?:["{\[\d-]|true\b|false\b|null\b|[\]}])',text):return 'De technische gegevens staan op het scherm.'
    text=re.sub(r'(?m)^\s*(?:[-*#>]+|\d+[.)])\s*','',text)
    text=re.sub(r'[`*_#|]','',text)
    text=re.sub(r'(?m)^Voorstel-ID:\s*[0-9a-fA-F-]{36}\s*$','',text)
    text=re.sub(r'\b[0-9a-fA-F]{8}(?:-[0-9a-fA-F]{4}){3}-[0-9a-fA-F]{12}\b','',text)
    def timestamp(match):
        try:
            value=datetime.fromisoformat(match[0].replace('Z','+00:00'))
            if value.tzinfo:value=value.astimezone(ZoneInfo(timezone))
            return f"{value.day:02d}-{value.month:02d}-{value.year:04d} om {value.hour:02d}:{value.minute:02d}"
        except ValueError:return match[0]
    text=re.sub(r'\b[12]\d{3}-\d{2}-\d{2}T\d{2}:\d{2}(?::\d{2}(?:\.\d{1,6})?)?(?:Z|[+-]\d{2}:\d{2})?',timestamp,text)
    def dutch_date(match):
        day,month,year=map(int,match.groups())
        try:calendar_date(year,month,day)
        except ValueError:return match[0]
        return number(day)+' '+MONTHS[month-1]+' '+number(year)
    text=re.sub(r'\b(\d{1,2})-(\d{1,2})-([12]\d{3})\b',dutch_date,text)
    def short_date(match):
        day,month=map(int,match.groups())
        if not 1<=month<=12 or not 1<=day<=31:return match[0]
        return number(day)+' '+MONTHS[month-1]
    text=re.sub(r'\b(\d{2})-(\d{2})(?=\s+\d{1,2}:\d{2}\b)',short_date,text)
    def date(match):
        year,month,day=map(int,match.groups())
        return number(day)+' '+MONTHS[month-1]+' '+number(year) if 1<=month<=12 and 1<=day<=31 else match[0]
    text=re.sub(r'\b(20\d{2})-(\d{2})-(\d{2})\b',date,text)
    text=re.sub(r'\b(\d{1,2}):(\d{2})(?::00)?\b',spoken_time,text)
    def money(match):
        euros=int(match[1].replace('.',''));cents=int(match[2] or 0)
        return number(euros)+' euro'+(' en '+number(cents)+' cent' if cents else '')
    text=re.sub(r'€\s*(-?\d+(?:\.\d{3})*)(?:,(\d{2}))?',money,text)
    text=re.sub(r'\b(\d+(?:,\d+)?)\s*%',lambda m:m[1]+' procent',text)
    units={'GB':'gigabyte','MB':'megabyte','TB':'terabyte','GHz':'gigahertz','MHz':'megahertz','km':'kilometer','kg':'kilogram','ms':'milliseconden','cm':'centimeter','mm':'millimeter'}
    text=re.sub(r'\b(\d+(?:,\d+)?)\s*('+ '|'.join(units)+r')\b',lambda m:m[1]+' '+units[m[2]],text)
    text=re.sub(r'(?<![\w@])(?:06(?:[ -]?\d){8}|\+31(?:[ -]?\d){9})(?!\d)',lambda m:('plus ' if m[0].startswith('+') else '')+' '.join(ONES[int(c)] for c in m[0] if c.isdigit()),text)
    text=re.sub(r'(?<![\w@.])(-?\d{1,9})(,\d+)?(?![\w@.])',lambda m:number(int(m[1]))+(' komma '+' '.join(ONES[int(c)] for c in m[2][1:]) if m[2] else ''),text)
    for key,value in {'CPU' :'cee pee uu','GPU':'gee pee uu','RAM':'ram','SSD':'es es dee','API':'aa pee ie','AI':'aa ie'}.items():text=re.sub(r'\b'+key+r'\b',value,text)
    return re.sub(r'\s+',' ',text).strip()
