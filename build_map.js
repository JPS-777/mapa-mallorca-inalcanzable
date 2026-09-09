const fs = require('fs');
const gj = JSON.parse(fs.readFileSync('mallorca.geojson'));

// ============================================================
//  DATOS DE TIEMPOS
//  Si existe tiempos_reales.json (calcular_tiempos.py, GTFS oficial TIB),
//  se usa ESE. Si no, valores ILUSTRATIVOS y marca de agua.
// ============================================================
const SIM = {
  'Palma':[25,15], 'Marratxí':[45,20], 'Calvià':[55,25], 'Llucmajor':[70,25],
  'Santa María del Camí':[55,25], 'Consell':[60,28], 'Binissalem':[62,30],
  'Lloseta':[70,33], 'Inca':[58,32], 'Bunyola':[75,28], 'Alaró':[95,35],
  'Sóller':[85,40], 'Andratx':[80,35], 'Esporles':[90,32], 'Valldemossa':[100,38],
  'Deià':[130,48], 'Banyalbufar':[145,45], 'Estellencs':[155,50], 'Fornalutx':[125,45],
  'Puigpunyent':[120,35], 'Mancor de la Vall':[115,40], 'Selva':[105,38],
  'Escorca':[999,55], 'Campanet':[95,40], 'Búger':[110,42], 'Sa Pobla':[75,45],
  'Muro':[80,45], 'Alcúdia':[85,50], 'Pollença':[90,50], 'Santa Margalida':[95,48],
  'Maria de la Salut':[125,45], 'Llubí':[120,43], 'Sineu':[85,42], 'Costitx':[135,40],
  'Sencelles':[130,38], 'Lloret de Vistalegre':[140,42], 'Santa Eugènia':[110,33],
  'Algaida':[95,32], 'Montuïri':[105,38], 'Porreres':[115,40], 'Sant Joan':[130,42],
  'Petra':[100,45], 'Ariany':[150,48], 'Vilafranca de Bonany':[110,45],
  'Manacor':[75,50], 'Felanitx':[95,48], 'Campos':[90,42], 'Santanyí':[110,55],
  'ses Salines':[120,52], 'Artà':[105,60], 'Capdepera':[115,65],
  'Son Servera':[100,58], 'Sant Llorenç des Cardassar':[110,55]
};

let REAL = null;
try { REAL = JSON.parse(fs.readFileSync('tiempos_reales.json','utf8')); } catch(e) {}
const SIM_TIEMPOS = !REAL;
const DATA = REAL ? REAL.municipios : SIM;
const FUENTE_TIEMPOS = REAL ? ((REAL.meta && REAL.meta.fuente) || 'GTFS oficial') : 'valores ilustrativos';

// ============================================================
//  DATOS DE NEGOCIOS
//  Si existe negocios_geocodificados.json (geocodificar_negocios.py,
//  Nominatim/OSM + IGN), se usan esos PUNTOS REALES individuales.
//  Si no, se cae a un puñado de puntos ilustrativos por municipio.
// ============================================================
const SIM_NEG_LIST = [
  {nombre:'(ilustrativo) Bodega A', tipo:'bodega', municipio_oficial:'Binissalem', localidad_pedania:'Binissalem', estado:'operativo', lat:39.688, lon:2.845},
  {nombre:'(ilustrativo) Agroturismo A', tipo:'agroturismo', municipio_oficial:'Sineu', localidad_pedania:'Sineu', estado:'operativo', lat:39.641, lon:3.011},
];

let REAL_NEG = null;
try { REAL_NEG = JSON.parse(fs.readFileSync('negocios_geocodificados.json','utf8')); } catch(e) {}
const SIM_NEGOCIOS = !(REAL_NEG && REAL_NEG.negocios && REAL_NEG.negocios.length);
const NEGOCIOS = SIM_NEGOCIOS ? SIM_NEG_LIST : REAL_NEG.negocios;

console.log(SIM_TIEMPOS ? '>> TIEMPOS: MODO SIMULACION' : '>> TIEMPOS: DATOS REALES: '+FUENTE_TIEMPOS);
console.log(SIM_NEGOCIOS ? '>> NEGOCIOS: MODO SIMULACION' : '>> NEGOCIOS: DATOS REALES ('+NEGOCIOS.length+' geocodificados)');

// Aeropuerto de Palma (Son Sant Joan), terminal de pasajeros.
// Verificado: 39 33'06"N, 2 44'20"E -> 39.551667, 2.738889
const AIRPORT = [2.738889, 39.551667];

