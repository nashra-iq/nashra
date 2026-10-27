#!/usr/bin/env python3
"""Daily crawler: add new bulletins from tasjeel.mot.gov.iq to data.json. Idempotent; exits 0 on site errors."""
import re, os, json, sys, html, subprocess, tempfile, datetime, urllib.request, urllib.parse
BASE = "https://tasjeel.mot.gov.iq/newtasjeel/"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data.json")
UA = {"User-Agent": "Mozilla/5.0"}
BIDI = re.compile(r'[\u200e\u200f\u202a-\u202e\u2066-\u2069\ufffd]')

def get(url, t=60):
    req = urllib.request.Request(urllib.parse.quote(url, safe=":/%?=&#~+"), headers=UA)
    with urllib.request.urlopen(req, timeout=t) as r: return r.read()

def links(page_url):
    try: raw = get(page_url)
    except Exception as e: print("fetch fail", page_url, e); return []
    s = raw.decode("utf-8", "ignore")
    if s.count("\ufffd") > 50: s = raw.decode("cp1256", "ignore")
    out = []
    for h in re.findall(r'href\s*=\s*["\']([^"\']+)["\']', s, re.I):
        h = html.unescape(h).strip()
        out.append(urllib.parse.urljoin(page_url, h))
    return out

def key(u):  # canonical relative, decoded path
    u = urllib.parse.unquote(u)
    u = re.sub(r'^https?://tasjeel\.mot\.gov\.iq/newtasjeel/', '', u)
    return u.replace('\\', '/').strip().lower()

def extract(base, t):
    t = BIDI.sub('', t)
    m = re.search(r'العدد\s*\(?\s*(\d{1,4})', t); iss = m.group(1) if m else ''
    b2 = re.sub(r"^\d{4}_\d+_", "", base)
    d = re.findall(r"(20\d\d)[-_/](\d{1,2})[-_/](\d{1,2})", b2) or [(y, mo, da) for da, mo, y in re.findall(r"(\d{1,2})-(\d{1,2})-(20\d\d)", b2)]
    date = '-'.join(str(int(x)) for x in d[-1]) if d else base
    seen = set(); lines = []
    for ln in t.split('\n'):
        ln = re.sub(r'^\s*[\d\.\s]*', '', ln).strip(' .')
        ln = re.sub(r'\s+', ' ', ln)
        if 'شرك' in ln and re.match(r'(قرار|عقد|بيان|اعالن|إعلان|محضر|تعديل|ملحق)', ln) and len(ln) < 220 and ln not in seen:
            seen.add(ln); lines.append(ln)
    return date, iss, lines

def main():
    data = json.load(open(DATA, encoding="utf-8"))
    have = {key(r[2]) for r in data}
    y = datetime.date.today().year
    pages = set()
    for idx in {f"{BASE}nashra--{y}all.htm", f"{BASE}nashra--{y-1}all.htm" if datetime.date.today().month == 1 else f"{BASE}nashra--{y}all.htm"}:
        pages.add(idx)
        for l in links(idx):
            if l.lower().endswith((".htm", ".html")) and "nashra" in l.lower() and str(y) in l: pages.add(l)
    pdfs = []
    for p in sorted(pages):
        for l in links(p):
            if not l.lower().endswith(".pdf") or not l.startswith(BASE): continue
            rel = key(l)
            # bulletin PDFs live under YYYY/M/ or YYYY/شهر M/ (or 'نشرة YYYY/')
            if not re.match(r'^(20\d\d/[^/]*\d{1,2}/|نشرة\s*20\d\d/)', rel): continue
            if rel not in have and l not in pdfs: pdfs.append(l)
    print(len(pages), "pages;", len(pdfs), "new pdfs")
    added = 0
    for u in pdfs:
        try:
            with tempfile.TemporaryDirectory() as td:
                f = os.path.join(td, "a.pdf"); open(f, "wb").write(get(u, 180))
                t = subprocess.run(["pdftotext", "-enc", "UTF-8", f, "-"], capture_output=True, timeout=300).stdout.decode("utf-8", "ignore")
        except Exception as e:
            print("skip", u, e); continue
        rel = urllib.parse.unquote(u[len(BASE):])
        base = os.path.splitext(os.path.basename(rel))[0]
        date, iss, lines = extract(base, t)
        # store percent-encoded relative path (same form the page prefixes with BASE)
        data.append([date, iss, urllib.parse.quote(rel), lines]); have.add(key(u)); added += 1
        print("added", date, iss, len(lines), rel)
    if added:
        data.sort(key=lambda r: [int(x) if x.isdigit() else 0 for x in r[0].split('-')])
        s = json.dumps(data, ensure_ascii=False, separators=(',', ':'))
        open(DATA, "w", encoding="utf-8").write(s)
    print("added", added, "total", len(data))

if __name__ == "__main__":
    try: main()
    except Exception as e: print("error:", e)
    sys.exit(0)
