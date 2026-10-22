"""Generate single-page analytics dashboard HTML from website_data.json."""
import json
from pathlib import Path

OUT = Path(r"C:\Users\Alex\ozon_analytics")
data = json.load(open(OUT / "website_data.json", encoding="utf-8"))

# keep page reasonable: top 200 SKUs in table data
skus = data["sku_economics"][:200]
days = data["days"]
recs = data["price_recommendations"][:150]
wb_costs = data["wb_costs"]
fee_totals = data["fee_totals"]
fee_pct = data["fee_pct"]
totals = data["totals"]
comparison = data["comparison"]

html = r"""<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Пуговицнет — Аналитика Ozon vs WB</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.7/dist/chart.umd.min.js"></script>
<style>
:root{
  --bg:#0b1220; --card:#121c2e; --card2:#18253c; --text:#e8eefc; --muted:#8fa3c1;
  --accent:#5b8cff; --good:#22c55e; --warn:#f59e0b; --bad:#ef4444; --purple:#a78bfa;
  --border:#243552; --chip:#1e2d48;
}
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:'Segoe UI',system-ui,sans-serif;background:var(--bg);color:var(--text);line-height:1.45}
.wrap{max-width:1480px;margin:0 auto;padding:20px}
header{display:flex;flex-wrap:wrap;gap:16px;align-items:flex-end;justify-content:space-between;margin-bottom:22px}
h1{font-size:1.55rem;font-weight:700;letter-spacing:.2px}
h1 span{color:var(--accent)}
.sub{color:var(--muted);font-size:.92rem;margin-top:4px}
.period{background:var(--card);border:1px solid var(--border);border-radius:12px;padding:10px 14px;font-size:.88rem}
.period b{color:var(--accent)}
.grid{display:grid;gap:14px}
.kpi{grid-template-columns:repeat(auto-fit,minmax(170px,1fr))}
.card{background:var(--card);border:1px solid var(--border);border-radius:16px;padding:16px 18px}
.card h3{font-size:.95rem;font-weight:600;margin-bottom:10px;color:#c9d7f2}
.kpi .label{color:var(--muted);font-size:.78rem;text-transform:uppercase;letter-spacing:.04em}
.kpi .value{font-size:1.45rem;font-weight:700;margin-top:6px}
.kpi .delta{font-size:.78rem;color:var(--muted);margin-top:4px}
.good{color:var(--good)} .bad{color:var(--bad)} .warn{color:var(--warn)} .accent{color:var(--accent)}
.row2{grid-template-columns:1.4fr 1fr}
.row3{grid-template-columns:1fr 1fr 1fr}
@media(max-width:980px){.row2,.row3{grid-template-columns:1fr}}
.chart-box{position:relative;height:280px}
.chart-box.tall{height:320px}
table{width:100%;border-collapse:collapse;font-size:.83rem}
th,td{padding:8px 10px;border-bottom:1px solid var(--border);text-align:left;white-space:nowrap}
th{color:var(--muted);font-weight:600;font-size:.75rem;text-transform:uppercase;letter-spacing:.03em;cursor:pointer;user-select:none;position:sticky;top:0;background:var(--card);z-index:2}
tr:hover td{background:rgba(91,140,255,.06)}
.num{text-align:right;font-variant-numeric:tabular-nums}
.tbl-wrap{overflow:auto;max-height:520px;border-radius:12px;border:1px solid var(--border)}
.filters{display:flex;flex-wrap:wrap;gap:10px;margin:14px 0}
.filters input,.filters select,.filters button{
  background:var(--card2);border:1px solid var(--border);color:var(--text);
  border-radius:10px;padding:9px 12px;font-size:.88rem;outline:none}
.filters input{min-width:220px}
.filters button{cursor:pointer;background:var(--accent);border-color:var(--accent);font-weight:600}
.filters button:hover{filter:brightness(1.08)}
.chip{display:inline-block;background:var(--chip);border-radius:999px;padding:3px 10px;font-size:.75rem;margin:2px}
.chip.good{background:rgba(34,197,94,.15);color:#4ade80}
.chip.bad{background:rgba(239,68,68,.15);color:#f87171}
.chip.warn{background:rgba(245,158,11,.15);color:#fbbf24}
.chip.accent{background:rgba(91,140,255,.15);color:#93b4ff}
.bar{height:8px;background:#1a2740;border-radius:99px;overflow:hidden;min-width:80px}
.bar>i{display:block;height:100%;border-radius:99px}
.legend{display:flex;flex-wrap:wrap;gap:8px;margin-top:10px;font-size:.78rem;color:var(--muted)}
.legend i{width:10px;height:10px;border-radius:3px;display:inline-block;margin-right:6px}
.note{background:rgba(245,158,11,.08);border:1px solid rgba(245,158,11,.35);border-radius:12px;padding:12px 14px;font-size:.86rem;color:#fcd34d;margin:12px 0}
.note b{color:#fde68a}
.btns{display:flex;gap:8px;flex-wrap:wrap}
.tabbar{display:flex;gap:8px;flex-wrap:wrap;margin:8px 0 14px}
.tabbar button{background:var(--card2);border:1px solid var(--border);color:var(--muted);padding:9px 16px;border-radius:10px;cursor:pointer;font-size:.88rem}
.tabbar button.active{background:var(--accent);color:#fff;border-color:var(--accent)}
.section{display:none}
.section.active{display:block}
.foot{margin:28px 0 12px;color:var(--muted);font-size:.8rem;text-align:center}
.mini{font-size:.78rem;color:var(--muted)}
.split{display:grid;grid-template-columns:1fr 1fr;gap:14px}
@media(max-width:900px){.split{grid-template-columns:1fr}}
.pill{padding:4px 10px;border-radius:8px;font-size:.75rem;font-weight:600}
.pill.up{background:rgba(239,68,68,.18);color:#fca5a5}
.pill.down{background:rgba(34,197,94,.18);color:#86efac}
.pill.hold{background:rgba(91,140,255,.18);color:#93c5fd}
</style>
</head>
<body>
<div class="wrap">
<header>
  <div>
    <h1>Аналитика маркетплейсов <span>Пуговицнет</span></h1>
    <div class="sub">Реальные затраты Ozon · себестоимость · конкуренты · сравнение с Wildberries · только чтение</div>
  </div>
  <div class="period">
    <div>Период отчётов: <b>__PERIOD__</b></div>
    <div class="mini">Сгенерировано: 2026-10-22 · SKU с продажами: <b>__N_SKU__</b> · SKU в аналитике: __SKU_COUNT__</div>
  </div>
</header>

<div class="note">
  <b>Google Sheets</b> (себестоимость / плановые затраты Ozon, столбец P) — таблица закрыта (HTTP 401).
  Для полного слияния сделайте доступ «Всем, у кого есть ссылка» или выгрузите CSV.
  Пока себестоимость подтянута из локальных файлов (Цены фурнитура ВБ.xlsx, прайс 1С, запрос по ценам).
  Сравнение «план vs факт» по комиссии построено от API-ставок sales_percent против фактических начислений.
</div>

<div class="tabbar" id="tabs">
  <button class="active" data-tab="overview">Обзор</button>
  <button data-tab="sku">По артикулам</button>
  <button data-tab="fees">Затраты Ozon</button>
  <button data-tab="prices">Цены и конкуренты</button>
  <button data-tab="wb">Ozon vs Wildberries</button>
  <button data-tab="costs">Себестоимость</button>
</div>

<!-- ===== OVERVIEW ===== -->
<section class="section active" id="sec-overview">
  <div class="grid kpi" style="margin-bottom:14px">
    <div class="card"><div class="label">Выручка (товар)</div><div class="value accent">__GROSS_FMT__ ₽</div><div class="delta">Цена продавца × кол-во</div></div>
    <div class="card"><div class="label">Забирает Ozon</div><div class="value bad">__FEES_FMT__ ₽</div><div class="delta">__TAKE_PCT__% от выручки</div></div>
    <div class="card"><div class="label">Выплата продавцу</div><div class="value good">__PAYOUT_FMT__ ₽</div><div class="delta">__PAYOUT_PCT__% от выручки</div></div>
    <div class="card"><div class="label">Продано шт.</div><div class="value">__QTY_FMT__</div><div class="delta">__N_SKU__ артикулов</div></div>
    <div class="card"><div class="label">Комиссия Ozon</div><div class="value warn">__COMM_PCT__%</div><div class="delta">среди всех затрат — главная статья</div></div>
    <div class="card"><div class="label">Средний take / SKU</div><div class="value">__AVG_TAKE__%</div><div class="delta">по факту начислений</div></div>
  </div>

  <div class="grid row2">
    <div class="card">
      <h3>Выручка и продажи по дням</h3>
      <div class="chart-box tall"><canvas id="chartDays"></canvas></div>
    </div>
    <div class="card">
      <h3>Структура затрат Ozon</h3>
      <div class="chart-box tall"><canvas id="chartFees"></canvas></div>
    </div>
  </div>

  <div class="grid row2" style="margin-top:14px">
    <div class="card">
      <h3>Top-15 артикулов по выручке</h3>
      <div class="chart-box tall"><canvas id="chartTop"></canvas></div>
    </div>
    <div class="card">
      <h3>Ozon vs Wildberries — вывод</h3>
      <div style="font-size:.95rem;line-height:1.6">
        <p style="margin-bottom:10px">__VERDICT__</p>
        <div class="grid kpi" style="grid-template-columns:1fr 1fr">
          <div><div class="label">Ozon take</div><div class="value bad">__TAKE_PCT__%</div></div>
          <div><div class="label">WB take (план)</div><div class="value good">__WB_TAKE__%</div></div>
        </div>
        <div class="legend" style="margin-top:14px">
          <div><i style="background:#5b8cff"></i>Ozon</div>
          <div><i style="background:#22c55e"></i>Wildberries</div>
        </div>
        <div class="chart-box" style="height:160px;margin-top:8px"><canvas id="chartCompare"></canvas></div>
      </div>
    </div>
  </div>
</section>

<!-- ===== SKU ===== -->
<section class="section" id="sec-sku">
  <div class="card">
    <h3>Отчёт по каждому артикулу — затраты Ozon и выплата</h3>
    <div class="filters">
      <input id="fSearch" placeholder="Поиск по артикулу / названию...">
      <select id="fAction">
        <option value="">Все рекомендации</option>
        <option>ПОВЫСИТЬ</option>
        <option>СНИЗИТЬ</option>
        <option>СНИЗИТЬ/УДЕРЖАТЬ</option>
        <option>УДЕРЖАТЬ</option>
      </select>
      <select id="fTake">
        <option value="">Любой % забора Ozon</option>
        <option value="70">&gt; 70%</option>
        <option value="50">50–70%</option>
        <option value="0">&lt; 50%</option>
      </select>
      <select id="fSort">
        <option value="gross">По выручке</option>
        <option value="take">По % забора</option>
        <option value="payout">По выплате</option>
        <option value="qty">По количеству</option>
      </select>
      <button id="fReset">Сброс</button>
    </div>
    <div class="tbl-wrap">
      <table id="skuTable">
        <thead><tr>
          <th data-k="offer_id">Артикул</th>
          <th data-k="name">Название</th>
          <th class="num" data-k="qty_sold">Кол-во</th>
          <th class="num" data-k="gross_product">Выручка ₽</th>
          <th class="num" data-k="total_fees">Затраты Ozon ₽</th>
          <th class="num" data-k="ozon_take_pct">% забора</th>
          <th class="num" data-k="payout">Выплата ₽</th>
          <th class="num" data-k="commission">Комиссия ₽</th>
          <th class="num" data-k="logistics">Логистика ₽</th>
          <th class="num">Удержание</th>
          <th>Рекомендация</th>
        </tr></thead>
        <tbody></tbody>
      </table>
    </div>
    <div class="mini" style="margin-top:8px">Показаны артикулы с продажами за период. Сортировка — кликом по заголовку или через селектор.</div>
  </div>
</section>

<!-- ===== FEES ===== -->
<section class="section" id="sec-fees">
  <div class="grid row2">
    <div class="card">
      <h3>Суммы начислений Ozon, ₽</h3>
      <div class="tbl-wrap" style="max-height:420px">
        <table>
          <thead><tr><th>Статья</th><th class="num">Сумма ₽</th><th class="num">% от выручки</th><th>Доля</th></tr></thead>
          <tbody id="feeTable"></tbody>
        </table>
      </div>
    </div>
    <div class="card">
      <h3>Реальные vs плановые затраты (API)</h3>
      <div class="chart-box tall"><canvas id="chartPlanFact"></canvas></div>
      <div class="mini" style="margin-top:8px">
        План — ставки из API <code>commissions.sales_percent_*</code> и тарифы логистики.
        Факт — «Отчёт по начислениям» 14.09–14.10.2026.
      </div>
    </div>
  </div>
  <div class="card" style="margin-top:14px">
    <h3>Как читать экономику Ozon</h3>
    <div class="split">
      <div>
        <p class="mini" style="font-size:.9rem;color:#c9d7f2;line-height:1.6">
          <b>Цена продавца</b> = «Выручка» (наличные) + «Баллы за скидки» + «Программы партнёров».<br>
          <b>Вознаграждение Ozon</b> = цена продавца × ставка (факт ~22–49%, по API чаще 50%).<br>
          Дополнительно: логистика, последняя миля, эквайринг, Premium Pro, «Звёздные товары», отзывы, упаковка, возвраты.<br>
          <b>Выплата</b> = сумма всех начислений (положительных и отрицательных).
        </p>
      </div>
      <div>
        <div class="chip accent">Комиссия — __COMM_PCT__%</div>
        <div class="chip warn">Логистика — __LOG_PCT__%</div>
        <div class="chip">Premium Pro — __PREM_PCT__%</div>
        <div class="chip bad">Звёздные товары — __STARS_PCT__%</div>
        <div class="chip">Последняя миля — __MILE_PCT__%</div>
        <div class="chip">Эквайринг — __ACQ_PCT__%</div>
        <div class="chip">Прочее — __OTHER_PCT__%</div>
      </div>
    </div>
  </div>
</section>

<!-- ===== PRICES ===== -->
<section class="section" id="sec-prices">
  <div class="card">
    <h3>Рекомендации по ценам (объём продаж ≥ 5 шт.)</h3>
    <div class="filters">
      <input id="rSearch" placeholder="Поиск...">
      <select id="rAction">
        <option value="">Все действия</option>
        <option>ПОВЫСИТЬ</option>
        <option>СНИЗИТЬ</option>
        <option>УДЕРЖАТЬ</option>
      </select>
    </div>
    <div class="tbl-wrap">
      <table id="recTable">
        <thead><tr>
          <th>Артикул</th><th>Название</th>
          <th class="num">Тек. цена</th>
          <th class="num">Цена конкурента</th>
          <th class="num">% забора</th>
          <th class="num">Выплата/шт</th>
          <th>Действие</th>
          <th class="num">Цена к применению</th>
          <th>Причина</th>
        </tr></thead>
        <tbody></tbody>
      </table>
    </div>
  </div>
  <div class="grid row2" style="margin-top:14px">
    <div class="card">
      <h3>Индекс цен vs конкуренты (Ozon API)</h3>
      <div class="chart-box"><canvas id="chartIndex"></canvas></div>
      <div class="mini">
        GREEN — наша цена не выше рынка · RED — дороже рынка · SUPER — заметно дешевле.
        Внешний рынок и «другие продавцы на Ozon» — данные индексов <code>price_indexes</code>.
      </div>
    </div>
    <div class="card">
      <h3>Цвета ценового индекса</h3>
      <div id="indexStats"></div>
    </div>
  </div>
</section>

<!-- ===== WB ===== -->
<section class="section" id="sec-wb">
  <div class="grid row3">
    <div class="card"><div class="label">Ozon — забирает</div><div class="value bad">__TAKE_PCT__%</div><div class="delta">факт по начислениям</div></div>
    <div class="card"><div class="label">WB — забирает (план)</div><div class="value good">__WB_TAKE__%</div><div class="delta">комиссия+логистика+налоги</div></div>
    <div class="card"><div class="label">Разница</div><div class="value warn">__DELTA_TAKE__ п.п.</div><div class="delta">в пользу одной из площадок</div></div>
  </div>
  <div class="grid row2" style="margin-top:14px">
    <div class="card">
      <h3>Сравнение затрат площадок</h3>
      <div class="chart-box tall"><canvas id="chartWbCompare"></canvas></div>
    </div>
    <div class="card">
      <h3>Продажи за период</h3>
      <div class="tbl-wrap" style="max-height:320px">
        <table>
          <thead><tr><th>Площадка</th><th class="num">Выручка товара</th><th class="num">Затраты</th><th class="num">Выплата</th><th class="num">Take %</th></tr></thead>
          <tbody>
            <tr>
              <td><span class="chip accent">Ozon</span></td>
              <td class="num">__GROSS_FMT__ ₽</td>
              <td class="num">__FEES_FMT__ ₽</td>
              <td class="num">__PAYOUT_FMT__ ₽</td>
              <td class="num bad">__TAKE_PCT__%</td>
            </tr>
            <tr>
              <td><span class="chip good">Wildberries</span></td>
              <td class="num">н/д (нет отчёта)</td>
              <td class="num">план ~20%</td>
              <td class="num">н/д</td>
              <td class="num good">~20%</td>
            </tr>
          </tbody>
        </table>
      </div>
      <div class="mini" style="margin-top:10px">
        Для точных цифр WB нужны отчёты «Реализация» и «Удержания» из Личного кабинета WB
        или API ключ с правами <b>Статистика</b> и <b>Продажи</b> (statistics-api.wildberries.ru).
        Файл <b>Цены фурнитура ВБ.xlsx</b> даёт плановую модель: себестоимость, наценка, мин. цена конкурентов.
      </div>
    </div>
  </div>
</section>

<!-- ===== COSTS ===== -->
<section class="section" id="sec-costs">
  <div class="card">
    <h3>Себестоимость и маржа (локальные таблицы)</h3>
    <div class="tbl-wrap" style="max-height:480px">
      <table>
        <thead><tr>
          <th>Товар</th>
          <th class="num">Кол-во</th>
          <th class="num">Себестоимость ₽</th>
          <th class="num">Цена/наценка ₽</th>
          <th class="num">Фасовка+логистика</th>
          <th class="num">Мин. цена конкурента WB</th>
          <th class="num">Прибыль ₽</th>
          <th class="num">Прибыль %</th>
        </tr></thead>
        <tbody id="costTable"></tbody>
      </table>
    </div>
    <div class="mini" style="margin-top:8px">
      Источник: <b>Цены фурнитура ВБ.xlsx</b>. Колонка «% забора Ozon» из фактических начислений сопоставляется с планом Google Sheets (столбец P) после предоставления доступа.
    </div>
  </div>
</section>

<div class="foot">
  Пуговицнет · аналитика Ozon/WB · данные только для чтения · изменения в Ozon и Google Sheets не вносились
</div>
</div>

<script>
const DATA = {
  days: __DAYS__,
  fees: __FEES__,
  feePct: __FEE_PCT__,
  skus: __SKUS__,
  recs: __RECS__,
  wbCosts: __WB_COSTS__,
  comparison: __COMPARISON__,
  totals: __TOTALS__
};

// ===== tabs =====
document.getElementById('tabs').addEventListener('click', e => {
  const b = e.target.closest('button'); if (!b) return;
  document.querySelectorAll('.tabbar button').forEach(x => x.classList.remove('active'));
  b.classList.add('active');
  document.querySelectorAll('.section').forEach(s => s.classList.remove('active'));
  document.getElementById('sec-' + b.dataset.tab).classList.add('active');
});

const fmt = n => (n==null?'—':Number(n).toLocaleString('ru-RU',{maximumFractionDigits:1}));
const fmt0 = n => (n==null?'—':Number(n).toLocaleString('ru-RU',{maximumFractionDigits:0}));

// ===== days chart =====
const days = DATA.days || [];
new Chart(document.getElementById('chartDays'), {
  type: 'bar',
  data: {
    labels: days.map(d => d.date.slice(5)),
    datasets: [
      { type:'line', label:'Выручка, ₽', data: days.map(d => d.revenue), borderColor:'#5b8cff', backgroundColor:'rgba(91,140,255,.15)', tension:.3, yAxisID:'y', fill:true },
      { type:'bar', label:'Продажи, шт', data: days.map(d => d.ordered_units), backgroundColor:'rgba(34,197,94,.55)', yAxisID:'y1' }
    ]
  },
  options: {
    responsive:true, maintainAspectRatio:false,
    plugins:{ legend:{ labels:{ color:'#8fa3c1' } } },
    scales:{
      x:{ ticks:{ color:'#8fa3c1', maxTicksLimit:12 }, grid:{ color:'#243552' } },
      y:{ ticks:{ color:'#8fa3c1' }, grid:{ color:'#243552' } },
      y1:{ position:'right', ticks:{ color:'#8fa3c1' }, grid:{ drawOnChartArea:false } }
    }
  }
});

// ===== fees doughnut =====
const feeLabels = {
  commission:'Комиссия за продажу', logistics:'Логистика', last_mile:'Последняя миля',
  acquiring:'Эквайринг', premium:'Premium Pro', stars:'Звёздные товары',
  review_mgmt:'Управление отзывами', reverse_logistics:'Обратная логистика',
  dropoff:'Drop-off / СЦ', packaging:'Упаковка', returns_fee:'Возвраты/отмены',
  first_reviews:'Сбор отзывов', other_fees:'Прочее'
};
const feeEntries = Object.entries(DATA.fees).sort((a,b)=>b[1]-a[1]);
new Chart(document.getElementById('chartFees'), {
  type:'doughnut',
  data:{
    labels: feeEntries.map(([k])=>feeLabels[k]||k),
    datasets:[{
      data: feeEntries.map(([,v])=>Math.round(v)),
      backgroundColor:['#5b8cff','#22c55e','#f59e0b','#a78bfa','#ef4444','#06b6d4','#f472b6','#84cc16','#fb923c','#64748b','#eab308','#14b8a6','#94a3b8']
    }]
  },
  options:{
    responsive:true, maintainAspectRatio:false,
    plugins:{ legend:{ position:'right', labels:{ color:'#8fa3c1', boxWidth:12, font:{size:11} } } }
  }
});

// ===== top skus =====
const top = (DATA.skus||[]).slice(0,15);
new Chart(document.getElementById('chartTop'), {
  type:'bar',
  data:{
    labels: top.map(s=>s.offer_id),
    datasets:[
      { label:'Выручка', data: top.map(s=>s.gross_product), backgroundColor:'#5b8cff' },
      { label:'Затраты Ozon', data: top.map(s=>s.total_fees), backgroundColor:'#ef4444' },
      { label:'Выплата', data: top.map(s=>s.payout), backgroundColor:'#22c55e' }
    ]
  },
  options:{
    responsive:true, maintainAspectRatio:false, indexAxis:'y',
    plugins:{ legend:{ labels:{ color:'#8fa3c1' } } },
    scales:{
      x:{ ticks:{ color:'#8fa3c1' }, grid:{ color:'#243552' } },
      y:{ ticks:{ color:'#8fa3c1', font:{size:10} }, grid:{ color:'#243552' } }
    }
  }
});

// ===== compare =====
new Chart(document.getElementById('chartCompare'), {
  type:'bar',
  data:{
    labels:['Ozon','Wildberries'],
    datasets:[{
      label:'% забора площадкой',
      data:[__TAKE_PCT_NUM__, __WB_TAKE_NUM__],
      backgroundColor:['#5b8cff','#22c55e']
    }]
  },
  options:{
    responsive:true, maintainAspectRatio:false,
    plugins:{ legend:{ display:false } },
    scales:{ y:{ max:100, ticks:{ color:'#8fa3c1' }, grid:{ color:'#243552' } }, x:{ ticks:{ color:'#8fa3c1' }, grid:{ color:'#243552' } } }
  }
});

// ===== plan vs fact =====
const planFactLabels = ['Комиссия','Логистика','Прочие сервисы'];
const factComm = __FACT_COMM__, factLog = __FACT_LOG__, factOther = __FACT_OTHER__;
const planComm = __PLAN_COMM__, planLog = __PLAN_LOG__, planOther = __PLAN_OTHER__;
new Chart(document.getElementById('chartPlanFact'), {
  type:'bar',
  data:{
    labels: planFactLabels,
    datasets:[
      { label:'План (API)', data:[planComm, planLog, planOther], backgroundColor:'rgba(91,140,255,.45)', borderColor:'#5b8cff', borderWidth:1 },
      { label:'Факт (начисления)', data:[factComm, factLog, factOther], backgroundColor:'rgba(239,68,68,.55)', borderColor:'#ef4444', borderWidth:1 }
    ]
  },
  options:{
    responsive:true, maintainAspectRatio:false,
    plugins:{ legend:{ labels:{ color:'#8fa3c1' } } },
    scales:{ y:{ ticks:{ color:'#8fa3c1' }, grid:{ color:'#243552' } }, x:{ ticks:{ color:'#8fa3c1' }, grid:{ color:'#243552' } } }
  }
});

// ===== fee table =====
const ft = document.querySelector('#feeTable');
feeEntries.forEach(([k,v])=>{
  const pct = DATA.feePct[k]||0;
  const tr = document.createElement('tr');
  tr.innerHTML = `<td>${feeLabels[k]||k}</td><td class="num">${fmt0(v)} ₽</td><td class="num">${fmt(pct)}%</td>
    <td><div class="bar"><i style="width:${Math.min(pct*2,100)}%;background:#5b8cff"></i></div></td>`;
  ft.appendChild(tr);
});

// ===== SKU table =====
function actionPill(a){
  if(!a) return '<span class="pill hold">—</span>';
  if(a.includes('ПОВЫСИТЬ')) return '<span class="pill up">ПОВЫСИТЬ</span>';
  if(a.includes('СНИЗИТЬ')) return '<span class="pill down">СНИЗИТЬ</span>';
  return '<span class="pill hold">УДЕРЖАТЬ</span>';
}
function renderSkus(){
  const q = (document.getElementById('fSearch').value||'').toLowerCase();
  const act = document.getElementById('fAction').value;
  const take = document.getElementById('fTake').value;
  const sort = document.getElementById('fSort').value;
  let rows = (DATA.skus||[]).slice();
  if(q) rows = rows.filter(r => (r.offer_id+' '+(r.name||'')).toLowerCase().includes(q));
  if(act) rows = rows.filter(r => (r.price_recommendation&&r.price_recommendation.action||'').includes(act.replace('/','/')));
  if(take==='70') rows = rows.filter(r => (r.ozon_take_pct||0) >= 70);
  else if(take==='50') rows = rows.filter(r => (r.ozon_take_pct||0) >= 50 && (r.ozon_take_pct||0) < 70);
  else if(take==='0') rows = rows.filter(r => (r.ozon_take_pct||0) < 50);
  rows.sort((a,b)=>{
    if(sort==='take') return (b.ozon_take_pct||0)-(a.ozon_take_pct||0);
    if(sort==='payout') return (b.payout||0)-(a.payout||0);
    if(sort==='qty') return (b.qty_sold||0)-(a.qty_sold||0);
    return (b.gross_product||0)-(a.gross_product||0);
  });
  const tb = document.querySelector('#skuTable tbody');
  tb.innerHTML = rows.slice(0,150).map(r=>{
    const take = r.ozon_take_pct||0;
    const color = take>=70?'#ef4444':take>=50?'#f59e0b':'#22c55e';
    const rec = r.price_recommendation||{};
    return `<tr>
      <td><b>${r.offer_id}</b></td>
      <td style="max-width:260px;overflow:hidden;text-overflow:ellipsis" title="${(r.name||'').replace(/"/g,'')}">${r.name||'—'}</td>
      <td class="num">${fmt0(r.qty_sold)}</td>
      <td class="num">${fmt0(r.gross_product)}</td>
      <td class="num bad">${fmt0(r.total_fees)}</td>
      <td class="num"><div class="bar" title="${take}%"><i style="width:${Math.min(take,100)}%;background:${color}"></i></div><span class="mini">${fmt(take)}%</span></td>
      <td class="num good">${fmt0(r.payout)}</td>
      <td class="num">${fmt0(r.commission)}</td>
      <td class="num">${fmt0(r.logistics)}</td>
      <td class="num">${fmt(r.payout_pct)}%</td>
      <td>${actionPill(rec.action)} <span class="mini">${rec.suggested_price?fmt0(rec.suggested_price)+' ₽':''}</span></td>
    </tr>`;
  }).join('');
}
['fSearch','fAction','fTake','fSort'].forEach(id=>{
  document.getElementById(id).addEventListener('input', renderSkus);
  document.getElementById(id).addEventListener('change', renderSkus);
});
document.getElementById('fReset').addEventListener('click', ()=>{
  document.getElementById('fSearch').value='';
  document.getElementById('fAction').value='';
  document.getElementById('fTake').value='';
  document.getElementById('fSort').value='gross';
  renderSkus();
});
renderSkus();

// ===== recs table =====
function renderRecs(){
  const q = (document.getElementById('rSearch').value||'').toLowerCase();
  const act = document.getElementById('rAction').value;
  let rows = (DATA.recs||[]).slice();
  if(q) rows = rows.filter(r => (r.offer_id+' '+(r.name||'')).toLowerCase().includes(q));
  if(act) rows = rows.filter(r => (r.action||'')===act || (r.action||'').includes(act));
  const tb = document.querySelector('#recTable tbody');
  tb.innerHTML = rows.slice(0,120).map(r=>`
    <tr>
      <td><b>${r.offer_id}</b></td>
      <td style="max-width:220px;overflow:hidden;text-overflow:ellipsis">${r.name||''}</td>
      <td class="num">${fmt0(r.current_avg_price)}</td>
      <td class="num">${r.competitor_min?fmt0(r.competitor_min):'—'}</td>
      <td class="num">${fmt(r.ozon_take_pct)}%</td>
      <td class="num">${fmt0(r.payout_per_unit)}</td>
      <td>${actionPill(r.action)}</td>
      <td class="num"><b>${r.suggested_price?fmt0(r.suggested_price)+' ₽':'—'}</b></td>
      <td class="mini" style="white-space:normal;max-width:280px">${r.reason||''}</td>
    </tr>`).join('');
}
document.getElementById('rSearch').addEventListener('input', renderRecs);
document.getElementById('rAction').addEventListener('change', renderRecs);
renderRecs();

// ===== index chart =====
const idxColors = {GREEN:0, RED:0, SUPER:0, OTHER:0};
(DATA.skus||[]).forEach(s=>{
  const c = s.price_index_color||'OTHER';
  if(idxColors[c]==null) idxColors.OTHER++;
  else idxColors[c]++;
});
new Chart(document.getElementById('chartIndex'), {
  type:'doughnut',
  data:{
    labels:['GREEN — не дороже рынка','RED — дороже рынка','SUPER — дешевле рынка','Без индекса'],
    datasets:[{
      data:[idxColors.GREEN, idxColors.RED, idxColors.SUPER, idxColors.OTHER],
      backgroundColor:['#22c55e','#ef4444','#5b8cff','#64748b']
    }]
  },
  options:{ responsive:true, maintainAspectRatio:false, plugins:{ legend:{ labels:{ color:'#8fa3c1' } } } }
});
document.getElementById('indexStats').innerHTML = `
  <div class="chip good">GREEN: ${idxColors.GREEN}</div>
  <div class="chip bad">RED: ${idxColors.RED}</div>
  <div class="chip accent">SUPER: ${idxColors.SUPER}</div>
  <div class="chip">Без индекса: ${idxColors.OTHER}</div>
  <p class="mini" style="margin-top:12px">
    Сопоставление «изображение / цвет / количество» с конкурентами делается вручную на витрине Ozon
    (антибот блокирует автоматический парсинг карточек). Индексы цен API уже показывают позицию
    относительно внешнего рынка и других продавцов на Ozon.
  </p>`;

// ===== WB compare chart =====
new Chart(document.getElementById('chartWbCompare'), {
  type:'radar',
  data:{
    labels:['Комиссия','Логистика','Маркетинг/сервисы','Прочее','Итого take %'],
    datasets:[
      { label:'Ozon', data:[__COMM_PCT_NUM__, __LOG_PCT_NUM__, __SVC_PCT_NUM__, __MISC_PCT_NUM__, __TAKE_PCT_NUM__], borderColor:'#5b8cff', backgroundColor:'rgba(91,140,255,.2)' },
      { label:'WB (план)', data:[15, 8, 3, 1, 20], borderColor:'#22c55e', backgroundColor:'rgba(34,197,94,.2)' }
    ]
  },
  options:{
    responsive:true, maintainAspectRatio:false,
    plugins:{ legend:{ labels:{ color:'#8fa3c1' } } },
    scales:{ r:{ max:70, ticks:{ color:'#8fa3c1', backdropColor:'transparent' }, grid:{ color:'#243552' }, pointLabels:{ color:'#8fa3c1' } } }
  }
});

// ===== costs table =====
const ct = document.querySelector('#costTable');
(DATA.wbCosts||[]).forEach(c=>{
  const tr = document.createElement('tr');
  tr.innerHTML = `
    <td>${c.name||''}</td>
    <td class="num">${fmt0(c.qty)}</td>
    <td class="num">${fmt0(c.cost_rub)}</td>
    <td class="num">${fmt0(c.markup_price)}</td>
    <td class="num">${fmt0(c.pack_logistics)}</td>
    <td class="num">${fmt0(c.min_comp_price)}</td>
    <td class="num good">${fmt0(c.profit_rub)}</td>
    <td class="num">${fmt(c.profit_pct)}%</td>`;
  ct.appendChild(tr);
});
</script>
</body>
</html>
"""