const W = 760, H = 560, PAD = 28;
let lons=[], lats=[];
const walk=(c,f)=>{ if(typeof c[0]==='number') f(c); else c.forEach(x=>walk(x,f)); };
gj.features.forEach(ft=>walk(ft.geometry.coordinates,p=>{lons.push(p[0]);lats.push(p[1]);}));
const lon0=Math.min(...lons), lon1=Math.max(...lons), lat0=Math.min(...lats), lat1=Math.max(...lats);
const latMid=(lat0+lat1)/2, kx=Math.cos(latMid*Math.PI/180);
const w=(lon1-lon0)*kx, h=(lat1-lat0);
const s=Math.min((W-2*PAD)/w,(H-2*PAD)/h);
const offx=(W-w*s)/2, offy=(H-h*s)/2;
const px=(lon,lat)=>[ offx+(lon-lon0)*kx*s, offy+(lat1-lat)*s ];
const fmt=n=>Math.round(n*10)/10;

const ringPath=r=>r.map((p,i)=>{const q=px(p[0],p[1]);return (i?'L':'M')+fmt(q[0])+' '+fmt(q[1]);}).join('')+'Z';
// Cabrera (archipiélago) pertenece administrativamente al municipio de Palma
// (verificado: palma.cat, Wikipedia, MITECO), pero no tiene transporte público
// regular ni negocios de interior que mostrar: se recorta del dibujo para no
// sugerir que "se llega" allí igual que al resto del municipio.
const CABRERA_LAT_MAX = 39.3;
function featPath(ft, opts){ const g=ft.geometry; let d='';
  const polys = g.type==='Polygon' ? [g.coordinates] : g.coordinates;
  polys.forEach(poly=>{
    if(opts && opts.excludeSouthOf){
      let allSouth = true;
      poly.forEach(r=>r.forEach(p=>{ if(p[1] >= opts.excludeSouthOf) allSouth = false; }));
      if(allSouth) return; // es la pieza de Cabrera: se omite
    }
    poly.forEach(r=>{d+=ringPath(r);});
  });
  return d; }

let paths='';
gj.features.forEach(ft=>{
  const n=ft.properties.name, d=DATA[n]; if(!d) return;
  const opts = (n === 'Palma') ? {excludeSouthOf: CABRERA_LAT_MAX} : null;
  paths += '<path class="mun" d="'+featPath(ft, opts)+'" data-n="'+n+'" data-tp="'+d[0]+'" data-car="'+d[1]+'"></path>\n';
});

