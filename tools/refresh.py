#!/usr/bin/env python3
"""
Refresh films.json from Georgina's live Letterboxd watchlist.

Incremental by design: the watchlist pages are cheap, so every run reads those,
then does full detail scraping only for films it has never seen. Films that have
left the watchlist are dropped.

Safety guard: a run that returns nothing, or that would delete more than half the
list, aborts without writing. A transient block upstream should never empty the app.
"""
import re, json, html, time, sys, gzip, os, random, datetime, unicodedata
import urllib.request, urllib.error
from concurrent.futures import ThreadPoolExecutor

USER = "genie_bean"
OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "films.json")
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
MC_RETRY_PER_RUN = 40          # slowly revisit films Metacritic had no entry for
WORKERS = 5

log = lambda m: (sys.stderr.write(m + "\n"), sys.stderr.flush())

def get(url, tries=3, timeout=30):
    for n in range(tries):
        try:
            req = urllib.request.Request(url, headers={
                "User-Agent": UA, "Accept-Language": "en-GB,en;q=0.9",
                "Accept": "text/html,application/xhtml+xml,*/*;q=0.8"})
            with urllib.request.urlopen(req, timeout=timeout) as r:
                raw = r.read()
                if r.headers.get("Content-Encoding") == "gzip":
                    raw = gzip.decompress(raw)
                return raw.decode("utf-8", "replace")
        except urllib.error.HTTPError as e:
            if e.code in (404, 403): return None
            time.sleep(1.5 * (n + 1))
        except Exception:
            time.sleep(1.5 * (n + 1))
    return None

# ---------------------------------------------------------------- watchlist
def watchlist_slugs():
    slugs, page = [], 1
    while True:
        h = get(f"https://letterboxd.com/{USER}/watchlist/page/{page}/")
        if not h:
            if page == 1:
                raise SystemExit("ABORT: could not read watchlist page 1")
            break
        found = re.findall(r'data-item-slug="([^"]+)"', h)
        if not found: break
        slugs += found
        if f'/watchlist/page/{page+1}/' not in h: break
        page += 1
        time.sleep(0.3)
    seen, out = set(), []
    for s in slugs:
        if s not in seen: seen.add(s); out.append(s)
    return out

# ---------------------------------------------------------------- film detail
def iso_minutes(d):
    if not d: return None
    m = re.match(r'PT(?:(\d+)H)?(?:(\d+)M)?', d)
    return int(m.group(1) or 0) * 60 + int(m.group(2) or 0) if m else None

def film(slug):
    h = get(f"https://letterboxd.com/film/{slug}/")
    if not h: return None
    m = re.search(r'application/ld\+json.*?/\* <!\[CDATA\[ \*/(.*?)/\* \]\]> \*/', h, re.S)
    ld = {}
    if m:
        try: ld = json.loads(m.group(1))
        except Exception: pass
    ym = re.search(r'/films/year/(\d{4})/', h)
    im = re.search(r'imdb\.com/title/(tt\d+)', h)
    tm = re.search(r'(?:youtube\.com/embed/|youtube\.com/watch\?v=)([A-Za-z0-9_-]{6,})', h)
    ar = ld.get("aggregateRating") or {}
    rating = None
    if ar.get("ratingValue") is not None:
        try: rating = round(float(ar["ratingValue"]), 2)
        except Exception: pass
    desc = ld.get("description") or ""
    if not desc:
        dm = re.search(r'<meta name="description" content="(.*?)"', h, re.S)
        desc = dm.group(1) if dm else ""
    desc = re.sub(r'\s+', ' ', html.unescape(re.sub(r'<[^>]+>', '', desc))).strip()
    poster = (ld.get("image") or "").split("?")[0] or None
    return {
        "slug": slug,
        "title": html.unescape(ld.get("name") or slug.replace("-", " ").title()),
        "year": int(ym.group(1)) if ym else None,
        "directors": [html.unescape(d.get("name", "")) for d in (ld.get("director") or [])][:3],
        "cast": [html.unescape(a.get("name", "")) for a in (ld.get("actor") or [])][:4],
        "genres": ld.get("genre") or [],
        "runtime": iso_minutes(ld.get("duration")),
        "poster": poster,
        "synopsis": desc,
        "lb": rating,
        "imdbId": im.group(1) if im else None,
        "trailer": tm.group(1) if tm else None,
        "imdb": None, "mc": None,
    }

# ---------------------------------------------------------------- imdb
def imdb_ratings(ids):
    if not ids: return {}
    log("  downloading IMDb ratings dataset")
    try:
        req = urllib.request.Request("https://datasets.imdbws.com/title.ratings.tsv.gz",
                                     headers={"User-Agent": UA})
        with urllib.request.urlopen(req, timeout=180) as r:
            blob = r.read()
    except Exception as e:
        log(f"  IMDb dataset unavailable ({e}); keeping existing scores")
        return {}
    out = {}
    with gzip.open(__import__("io").BytesIO(blob), "rt") as fh:
        next(fh)
        for line in fh:
            t, avg, _votes = line.rstrip("\n").split("\t")
            if t in ids:
                out[t] = float(avg)
    return out