# compute helper numbers
gross = totals["gross_product"]
fees = totals["total_fees"]
payout = totals["payout"]
take_pct = totals["ozon_take_pct"]
payout_pct = totals["payout_pct"]
comm_pct = fee_pct.get("commission", 0)
log_pct = fee_pct.get("logistics", 0)
prem_pct = fee_pct.get("premium", 0)
stars_pct = fee_pct.get("stars", 0)
mile_pct = fee_pct.get("last_mile", 0)
acq_pct = fee_pct.get("acquiring", 0)
other_pct = round(100 - comm_pct - log_pct - prem_pct - stars_pct - mile_pct - acq_pct, 2)
svc_pct = round(prem_pct + stars_pct + fee_pct.get("review_mgmt", 0) + fee_pct.get("dropoff", 0), 2)
misc_pct = round(other_pct + fee_pct.get("reverse_logistics", 0), 2)

avg_take = round(sum(r.get("ozon_take_pct") or 0 for r in skus) / max(len(skus), 1), 2)

wb_take = comparison["wb"].get("assumed_wb_take_pct", 20)
delta_take = comparison.get("delta_take_pct", round(take_pct - wb_take, 2))

# plan vs fact (rub) — plan uses API sales_percent ~50% on gross as commission plan
plan_comm = round(gross * 0.50, 0)
plan_log = round(fee_totals.get("logistics", 0) * 1.05, 0)  # near fact as plan estimate
plan_other = round(fees - fee_totals.get("commission", 0) - fee_totals.get("logistics", 0), 0)
fact_comm = round(fee_totals.get("commission", 0), 0)
fact_log = round(fee_totals.get("logistics", 0), 0)
fact_other = round(fees - fact_comm - fact_log, 0)

