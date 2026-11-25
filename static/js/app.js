const $=s=>document.querySelector(s), inr=n=>'₹'+Math.round(n).toLocaleString('en-IN');
let P=[], cat='All', me=null, cur=null, mode='login', lastUnseen=0, openId=null, sortv='';

async function api(u,o={}){
  const r=await fetch(u,{method:o.method||'GET',headers:{'Content-Type':'application/json'},body:o.body?JSON.stringify(o.body):undefined});
  const j=await r.json().catch(()=>({}));
  if(!r.ok)throw Object.assign(new Error(j.error||'Something went wrong'),{status:r.status});
  return j;
}

function toast(t){
  const e=$('#toast');e.textContent=t;e.classList.add('show');
  clearTimeout(toast.t);toast.t=setTimeout(()=>e.classList.remove('show'),3500);
}

/* ── Drawer ── */
function toggleDrawer(open){
  const d=$('#drawer'), s=$('#drawerScrim');
  if(open){d.classList.add('open');s.classList.add('open')}
  else{d.classList.remove('open');s.classList.remove('open')}
}
$('#menuBtn').addEventListener('click',()=>toggleDrawer(true));
$('#drawerClose').addEventListener('click',()=>toggleDrawer(false));
$('#drawerScrim').addEventListener('click',()=>toggleDrawer(false));
$('#logoLink').addEventListener('click',e=>{e.preventDefault();cat='All';renderFilterState();drawGrid();window.scrollTo({top:0,behavior:'smooth'})});

function renderFilterState(){
  const cats=['All',...new Set(P.map(p=>p.cat))];
  const heroCountEl=$('#heroProductCount');
  if(heroCountEl) heroCountEl.textContent=P.length;

  $('#drawerCats').innerHTML=cats.map(c=>{
    const cnt=c==='All'?P.length:P.filter(p=>p.cat===c).length;
    return `<button class="cat-item-btn ${c===cat?'active':''}" data-c="${c}">
      <span>${c==='All'?'All Categories':c}</span>
      <span class="cat-count">${cnt}</span>
    </button>`;
  }).join('');

  $('#quickChips').innerHTML=cats.map(c=>`
    <button class="cat-chip ${c===cat?'active':''}" data-c="${c}">${c==='All'?'All Gadgets':c}</button>
  `).join('');
}

function selectCategory(c){cat=c;renderFilterState();drawGrid();toggleDrawer(false);}

$('#drawerCats').addEventListener('click',e=>{
  const b=e.target.closest('.cat-item-btn');
  if(b){selectCategory(b.dataset.c);$('#shop').scrollIntoView({behavior:'smooth'})}
});
$('#quickChips').addEventListener('click',e=>{
  const b=e.target.closest('.cat-chip');
  if(b) selectCategory(b.dataset.c);
});

/* ── Grid & Filtering ── */
let storeFilterVal='';

function applySearch(query){
  $('#q').value=query;
  $('#clearSearch').hidden=false;
  drawGrid();
  $('#shop').scrollIntoView({behavior:'smooth'});
}

function resetFilters(){
  cat='All';$('#q').value='';$('#clearSearch').hidden=true;
  storeFilterVal='';sortv='';$('#storeFilter').value='';$('#sort').value='';
  renderFilterState();drawGrid();
}