// --- negocios: puntos individuales reales (o ilustrativos) ---
const COLOR = {bodega:'#7B3F8F', agroturismo:'#B8860B', gastronomia:'#2F8F5B'};
let dots = '';
NEGOCIOS.forEach((neg, i)=>{
  const q = px(neg.lon, neg.lat);
  const munData = DATA[neg.municipio_oficial];
  const tp = munData ? munData[0] : 999;
  const car = munData ? munData[1] : 999;
  const esProxima = neg.estado === 'proxima_apertura';
  const cls = ['neg', neg.tipo, esProxima ? 'proxima' : 'operativa'].join(' ');
  const nombreAttr = String(neg.nombre).replace(/"/g,'&quot;');
  const locAttr = String(neg.localidad_pedania||'').replace(/"/g,'&quot;');
  const munAttr = String(neg.municipio_oficial||'').replace(/"/g,'&quot;');
  const notaAttr = String(neg.nota_geometria||'').replace(/"/g,'&quot;');
  dots += `<circle class="${cls}" cx="${fmt(q[0])}" cy="${fmt(q[1])}" r="${esProxima?3.0:3.6}" `
        + `data-i="${i}" data-nombre="${nombreAttr}" data-loc="${locAttr}" data-mun="${munAttr}" `
        + `data-tipo="${neg.tipo}" data-estado="${neg.estado}" data-nota="${notaAttr}" `
        + `data-tp="${tp}" data-car="${car}"></circle>\n`;
});

const ap=px(AIRPORT[0],AIRPORT[1]);
const nMun=Object.keys(DATA).length;
const countByTipo = t => NEGOCIOS.filter(n=>n.tipo===t && n.estado!=='proxima_apertura').length;
const nBodegas = countByTipo('bodega');
const nAgro = countByTipo('agroturismo');
const nGastro = countByTipo('gastronomia');
const nProxima = NEGOCIOS.filter(n=>n.estado==='proxima_apertura').length;
const totalNegOperativos = nBodegas + nAgro + nGastro;

// --- marca de agua: independiente para tiempos y para negocios ---
let wm='';
if(SIM_TIEMPOS || SIM_NEGOCIOS){
  const texto = (SIM_TIEMPOS && SIM_NEGOCIOS) ? 'DATOS SIMULADOS'
              : SIM_TIEMPOS ? 'TIEMPOS SIMULADOS' : 'NEGOCIOS SIMULADOS';
  wm='<g class="wm" aria-hidden="true">';
  for(let y=-30;y<H+130;y+=116){
    for(let x=-70;x<W+130;x+=292){
      wm+='<text x="'+x+'" y="'+y+'" transform="rotate(-24 '+x+' '+y+')">'+texto+'</text>';
    }
  }
  wm+='</g>';
}

function bannerHTML(){
  if(SIM_TIEMPOS && SIM_NEGOCIOS){
    return `<b>PROTOTIPO — TIEMPOS Y NEGOCIOS SON DATOS SIMULADOS, NO REALES</b>
     <p>La <b>geometría de los 53 municipios es real</b> (IGN). Los minutos de viaje y los negocios mostrados
     son ilustrativos y no deben citarse ni publicarse.</p>`;
  }
  if(SIM_TIEMPOS && !SIM_NEGOCIOS){
    return `<b>NEGOCIOS REALES · TIEMPOS AÚN SIMULADOS</b>
     <p>La capa de bodegas/agroturismos/gastronomía (${NEGOCIOS.length} puntos) es real y geocodificada.
     Los tiempos de viaje todavía son ilustrativos: ejecuta calcular_tiempos.py para completarlo.</p>`;
  }
  if(!SIM_TIEMPOS && SIM_NEGOCIOS){
    return `<b>TIEMPOS REALES · NEGOCIOS AÚN SIMULADOS</b>
     <p>Los tiempos de viaje (${FUENTE_TIEMPOS}) son reales. La capa de negocios todavía es ilustrativa:
     ejecuta geocodificar_negocios.py para completarla.</p>`;
  }
  return `<b>DATOS REALES — TIEMPOS Y NEGOCIOS</b>
   <p>Tiempos: ${FUENTE_TIEMPOS}. Negocios: ${NEGOCIOS.length} geocodificados (Nominatim/OSM) y asignados a
   su municipio oficial por geometría real del IGN. 4 casos marcados como "cerca de un límite administrativo"
   se muestran con nota, sin asignación forzada. Metodología replicable detallada al pie.</p>`;
}
const bothReal = !SIM_TIEMPOS && !SIM_NEGOCIOS;
const warnColor = bothReal ? '#1E7A46' : (SIM_TIEMPOS && SIM_NEGOCIOS) ? '#E31B23' : '#B98900';
const warnBg = bothReal ? '#EAF6EF' : (SIM_TIEMPOS && SIM_NEGOCIOS) ? '#FDECEE' : '#FFF8E6';

const html = `<!DOCTYPE html>
<html lang="es"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>El mapa de la Mallorca inalcanzable ${bothReal ? '· datos reales' : '· prototipo'}</title>
<style>
  *{box-sizing:border-box;margin:0;padding:0}
  body{font-family:'Segoe UI',system-ui,-apple-system,Helvetica,Arial,sans-serif;background:#fff;color:#4A5568;padding:18px}
  .wrap{max-width:1120px;margin:0 auto}
  .warn{border:2px solid ${warnColor};background:${warnBg};border-radius:5px;padding:11px 14px;margin-bottom:14px}
  .warn b{color:${warnColor};font-size:12px;letter-spacing:.05em}
  .warn p{font-size:12px;margin-top:4px;line-height:1.5}
  h1{font-size:25px;color:#002B49;font-weight:800;line-height:1.15;letter-spacing:-.01em}
  h1 span{color:#E31B23}
  .sub{font-size:13.5px;margin-top:7px;max-width:720px;line-height:1.5}
  .grid{display:grid;grid-template-columns:1fr 300px;gap:22px;margin-top:18px;align-items:start}
  @media(max-width:900px){.grid{grid-template-columns:1fr}}
  .panel{border:1px solid #E2E8F0;border-radius:6px;padding:16px}
  .ctl{margin-bottom:16px}
  .lbl{font-size:10.5px;font-weight:700;color:#002B49;letter-spacing:.07em;margin-bottom:7px}
  .seg{display:flex;border:1px solid #CBD5E1;border-radius:5px;overflow:hidden}
  .seg button{flex:1;padding:8px 4px;font-size:12.5px;font-weight:600;background:#fff;color:#4A5568;
    border:0;cursor:pointer;font-family:inherit;transition:.12s}
  .seg button.on{background:#002B49;color:#fff}
  .seg button:not(.on):hover{background:#F1F5F9}
  .stat{border-left:3px solid #E31B23;padding:8px 0 8px 11px;margin-bottom:12px;background:#FAFBFC;position:relative}
  .stat .big{font-size:27px;font-weight:800;color:#002B49;line-height:1}
  .stat .cap{font-size:11px;margin-top:3px;line-height:1.35}
  .stat.teal{border-left-color:#36A7B7}
  .simchip{position:absolute;top:6px;right:6px;background:#E31B23;color:#fff;font-size:8px;
    font-weight:800;letter-spacing:.08em;padding:2px 5px;border-radius:2px}
  .mapbox{border:1px solid #E2E8F0;border-radius:6px;background:#F8FAFC;overflow:hidden;position:relative}
  svg{display:block;width:100%;height:auto}
  .mun{stroke:#fff;stroke-width:.7;transition:fill .35s;cursor:pointer}
  .mun.ok{fill:#36A7B7}
  .mun.no{fill:#C9D3DA}
  .mun:hover{stroke:#002B49;stroke-width:1.5}
  .neg{stroke:#fff;stroke-width:1;cursor:pointer;transition:opacity .3s}
  .neg.bodega{fill:${COLOR.bodega}}
  .neg.agroturismo{fill:${COLOR.agroturismo}}
  .neg.gastronomia{fill:${COLOR.gastronomia}}
  .neg.proxima{stroke:#002B49;stroke-dasharray:1.4 1.1;fill-opacity:.55}
  .neg.hide{display:none}
  .ap{fill:#E31B23;stroke:#fff;stroke-width:1.6}
  .aplbl-bg{fill:#ffffff;fill-opacity:.85;stroke:#E31B23;stroke-width:.6}
  .aplbl{font-size:9.5px;font-weight:700;fill:#E31B23;text-anchor:middle}
  .wm{pointer-events:none}
  .wm text{font-size:20px;font-weight:800;fill:#E31B23;opacity:.13;letter-spacing:.13em}
  .legend{display:flex;gap:12px;flex-wrap:wrap;padding:10px 14px;border-top:1px solid #E2E8F0;
    background:#fff;font-size:10.5px;align-items:center}
  .key{display:flex;align-items:center;gap:5px}
  .sw{width:11px;height:11px;border-radius:2px}
  .tip{position:fixed;background:#002B49;color:#fff;font-size:11.5px;padding:6px 9px;border-radius:4px;
    pointer-events:none;opacity:0;transition:opacity .12s;z-index:9;line-height:1.45;max-width:260px}
  .foot{margin-top:14px;font-size:10.5px;color:#878E90;line-height:1.55;border-top:1px solid #E2E8F0;padding-top:10px}
  .chk{display:flex;align-items:center;gap:7px;font-size:12.5px;cursor:pointer;user-select:none;margin-bottom:6px}
</style></head><body><div class="wrap">

<div class="warn">${bannerHTML()}</div>

<h1>El mapa de la Mallorca <span>inalcanzable</span></h1>
<p class="sub">Hasta dónde se puede llegar desde el aeropuerto de Palma sin coche de alquiler?
Compara el alcance en transporte público frente al vehículo, y dónde quedan bodegas, agroturismos
y gastronomía de interior.</p>

<div class="grid">
  <div>
    <div class="mapbox">
      <svg viewBox="0 0 ${W} ${H}" id="map">
        <g id="muns">
${paths}        </g>
        <g id="negs">
${dots}        </g>
        <circle class="ap" cx="${fmt(ap[0])}" cy="${fmt(ap[1])}" r="5"></circle>
        <rect class="aplbl-bg" x="${fmt(ap[0]-59)}" y="${fmt(ap[1]+8)}" width="118" height="15" rx="3"></rect>
        <text class="aplbl" x="${fmt(ap[0])}" y="${fmt(ap[1]+18.5)}">Aeropuerto de Palma</text>
        ${wm}
      </svg>
      <div class="legend">
        <div class="key"><div class="sw" style="background:#36A7B7"></div>Alcanzable</div>
        <div class="key"><div class="sw" style="background:#C9D3DA"></div>Fuera de alcance</div>
        <div class="key"><div class="sw" style="background:${COLOR.bodega}"></div>Bodegas</div>
        <div class="key"><div class="sw" style="background:${COLOR.agroturismo}"></div>Agroturismos</div>
        <div class="key"><div class="sw" style="background:${COLOR.gastronomia}"></div>Gastronomía</div>
        <div class="key"><div class="sw" style="background:#fff;border:1.5px dashed #002B49"></div>Próxima apertura</div>
        <div class="key"><div class="sw" style="background:#E31B23;border-radius:50%"></div>Origen</div>
      </div>
    </div>
  </div>

  <div class="panel">
    <div class="ctl">
      <div class="lbl">CÓMO TE MUEVES</div>
      <div class="seg" id="mode">
        <button data-m="tp" class="on">Transporte público</button>
        <button data-m="car">Coche</button>
      </div>
    </div>
    <div class="ctl">
      <div class="lbl">TIEMPO MÁXIMO DE VIAJE</div>
      <div class="seg" id="thr">
        <button data-t="60">60 min</button>
        <button data-t="90" class="on">90 min</button>
        <button data-t="120">120 min</button>
      </div>
    </div>
    <div class="ctl">
      <div class="lbl">ECONOMÍA DE INTERIOR</div>
      <label class="chk"><input type="checkbox" id="tBodega" checked> Bodegas (${nBodegas})</label>
      <label class="chk"><input type="checkbox" id="tAgro" checked> Agroturismos (${nAgro})</label>
      <label class="chk"><input type="checkbox" id="tGastro" checked> Gastronomía (${nGastro})</label>
      <label class="chk"><input type="checkbox" id="tProxima" checked> Incluir "próxima apertura" (${nProxima})</label>
    </div>
    <hr style="border:0;border-top:1px solid #E2E8F0;margin:14px 0">
    <div class="stat teal"><div class="big" id="s1">-</div><div class="cap">municipios alcanzables<br>de ${nMun} en Mallorca</div></div>
    <div class="stat"><div class="big" id="s2">-</div><div class="cap">municipios sin conexión útil</div></div>
    <div class="stat"><div class="big" id="s3">-</div><div class="cap">negocios visibles<br>fuera de alcance (de ${totalNegOperativos + nProxima})</div></div>
  </div>
</div>

<div class="foot">
  <b>Fuentes.</b> Geometría municipal: <b>Instituto Geográfico Nacional (IGN)</b> vía es-atlas — 53 municipios de Mallorca (dato real).
  Origen: aeropuerto de Son Sant Joan, terminal de pasajeros, 39,551667 / 2,738889 (dato real).
  ${SIM_TIEMPOS
    ? '<b style="color:#B98900">Tiempos de viaje: SIMULADOS.</b> '
    : '<b>Tiempos de viaje: '+FUENTE_TIEMPOS+'.</b> '}
  ${SIM_NEGOCIOS
    ? '<b style="color:#B98900">Capa de negocios: SIMULADA.</b> '
    : '<b>Capa de negocios: '+NEGOCIOS.length+' establecimientos geocodificados</b> (Nominatim/OpenStreetMap), '
      + 'asignados a su municipio oficial por contención geométrica real contra el IGN, con reparación de polígonos '
      + 'inválidos y tolerancia documentada para desajustes de línea de costa. En 2 casos la geometría estricta '
      + 'entraba en conflicto con el código postal oficial de la dirección (evidencia más fuerte): se corrigieron '
      + 'con nota explícita, nunca en silencio. Fuentes: C.R. D.O. Binissalem, D.O. Pla i Llevant, ABATI '
      + '(Associació Balear d\'Agroturisme). '
  }
  <b>Nota sobre Sóller:</b> el histórico Ferrocarril de Sóller es una empresa privada (Ferrocarril de Sóller S.A.),
  ajena a la red pública TIB y sin billete integrado; el tiempo mostrado a Sóller usa el transporte público
  regular (autobús por el túnel), no el tren turístico de madera.
  <b>Cabrera</b> (archipiélago, parque nacional) pertenece administrativamente al municipio de Palma pero se ha
  recortado del dibujo: no tiene transporte público regular ni negocios de interior que mostrar.
  Metodología publicable y replicable por terceros.
  <br><b>LLYC para ANEVAL/BALEVAL — Documento de trabajo interno.</b>
</div>
</div>

<div class="tip" id="tip"></div>
<script>
(function(){
  var mode='tp', thr=90, TOTAL=${nMun};
  var muns=[].slice.call(document.querySelectorAll('.mun'));
  var negs=[].slice.call(document.querySelectorAll('.neg'));
  var tip=document.getElementById('tip');
  var carOf={}; muns.forEach(function(p){carOf[p.getAttribute('data-n')]=+p.getAttribute('data-car');});

  var showBodega=true, showAgro=true, showGastro=true, showProxima=true;

  function tipoVisible(tipo){
    if(tipo==='bodega') return showBodega;
    if(tipo==='agroturismo') return showAgro;
    if(tipo==='gastronomia') return showGastro;
    return true;
  }

  function render(){
    var ok=0;
    muns.forEach(function(p){
      var v=+p.getAttribute(mode==='tp'?'data-tp':'data-car');
      var good=v<=thr;
      p.classList.toggle('ok',good); p.classList.toggle('no',!good);
      if(good) ok++;
    });
    var out=0, visibles=0;
    negs.forEach(function(c){
      var esProxima = c.getAttribute('data-estado')==='proxima_apertura';
      var tipo = c.getAttribute('data-tipo');
      var visible = tipoVisible(tipo) && (!esProxima || showProxima);
      c.classList.toggle('hide', !visible);
      if(!visible) return;
      visibles++;
      var val=(mode==='tp')? +c.getAttribute('data-tp') : carOf[c.getAttribute('data-mun')];
      if(val===undefined || isNaN(val)) val = +c.getAttribute(mode==='tp'?'data-tp':'data-car');
      if(val>thr) out++;
    });
    document.getElementById('s1').textContent=ok;
    document.getElementById('s2').textContent=TOTAL-ok;
    document.getElementById('s3').textContent=out;
  }

  document.getElementById('mode').addEventListener('click',function(e){
    var b=e.target.closest('button'); if(!b)return;
    mode=b.getAttribute('data-m');
    [].slice.call(this.children).forEach(function(x){x.classList.toggle('on',x===b);});
    render();
  });
  document.getElementById('thr').addEventListener('click',function(e){
    var b=e.target.closest('button'); if(!b)return;
    thr=+b.getAttribute('data-t');
    [].slice.call(this.children).forEach(function(x){x.classList.toggle('on',x===b);});
    render();
  });
  document.getElementById('tBodega').addEventListener('change',function(){showBodega=this.checked;render();});
  document.getElementById('tAgro').addEventListener('change',function(){showAgro=this.checked;render();});
  document.getElementById('tGastro').addEventListener('change',function(){showGastro=this.checked;render();});
  document.getElementById('tProxima').addEventListener('change',function(){showProxima=this.checked;render();});

  muns.forEach(function(p){
    p.addEventListener('mousemove',function(e){
      var tp=+p.getAttribute('data-tp'), car=p.getAttribute('data-car');
      tip.innerHTML='<b>'+p.getAttribute('data-n')+'</b><br>Transporte público: '+(tp>=999?'sin servicio útil':tp+' min')
        +'<br>Coche: '+car+' min';
      tip.style.left=(e.clientX+13)+'px'; tip.style.top=(e.clientY+13)+'px'; tip.style.opacity=1;
    });
    p.addEventListener('mouseleave',function(){tip.style.opacity=0;});
  });

  var TIPO_LABEL={bodega:'Bodega',agroturismo:'Agroturismo',gastronomia:'Gastronomía'};
  negs.forEach(function(c){
    c.addEventListener('mousemove',function(e){
      var tipoLbl = TIPO_LABEL[c.getAttribute('data-tipo')] || c.getAttribute('data-tipo');
      var estado = c.getAttribute('data-estado')==='proxima_apertura' ? ' · próxima apertura' : '';
      var nota = c.getAttribute('data-nota');
      tip.innerHTML = '<b>'+c.getAttribute('data-nombre')+'</b> ('+tipoLbl+estado+')'
        + '<br>'+c.getAttribute('data-loc')+' · municipio: '+c.getAttribute('data-mun')
        + (nota ? '<br><i style="color:#FFD27A">'+nota+'</i>' : '');
      tip.style.left=(e.clientX+13)+'px'; tip.style.top=(e.clientY+13)+'px'; tip.style.opacity=1;
      e.stopPropagation();
    });
    c.addEventListener('mouseleave',function(){tip.style.opacity=0;});
  });

  render();
})();
</script>
</body></html>`;

fs.writeFileSync('mapa_mallorca_inalcanzable.html', html);
console.log('HTML escrito ('+Math.round(html.length/1024)+' KB) · tiempos_simulado='+SIM_TIEMPOS+' · negocios_simulado='+SIM_NEGOCIOS);