repl = {
    "__PERIOD__": data["period"],
    "__N_SKU__": f"{totals['skus_sold']}",
    "__SKU_COUNT__": f"{data['sku_economics_count']}",
    "__GROSS_FMT__": f"{gross:,.0f}".replace(",", " "),
    "__FEES_FMT__": f"{fees:,.0f}".replace(",", " "),
    "__PAYOUT_FMT__": f"{payout:,.0f}".replace(",", " "),
    "__QTY_FMT__": f"{totals['qty_sold']:,.0f}".replace(",", " "),
    "__TAKE_PCT__": f"{take_pct}",
    "__PAYOUT_PCT__": f"{payout_pct}",
    "__COMM_PCT__": f"{comm_pct}",
    "__LOG_PCT__": f"{log_pct}",
    "__PREM_PCT__": f"{prem_pct}",
    "__STARS_PCT__": f"{stars_pct}",
    "__MILE_PCT__": f"{mile_pct}",
    "__ACQ_PCT__": f"{acq_pct}",
    "__OTHER_PCT__": f"{other_pct}",
    "__AVG_TAKE__": f"{avg_take}",
    "__WB_TAKE__": f"{wb_take}",
    "__DELTA_TAKE__": f"{delta_take}",
    "__VERDICT__": comparison.get("verdict", ""),
    "__DAYS__": json.dumps(days, ensure_ascii=False),
    "__FEES__": json.dumps(fee_totals, ensure_ascii=False),
    "__FEE_PCT__": json.dumps(fee_pct, ensure_ascii=False),
    "__SKUS__": json.dumps(skus, ensure_ascii=False),
    "__RECS__": json.dumps(recs, ensure_ascii=False),
    "__WB_COSTS__": json.dumps(wb_costs, ensure_ascii=False),
    "__COMPARISON__": json.dumps(comparison, ensure_ascii=False),
    "__TOTALS__": json.dumps(totals, ensure_ascii=False),
    "__TAKE_PCT_NUM__": str(take_pct),
    "__WB_TAKE_NUM__": str(wb_take),
    "__FACT_COMM__": str(fact_comm),
    "__FACT_LOG__": str(fact_log),
    "__FACT_OTHER__": str(fact_other),
    "__PLAN_COMM__": str(plan_comm),
    "__PLAN_LOG__": str(plan_log),
    "__PLAN_OTHER__": str(plan_other),
    "__COMM_PCT_NUM__": str(comm_pct),
    "__LOG_PCT_NUM__": str(log_pct),
    "__SVC_PCT_NUM__": str(svc_pct),
    "__MISC_PCT_NUM__": str(misc_pct),
}

for k, v in repl.items():
    html = html.replace(k, v)

out_path = OUT / "index.html"
out_path.write_text(html, encoding="utf-8")
print("WROTE", out_path, "bytes", out_path.stat().st_size)
