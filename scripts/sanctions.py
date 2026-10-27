# Builds sanctions.json from official public lists: OFAC SDN (US Treasury) and UN Security Council consolidated list.
import json, urllib.request, xml.etree.ElementTree as ET, sys
UA={"User-Agent":"Mozilla/5.0 nashra-bot"}
def get(u):
    return urllib.request.urlopen(urllib.request.Request(u,headers=UA),timeout=180).read()
def strip(t): return t.split('}')[-1]
out=[]
def ofac():
    x=ET.fromstring(get("https://sanctionslistservice.ofac.treas.gov/api/PublicationPreview/exports/SDN.XML"))
    n=0
    for e in x.iter():
        if strip(e.tag)!="sdnEntry": continue
        d={strip(c.tag):c for c in e}
        g=lambda k:(d[k].text or "").strip() if k in d else ""
        name=" ".join(filter(None,[g("firstName"),g("lastName")]))
        al=[]; progs=[]
        for c in e.iter():
            t=strip(c.tag)
            if t=="aka":
                dd={strip(z.tag):(z.text or "").strip() for z in c}
                a=" ".join(filter(None,[dd.get("firstName"),dd.get("lastName")]))
                if a: al.append(a)
            if t=="program" and c.text: progs.append(c.text.strip())
        out.append({"n":name,"a":al[:15],"l":"OFAC","t":g("sdnType"),"r":" ".join(progs),"d":"","u":"https://sanctionssearch.ofac.treas.gov/Details.aspx?id="+g("uid")}); n+=1
    return n
def un():
    x=ET.fromstring(get("https://scsanctions.un.org/resources/xml/en/consolidated.xml"))
    n=0
    for tag,typ in (("INDIVIDUAL","Individual"),("ENTITY","Entity")):
        for e in x.iter(tag):
            f=lambda k:(e.findtext(k) or "").strip()
            name=" ".join(filter(None,[f("FIRST_NAME"),f("SECOND_NAME"),f("THIRD_NAME"),f("FOURTH_NAME")]))
            al=[(a.findtext("ALIAS_NAME") or "").strip() for a in e.iter(tag+"_ALIAS")]
            orig=f("NAME_ORIGINAL_SCRIPT")
            if orig: al.insert(0,orig)
            out.append({"n":name,"a":[a for a in al if a][:15],"l":"UN","t":typ,"r":f("UN_LIST_TYPE")+" "+f("REFERENCE_NUMBER"),"d":f("LISTED_ON"),"u":"https://main.un.org/securitycouncil/en/content/un-sc-consolidated-list"}); n+=1
    return n
ok=0
for fn in (ofac,un):
    try: print(fn.__name__,fn()); ok+=1
    except Exception as e: print(fn.__name__,"FAILED",e,file=sys.stderr)
if ok==2:
    json.dump(out,open("sanctions.json","w"),ensure_ascii=False,separators=(",",":"))
