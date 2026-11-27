import initSqlJs from "sql.js";
import fs from "fs";
import path from "path";
import { fileURLToPath } from "url";

const dir = path.dirname(fileURLToPath(import.meta.url));
const DB_PATH = path.join(dir, "pricelens.db"), DATA_PATH = path.join(dir, "data", "products.json");
let db = null;

export async function initSQL() {
  const SQL = await initSqlJs();
  db = fs.existsSync(DB_PATH) ? new SQL.Database(fs.readFileSync(DB_PATH)) : new SQL.Database();
  db.run("CREATE TABLE IF NOT EXISTS products (id INTEGER PRIMARY KEY, name TEXT NOT NULL, brand TEXT NOT NULL, cat TEXT NOT NULL, price REAL NOT NULL, mrp REAL NOT NULL, lowest_store TEXT NOT NULL, lowest_price REAL NOT NULL, highest_store TEXT NOT NULL, highest_price REAL NOT NULL, savings REAL DEFAULT 0, savings_pct REAL DEFAULT 0, day REAL DEFAULT 0, low REAL NOT NULL, high REAL NOT NULL, real INTEGER DEFAULT 1, image TEXT NOT NULL, verified TEXT DEFAULT 'Real-Time Active', stores_json TEXT NOT NULL, hist_json TEXT NOT NULL);");
  const seed = JSON.parse(fs.readFileSync(DATA_PATH, "utf-8"));
  if (seed.length) {
    db.run("DELETE FROM products");
    const stmt = db.prepare("INSERT INTO products VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)");
    for (const p of seed) stmt.run([p.id, p.name, p.brand, p.cat, p.price, p.mrp, p.lowest_store, p.lowest_price, p.highest_store, p.highest_price, p.savings || 0, p.savings_pct || 0, p.day || 0, p.low, p.high, p.real ?? 1, p.image, p.verified || "Real-Time Active", JSON.stringify(p.stores || []), JSON.stringify(p.hist || [])]);
    stmt.free();
    fs.writeFileSync(DB_PATH, Buffer.from(db.export()));
  }
}

const mapRow = ({ stores_json, hist_json, ...rest }, withHist) => ({ ...rest, stores: JSON.parse(stores_json), ...(withHist ? { hist: JSON.parse(hist_json) } : {}) });
export const getAllProducts = () => { const s = db.prepare("SELECT * FROM products ORDER BY id ASC"), out = []; while (s.step()) out.push(mapRow(s.getAsObject(), false)); s.free(); return out; };
export const getProductById = (id) => { const s = db.prepare("SELECT * FROM products WHERE id = ?"); s.bind([Number(id)]); const r = s.step() ? mapRow(s.getAsObject(), true) : null; s.free(); return r; };
export const getProductCount = () => db.exec("SELECT COUNT(*) FROM products")[0]?.values[0][0] || 0;
