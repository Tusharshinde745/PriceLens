import json, os, random, sqlite3, threading, time
from dotenv import load_dotenv
from flask import Flask, jsonify, request, session, send_from_directory
from werkzeug.security import generate_password_hash, check_password_hash

load_dotenv()

BASE = os.path.dirname(os.path.abspath(__file__))
DB = os.path.join(BASE, "pricelens.db")
app = Flask(__name__, static_folder="static")
app.secret_key = os.getenv("SECRET_KEY", "dev-only-change-me")

# Starting prices are approximate INR list prices used to seed the demo.
CATALOG = {
"Phones": """iPhone 17|Apple|82900; iPhone 17 Pro|Apple|134900; iPhone 17 Pro Max|Apple|149900; iPhone Air|Apple|119900;
iPhone 16|Apple|69900; Galaxy S25 Ultra|Samsung|129999; Galaxy S25|Samsung|80999; Galaxy Z Fold7|Samsung|174999;
Galaxy Z Flip7|Samsung|109999; Galaxy A56|Samsung|41999; Pixel 10 Pro|Google|109999; Pixel 10|Google|79999;
OnePlus 13|OnePlus|69999; Nothing Phone (3)|Nothing|79999; Xiaomi 15|Xiaomi|64999; Realme GT 7|Realme|39999""",
"Laptops": """MacBook Air 13 M4|Apple|99900; MacBook Air 15 M4|Apple|124900; MacBook Pro 14 M5|Apple|169900;
MacBook Pro 16 M4 Pro|Apple|249900; Dell XPS 14|Dell|179990; Dell Inspiron 14|Dell|64990; HP Spectre x360|HP|159990;
HP Pavilion 15|HP|62990; ThinkPad X1 Carbon|Lenovo|189990; Legion 5|Lenovo|109990; ROG Zephyrus G14|ASUS|169990;
Zenbook 14 OLED|ASUS|89990""",
"Tablets": """iPad Pro 13 M5|Apple|129900; iPad Air 11 M3|Apple|59900; iPad 11th Gen|Apple|34900; iPad mini|Apple|49900;
Galaxy Tab S10 Ultra|Samsung|108999; Galaxy Tab S10 FE|Samsung|38999; OnePlus Pad 3|OnePlus|47999;
Xiaomi Pad 7|Xiaomi|27999; Lenovo Tab P12|Lenovo|31999""",
"Audio": """AirPods Pro 3|Apple|24900; AirPods 4|Apple|12900; AirPods Max|Apple|59900; Sony WH-1000XM6|Sony|39990;
Sony WF-1000XM5|Sony|24990; Bose QuietComfort Ultra|Bose|35900; Galaxy Buds3 Pro|Samsung|17999;
Nothing Ear (a)|Nothing|7999; JBL Flip 7|JBL|11999; Marshall Emberton III|Marshall|17999; Sonos Ace|Sonos|39999;
boAt Airdopes 311 Pro|boAt|1299""",
"Wearables": """Apple Watch Series 11|Apple|46900; Apple Watch Ultra 3|Apple|89900; Apple Watch SE 3|Apple|25900;
Galaxy Watch8|Samsung|32999; Galaxy Ring|Samsung|38999; Pixel Watch 4|Google|39999; Garmin Forerunner 265|Garmin|42990;
Garmin Fenix 8|Garmin|99990; Fitbit Charge 6|Fitbit|14999; Amazfit Balance 2|Amazfit|24999""",
"Gaming": """PlayStation 5 Pro|Sony|59990; PlayStation 5 Slim|Sony|49990; Xbox Series X|Microsoft|52990;
Xbox Series S|Microsoft|34990; Nintendo Switch 2|Nintendo|44999; ROG Ally X|ASUS|89990; Meta Quest 3S|Meta|29990;
DualSense Controller|Sony|5990; G Pro X Superlight 2|Logitech|14995; BlackShark V2 Pro|Razer|17999""",
"Home": """LG C5 55 inch OLED|LG|139990; Samsung Crystal 4K 55 inch|Samsung|44990; Xiaomi FX Pro 43 inch|Xiaomi|28999;
Apple TV 4K|Apple|14900; Echo Dot|Amazon|5499; Echo Show 8|Amazon|14999; Nest Mini|Google|4499;
Dyson V15 Detect|Dyson|65900; Roborock Q Revo|Roborock|49999; Philips Air Fryer XXL|Philips|14995;
Dyson Airwrap|Dyson|45900; Kindle Paperwhite|Amazon|16999""",
"Cameras": """Sony A7 IV|Sony|239990; Canon EOS R50|Canon|74995; Nikon Z6 III|Nikon|219995; Fujifilm X-T50|Fujifilm|139999;
GoPro Hero 13 Black|GoPro|39990; DJI Osmo Pocket 3|DJI|49990; DJI Mini 4 Pro|DJI|78990; Insta360 X4|Insta360|49990;
Instax Mini 12|Fujifilm|7999""",
"Accessories": """Anker 737 Power Bank|Anker|8999; MagSafe Charger|Apple|4500; Apple Pencil Pro|Apple|11900;
Magic Keyboard|Apple|9900; Magic Mouse|Apple|9500; AirTag 4 pack|Apple|10900; MX Master 3S|Logitech|9995;
Samsung T7 SSD 1TB|Samsung|9999; SanDisk Extreme 1TB|SanDisk|8999; Keychron K2|Keychron|8999;
Dell UltraSharp 27 4K|Dell|45999""",
}
STORES = ["Amazon.in", "Flipkart", "Croma", "Reliance Digital"]


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
    create table if not exists products(id integer primary key, name text, brand text, cat text, price real, hist text);
    create table if not exists watches(user_id int, product_id int, target real, hit int default 0, primary key(user_id, product_id));
    create table if not exists notes(id integer primary key, user_id int, msg text, ts real, seen int default 0);
    create table if not exists offers(product_id int, store text, price real, url text, updated text, primary key(product_id, store));
    create table if not exists meta(k text primary key, v text);
    """)
    for col in ("real integer default 0", "image text", "url text", "mkey text", "hday text"):
        try:
            c.execute("alter table products add column " + col)
        except sqlite3.OperationalError:
            pass  # already there
    if not c.execute("select 1 from products").fetchone():
        rnd = random.Random(11)
        for cat, blob in CATALOG.items():
            for item in blob.split(";"):
                n, b, p = [x.strip() for x in item.split("|")]
                h = make_history(float(p), rnd)
                c.execute("insert into products(name,brand,cat,price,hist) values(?,?,?,?,?)",
                          (n, b, cat, h[-1], json.dumps(h)))
    c.commit()
    c.close()


def card(r):
    h = json.loads(r["hist"])
    prev = h[-2] if len(h) > 1 else r["price"]
    return dict(id=r["id"], name=r["name"], brand=r["brand"], cat=r["cat"], price=r["price"],
                day=round((r["price"] - prev) / prev * 100, 1), low=min(h), high=max(h),
                real=r["real"] or 0, image=r["image"])


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


@app.get("/api/products")
def products():
    c = db()
    rows = [card(r) for r in c.execute("select * from products")]
    c.close()
    return jsonify(rows)


@app.get("/api/products/<int:pid>")
def product(pid):
    c = db()
    r = c.execute("select * from products where id=?", (pid,)).fetchone()
    if not r:
        c.close()
        return jsonify(error="Product not found"), 404
    d = card(r)
    d["hist"] = json.loads(r["hist"])
    offers = c.execute("select store,price,url from offers where product_id=?", (pid,)).fetchall()
    if offers:
        d["stores"] = sorted([dict(name=o["store"], price=o["price"], url=o["url"]) for o in offers],
                             key=lambda x: x["price"])
    else:
        rnd = random.Random(pid)
        d["stores"] = sorted([dict(name=s, price=round(r["price"] * rnd.uniform(0.98, 1.05))) for s in STORES],
                             key=lambda x: x["price"])
    w = c.execute("select target from watches where user_id=? and product_id=?", (uid(), pid)).fetchone()
    d["watch"] = w["target"] if w else None
    c.close()
    return jsonify(d)


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