# ---------------------------------------------------------------- metacritic
def norm(s):
    s = unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode()
    return re.sub(r'[^a-z0-9]', '', s.lower())

def slugify(t):
    s = unicodedata.normalize("NFKD", t).encode("ascii", "ignore").decode()
    s = s.lower().replace("&", "and")
    s = re.sub(r"['’]", "", s)
    return re.sub(r'[^a-z0-9]+', '-', s).strip('-')

def metascore(f):
    cands = [slugify(f["title"])]
    if f.get("year"): cands.append(f"{cands[0]}-{f['year']}")
    lb = re.sub(r'-\d{4}$', '', f["slug"])
    if lb not in cands: cands.append(lb)
    for slug in cands:
        h = get(f"https://www.metacritic.com/movie/{slug}/", tries=2)
        if not h: continue
        m = re.search(r'application/ld\+json[^>]*>(.*?)</script>', h, re.S)
        if not m: continue
        try: d = json.loads(m.group(1))
        except Exception: continue
        if norm(d.get("name") or "") != norm(f["title"]): continue
        pub = re.search(r'(\d{4})', str(d.get("datePublished") or ""))
        if pub and f.get("year") and abs(int(pub.group(1)) - f["year"]) > 1: continue
        ar = d.get("aggregateRating") or {}
        if ar.get("name") == "Metascore" and ar.get("ratingValue") is not None:
            try: return int(ar["ratingValue"])
            except Exception: pass
    return None

# ---------------------------------------------------------------- main
def main():
    prev = {}
    if os.path.exists(OUT):
        try:
            prev = {f["slug"]: f for f in json.load(open(OUT, encoding="utf-8"))["films"]}
        except Exception as e:
            log(f"  could not read existing films.json ({e}); treating as first run")

    log("reading watchlist")
    slugs = watchlist_slugs()
    log(f"  watchlist has {len(slugs)} films (had {len(prev)})")

    # guard: never let a bad upstream response empty or gut the list
    if not slugs:
        raise SystemExit("ABORT: watchlist came back empty")
    if prev and len(slugs) < len(prev) * 0.5:
        raise SystemExit(f"ABORT: watchlist dropped from {len(prev)} to {len(slugs)} "
                         f"(>50%); refusing to write. Likely blocked or rate-limited upstream.")

    added = [s for s in slugs if s not in prev]
    removed = [s for s in prev if s not in set(slugs)]
    log(f"  {len(added)} new, {len(removed)} removed")

    films = {s: prev[s] for s in slugs if s in prev}

    if added:
        log(f"scraping {len(added)} new film pages")
        with ThreadPoolExecutor(max_workers=WORKERS) as ex:
            for r in ex.map(film, added):
                if r: films[r["slug"]] = r
        log(f"  got detail for {sum(1 for s in added if s in films)}/{len(added)}")

    ordered = [films[s] for s in slugs if s in films]

    # IMDb scores refresh for everything -- one download, so it is nearly free
    ids = {f["imdbId"] for f in ordered if f.get("imdbId")}
    r = imdb_ratings(ids)
    if r:
        for f in ordered:
            if f.get("imdbId") in r: f["imdb"] = r[f["imdbId"]]
    log(f"  IMDb scores on {sum(1 for f in ordered if f.get('imdb') is not None)}/{len(ordered)}")

    # Metacritic: new films, plus a slice of previous misses in case one was added
    todo = [f for f in ordered if f["slug"] in set(added)]
    misses = [f for f in ordered if f.get("mc") is None and f["slug"] not in set(added)]
    random.shuffle(misses)
    todo += misses[:MC_RETRY_PER_RUN]
    if todo:
        log(f"checking Metacritic for {len(todo)} films")
        def work(f):
            s = metascore(f)
            if s is not None: f["mc"] = s
        with ThreadPoolExecutor(max_workers=WORKERS) as ex:
            list(ex.map(work, todo))
    log(f"  Metascores on {sum(1 for f in ordered if f.get('mc') is not None)}/{len(ordered)}")

    ordered.sort(key=lambda x: (x.get("title") or "").lower())
    payload = {
        "generated": datetime.datetime.now(datetime.timezone.utc)
                        .replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "user": USER,
        "source": f"https://letterboxd.com/{USER}/watchlist/",
        "count": len(ordered),
        "films": ordered,
    }

    old = open(OUT, encoding="utf-8").read() if os.path.exists(OUT) else ""
    new = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    # compare ignoring the timestamp so an unchanged watchlist makes no commit
    def strip_ts(s):
        return re.sub(r'"generated":"[^"]*",', '', s)
    changed = strip_ts(old) != strip_ts(new)
    if changed:
        open(OUT, "w", encoding="utf-8").write(new)
        log(f"WROTE films.json: {len(ordered)} films (+{len(added)} -{len(removed)})")
    else:
        log("no change")
    print(f"changed={'true' if changed else 'false'}")

if __name__ == "__main__":
    main()