function drawGrid(){
  const q=$('#q').value.trim().toLowerCase();
  const clearBtn=$('#clearSearch');
  if(clearBtn) clearBtn.hidden=!q;

  let L=P.filter(p=>{
    const matchCat=(cat==='All'||p.cat===cat);
    const matchQ=(!q||(p.name+' '+p.brand+' '+p.cat).toLowerCase().includes(q));
    const matchStore=(!storeFilterVal||p.lowest_store===storeFilterVal);
    return matchCat&&matchQ&&matchStore;
  });

  if(sortv==='savings') L.sort((a,b)=>b.savings-a.savings);
  else if(sortv==='lo') L.sort((a,b)=>a.price-b.price);
  else if(sortv==='hi') L.sort((a,b)=>b.price-a.price);
  else if(sortv==='drop') L.sort((a,b)=>a.day-b.day);

  $('#catLabel').innerHTML=`${cat==='All'?'All Products':cat} <span id="countLabel">(${L.length} items)</span>`;

  if(!L.length){
    $('#grid').innerHTML=`
      <div class="empty-state">
        <div class="empty-icon">🔍</div>
        <h3>No products found</h3>
        <p>No products match "${q||storeFilterVal}". Try a broader search term or reset filters.</p>
        <button class="reset-filter-btn" onclick="resetFilters()">View All Products</button>
      </div>`;
    return;
  }

  $('#grid').innerHTML=L.map(p=>`
    <div class="card" data-id="${p.id}">
      <div class="card-img-wrap">
        <span class="card-badge"><span class="badge-dot">●</span> Live</span>
        ${p.savings>0?`<span class="card-savings-badge">Save ${inr(p.savings)}</span>`:''}
        <img src="${p.image}" alt="${p.name}" loading="lazy" onerror="this.onerror=null;this.src='https://images.unsplash.com/photo-1526738549149-8e07eca6c147?w=600&auto=format&fit=crop&q=80'">
      </div>
      <div class="card-body">
        <div class="card-meta">${p.brand} &nbsp;•&nbsp; ${p.cat}</div>
        <div class="card-title">${p.name}</div>
        <div class="price-container">
          <div class="price-stack">
            <span class="card-price">${inr(p.lowest_price||p.price)}</span>
            <span class="price-lowest-label">↓ Lowest on ${(p.lowest_store||'').replace('.in','')}</span>
          </div>
          <span class="card-low" title="52-Week lowest price">52W Low ${inr(p.low)}</span>
        </div>
        <div class="store-actions">
          <div class="store-actions-label">
            <span>Live Store Prices</span>
            <span class="lowest-pill-mini">Lowest highlighted</span>
          </div>
          <div class="store-links-grid">
            ${p.stores.map(s=>{
              const sk=s.name.toLowerCase();
              const dotClass=sk.includes('amazon')?'store-dot-amazon':sk.includes('flipkart')?'store-dot-flipkart':sk.includes('croma')?'store-dot-croma':'store-dot-reliance';
              return `
              <a href="${s.url}" target="_blank" rel="noopener noreferrer" class="store-link-btn ${s.is_lowest?'is-lowest':''}" title="${s.is_lowest?'Lowest price — Buy on '+s.name:'Buy on '+s.name}">
                <div class="store-btn-header">
                  <span class="store-btn-name">
                    <span class="store-color-dot ${dotClass}"></span>
                    ${s.name.replace('.in','')}
                  </span>
                  ${s.is_lowest?'<span class="lowest-badge-pill">Lowest</span>':''}
                </div>
                <div class="store-btn-price">${inr(s.price)} ↗</div>
              </a>`;
            }).join('')}
          </div>
          <button class="detail-view-btn" onclick="openProduct(${p.id})">Price History &amp; Set Alert →</button>
        </div>
      </div>
    </div>
  `).join('');
}

$('#sort').addEventListener('change',e=>{sortv=e.target.value;drawGrid()});
const storeFilterEl=$('#storeFilter');
if(storeFilterEl) storeFilterEl.addEventListener('change',e=>{storeFilterVal=e.target.value;drawGrid()});
$('#q').addEventListener('input',drawGrid);
const clearSearchBtn=$('#clearSearch');
if(clearSearchBtn) clearSearchBtn.addEventListener('click',()=>{$('#q').value='';drawGrid();$('#q').focus()});
$('#heroSearch').addEventListener('submit',e=>{e.preventDefault();drawGrid();$('#shop').scrollIntoView({behavior:'smooth'})});

/* ── Keyboard shortcut ── */
document.addEventListener('keydown',e=>{
  if(e.key==='/'&&e.target.tagName!=='INPUT'&&e.target.tagName!=='TEXTAREA'){
    e.preventDefault();$('#q').focus();
  }
});

