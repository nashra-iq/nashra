# Builds tenders.json from public Iraqi government sites (RSS / WordPress API / HTML).
import json, re, urllib.request, html, datetime as dt, email.utils, sys, os
UA={"User-Agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0 Safari/537.36","Accept-Language":"ar"}
KW=re.compile("مناقص|مزايد|إحال|احال|إعلان|اعلان|عطاء|تعاقد|متعاقد|عقود|العروض")
def get(u,t=40): return urllib.request.urlopen(urllib.request.Request(u,headers=UA),timeout=t).read().decode("utf-8","replace")
def clean(s): return re.sub(r"\s+"," ",html.unescape(re.sub(r"<[^>]+>"," ",s))).strip()
def rss(u,src):
    x=get(u); out=[]
    for it in re.findall(r"<item>(.*?)</item>",x,re.S):
        g=lambda t:(re.search(r"<%s[^>]*>(.*?)</%s>"%(t,t),it,re.S) or [None,""])[1]
        g2=lambda t:clean(re.sub(r"<!\[CDATA\[|\]\]>","",g(t)))
        d=g2("pubDate")
        try: d=email.utils.parsedate_to_datetime(d).date().isoformat()
        except Exception: d=""
        out.append({"t":g2("title"),"s":src,"d":d,"u":g2("link")})
    return out
def wp(base,src):
    out=[]
    for q in ("مناقصة","اعلان","إحالة"):
        j=json.loads(get(base+"/wp-json/wp/v2/posts?per_page=50&_fields=date,link,title&search="+urllib.parse.quote(q)))
        out+=[{"t":clean(p["title"]["rendered"]),"s":src,"d":p["date"][:10],"u":p["link"]} for p in j]
    return out
def karbala():
    out=[]
    for p in ("","?page=2","?page=3"):
        x=get("https://www.karbala.gov.iq/contracts-and-tenders/"+p)
        for m in re.finditer(r'href="(/contracts-and-tenders/(\d+))"[^>]*>(.*?)</a>',x,re.S):
            t=clean(m.group(3))
            dm=re.search(r"تم النشر في (\d{4})/(\d\d)/(\d\d)",t); d="-".join(dm.groups()) if dm else ""
            t=re.sub(r"تم النشر في [\d/]+ [\d:]+","",t).strip()
            if len(t)>8: out.append({"t":t,"s":"محافظة كربلاء","d":d,"u":"https://www.karbala.gov.iq"+m.group(1),"k":1})
    return out
import urllib.parse
SRC=[("وزارة التخطيط",lambda:rss("https://mop.gov.iq/?s=%D9%85%D9%86%D8%A7%D9%82%D8%B5%D8%A9&feed=rss2","وزارة التخطيط")),
 ("محافظة البصرة",lambda:wp("https://basra.gov.iq","محافظة البصرة")),
 ("محافظة كربلاء",karbala),
 ("محافظة بغداد",lambda:rss("https://baghdad.gov.iq/feed/index.rss","محافظة بغداد")),
 ("محافظة واسط",lambda:rss("https://wasit.gov.iq/?cat=133&feed=rss2","محافظة واسط"))]
old={}
try: old=json.load(open("tenders.json"))
except Exception: pass
cut=(dt.date.today()-dt.timedelta(days=183)).isoformat()
items=[]; stat={}
prev={}
for i in old.get("items",[]): prev.setdefault(i["s"],[]).append(i)
for name,fn in SRC:
    try:
        r=[i for i in fn() if i["u"].startswith("https://") and i["t"]]
        r=[i for i in r if i.pop("k",0) or KW.search(i["t"])]
        r=[i for i in r if not i["d"] or i["d"]>=cut]
        stat[name]=len(r); items+=r
    except Exception as e:
        stat[name]="فشل"; items+=prev.get(name,[]); print(name,"FAILED",e,file=sys.stderr)
seen=set(); u=[]
for i in items:
    if i["u"] in seen: continue
    seen.add(i["u"]); u.append(i)
u.sort(key=lambda i:i["d"] or "0",reverse=True)
json.dump({"updated":dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),"stat":stat,"items":u},open("tenders.json","w"),ensure_ascii=False,indent=0)
print(stat,len(u))
