import json
import os
import random
import sqlite3

from data import RECENT_PRODUCTS, REAL_STORE_PRICES, stores_for_product

BASE = os.path.dirname(os.path.abspath(__file__))
DB = os.path.join(BASE, "pricelens.db")


def db():
    """Open a SQLite connection with Row factory enabled."""
    c = sqlite3.connect(DB)
    c.row_factory = sqlite3.Row
    return c


def make_history(base, rnd):
    """Generate 365 days of synthetic price history ending near base price."""
    p = base * rnd.uniform(1.04, 1.12)
    out = []
    for _ in range(365):
        p += (base * 0.97 - p) * 0.02 + p * rnd.gauss(0, 0.006)
        if rnd.random() < 0.02:
            p *= 0.93
        out.append(round(p))
    return out


def init():
    """Initialize SQLite tables and seed/refresh verified products."""
    c = db()
    c.executescript("""
    create table if not exists products(id integer primary key, name text, brand text, cat text, price real, hist text, image text);
    create table if not exists offers(product_id int, store text, price real, url text, updated text, primary key(product_id, store));
    create table if not exists meta(k text primary key, v text);
    """)
    for col in ("real integer default 0", "image text", "url text", "mkey text", "hday text"):
        try:
            c.execute("alter table products add column " + col)
        except sqlite3.OperationalError:
            pass

    db_names = set(row[0] for row in c.execute("select name from products").fetchall())
    expected_names = set(p[0] for p in RECENT_PRODUCTS)
    p1 = c.execute("select price from products where name=?", ("Samsung Galaxy S25 Ultra",)).fetchone()
    needs_refresh = (db_names != expected_names) or (not p1) or (p1[0] != 86619)
    if needs_refresh:
        c.execute("delete from products")
        rnd = random.Random(42)
        for name, brand, cat, base_price, img in RECENT_PRODUCTS:
            p_stores = stores_for_product(name, cat)
            lowest = min((REAL_STORE_PRICES.get((name, s), base_price) for s in p_stores if REAL_STORE_PRICES.get((name, s), base_price) is not None), default=base_price)
            h = make_history(float(lowest), rnd)
            h[-1] = lowest
            c.execute(
                "insert into products(name,brand,cat,price,hist,image,real) values(?,?,?,?,?,?,1)",
                (name, brand, cat, lowest, json.dumps(h), img),
            )
    c.commit()
    c.close()


def offers_map(c, pid=None):
    """Return {product_id: {store: {price, url}}} from the offers table."""
    q = "select product_id, store, price, url from offers" + (" where product_id=?" if pid is not None else "")
    rows = c.execute(q, (pid,) if pid is not None else ()).fetchall()
    out = {}
    for o in rows:
        out.setdefault(o["product_id"], {})[o["store"]] = dict(price=o["price"], url=o["url"])
    return out


def fetch_products(real_only=False):
    """Fetch all products (or only real=1) along with their offers map."""
    c = db()
    omap = offers_map(c)
    sql = "select * from products" + (" where real=1" if real_only else "")
    rows = c.execute(sql).fetchall()
    c.close()
    return rows, omap


def fetch_product(pid):
    """Fetch a single product row and its offers map by product id."""
    c = db()
    r = c.execute("select * from products where id=?", (pid,)).fetchone()
    omap = offers_map(c, pid) if r else {}
    c.close()
    return r, omap


def fetch_product_meta(pid):
    """Fetch product name and category for redirect lookup."""
    c = db()
    r = c.execute("select name, cat from products where id=?", (pid,)).fetchone()
    c.close()
    return r


def fetch_status():
    """Fetch last_sync metadata and count of live products."""
    c = db()
    m = c.execute("select v from meta where k='last_sync'").fetchone()
    n = c.execute("select count(*) n from products where real=1").fetchone()["n"]
    c.close()
    return (m["v"] if m else None), n
