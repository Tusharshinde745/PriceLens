import initSqlJs from "sql.js";
import fs from "fs";
import path from "path";
import { fileURLToPath } from "url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const DB_PATH = path.join(__dirname, "pricelens.db");
const DATA_PATH = path.join(__dirname, "data", "products.json");
let db = null;

export async function initSQL() {
  const SQL = await initSqlJs();
  db = fs.existsSync(DB_PATH) ? new SQL.Database(fs.readFileSync(DB_PATH)) : new SQL.Database();
  db.run(`CREATE TABLE IF NOT EXISTS products (
    id INTEGER PRIMARY KEY, name TEXT NOT NULL, brand TEXT NOT NULL, cat TEXT NOT NULL,
    price REAL NOT NULL, mrp REAL NOT NULL, lowest_store TEXT NOT NULL, lowest_price REAL NOT NULL,
    highest_store TEXT NOT NULL, highest_price REAL NOT NULL, savings REAL DEFAULT 0,
    savings_pct REAL DEFAULT 0, day REAL DEFAULT 0, low REAL NOT NULL, high REAL NOT NULL,
    real INTEGER DEFAULT 1, image TEXT NOT NULL, verified TEXT DEFAULT 'Real-Time Active',
    stores_json TEXT NOT NULL, hist_json TEXT NOT NULL
  );`);

  const seed = JSON.parse(fs.readFileSync(DATA_PATH, "utf-8"));
  if (seed.length) {
    db.run("DELETE FROM products");
    const stmt = db.prepare(`INSERT INTO products VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)`);
    for (const p of seed) {
      stmt.run([
        p.id, p.name, p.brand, p.cat, p.price, p.mrp, p.lowest_store, p.lowest_price,
        p.highest_store, p.highest_price, p.savings || 0, p.savings_pct || 0, p.day || 0,
        p.low, p.high, p.real ?? 1, p.image, p.verified || "Real-Time Active",
        JSON.stringify(p.stores || []), JSON.stringify(p.hist || []),
      ]);
    }
    stmt.free();
    fs.writeFileSync(DB_PATH, Buffer.from(db.export()));
  }
}

const mapRow = (r, withHist) => {
  const { stores_json, hist_json, ...rest } = r;
  return { ...rest, stores: JSON.parse(stores_json), ...(withHist ? { hist: JSON.parse(hist_json) } : {}) };
};

export function getAllProducts() {
  const stmt = db.prepare("SELECT * FROM products ORDER BY id ASC"), out = [];
  while (stmt.step()) out.push(mapRow(stmt.getAsObject(), false));
  stmt.free();
  return out;
}

export function getProductById(pid) {
  const stmt = db.prepare("SELECT * FROM products WHERE id = ?");
  stmt.bind([Number(pid)]);
  const item = stmt.step() ? mapRow(stmt.getAsObject(), true) : null;
  stmt.free();
  return item;
}

export const getProductCount = () => db.exec("SELECT COUNT(*) AS cnt FROM products")[0]?.values[0][0] || 0;