/* ── Chart ── */
function chart(h,days){
  const d=h.slice(-days);
  if(d.length<2)return{svg:'<div style="padding:24px;text-align:center;color:var(--text-muted)">Price history chart recording.</div>',d,fmt:()=>'',x:()=>0,y:()=>0,L:0,W:0,R:0};
  const W=660,H=230,L=68,R=16,T=18,B=34,mn=Math.min(...d),mx=Math.max(...d);
  const x=i=>L+i*(W-L-R)/(d.length-1),y=v=>H-B-(v-mn)/(mx-mn||1)*(H-T-B);
  const line=d.map((v,i)=>`${i?'L':'M'}${x(i).toFixed(1)} ${y(v).toFixed(1)}`).join('');
  const dt=i=>new Date(Date.now()-(d.length-1-i)*864e5);
  const fmt=i=>dt(i).toLocaleDateString('en-IN',{day:'numeric',month:'short',year:'2-digit'});
  const li=d.indexOf(mn),mid=(mn+mx)/2;
  return{fmt,d,svg:`<svg class="chart" viewBox="0 0 ${W} ${H}" role="img" aria-label="Price history chart">
   <defs>
     <linearGradient id="chartGrad" x1="0" y1="0" x2="0" y2="1">
       <stop offset="0%" stop-color="#6c63ff" stop-opacity="0.18"/>
       <stop offset="100%" stop-color="#6c63ff" stop-opacity="0.00"/>
     </linearGradient>
   </defs>
   ${[mn,mid,mx].map(v=>`<line x1="${L}" x2="${W-R}" y1="${y(v)}" y2="${y(v)}" stroke="rgba(255,255,255,0.06)" stroke-dasharray="3 4"/><text x="${L-8}" y="${y(v)+4}" text-anchor="end" font-size="11" font-weight="600" fill="#555570">${inr(v)}</text>`).join('')}
   <path d="${line}L${x(d.length-1)} ${H-B}L${L} ${H-B}Z" fill="url(#chartGrad)"/>
   <path d="${line}" fill="none" stroke="#6c63ff" stroke-width="2.5" stroke-linejoin="round" stroke-linecap="round"/>
   <circle cx="${x(li)}" cy="${y(mn)}" r="5" fill="#00d4aa" stroke="#0a0a0f" stroke-width="2"/>
   <text x="${Math.min(Math.max(x(li),L+28),W-R-28)}" y="${y(mn)-10}" text-anchor="middle" font-size="11" font-weight="700" fill="#00d4aa">Lowest: ${inr(mn)}</text>
   <text x="${L}" y="${H-10}" font-size="11" font-weight="600" fill="#555570">${fmt(0)}</text>
   <text x="${W-R}" y="${H-10}" text-anchor="end" font-size="11" font-weight="600" fill="#555570">${fmt(d.length-1)}</text>
   <line id="cl" y1="${T}" y2="${H-B}" stroke="#6c63ff" stroke-width="1.5" stroke-dasharray="2 2" opacity="0"/>
   <circle id="cd" r="4.5" fill="#6c63ff" opacity="0"/>
   <rect id="hit" x="${L}" y="0" width="${W-L-R}" height="${H}" fill="transparent"/></svg>`,x,y,L,W,R};
}

function wire(el,c,tip){
  const hit=el.querySelector('#hit');if(!hit)return;
  const move=e=>{
    const r=el.querySelector('svg').getBoundingClientRect(),px=((e.touches?e.touches[0].clientX:e.clientX)-r.left)*c.W/r.width;
    const i=Math.max(0,Math.min(c.d.length-1,Math.round((px-c.L)/(c.W-c.L-c.R)*(c.d.length-1))));
    const cl=el.querySelector('#cl'),cd=el.querySelector('#cd');
    cl.setAttribute('x1',c.x(i));cl.setAttribute('x2',c.x(i));cl.setAttribute('opacity',1);
    cd.setAttribute('cx',c.x(i));cd.setAttribute('cy',c.y(c.d[i]));cd.setAttribute('opacity',1);
    tip.textContent=`${c.fmt(i)}: ${inr(c.d[i])}`;
  };
  hit.addEventListener('mousemove',move);hit.addEventListener('touchmove',move);
}

