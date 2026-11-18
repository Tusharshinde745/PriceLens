"""Pulls the latest products and prices from Indian stores into PriceLens.

Run once:           python sync.py
Only some cats:     python sync.py --cats Phones,Laptops
Run automatically:  set SYNC_INTERVAL_MIN in .env and start app.py

Keys live in .env (see .env.example) and are only ever read on the server.
"""
import argparse, datetime, json, os, re
import requests
from dotenv import load_dotenv

load_dotenv()
from app import db, init, check_watches  # noqa: E402

QUERIES = {
    "Phones": ["latest smartphones 2026", "new iPhone", "new Samsung Galaxy"],
    "Laptops": ["latest laptops 2026", "new MacBook"],
    "Tablets": ["latest tablets 2026"],
    "Audio": ["new wireless earbuds 2026", "new noise cancelling headphones"],
    "Wearables": ["latest smartwatch 2026"],
    "Gaming": ["new gaming console", "latest gaming laptop"],
    "Home": ["latest smart tv 2026", "new robot vacuum"],
    "Cameras": ["latest mirrorless camera", "new action camera"],
    "Accessories": ["latest power bank", "new mechanical keyboard"],
}
STORE_MAP = [("amazon", "Amazon.in"), ("flipkart", "Flipkart"), ("croma", "Croma"),
             ("reliance", "Reliance Digital"), ("vijay", "Vijay Sales"), ("tata cliq", "Tata CLiQ")]


def norm_store(name):
    n = (name or "").lower()
    return next((label for key, label in STORE_MAP if key in n), None)


# ---------- providers: each returns a list of dicts, or None when no key is set ----------
def flipkart(query, n):
    """Official Flipkart Affiliate API (affiliate.flipkart.com > API > API Token)."""
    fid, tok = os.getenv("FLIPKART_AFFILIATE_ID"), os.getenv("FLIPKART_AFFILIATE_TOKEN")
    if not (fid and tok):
        return None
    r = requests.get("https://affiliate-api.flipkart.net/affiliate/1.0/search.json",
                     params={"query": query, "resultCount": n},
                     headers={"Fk-Affiliate-Id": fid, "Fk-Affiliate-Token": tok}, timeout=20)
    r.raise_for_status()
    out = []
    for p in r.json().get("products", []):
        b = p.get("productBaseInfoV1", {})
        price = (b.get("flipkartSellingPrice") or {}).get("amount")
        if not price or b.get("inStock") is False:
            continue
        imgs = b.get("imageUrls") or {}
        out.append(dict(title=b.get("title", ""), store="Flipkart", price=float(price), url=b.get("productUrl"),
                        image=imgs.get("400x400") or next(iter(imgs.values()), None)))
    return out


def serpapi(query, n):
    """Google Shopping (India) through SerpApi. Returns offers from Amazon.in, Croma, Reliance Digital etc."""
    key = os.getenv("SERPAPI_KEY")
    if not key:
        return None
    r = requests.get("https://serpapi.com/search.json",
                     params={"engine": "google_shopping", "q": query, "gl": "in", "hl": "en",
                             "google_domain": "google.co.in", "num": n, "api_key": key}, timeout=30)
    r.raise_for_status()
    out = []
    for p in r.json().get("shopping_results", []):
        store, price = norm_store(p.get("source")), p.get("extracted_price")
        if store and price:
            out.append(dict(title=p.get("title", ""), store=store, price=float(price),
                            url=p.get("link") or p.get("product_link"), image=p.get("thumbnail")))
    return out


PROVIDERS = {"flipkart": flipkart, "serpapi": serpapi}


# ---------- ingest ----------
def mkey(title):
    """Rough model key so the same phone from two stores lands on one product (heuristic, not perfect)."""
    t = re.sub(r"\(.*?\)", " ", title.lower())
    t = re.sub(r"\b\d+\s?(gb|tb)\b", " ", t)
    return " ".join(re.sub(r"[^a-z0-9 ]", " ", t).split()[:4])


def ingest(c, cat, it, today):
    k = mkey(it["title"])
    if not k:
        return None
    row = c.execute("select id from products where real=1 and mkey=?", (k,)).fetchone()
    if row:
        pid = row["id"]
    else:
        name = re.sub(r"\s+", " ", it["title"]).strip()[:70]
        pid = c.execute("insert into products(name,brand,cat,price,hist,real,image,url,mkey,hday) "
                        "values(?,?,?,?,?,1,?,?,?,?)",
                        (name, name.split()[0], cat, it["price"], json.dumps([it["price"]]),
                         it["image"], it["url"], k, today)).lastrowid
    c.execute("insert or replace into offers values(?,?,?,?,?)", (pid, it["store"], it["price"], it["url"], today))
    return pid


def finalize(c, pids, today):
    """Headline price = cheapest offer. One history point per day; skipped days repeat the last known price."""
    t = datetime.date.fromisoformat(today)
    for pid in pids:
        p = c.execute("select name,hist,hday from products where id=?", (pid,)).fetchone()
        best = c.execute("select min(price) m from offers where product_id=?", (pid,)).fetchone()["m"]
        h = json.loads(p["hist"])
        gap = (t - datetime.date.fromisoformat(p["hday"])).days if p["hday"] else 1
        if gap <= 0:
            h[-1] = best
        else:
            h += [h[-1]] * (gap - 1) + [best]
        c.execute("update products set price=?, hist=?, hday=? where id=?", (best, json.dumps(h[-365:]), today, pid))
        check_watches(c, pid, p["name"], best)


def run(cats=None, per=10):
    init()
    c, today, touched, dead, log = db(), datetime.date.today().isoformat(), set(), set(), []
    for cat, queries in QUERIES.items():
        if cats and cat not in cats:
            continue
        for q in queries:
            for name, fn in PROVIDERS.items():
                if name in dead:
                    continue
                try:
                    items = fn(q, per)
                except requests.HTTPError as e:
                    dead.add(name)
                    log.append(f"{name}: HTTP {e.response.status_code} on '{q}'. Check the key or your quota; skipping it for this run.")
                    continue
                except Exception as e:
                    log.append(f"{name}: {e}")
                    continue
                if items is None:
                    dead.add(name)
                    log.append(f"{name}: no key in .env, skipped.")
                    continue
                touched.update(p for p in (ingest(c, cat, it, today) for it in items) if p)
    finalize(c, touched, today)
    if touched:
        c.execute("insert or replace into meta values('last_sync', ?)",
                  (datetime.datetime.now(datetime.timezone.utc).isoformat(),))
    c.commit()
    c.close()
    log.append(f"Updated {len(touched)} live products.")
    return log


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--cats", help="comma-separated, e.g. Phones,Laptops")
    ap.add_argument("--per", type=int, default=10, help="results per query")
    a = ap.parse_args()
    for line in run(a.cats.split(",") if a.cats else None, a.per):
        print(line)
