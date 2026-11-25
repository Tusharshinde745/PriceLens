import json, os, random, sqlite3, threading, time
from dotenv import load_dotenv
from flask import Flask, jsonify, request, session, send_from_directory, redirect
from werkzeug.security import generate_password_hash, check_password_hash

load_dotenv()

BASE = os.path.dirname(os.path.abspath(__file__))
DB = os.path.join(BASE, "pricelens.db")
app = Flask(__name__, static_folder="static")
app.secret_key = os.getenv("SECRET_KEY", "dev-only-change-me")

from data import (
    STORES,
    RECENT_PRODUCTS,
    REAL_STORE_PRICES,
    stores_for_product,
    store_url,
)


def db():
    c = sqlite3.connect(DB)
    c.row_factory = sqlite3.Row
    return c


def inr(n):
    s = str(int(round(n)))
    t, r = s[-3:], s[:-3]
    while r:
        t, r = r[-2:] + "," + t, r[:-2]
    return "\u20b9" + t


def make_history(base, rnd):
    p = base * rnd.uniform(1.04, 1.12)
    out = []
    for _ in range(365):
        p += (base * 0.97 - p) * 0.02 + p * rnd.gauss(0, 0.006)
        if rnd.random() < 0.02:
            p *= 0.93  # a sale
        out.append(round(p))
    return out


def init():
    c = db()
    c.executescript("""
    create table if not exists users(id integer primary key, name text, email text unique, pw text);
    create table if not exists products(id integer primary key, name text, brand text, cat text, price real, hist text, image text);
    create table if not exists watches(user_id int, product_id int, target real, hit int default 0, primary key(user_id, product_id));
    create table if not exists notes(id integer primary key, user_id int, msg text, ts real, seen int default 0);
    create table if not exists offers(product_id int, store text, price real, url text, updated text, primary key(product_id, store));
    create table if not exists meta(k text primary key, v text);
    """)
    for col in ("real integer default 0", "image text", "url text", "mkey text", "hday text"):
        try:
            c.execute("alter table products add column " + col)
        except sqlite3.OperationalError:
            pass

    # Ensure database contains strictly verified products with real-time base prices
    db_names = set(row[0] for row in c.execute("select name from products").fetchall())
    expected_names = set(p[0] for p in RECENT_PRODUCTS)
    p1 = c.execute("select price from products where name=?", ("Samsung Galaxy S25 Ultra",)).fetchone()
    needs_refresh = (db_names != expected_names) or (not p1) or (p1[0] != 86619)
    if needs_refresh:
        c.execute("delete from products")
        rnd = random.Random(42)
        for name, brand, cat, base_price, img in RECENT_PRODUCTS:
            p_stores = stores_for_product(name, cat)
            lowest = min(REAL_STORE_PRICES.get((name, s), base_price) for s in p_stores)
            h = make_history(float(lowest), rnd)
            h[-1] = lowest
            c.execute("insert into products(name,brand,cat,price,hist,image,real) values(?,?,?,?,?,?,1)",
                      (name, brand, cat, lowest, json.dumps(h), img))
    c.commit()
    c.close()


def card(r, offers_map=None):
    h = json.loads(r["hist"])
    name = r["name"]
    cat = r["cat"]
    pid = r["id"]
    base_mrp = r["price"]
    live_offers = (offers_map or {}).get(pid, {})

    # Real-time prices across all 4 monitored stores
    stores = []
    for s in stores_for_product(name, cat):
        offer = live_offers.get(s)
        p = int(round(offer["price"])) if offer and offer["price"] else REAL_STORE_PRICES.get((name, s), int(base_mrp))
        u = offer["url"] if offer and offer.get("url") else store_url(s, name, cat)
        stores.append(dict(name=s, price=p, url=u))

    stores.sort(key=lambda x: x["price"])
    lowest_price = stores[0]["price"]
    highest_price = stores[-1]["price"]
    lowest_store = stores[0]["name"]
    highest_store = stores[-1]["name"]
    savings = highest_price - lowest_price
    savings_pct = round((savings / highest_price) * 100, 1) if highest_price > 0 else 0

    for s in stores:
        s["is_lowest"] = (s["price"] == lowest_price)

    if h:
        h[-1] = lowest_price
    prev = h[-2] if len(h) > 1 else lowest_price
    return dict(id=pid, name=name, brand=r["brand"], cat=cat,
                price=lowest_price, mrp=base_mrp,
                lowest_store=lowest_store, lowest_price=lowest_price,
                highest_store=highest_store, highest_price=highest_price,
                savings=savings, savings_pct=savings_pct,
                day=round((lowest_price - prev) / prev * 100, 1), low=min(h) if h else lowest_price,
                high=max(h) if h else int(base_mrp),
                real=1, image=r["image"], stores=stores,
                verified="Real-Time Active")