/* ── Product Modal ── */
let range=365;
async function openProduct(id,quiet){
  openId=id;
  const d=await api('/api/products/'+id);cur=d;
  const draw=()=>{
    const c=chart(d.hist,range);
    $('#pbody').innerHTML=`
      <div class="modal-header-row">
        <img src="${d.image}" alt="${d.name}" class="modal-thumb" onerror="this.onerror=null;this.src='https://images.unsplash.com/photo-1526738549149-8e07eca6c147?w=600&auto=format&fit=crop&q=80'">
        <div>
          <span style="font-size:10px;font-weight:800;color:var(--text-subtle);text-transform:uppercase;letter-spacing:0.08em">Launched in Last 6 Months</span>
          <h2 class="modal-title">${d.name}</h2>
          <div class="modal-meta">${d.brand} &nbsp;•&nbsp; ${d.cat}</div>
          <div style="display:flex;align-items:baseline;gap:10px;margin-top:6px">
            <div class="modal-price">${inr(d.lowest_price||d.price)}</div>
            <span class="lowest-pill-mini">Lowest on ${(d.lowest_store||'').replace('.in','')}</span>
          </div>
        </div>
      </div>

      ${(d.savings&&d.savings>0)?`
        <div class="modal-savings-callout">
          <span class="savings-icon">💡</span>
          <div>
            <b>Save ${inr(d.savings)} (${d.savings_pct}% cheaper):</b> Buy on <b>${(d.lowest_store||'').replace('.in','')}</b> instead of ${(d.highest_store||'').replace('.in','')} (${inr(d.highest_price)}).
          </div>
        </div>
      `:''}

      <div class="modal-stores-heading">Live Store Prices — Click to Buy Directly:</div>
      <div class="modal-stores-grid">
        ${d.stores.map((s,i)=>{
          const sk=s.name.toLowerCase();
          const dotClass=sk.includes('amazon')?'store-dot-amazon':sk.includes('flipkart')?'store-dot-flipkart':sk.includes('croma')?'store-dot-croma':'store-dot-reliance';
          const diffFromLowest=s.price-(d.lowest_price||d.price);
          return `
          <a href="${s.url}" target="_blank" rel="noopener noreferrer" class="store-card ${s.is_lowest||i===0?'best':''}">
            <div class="store-top-line">
              <span><span class="store-color-dot ${dotClass}" style="display:inline-block;margin-right:6px"></span>${s.name.replace('.in','')}</span>
              ${s.is_lowest||i===0?'<span class="best-pill">Lowest</span>':(diffFromLowest>0?`<span style="font-size:10px;color:var(--text-subtle);font-weight:600">+${inr(diffFromLowest)}</span>`:'')}
            </div>
            <div class="store-card-price">${inr(s.price)}</div>
            <div class="store-card-cta">Buy on ${s.name.replace('.in','')} ↗</div>
          </a>`;
        }).join('')}
      </div>

      <div class="range-pills">
        ${[[30,'1 Month'],[90,'3 Months'],[180,'6 Months'],[365,'1 Year']].map(([n,l])=>`
          <button class="range-btn ${range===n?'active':''}" data-r="${n}">${l}</button>
        `).join('')}
      </div>
      ${c.svg}
      <div class="chart-tooltip" id="tip">Hover to inspect price movement &nbsp;•&nbsp; Year Low: ${inr(d.low)} &nbsp;•&nbsp; High: ${inr(d.high)}</div>

      <div class="alert-row">
        <div>
          <div style="font-weight:800;font-size:14px;color:var(--text-main)">Set Price Drop Notification</div>
          <div style="font-size:12px;color:var(--text-muted);margin-top:2px">Get alerted when price falls to your budget.</div>
          ${!d.watch?`
            <div style="display:flex;gap:6px;margin-top:8px;flex-wrap:wrap">
              <button type="button" class="preset-btn" onclick="$('#tgt').value=Math.round(${d.price}*0.95/100)*100">-5% (${inr(Math.round(d.price*0.95))})</button>
              <button type="button" class="preset-btn" onclick="$('#tgt').value=Math.round(${d.price}*0.90/100)*100">-10% (${inr(Math.round(d.price*0.90))})</button>
              <button type="button" class="preset-btn" onclick="$('#tgt').value=Math.round(${d.price}*0.85/100)*100">-15% (${inr(Math.round(d.price*0.85))})</button>
            </div>
          `:''}
        </div>
        ${d.watch?`
          <div style="display:flex;align-items:center;gap:10px">
            <span style="font-weight:700;font-size:13px;color:var(--green)">Tracking at ${inr(d.watch)}</span>
            <button class="btn-secondary" id="untrack">Stop Alert</button>
          </div>
        `:`
          <div class="alert-input-group">
            <input id="tgt" type="number" min="1" value="${Math.round(d.price*.95/100)*100}">
            <button class="btn-primary" id="dotrack">Set Alert</button>
          </div>
        `}
      </div>
    `;
    wire($('#pbody'),c,$('#tip'));
  };
  draw();
  $('#pm').classList.add('open');
  $('#pbody').onclick=async e=>{
    const r=e.target.dataset.r;if(r){range=+r;draw();return}
    if(e.target.id==='dotrack'){
      if(!me){openAuth('login');return}
      try{await api('/api/watch',{method:'POST',body:{product_id:id,target:+$('#tgt').value}});toast("Price alert set successfully.");await loadNotes(true);openProduct(id,true)}catch(er){toast(er.message)}
    }
    if(e.target.id==='untrack'){
      await api('/api/watch/'+id,{method:'DELETE'});
      toast('Price alert removed.');openProduct(id,true);
    }
  };
}

