import { useEffect, useMemo, useRef, useState } from "react";

const inr = (n) => "₹" + Math.round(n).toLocaleString("en-IN");
const FALLBACK_IMG =
  "https://images.unsplash.com/photo-1526738549149-8e07eca6c147?w=600&auto=format&fit=crop&q=80";

function dotClassFor(name) {
  const sk = name.toLowerCase();
  if (sk.includes("amazon")) return "store-dot-amazon";
  if (sk.includes("flipkart")) return "store-dot-flipkart";
  if (sk.includes("croma")) return "store-dot-croma";
  if (sk.includes("nykaa")) return "store-dot-nykaa";
  if (sk.includes("tira")) return "store-dot-tira";
  return "store-dot-reliance";
}

function PriceChart({ hist, range, low, high }) {
  const [hoverIdx, setHoverIdx] = useState(null);
  const svgRef = useRef(null);

  const d = useMemo(() => (hist || []).slice(-range), [hist, range]);
  if (d.length < 2) {
    return (
      <div style={{ padding: 24, textAlign: "center", color: "var(--text-muted)" }}>
        Price history chart recording.
      </div>
    );
  }

  const W = 660, H = 230, L = 68, R = 16, T = 18, B = 34;
  const mn = Math.min(...d), mx = Math.max(...d);
  const x = (i) => L + (i * (W - L - R)) / (d.length - 1);
  const y = (v) => H - B - ((v - mn) / (mx - mn || 1)) * (H - T - B);
  const line = d.map((v, i) => `${i ? "L" : "M"}${x(i).toFixed(1)} ${y(v).toFixed(1)}`).join("");
  const fmt = (i) =>
    new Date(Date.now() - (d.length - 1 - i) * 864e5).toLocaleDateString("en-IN", {
      day: "numeric",
      month: "short",
      year: "2-digit",
    });
  const li = d.indexOf(mn);
  const mid = (mn + mx) / 2;

  const handleMove = (e) => {
    if (!svgRef.current) return;
    const r = svgRef.current.getBoundingClientRect();
    const clientX = e.touches ? e.touches[0].clientX : e.clientX;
    const px = ((clientX - r.left) * W) / r.width;
    const i = Math.max(0, Math.min(d.length - 1, Math.round(((px - L) / (W - L - R)) * (d.length - 1))));
    setHoverIdx(i);
  };

  return (
    <>
      <svg
        ref={svgRef}
        className="chart"
        viewBox={`0 0 ${W} ${H}`}
        role="img"
        aria-label="Price history chart"
        onMouseMove={handleMove}
        onTouchMove={handleMove}
        onMouseLeave={() => setHoverIdx(null)}
      >
        <defs>
          <linearGradient id="chartGrad" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="#4f46e5" stopOpacity="0.16" />
            <stop offset="100%" stopColor="#4f46e5" stopOpacity="0.00" />
          </linearGradient>
        </defs>
        {[mn, mid, mx].map((v, idx) => (
          <g key={idx}>
            <line x1={L} x2={W - R} y1={y(v)} y2={y(v)} stroke="#e2e8f0" strokeDasharray="3 4" />
            <text x={L - 8} y={y(v) + 4} textAnchor="end" fontSize="11" fontWeight="600" fill="#64748b">
              {inr(v)}
            </text>
          </g>
        ))}
        <path d={`${line}L${x(d.length - 1)} ${H - B}L${L} ${H - B}Z`} fill="url(#chartGrad)" />
        <path d={line} fill="none" stroke="#4f46e5" strokeWidth="2.5" strokeLinejoin="round" strokeLinecap="round" />
        <circle cx={x(li)} cy={y(mn)} r="5" fill="#059669" stroke="#ffffff" strokeWidth="2" />
        <text
          x={Math.min(Math.max(x(li), L + 28), W - R - 28)}
          y={y(mn) - 10}
          textAnchor="middle"
          fontSize="11"
          fontWeight="700"
          fill="#059669"
        >
          Lowest: {inr(mn)}
        </text>
        <text x={L} y={H - 10} fontSize="11" fontWeight="600" fill="#64748b">
          {fmt(0)}
        </text>
        <text x={W - R} y={H - 10} textAnchor="end" fontSize="11" fontWeight="600" fill="#64748b">
          {fmt(d.length - 1)}
        </text>
        {hoverIdx !== null && (
          <>
            <line x1={x(hoverIdx)} x2={x(hoverIdx)} y1={T} y2={H - B} stroke="#4f46e5" strokeWidth="1.5" strokeDasharray="2 2" />
            <circle cx={x(hoverIdx)} cy={y(d[hoverIdx])} r="4.5" fill="#4f46e5" />
          </>
        )}
      </svg>
      <div className="chart-tooltip">
        {hoverIdx !== null
          ? `${fmt(hoverIdx)}: ${inr(d[hoverIdx])}`
          : `Hover to inspect price movement • Year Low: ${inr(low)} • High: ${inr(high)}`}
      </div>
    </>
  );
}