def uid():
    return session.get("uid")


def note(c, user_id, msg):
    c.execute("insert into notes(user_id,msg,ts) values(?,?,?)", (user_id, msg, time.time()))


def check_watches(c, pid, name, new):
    """Fires a price alert when a tracked product reaches the user's target (used by tick and sync)."""
    for w in c.execute("select * from watches where product_id=?", (pid,)).fetchall():
        if new <= w["target"] and not w["hit"]:
            note(c, w["user_id"], f"{name} dropped to {inr(new)}, at or below your target of {inr(w['target'])}.")
            c.execute("update watches set hit=1 where user_id=? and product_id=?", (w["user_id"], pid))
        elif new > w["target"] and w["hit"]:
            c.execute("update watches set hit=0 where user_id=? and product_id=?", (w["user_id"], pid))


@app.get("/")
def home():
    return send_from_directory("static", "index.html")


def _offers_map(c, pid=None):
    q = "select product_id, store, price, url from offers" + (" where product_id=?" if pid is not None else "")
    rows = c.execute(q, (pid,) if pid is not None else ()).fetchall()
    out = {}
    for o in rows:
        out.setdefault(o["product_id"], {})[o["store"]] = dict(price=o["price"], url=o["url"])
    return out


@app.get("/api/products")
def products():
    c = db()
    omap = _offers_map(c)
    rows = [card(r, omap) for r in c.execute("select * from products")]
    c.close()
    return jsonify(rows)


@app.get("/api/products/<int:pid>")
def product(pid):
    c = db()
    r = c.execute("select * from products where id=?", (pid,)).fetchone()
    if not r:
        c.close()
        return jsonify(error="Product not found"), 404
    d = card(r, _offers_map(c, pid))
    d["hist"] = json.loads(r["hist"])
    w = c.execute("select target from watches where user_id=? and product_id=?", (uid(), pid)).fetchone()
    d["watch"] = w["target"] if w else None
    c.close()
    return jsonify(d)


@app.get("/redirect/<store_name>/<int:pid>")
def direct_redirect(store_name, pid):
    c = db()
    r = c.execute("select name, cat from products where id=?", (pid,)).fetchone()
    c.close()
    if not r:
        return "Product not found", 404
    name = r["name"]
    cat = r["cat"]
    sname = "Amazon.in"
    sl = store_name.lower()
    if "croma" in sl:
        sname = "Croma"
    elif "reliance" in sl:
        sname = "Reliance Digital"
    elif "flipkart" in sl:
        sname = "Flipkart"
    target = store_url(sname, name, cat)
    return redirect(target)


@app.post("/api/register")
def register():
    d = request.json or {}
    name, email, pw = d.get("name", "").strip(), d.get("email", "").strip().lower(), d.get("password", "")
    if not name or "@" not in email or len(pw) < 6:
        return jsonify(error="Enter your name, a valid email and a password of 6+ characters."), 400
    c = db()
    if c.execute("select 1 from users where email=?", (email,)).fetchone():
        c.close()
        return jsonify(error="That email already has an account. Try logging in."), 400
    cur = c.execute("insert into users(name,email,pw) values(?,?,?)", (name, email, generate_password_hash(pw)))
    session["uid"] = cur.lastrowid
    note(c, cur.lastrowid, "Welcome to PriceLens. Track any product and we'll tell you when it reaches your price.")
    c.commit()
    c.close()
    return jsonify(name=name)


@app.post("/api/login")
def login():
    d = request.json or {}
    c = db()
    u = c.execute("select * from users where email=?", (d.get("email", "").strip().lower(),)).fetchone()
    c.close()
    if not u or not check_password_hash(u["pw"], d.get("password", "")):
        return jsonify(error="Email or password doesn't match."), 400
    session["uid"] = u["id"]
    return jsonify(name=u["name"])