/* ── Auth Modal ── */
function openAuth(m){
  mode=m;const reg=m==='register';
  $('#atitle').textContent=reg?'Create Account':'Sign In';
  $('#asub').textContent=reg?'Free, takes 30 seconds.':'Manage your price alerts and tracked gadgets.';
  $('#nameF').hidden=!reg;
  $('#asubmit').textContent=reg?'Create Account':'Sign In';
  $('#aswl').textContent=reg?'Already registered?':"Don't have an account?";
  $('#aswap').textContent=reg?'Sign In':'Create account';
  $('#aerr').textContent='';
  $('#am').classList.add('open');
  setTimeout(()=>(reg?$('#an'):$('#ae')).focus(),50);
}

$('#aswap').onclick=()=>openAuth(mode==='login'?'register':'login');
$('#asubmit').onclick=async()=>{
  try{
    const j=await api('/api/'+mode,{method:'POST',body:{name:$('#an').value,email:$('#ae').value,password:$('#ap').value}});
    me=j.name;$('#am').classList.remove('open');setAcct();toast(`Welcome, ${me.split(' ')[0]}!`);loadNotes(false);
  }catch(e){$('#aerr').textContent=e.message}
};
$('#am').addEventListener('keydown',e=>{if(e.key==='Enter')$('#asubmit').click()});

function setAcct(){
  $('#acct').textContent=me?`${me.split(' ')[0]}`:'Sign In';
  if(!me)$('#badge').hidden=true;
  if(me){
    $('#acct').classList.remove('btn-signin');
    $('#acct').classList.add('header-btn');
  } else {
    $('#acct').classList.add('btn-signin');
  }
}

$('#acct').onclick=async()=>{
  if(me){
    if(confirm(`Signed in as ${me}. Sign out?`)){
      await api('/api/logout',{method:'POST'});
      me=null;setAcct();$('#panel').classList.remove('open');toast('Signed out.');
    }
  } else {
    openAuth('login');
  }
};

/* ── Notifications ── */
async function loadNotes(announce){
  if(!me)return;
  const j=await api('/api/notes');
  const b=$('#badge');b.hidden=!j.unseen;b.textContent=j.unseen;
  if(announce&&j.unseen>lastUnseen)toast(j.items[0].msg);
  lastUnseen=j.unseen;
  $('#panel').innerHTML=j.items.length?j.items.map(n=>`
    <div class="${n.seen?'':'new'}">${n.msg}<small>${new Date(n.ts*1000).toLocaleString('en-IN',{day:'numeric',month:'short',hour:'numeric',minute:'2-digit'})}</small></div>
  `).join(''):'<div>No active alerts. Click any product to set a target price.</div>';
}

$('#bell').onclick=async()=>{
  if(!me){openAuth('login');return}
  const p=$('#panel');p.classList.toggle('open');
  if(p.classList.contains('open')){await loadNotes(false);await api('/api/notes/seen',{method:'POST'});lastUnseen=0;$('#badge').hidden=true}
};

/* ── Modal close ── */
document.addEventListener('click',e=>{
  if(e.target.matches('[data-close]')||e.target.classList.contains('modal-scrim')){
    document.querySelectorAll('.modal-scrim').forEach(s=>s.classList.remove('open'));
    openId=null;
  }
  if(!e.target.closest('#panel,#bell'))$('#panel').classList.remove('open');
});
document.addEventListener('keydown',e=>{
  if(e.key==='Escape'){
    document.querySelectorAll('.modal-scrim').forEach(s=>s.classList.remove('open'));
    toggleDrawer(false);openId=null;
  }
});

/* ── Live clock & refresh ── */
function updateLiveClock(){
  const now=new Date();
  const t=now.toLocaleTimeString('en-IN',{hour:'2-digit',minute:'2-digit',second:'2-digit'});
  const el=$('#liveClock');
  if(el) el.innerHTML=`Last synced at ${t}`;
}
async function refreshLivePrices(){
  try{
    const fresh=await api('/api/products');
    if(fresh&&fresh.length){P=fresh;updateLiveClock();}
  }catch(e){}
}

/* ── Init ── */
(async()=>{
  P=await api('/api/products');
  me=(await api('/api/me')).name;
  setAcct();
  renderFilterState();
  drawGrid();
  loadNotes(false);
  updateLiveClock();
  setInterval(refreshLivePrices,15000);
  setInterval(updateLiveClock,1000);
})();
