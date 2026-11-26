import initSqlJs from "sql.js";
import fs from "fs";
import path from "path";
import { fileURLToPath } from "url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const DB_PATH = path.join(__dirname, "pricelens.db");
const DATA_PATH = path.join(__dirname, "data", "products.json");

let db = null;

function saveDB() {
  if (!db) return;
  const data = db.export();
  fs.writeFileSync(DB_PATH, Buffer.from(data));
}

export async function initSQL() {
  const SQL = await initSqlJs();
  if (fs.existsSync(DB_PATH)) {
    const fileBuffer = fs.readFileSync(DB_PATH);
    db = new SQL.Database(fileBuffer);
  } else {
    db = new SQL.Database();
  }

  db.run(`
    CREATE TABLE IF NOT EXISTS products (
      id INTEGER PRIMARY KEY,
      name TEXT NOT NULL,
      brand TEXT NOT NULL,
      cat TEXT NOT NULL,
      price REAL NOT NULL,
      mrp REAL NOT NULL,
      lowest_store TEXT NOT NULL,
      lowest_price REAL NOT NULL,
      highest_store TEXT NOT NULL,
      highest_price REAL NOT NULL,
      savings REAL DEFAULT 0,
      savings_pct REAL DEFAULT 0,
      day REAL DEFAULT 0,
      low REAL NOT NULL,
      high REAL NOT NULL,
      real INTEGER DEFAULT 1,
      image TEXT NOT NULL,
      verified TEXT DEFAULT 'Real-Time Active',
      stores_json TEXT NOT NULL,
      hist_json TEXT NOT NULL
    );
  `);

  const seedProducts = JSON.parse(fs.readFileSync(DATA_PATH, "utf-8"));
  if (seedProducts.length > 0) {
    db.run("DELETE FROM products");
    const stmt = db.prepare(`
      INSERT INTO products (
        id, name, brand, cat, price, mrp, lowest_store, lowest_price,
        highest_store, highest_price, savings, savings_pct, day, low, high,
        real, image, verified, stores_json, hist_json
      ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    `);
    for (const p of seedProducts) {
      stmt.run([
        p.id,
        p.name,
        p.brand,
        p.cat,
        p.price,
        p.mrp,
        p.lowest_store,
        p.lowest_price,
        p.highest_store,
        p.highest_price,
        p.savings || 0,
        p.savings_pct || 0,
        p.day || 0,
        p.low,
        p.high,
        p.real ?? 1,
        p.image,
        p.verified || "Real-Time Active",
        JSON.stringify(p.stores || []),
        JSON.stringify(p.hist || []),
      ]);
    }
    stmt.free();
    saveDB();
    console.log(`[PriceLens SQL] Synced ${seedProducts.length} products into SQLite.`);
  }
}

function rowToProduct(row, includeHist = false) {
  const obj = {
    id: row.id,
    name: row.name,
    brand: row.brand,
    cat: row.cat,
    price: row.price,
    mrp: row.mrp,
    lowest_store: row.lowest_store,
    lowest_price: row.lowest_price,
    highest_store: row.highest_store,
    highest_price: row.highest_price,
    savings: row.savings,
    savings_pct: row.savings_pct,
    day: row.day,
    low: row.low,
    high: row.high,
    real: row.real,
    image: row.image,
    verified: row.verified,
    stores: JSON.parse(row.stores_json),
  };
  if (includeHist) obj.hist = JSON.parse(row.hist_json);
  return obj;
}

export function getAllProducts() {
  const stmt = db.prepare("SELECT * FROM products ORDER BY id ASC");
  const out = [];
  while (stmt.step()) {
    out.push(rowToProduct(stmt.getAsObject(), false));
  }
  stmt.free();
  return out;
}

export function getProductById(pid) {
  const stmt = db.prepare("SELECT * FROM products WHERE id = ?");
  stmt.bind([Number(pid)]);
  let item = null;
  if (stmt.step()) {
    item = rowToProduct(stmt.getAsObject(), true);
  }
  stmt.free();
  return item;
}

export function getProductCount() {
  const res = db.exec("SELECT COUNT(*) AS cnt FROM products");
  return res[0]?.values[0][0] || 0;
}