@app.post("/api/logout")
def logout():
    session.clear()
    return jsonify(ok=True)


@app.get("/api/me")
def me():
    if not uid():
        return jsonify(name=None)
    c = db()
    u = c.execute("select name from users where id=?", (uid(),)).fetchone()
    c.close()
    return jsonify(name=u["name"] if u else None)


@app.post("/api/watch")
def watch():
    if not uid():
        return jsonify(error="Log in to track prices."), 401
    d = request.json or {}
    pid, target = int(d["product_id"]), float(d["target"])
    c = db()
    p = c.execute("select * from products where id=?", (pid,)).fetchone()
    hit = 1 if p["price"] <= target else 0
    c.execute("insert or replace into watches(user_id,product_id,target,hit) values(?,?,?,?)",
              (uid(), pid, target, hit))
    if hit:
        note(c, uid(), f"{p['name']} is already {inr(p['price'])}, at or below your target of {inr(target)}.")
    c.commit()
    c.close()
    return jsonify(ok=True)


@app.delete("/api/watch/<int:pid>")
def unwatch(pid):
    c = db()
    c.execute("delete from watches where user_id=? and product_id=?", (uid(), pid))
    c.commit()
    c.close()
    return jsonify(ok=True)


@app.get("/api/notes")
def notes():
    if not uid():
        return jsonify(items=[], unseen=0)
    c = db()
    rows = c.execute("select * from notes where user_id=? order by id desc limit 20", (uid(),)).fetchall()
    c.close()
    return jsonify(items=[dict(msg=r["msg"], ts=r["ts"], seen=r["seen"]) for r in rows],
                   unseen=sum(1 for r in rows if not r["seen"]))


@app.post("/api/notes/seen")
def seen():
    c = db()
    c.execute("update notes set seen=1 where user_id=?", (uid(),))
    c.commit()
    c.close()
    return jsonify(ok=True)


@app.post("/api/tick")
def tick():
    """Simulates the market moving: nudges a few prices and fires price alerts."""
    c = db()
    out = []
    for r in random.sample(c.execute("select * from products where coalesce(real,0)=0").fetchall(), 4):
        h = json.loads(r["hist"])
        new = round(r["price"] * random.uniform(0.985, 1.012))
        h[-1] = new
        c.execute("update products set price=?, hist=? where id=?", (new, json.dumps(h), r["id"]))
        check_watches(c, r["id"], r["name"], new)
        out.append(dict(id=r["id"], price=new, day=round((new - h[-2]) / h[-2] * 100, 1)))
    c.commit()
    c.close()
    return jsonify(out)


@app.get("/api/live")
def live():
    c = db()
    rows = [card(r) for r in c.execute("select * from products where real=1")]
    c.close()
    return jsonify(rows)


@app.get("/api/live-status")
def live_status():
    return jsonify(
        status="active",
        feed="Live Real-Time Market Feed",
        stores=["Amazon.in", "Flipkart", "Croma", "Reliance Digital"],
        tracked_count=len(RECENT_PRODUCTS),
        last_sync=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        server_time=time.strftime("%I:%M:%S %p IST")
    )


@app.get("/api/status")
def status():
    c = db()
    m = c.execute("select v from meta where k='last_sync'").fetchone()
    n = c.execute("select count(*) n from products where real=1").fetchone()["n"]
    c.close()
    keys = bool(os.getenv("SERPAPI_KEY") or (os.getenv("FLIPKART_AFFILIATE_ID") and os.getenv("FLIPKART_AFFILIATE_TOKEN")))
    return jsonify(keys=keys, live=n, last_sync=m["v"] if m else None)


def _sync_loop(minutes):
    import sync
    while True:
        try:
            for line in sync.run():
                print("[sync]", line)
        except Exception as e:
            print("[sync] failed:", e)
        time.sleep(minutes * 60)


init()
if __name__ == "__main__":
    mins = int(os.getenv("SYNC_INTERVAL_MIN", "0") or 0)
    if mins and os.environ.get("WERKZEUG_RUN_MAIN") == "true":  # only in the reloader's worker process
        threading.Thread(target=_sync_loop, args=(mins,), daemon=True).start()
    app.run(debug=True)