export default function App() {
  const [products, setProducts] = useState([]);
  const [cat, setCat] = useState("All");
  const [q, setQ] = useState("");
  const [storeFilter, setStoreFilter] = useState("");
  const [sortv, setSortv] = useState("");
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [clock, setClock] = useState("Loading…");
  const [modalProduct, setModalProduct] = useState(null);
  const [range, setRange] = useState(365);
  const searchInputRef = useRef(null);

  const loadProducts = async () => {
    try {
      const res = await fetch("/api/products");
      const data = await res.json();
      if (Array.isArray(data)) setProducts(data);
    } catch {}
  };

  useEffect(() => {
    loadProducts();
    const updateClock = () =>
      setClock("Last synced at " + new Date().toLocaleTimeString("en-IN", { hour: "2-digit", minute: "2-digit", second: "2-digit" }));
    updateClock();
    const t1 = setInterval(loadProducts, 15000);
    const t2 = setInterval(updateClock, 1000);
    return () => {
      clearInterval(t1);
      clearInterval(t2);
    };
  }, []);

  useEffect(() => {
    const onKey = (e) => {
      if (e.key === "/" && e.target.tagName !== "INPUT" && e.target.tagName !== "TEXTAREA") {
        e.preventDefault();
        searchInputRef.current?.focus();
      }
      if (e.key === "Escape") {
        setDrawerOpen(false);
        setModalProduct(null);
      }
    };
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, []);

  const cats = useMemo(() => ["All", ...new Set(products.map((p) => p.cat))], [products]);

  const filtered = useMemo(() => {
    const query = q.trim().toLowerCase();
    let list = products.filter((p) => {
      const matchCat = cat === "All" || p.cat === cat;
      const matchQ = !query || `${p.name} ${p.brand} ${p.cat}`.toLowerCase().includes(query);
      const matchStore = !storeFilter || p.lowest_store === storeFilter;
      return matchCat && matchQ && matchStore;
    });
    if (sortv === "savings") list = [...list].sort((a, b) => b.savings - a.savings);
    else if (sortv === "lo") list = [...list].sort((a, b) => a.price - b.price);
    else if (sortv === "hi") list = [...list].sort((a, b) => b.price - a.price);
    else if (sortv === "drop") list = [...list].sort((a, b) => a.day - b.day);
    return list;
  }, [products, cat, q, storeFilter, sortv]);

  const openProduct = async (id) => {
    try {
      const res = await fetch(`/api/products/${id}`);
      const data = await res.json();
      setModalProduct(data);
    } catch {}
  };

  const resetFilters = () => {
    setCat("All");
    setQ("");
    setStoreFilter("");
    setSortv("");
  };

  return (
    <>
      <div className="orb orb-1" />
      <div className="orb orb-2" />
      <div className="orb orb-3" />

      <div className="live-strip">
        <div className="live-strip-inner">
          <div className="live-indicator">
            <span className="live-beacon" />
            <span>Live Real-Time Pricing</span>
          </div>
          <div className="live-sync-info">
            <span>Amazon.in</span>
            <span className="live-sep">•</span>
            <span>Flipkart</span>
            <span className="live-sep">•</span>
            <span>Croma</span>
            <span className="live-sep">•</span>
            <span>Reliance Digital</span>
            <span className="live-sep">•</span>
            <span className="live-clock">{clock}</span>
          </div>
        </div>
      </div>

      <header>
        <div className="header-left">
          <button className="menu-trigger" onClick={() => setDrawerOpen(true)} aria-label="Open categories menu">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round">
              <line x1="3" y1="6" x2="21" y2="6" />
              <line x1="3" y1="12" x2="21" y2="12" />
              <line x1="3" y1="18" x2="21" y2="18" />
            </svg>
            <span>Categories</span>
          </button>
          <a
            href="#"
            className="brand"
            onClick={(e) => {
              e.preventDefault();
              setCat("All");
              window.scrollTo({ top: 0, behavior: "smooth" });
            }}
          >
            <div className="brand-icon">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#ffffff" strokeWidth="2.5" strokeLinecap="round">
                <circle cx="11" cy="11" r="7" />
                <path d="M21 21l-4.35-4.35" />
              </svg>
            </div>
            <span className="brand-name">PriceLens</span>
            <span className="brand-badge">INDIA</span>
          </a>
        </div>
        <div className="header-right" />
      </header>

      <div className={`drawer-scrim ${drawerOpen ? "open" : ""}`} onClick={() => setDrawerOpen(false)} />
      <aside className={`drawer ${drawerOpen ? "open" : ""}`} role="dialog" aria-label="Categories Navigation">
        <div className="drawer-header">
          <span className="drawer-heading">Browse Categories</span>
          <button className="drawer-close" onClick={() => setDrawerOpen(false)} aria-label="Close menu">
            &times;
          </button>
        </div>
        <div className="drawer-body">
          <div className="drawer-section-title">Categories</div>
          <div>
            {cats.map((c) => {
              const cnt = c === "All" ? products.length : products.filter((p) => p.cat === c).length;
              return (
                <button
                  key={c}
                  className={`cat-item-btn ${c === cat ? "active" : ""}`}
                  onClick={() => {
                    setCat(c);
                    setDrawerOpen(false);
                    document.getElementById("shop")?.scrollIntoView({ behavior: "smooth" });
                  }}
                >
                  <span>{c === "All" ? "All Categories" : c}</span>
                  <span className="cat-count">{cnt}</span>
                </button>
              );
            })}
          </div>
          <div className="drawer-card">
            <div className="drawer-card-title">
              <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="#00d4aa" strokeWidth="2.5">
                <polyline points="20 6 9 17 4 12" />
              </svg>
              <span>Verified 4-Store Availability</span>
            </div>
            <p style={{ color: "var(--text-muted)", fontSize: 12, marginTop: 4 }}>
              Every product is verified across India's top 4 retailers:
            </p>
            <div className="store-tags">
              <span className="store-tag">Amazon.in</span>
              <span className="store-tag">Flipkart</span>
              <span className="store-tag">Croma</span>
              <span className="store-tag">Reliance Digital</span>
            </div>
          </div>
        </div>
      </aside>

      <main>
        <section className="hero">
          <div className="hero-eyebrow">
            <span className="eyebrow-dot" />
            Verified Recent Launches • Direct Product Links
          </div>
          <h1>
            Compare prices across
            <br />
            <span className="gradient-text">all 4 major stores.</span>
          </h1>
          <p>
            Track live prices, 1-year history & price differences on newly launched tech, appliances & grooming gadgets — across Amazon, Flipkart, Croma & Reliance Digital.
          </p>

          <form
            className="search-wrap"
            onSubmit={(e) => {
              e.preventDefault();
              document.getElementById("shop")?.scrollIntoView({ behavior: "smooth" });
            }}
          >
            <div className="search-box">
              <div className="search-icon">
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.3" strokeLinecap="round">
                  <circle cx="11" cy="11" r="7" />
                  <path d="M21 21l-4.35-4.35" />
                </svg>
              </div>
              <input
                ref={searchInputRef}
                value={q}
                onChange={(e) => setQ(e.target.value)}
                placeholder="Search S25 Ultra, MacBook M5, MacBook Neo, PS5… (Press '/' to search)"
                aria-label="Search products"
              />
              {q && (
                <button
                  type="button"
                  className="search-clear-btn"
                  aria-label="Clear search"
                  onClick={() => {
                    setQ("");
                    searchInputRef.current?.focus();
                  }}
                >
                  &times;
                </button>
              )}
              <button type="submit" className="search-submit-btn">
                Search
              </button>
            </div>
          </form>

          <div className="trending-tags">
            <span className="trending-label">Trending:</span>
            {["S25 Ultra", "iPhone 16", "MacBook M5", "MacBook Neo", "AirPods", "Dyson"].map((term) => (
              <button
                key={term}
                type="button"
                className="trend-tag"
                onClick={() => {
                  setQ(term);
                  document.getElementById("shop")?.scrollIntoView({ behavior: "smooth" });
                }}
              >
                {term}
              </button>
            ))}
          </div>

          <div className="quick-cats">
            {cats.map((c) => (
              <button key={c} className={`cat-chip ${c === cat ? "active" : ""}`} onClick={() => setCat(c)}>
                {c === "All" ? "All Gadgets" : c}
              </button>
            ))}
          </div>

          <div className="hero-stats">
            <div className="hero-stat-item">
              <div className="hero-stat-value">{products.length}</div>
              <div className="hero-stat-desc">Recent Flagships</div>
            </div>
            <div className="hero-stat-item">
              <div className="hero-stat-value">4 Top Stores</div>
              <div className="hero-stat-desc">Amazon • Flipkart • Croma • Reliance</div>
            </div>
            <div className="hero-stat-item">
              <div className="hero-stat-value">Save up to 15%</div>
              <div className="hero-stat-desc">Real-Time Price Differences</div>
            </div>
            <div className="hero-stat-item">
              <div className="hero-stat-value">MERN Stack</div>
              <div className="hero-stat-desc">MongoDB • Express • React • Node</div>
            </div>
          </div>
        </section>

        <section id="shop">
          <div className="controls-row">
            <div className="section-label">
              {cat === "All" ? "All Products" : cat} <span>({filtered.length} items)</span>
            </div>
            <div className="filters-wrap">
              <div className="filter-item">
                <label htmlFor="storeFilter" className="filter-lbl">
                  Cheapest on:
                </label>
                <select className="sort-select" id="storeFilter" value={storeFilter} onChange={(e) => setStoreFilter(e.target.value)}>
                  <option value="">All Stores</option>
                  <option value="Amazon.in">Amazon.in</option>
                  <option value="Flipkart">Flipkart</option>
                  <option value="Croma">Croma</option>
                  <option value="Reliance Digital">Reliance Digital</option>
                  <option value="Nykaa">Nykaa</option>
                  <option value="Tira">Tira</option>
                </select>
              </div>
              <div className="filter-item">
                <label htmlFor="sort" className="filter-lbl">
                  Sort:
                </label>
                <select className="sort-select" id="sort" value={sortv} onChange={(e) => setSortv(e.target.value)}>
                  <option value="">Featured</option>
                  <option value="savings">Biggest Savings (₹)</option>
                  <option value="lo">Price: Low to High</option>
                  <option value="hi">Price: High to Low</option>
                  <option value="drop">Biggest Price Drop</option>
                </select>
              </div>
            </div>
          </div>

          <div className="grid">
            {!filtered.length ? (
              <div className="empty-state">
                <div className="empty-icon">🔍</div>
                <h3>No products found</h3>
                <p>No products match "{q || storeFilter}". Try a broader search term or reset filters.</p>
                <button className="reset-filter-btn" onClick={resetFilters}>
                  View All Products
                </button>
              </div>
            ) : (
              filtered.map((p) => (
                <div className="card" key={p.id}>
                  <div className="card-img-wrap">
                    <span className="card-badge">
                      <span className="badge-dot">●</span> Live
                    </span>
                    {p.savings > 0 && <span className="card-savings-badge">Save {inr(p.savings)}</span>}
                    <img
                      src={p.image}
                      alt={p.name}
                      loading="lazy"
                      onError={(e) => {
                        e.currentTarget.onerror = null;
                        e.currentTarget.src = FALLBACK_IMG;
                      }}
                    />
                  </div>
                  <div className="card-body">
                    <div className="card-meta">
                      {p.brand} &nbsp;•&nbsp; {p.cat}
                    </div>
                    <div className="card-title">{p.name}</div>
                    <div className="price-container">
                      <div className="price-stack">
                        <span className="card-price">{inr(p.lowest_price || p.price)}</span>
                        <span className="price-lowest-label">↓ Lowest on {(p.lowest_store || "").replace(".in", "")}</span>
                      </div>
                      <span className="card-low" title="52-Week lowest price">
                        52W Low {inr(p.low)}
                      </span>
                    </div>
                    <div className="store-actions">
                      <div className="store-actions-label">
                        <span>Live Store Prices</span>
                        <span className="lowest-pill-mini">Lowest highlighted</span>
                      </div>
                      <div className="store-links-grid">
                        {p.stores.map((s) =>
                          !s.available || s.price === null ? (
                            <div key={s.name} className="store-link-btn is-unavailable" title={`${s.name} — Currently not available`}>
                              <div className="store-btn-header">
                                <span className="store-btn-name">
                                  <span className={`store-color-dot ${dotClassFor(s.name)}`} />
                                  {s.name.replace(".in", "")}
                                </span>
                              </div>
                              <div className="store-btn-price" style={{ color: "var(--text-subtle)", fontSize: 11, fontWeight: 600 }}>
                                Not Available
                              </div>
                            </div>
                          ) : (
                            <a
                              key={s.name}
                              href={s.url}
                              target="_blank"
                              rel="noopener noreferrer"
                              className={`store-link-btn ${s.is_lowest ? "is-lowest" : ""}`}
                              title={s.is_lowest ? `Lowest price — Buy on ${s.name}` : `Buy on ${s.name}`}
                            >
                              <div className="store-btn-header">
                                <span className="store-btn-name">
                                  <span className={`store-color-dot ${dotClassFor(s.name)}`} />
                                  {s.name.replace(".in", "")}
                                </span>
                                {s.is_lowest && <span className="lowest-badge-pill">Lowest</span>}
                              </div>
                              <div className="store-btn-price">{inr(s.price)} ↗</div>
                            </a>
                          )
                        )}
                      </div>
                      <button className="detail-view-btn" onClick={() => openProduct(p.id)}>
                        Price History &amp; Details →
                      </button>
                    </div>
                  </div>
                </div>
              ))
            )}
          </div>
        </section>
      </main>

      <footer>
        PriceLens &nbsp;•&nbsp; MERN Stack (MongoDB, Express, React, Node.js) • Comparing live gadget prices across Amazon.in, Flipkart, Croma, and Reliance Digital.
      </footer>

      {modalProduct && (
        <div
          className="modal-scrim open"
          onClick={(e) => {
            if (e.target.classList.contains("modal-scrim")) setModalProduct(null);
          }}
        >
          <div className="modal-card" role="dialog" aria-modal="true">
            <button className="modal-close-btn" aria-label="Close" onClick={() => setModalProduct(null)}>
              &times;
            </button>
            <div className="modal-header-row">
              <img
                src={modalProduct.image}
                alt={modalProduct.name}
                className="modal-thumb"
                onError={(e) => {
                  e.currentTarget.onerror = null;
                  e.currentTarget.src = FALLBACK_IMG;
                }}
              />
              <div>
                <span style={{ fontSize: 10, fontWeight: 800, color: "var(--text-subtle)", textTransform: "uppercase", letterSpacing: "0.08em" }}>
                  Launched in Last 6 Months
                </span>
                <h2 className="modal-title">{modalProduct.name}</h2>
                <div className="modal-meta">
                  {modalProduct.brand} &nbsp;•&nbsp; {modalProduct.cat}
                </div>
                <div style={{ display: "flex", alignItems: "baseline", gap: 10, marginTop: 6 }}>
                  <div className="modal-price">{inr(modalProduct.lowest_price || modalProduct.price)}</div>
                  <span className="lowest-pill-mini">Lowest on {(modalProduct.lowest_store || "").replace(".in", "")}</span>
                </div>
              </div>
            </div>

            {modalProduct.savings > 0 && (
              <div className="modal-savings-callout">
                <span className="savings-icon">💡</span>
                <div>
                  <b>
                    Save {inr(modalProduct.savings)} ({modalProduct.savings_pct}% cheaper):
                  </b>{" "}
                  Buy on <b>{(modalProduct.lowest_store || "").replace(".in", "")}</b> instead of{" "}
                  {(modalProduct.highest_store || "").replace(".in", "")} ({inr(modalProduct.highest_price)}).
                </div>
              </div>
            )}

            <div className="modal-stores-heading">Live Store Prices — Click to Buy Directly:</div>
            <div className="modal-stores-grid">
              {modalProduct.stores.map((s, i) => {
                if (!s.available || s.price === null) {
                  return (
                    <div key={s.name} className="store-card is-unavailable">
                      <div className="store-top-line">
                        <span>
                          <span className={`store-color-dot ${dotClassFor(s.name)}`} style={{ display: "inline-block", marginRight: 6 }} />
                          {s.name.replace(".in", "")}
                        </span>
                      </div>
                      <div className="store-card-price" style={{ color: "var(--text-subtle)", fontSize: 13 }}>
                        Not Available
                      </div>
                      <div className="store-card-cta" style={{ color: "var(--text-subtle)" }}>
                        Unavailable
                      </div>
                    </div>
                  );
                }
                const diffFromLowest = s.price - (modalProduct.lowest_price || modalProduct.price);
                return (
                  <a
                    key={s.name}
                    href={s.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className={`store-card ${s.is_lowest || i === 0 ? "best" : ""}`}
                  >
                    <div className="store-top-line">
                      <span>
                        <span className={`store-color-dot ${dotClassFor(s.name)}`} style={{ display: "inline-block", marginRight: 6 }} />
                        {s.name.replace(".in", "")}
                      </span>
                      {s.is_lowest || i === 0 ? (
                        <span className="best-pill">Lowest</span>
                      ) : (
                        diffFromLowest > 0 && <span style={{ fontSize: 10, color: "var(--text-subtle)", fontWeight: 600 }}>+{inr(diffFromLowest)}</span>
                      )}
                    </div>
                    <div className="store-card-price">{inr(s.price)}</div>
                    <div className="store-card-cta">Buy on {s.name.replace(".in", "")} ↗</div>
                  </a>
                );
              })}
            </div>

            <div className="range-pills">
              {[
                [30, "1 Month"],
                [90, "3 Months"],
                [180, "6 Months"],
                [365, "1 Year"],
              ].map(([n, l]) => (
                <button key={n} className={`range-btn ${range === n ? "active" : ""}`} onClick={() => setRange(n)}>
                  {l}
                </button>
              ))}
            </div>
            <PriceChart hist={modalProduct.hist} range={range} low={modalProduct.low} high={modalProduct.high} />
          </div>
        </div>
      )}
    </>
  );
}
