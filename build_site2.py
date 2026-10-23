"""Rebuild analytics dashboard: local Chart.js, working filters, period, cost J, plan P vs fact."""
import json
from pathlib import Path

OUT = Path(r"C:\Users\Alex\ozon_analytics")
web = json.load(open(OUT / "website_data.json", encoding="utf-8"))
chart_js = (OUT / "chart.umd.min.js").read_text(encoding="utf-8")

days = web["days"]
skus = web["sku_economics"][:250]
recs = list(web["price_recommendations"][:200])

# Wildberries economics (read-only API + gsheet plan)
wb_econ_path = OUT / "wb_economics.json"
wb_econ = json.load(open(wb_econ_path, encoding="utf-8")) if wb_econ_path.exists() else {"skus": [], "totals": {}}
wb_skus = (wb_econ.get("skus") or [])[:200]
wb_totals = wb_econ.get("totals") or {}
wb_notes = wb_econ.get("notes") or {}


def _rec_from_sku(s):
    """Map sku economics row → rec-table shape (for filter parity)."""
    qty = s.get("qty_sold") or 1
    payout = s.get("payout")
    payout_u = round(payout / max(qty, 1), 2) if payout is not None else None
    return {
        "offer_id": s.get("offer_id"),
        "name": s.get("name"),
        "qty_sold": s.get("qty_sold"),
        "current_price_ozon": s.get("price_ozon"),
        "avg_sale_price": s.get("avg_sale_price"),
        "cost_rub": s.get("cost_rub"),
        "competitor_price": s.get("competitor_price"),
        "competitor_seller": s.get("competitor_seller"),
        "competitor_source": s.get("competitor_source"),
        "competitor_display": s.get("competitor_display"),
        "ozon_take_pct": s.get("ozon_take_pct"),
        "payout_per_unit": payout_u,
        "profit_unit": s.get("profit_unit"),
        "margin_on_payout_pct": s.get("margin_on_payout_pct"),
        "ozon_fee_plan": s.get("ozon_fee_plan"),
        "ozon_fee_actual_unit": s.get("ozon_fee_actual_unit"),
        "ozon_fee_diff": s.get("ozon_fee_diff"),
        "action": (s.get("price_recommendation") or {}).get("action", "ПРОВЕРИТЬ"),
        "suggested_price": s.get("price_rec_for_margin_k"),
        "reason": "включён как убыточный (для совпадения фильтров)",
    }


# Keep «Убыточные» filter identical on Prices and Costs tabs:
# every unprofitable SKU visible in skus[] must also exist in recs[].
_rec_ids = {r.get("offer_id") for r in recs}
for _s in skus:
    _profit = _s.get("profit_unit")
    if _profit is not None and _profit <= 0 and _s.get("offer_id") not in _rec_ids:
        recs.append(_rec_from_sku(_s))
        _rec_ids.add(_s.get("offer_id"))

wb_costs = web["wb_costs"]
fee_totals = web["fee_totals"]
fee_pct = web["fee_pct"]
totals = web["totals"]
comparison = web["comparison"]
pvf = web.get("plan_vs_fact_sheet") or {}

# keep only needed fields in skus to reduce size
KEEP = [
    "offer_id", "name", "sku", "qty_sold", "qty_returned", "gross_product", "total_fees",
    "ozon_take_pct", "payout", "payout_pct", "commission", "logistics", "last_mile",
    "acquiring", "premium", "stars", "review_mgmt", "reverse_logistics", "dropoff",
    "cost_rub", "ozon_fee_plan", "ozon_fee_actual_unit", "ozon_fee_diff", "ozon_fee_diff_pct",
    "ozon_other_unit", "price_rec_for_margin_k", "target_margin_k", "comm_rate_pct",
    "expected_profit_rec", "expected_payout_rec",
    "profit_unit", "margin_on_payout_pct", "price_ozon", "avg_sale_price", "min_price_ozon", "old_price_ozon",
    "price_source", "competitor_price", "competitor_seller", "competitor_source", "competitor_source_code",
    "competitor_display", "competitor_all",
    "price_index_color", "price_index_value",
    "avg_reward_pct_actual", "api_sales_percent", "schemes", "sheet_name", "retail",
    "ozon_final_price", "required_markup",
]
skus_slim = []
for s in skus:
    skus_slim.append({k: s.get(k) for k in KEEP})

gross = totals["gross_product"]
fees = totals["total_fees"]
payout = totals["payout"]
take_pct = totals["ozon_take_pct"]
payout_pct = totals["payout_pct"]
comm_pct = fee_pct.get("commission", 0)
log_pct = fee_pct.get("logistics", 0)
avg_cost = round(sum(s.get("cost_rub") or 0 for s in skus_slim if s.get("cost_rub")) /
                 max(sum(1 for s in skus_slim if s.get("cost_rub")), 1), 1)

# plan vs fact chart data: per-fee-bucket
plan_fee = pvf.get("avg_plan_fee")
fact_fee = pvf.get("avg_fact_fee")
diff_fee = pvf.get("avg_diff")
diff_pct = pvf.get("avg_diff_pct")

# fee buckets in % for radar
comm_n = fee_pct.get("commission", 0)
log_n = fee_pct.get("logistics", 0)
svc_n = round(fee_pct.get("premium", 0) + fee_pct.get("stars", 0) + fee_pct.get("review_mgmt", 0) + fee_pct.get("dropoff", 0), 2)
misc_n = round(take_pct - comm_n - log_n - svc_n, 2)

html = """<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Пуговицнет — Аналитика Ozon vs WB</title>
<script>/* chart.js local */__CHARTJS__</script>
<style>
:root{
  --bg:#0b1220; --card:#121c2e; --card2:#18253c; --text:#e8eefc; --muted:#8fa3c1;
  --accent:#5b8cff; --good:#22c55e; --warn:#f59e0b; --bad:#ef4444; --purple:#a78bfa;
  --border:#243552; --chip:#1e2d48;
}
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:'Segoe UI',system-ui,sans-serif;background:var(--bg);color:var(--text);line-height:1.45}
.wrap{max-width:1500px;margin:0 auto;padding:18px}
header{display:flex;flex-wrap:wrap;gap:14px;align-items:flex-end;justify-content:space-between;margin-bottom:18px}
h1{font-size:1.5rem;font-weight:700}
h1 span{color:var(--accent)}
.sub{color:var(--muted);font-size:.9rem;margin-top:4px}
.period{background:var(--card);border:1px solid var(--border);border-radius:12px;padding:12px 14px;font-size:.88rem}
.period label{color:var(--muted);font-size:.78rem;display:block;margin-bottom:4px}
.period input{background:var(--card2);border:1px solid var(--border);color:var(--text);border-radius:8px;padding:7px 10px;font-size:.88rem}
.grid{display:grid;gap:14px}
.kpi{grid-template-columns:repeat(auto-fit,minmax(165px,1fr))}
.card{background:var(--card);border:1px solid var(--border);border-radius:16px;padding:16px 18px}
.card h3{font-size:.95rem;font-weight:600;margin-bottom:10px;color:#c9d7f2}
.kpi .label{color:var(--muted);font-size:.76rem;text-transform:uppercase;letter-spacing:.04em}
.kpi .value{font-size:1.4rem;font-weight:700;margin-top:6px}
.kpi .delta{font-size:.78rem;color:var(--muted);margin-top:4px}
.good{color:var(--good)} .bad{color:var(--bad)} .warn{color:var(--warn)} .accent{color:var(--accent)}
.row2{grid-template-columns:1.35fr 1fr}
.row3{grid-template-columns:1fr 1fr 1fr}
@media(max-width:980px){.row2,.row3{grid-template-columns:1fr}}
.chart-box{position:relative;height:280px}
.chart-box.tall{height:320px}
table{width:100%;border-collapse:collapse;font-size:.83rem}
th,td{padding:8px 10px;border-bottom:1px solid var(--border);border-right:1px solid var(--border);text-align:left;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;max-width:none}
td.clip-name{white-space:nowrap;overflow:hidden;text-overflow:ellipsis;max-width:none}
td.wrap-cell{white-space:normal;overflow:visible;text-overflow:clip;word-break:break-word}
thead th{border-bottom:1px solid var(--border)}
tr > *:last-child{border-right:none}
th{color:var(--muted);font-weight:600;font-size:.74rem;text-transform:uppercase;letter-spacing:.03em;cursor:pointer;user-select:none;position:sticky;top:0;background:var(--card);z-index:2}
th .resizer{position:absolute;top:0;right:0;width:7px;height:100%;cursor:col-resize;user-select:none;z-index:3;background:linear-gradient(to right, transparent 0 3px, var(--border) 3px 5px, transparent 5px)}
th .resizer:hover,th .resizer.active{background:var(--accent);opacity:.9}
table.col-resizing{cursor:col-resize}
table.col-resizing th{cursor:col-resize}
.col-hidden{display:none !important}
.col-picker{position:relative;display:inline-block}
.col-picker-btn{background:var(--card2);border:1px solid var(--border);color:var(--text);border-radius:10px;padding:9px 12px;font-size:.88rem;cursor:pointer}
.col-picker-btn:hover{border-color:var(--accent)}
.col-menu{display:none;position:absolute;top:calc(100% + 6px);left:0;right:auto;z-index:50;background:var(--card);border:1px solid var(--border);border-radius:12px;padding:10px;min-width:260px;max-height:360px;overflow:auto;box-shadow:0 12px 40px rgba(0,0,0,.45)}
.col-menu.open{display:block}
.col-menu label{display:flex;align-items:center;justify-content:flex-start;gap:8px;padding:6px 8px;border-radius:8px;font-size:.86rem;cursor:pointer;color:var(--text);text-align:left;width:100%}
.col-menu label:hover{background:rgba(91,140,255,.12)}
.col-menu input{accent-color:var(--accent);margin:0;flex:0 0 auto}
.col-menu label span{flex:1 1 auto;text-align:left}
.col-menu .col-actions{display:flex;gap:8px;margin-top:8px;padding-top:8px;border-top:1px solid var(--border)}
.col-menu .col-actions button{flex:1;background:var(--card2);border:1px solid var(--border);color:var(--muted);border-radius:8px;padding:7px 10px;cursor:pointer;font-size:.8rem}
.col-menu .col-actions button:hover{color:var(--text);border-color:var(--accent)}
tr:hover td{background:rgba(91,140,255,.06)}
.num{text-align:right;font-variant-numeric:tabular-nums}
.tbl-wrap{overflow:auto;max-height:540px;border-radius:12px;border:1px solid var(--border)}
.filters{display:flex;flex-wrap:wrap;gap:10px;margin:12px 0}
.filters input,.filters select,.filters button{
  background:var(--card2);border:1px solid var(--border);color:var(--text);
  border-radius:10px;padding:9px 12px;font-size:.88rem;outline:none}
.filters input{min-width:200px}
.filters button{cursor:pointer;background:var(--accent);border-color:var(--accent);font-weight:600}
.filters button:hover{filter:brightness(1.08)}
.filters button.ghost{background:var(--card2);border-color:var(--border);color:var(--muted)}
.chip{display:inline-block;background:var(--chip);border-radius:999px;padding:3px 10px;font-size:.75rem;margin:2px}
.chip.good{background:rgba(34,197,94,.15);color:#4ade80}
.chip.bad{background:rgba(239,68,68,.15);color:#f87171}
.chip.warn{background:rgba(245,158,11,.15);color:#fbbf24}
.chip.accent{background:rgba(91,140,255,.15);color:#93b4ff}
.bar{height:8px;background:#1a2740;border-radius:99px;overflow:hidden;min-width:70px}
.bar>i{display:block;height:100%;border-radius:99px}
.note{background:rgba(34,197,94,.08);border:1px solid rgba(34,197,94,.3);border-radius:12px;padding:12px 14px;font-size:.86rem;color:#86efac;margin:12px 0}
.note.warnbox{background:rgba(245,158,11,.08);border-color:rgba(245,158,11,.35);color:#fcd34d}
.note b{color:inherit;font-weight:700}
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
.err{color:#fca5a5;background:rgba(239,68,68,.1);padding:8px 12px;border-radius:8px;font-size:.85rem;display:none}
.stat-row{display:flex;justify-content:space-between;align-items:center;padding:10px 0;border-bottom:1px solid var(--border);font-size:.9rem}
.stat-row:last-child{border-bottom:none}
.stat-row .v{font-weight:700;font-variant-numeric:tabular-nums}
</style>
</head>
<body>
<div class="wrap">
<header>
  <div>
    <h1>Аналитика маркетплейсов <span>Пуговицнет</span></h1>
    <div class="sub">Реальные затраты Ozon · себестоимость (табл. J) · план затрат (табл. P) · конкуренты · Ozon vs WB</div>
  </div>
  <div class="period">
    <label>Период отчётов</label>
    <input type="date" id="dFrom" value="__DATE_FROM__"> —
    <input type="date" id="dTo" value="__DATE_TO__">
    <button id="btnPeriod" style="margin-left:8px;background:var(--accent);color:#fff;border:none;border-radius:8px;padding:8px 12px;cursor:pointer;font-weight:600">Применить</button>
    <button id="btnPeriodReset" class="ghost" style="background:var(--card2);color:var(--muted);border:1px solid var(--border);border-radius:8px;padding:8px 12px;cursor:pointer">Весь период</button>
    <div class="mini" style="margin-top:6px">В отчётах Ozon: <b>__PERIOD__</b> · SKU с продажами: <b>__N_SKU__</b></div>
  </div>
</header>

<div class="note">
  <b>Себестоимость</b> — Google Sheets, столбец J · <b>План затрат Ozon</b> — столбец P ·
  <b>Затраты озон на шт</b> — «Отчёт по начислениям» Ozon (реальные комиссия+логистика+прочее). Сопоставлено SKU: __MATCHED__ из __N_SKU__.
  Средняя себестоимость: <b>__AVG_COST__ ₽</b>.
</div>

<div class="note warnbox" id="jsError" style="display:none"></div>

<div class="tabbar" id="tabs">
  <button type="button" class="active" data-tab="overview">Обзор</button>
  <button type="button" data-tab="sku">По артикулам</button>
  <button type="button" data-tab="fees">Затраты Ozon</button>
  <button type="button" data-tab="prices">Цены и конкуренты</button>
  <button type="button" data-tab="wbsku">Аналитика WB</button>
  <button type="button" data-tab="wb">Сравнение Ozon vs WB</button>
  <button type="button" data-tab="costs">Себестоимость и маржа</button>
</div>

<!-- OVERVIEW -->
<section class="section active" id="sec-overview">
  <div class="grid kpi" style="margin-bottom:14px">
    <div class="card"><div class="label">Выручка товара</div><div class="value accent" id="kGross">__GROSS_FMT__ ₽</div><div class="delta">цена продавца × кол-во</div></div>
    <div class="card"><div class="label">Забирает Ozon</div><div class="value bad" id="kFees">__FEES_FMT__ ₽</div><div class="delta"><span id="kTake">__TAKE_PCT__</span>% от выручки</div></div>
    <div class="card"><div class="label">Выплата продавцу</div><div class="value good" id="kPayout">__PAYOUT_FMT__ ₽</div><div class="delta"><span id="kPayPct">__PAYOUT_PCT__</span>% от выручки</div></div>
    <div class="card"><div class="label">Продано</div><div class="value" id="kQty">__QTY_FMT__ шт</div><div class="delta">__N_SKU__ артикулов</div></div>
    <div class="card"><div class="label">Комиссия Ozon</div><div class="value warn">__COMM_PCT__%</div><div class="delta">главная статья затрат</div></div>
    <div class="card"><div class="label">Ср. забор / SKU</div><div class="value">__AVG_TAKE__%</div><div class="delta">по факту начислений</div></div>
    <div class="card"><div class="label">Ср. себестоимость</div><div class="value accent">__AVG_COST__ ₽</div><div class="delta">из таблицы, столбец J</div></div>
    <div class="card"><div class="label">План vs факт затрат</div><div class="value __PVF_CLS__">__PVF_DIFF__%</div><div class="delta">факт к плану (столбец P)</div></div>
  </div>

  <div class="grid row2">
    <div class="card">
      <h3>Выручка и продажи по дням <span class="mini">(с учётом периода)</span></h3>
      <div class="chart-box tall"><canvas id="chartDays"></canvas></div>
    </div>
    <div class="card">
      <h3>Структура затрат Ozon</h3>
      <div class="chart-box tall"><canvas id="chartFees"></canvas></div>
    </div>
  </div>

  <div class="grid row2" style="margin-top:14px">
    <div class="card">
      <h3>Top-15 артикулов: выручка / затраты / выплата</h3>
      <div class="chart-box tall"><canvas id="chartTop"></canvas></div>
    </div>
    <div class="card">
      <h3>Ozon vs Wildberries</h3>
      <p class="mini" style="margin-bottom:10px;font-size:.92rem;color:#c9d7f2">__VERDICT__</p>
      <div class="chart-box" style="height:200px"><canvas id="chartCompare"></canvas></div>
    </div>
  </div>
</section>

<!-- SKU -->
<section class="section" id="sec-sku">
  <div class="card">
    <h3>Отчёт по каждому артикулу — затраты Ozon, себестоимость, выплата</h3>
    <div class="filters">
      <input id="fSearch" type="search" placeholder="Поиск по артикулу / названию...">
      <select id="fAction">
        <option value="">Все рекомендации</option>
        <option value="ПОВЫСИТЬ">ПОВЫСИТЬ</option>
        <option value="СНИЗИТЬ">СНИЗИТЬ</option>
        <option value="УДЕРЖАТЬ">УДЕРЖАТЬ</option>
      </select>
      <select id="fTake">
        <option value="">Любой % забора Ozon</option>
        <option value="high">&gt; 70%</option>
        <option value="mid">50–70%</option>
        <option value="low">&lt; 50%</option>
      </select>
      <select id="fProfit">
        <option value="">Любая маржа</option>
        <option value="neg">Убыточные</option>
        <option value="ok">Прибыльные</option>
      </select>
      <select id="fSort">
        <option value="gross">По выручке</option>
        <option value="take">По % забора</option>
        <option value="payout">По выплате</option>
        <option value="qty">По количеству</option>
        <option value="profit">По прибыли/шт</option>
        <option value="diff">По отклонению план/факт</option>
      </select>
      <button type="button" id="fReset">Сброс фильтров</button>
      <button type="button" class="ghost btn-xls" data-xls="sku">Excel</button>
      <div class="col-picker" id="colPickerSku">
        <button type="button" class="col-picker-btn" data-toggle="colMenuSku">Столбцы ▾</button>
        <div class="col-menu" id="colMenuSku"></div>
      </div>
    </div>
    <div class="tbl-wrap">
      <table id="skuTable">
        <thead><tr>
          <th data-k="offer_id">Артикул</th>
          <th data-k="name">Название</th>
          <th class="num" data-k="qty_sold">Кол-во</th>
          <th class="num" data-k="price_ozon">Цена Ozon ₽</th>
          <th class="num" data-k="competitor_price">Цена конкурента ₽</th>
          <th data-k="competitor_seller">Конкурент / источник</th>
          <th class="num" data-k="gross_product">Выручка ₽</th>
          <th class="num" data-k="total_fees">Затраты Ozon ₽</th>
          <th class="num" data-k="ozon_take_pct">% забора</th>
          <th class="num" data-k="payout">Выплата ₽</th>
          <th class="num" data-k="cost_rub">Себест. ₽</th>
          <th class="num" data-k="ozon_fee_plan">План P ₽/шт</th>
          <th class="num" data-k="ozon_fee_actual_unit">Затраты озон на шт</th>
          <th class="num" data-k="ozon_fee_diff">Δ план/факт</th>
          <th class="num" data-k="profit_unit">Прибыль ₽/шт</th>
          <th class="num" data-k="price_rec_for_margin_k">Рекомендованная цена</th>
          <th>Рекомендация</th>
        </tr></thead>
        <tbody></tbody>
      </table>
    </div>
    <div class="mini" style="margin-top:8px" id="skuCount">—</div>
  </div>
</section>

<!-- FEES -->
<section class="section" id="sec-fees">
  <div class="grid row2">
    <div class="card">
      <h3>Начисления Ozon, ₽ (факт)
        <button type="button" class="ghost btn-xls" data-xls="fee" style="float:right;padding:6px 12px;font-size:.8rem">Excel</button>
      </h3>
      <div class="tbl-wrap" style="max-height:440px">
        <table>
          <thead><tr><th>Статья</th><th class="num">Сумма ₽</th><th class="num">% от выручки</th><th>Доля</th></tr></thead>
          <tbody id="feeTable"></tbody>
        </table>
      </div>
    </div>
    <div class="card">
      <h3>План (табл. P) vs Факт (начисления Ozon)</h3>
      <div class="chart-box tall"><canvas id="chartPlanFact"></canvas></div>
      <div style="margin-top:12px">
        <div class="stat-row"><span>Средний план затрат / шт (столбец P)</span><span class="v accent">__PLAN_FEE__ ₽</span></div>
        <div class="stat-row"><span>Средний факт затрат / шт</span><span class="v bad">__FACT_FEE__ ₽</span></div>
        <div class="stat-row"><span>Отклонение</span><span class="v __PVF_CLS__">__PVF_DIFF__ ₽ (__PVF_DIFF_PCT__%)</span></div>
        <div class="stat-row"><span>SKU в сравнении</span><span class="v">__PVF_N__</span></div>
      </div>
    </div>
  </div>
  <div class="card" style="margin-top:14px">
    <h3>Формула экономики Ozon</h3>
    <div class="split">
      <div class="mini" style="font-size:.92rem;color:#c9d7f2;line-height:1.65">
        <b>Цена продавца</b> = «Выручка» + «Баллы за скидки» + «Программы партнёров».<br>
        <b>Вознаграждение Ozon</b> = цена × ставка (факт 21–50%, в среднем ~48%).<br>
        Далее: логистика, последняя миля, эквайринг, Premium Pro, «Звёздные товары», отзывы, упаковка, возвраты.<br>
        <b>Выплата</b> = сумма всех начислений. <b>Прибыль</b> = выплата − себестоимость (столбец J).
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

<!-- PRICES -->
<section class="section" id="sec-prices">
  <div class="card">
    <h3>Рекомендации по ценам (продажи ≥ 5 шт.)</h3>
    <div class="filters">
      <input id="rSearch" type="search" placeholder="Поиск...">
      <select id="rAction">
        <option value="">Все действия</option>
        <option value="ПОВЫСИТЬ">ПОВЫСИТЬ</option>
        <option value="СНИЗИТЬ">СНИЗИТЬ</option>
        <option value="УДЕРЖАТЬ">УДЕРЖАТЬ</option>
      </select>
      <select id="rMargin">
        <option value="">Любая маржа</option>
        <option value="neg">Убыточные (маржа ≤ 0)</option>
        <option value="low">Маржа &lt; 20%</option>
        <option value="ok">Маржа ≥ 20%</option>
      </select>
      <select id="rMarket">
        <option value="">Любое положение vs рынок</option>
        <option value="cheap">Дешевле рынка</option>
        <option value="dear">Дороже рынка</option>
        <option value="not_dear">Не дороже рынка</option>
        <option value="no_index">Без индекса</option>
      </select>
      <button type="button" id="rReset">Сброс фильтров</button>
      <button type="button" class="ghost btn-xls" data-xls="rec">Excel</button>
      <div class="col-picker" id="colPickerRec">
        <button type="button" class="col-picker-btn" data-toggle="colMenuRec">Столбцы ▾</button>
        <div class="col-menu" id="colMenuRec"></div>
      </div>
    </div>
    <div class="tbl-wrap">
      <table id="recTable">
        <thead><tr>
          <th>Артикул</th><th>Название</th>
          <th class="num">Цена Ozon</th>
          <th class="num">Ср. цена продажи</th>
          <th class="num">Себест.</th>
          <th class="num">Цена конкурента</th>
          <th>Конкурент / источник</th>
          <th class="num">% забора</th>
          <th class="num">Выплата/шт</th>
          <th class="num">Прибыль/шт</th>
          <th>Действие</th>
          <th class="num">Цена к применению</th>
          <th>Причина</th>
        </tr></thead>
        <tbody></tbody>
      </table>
    </div>
    <div class="mini" style="margin-top:8px" id="recCount">—</div>
  </div>
  <div class="grid row2" style="margin-top:14px">
    <div class="card">
      <h3>Индекс цен vs конкуренты</h3>
      <div class="chart-box"><canvas id="chartIndex"></canvas></div>
    </div>
    <div class="card">
      <h3>Распределение индексов</h3>
      <div id="indexStats"></div>
      <p class="mini" style="margin-top:12px">
        <b>Цена Ozon</b> — живая цена из Ozon API <code>/v3/product/info/list</code> (одинакова во всех вкладках).<br>
        <b>Цена конкурента</b> — min price из <code>price_indexes</code> API Ozon.<br>
        <b>Конкурент / источник</b> — все источники из Ozon price_indexes: «Внешние МП» (WB/Я.Маркет/др.), «Другие продавцы на Ozon», «Ozon Retail» (имена магазинов API не отдаёт).
        Имена продавцов-конкурентов Ozon API не раскрывает (поле <code>competitor_index_data</code> пустое) —
        указана площадка-источник, откуда взята min-цена. Для имён конкретных магазинов нужен разовый снимок витрины вручную.
      </p>
    </div>
  </div>
</section>

<!-- WB ANALYTICS -->
<section class="section" id="sec-wbsku">
  <div class="card">
    <h3>Аналитика Wildberries (WB) — карточки, продажи, экономика</h3>
    <div class="note">Данные WB: content-api (карточки) + statistics-api (продажи/заказы, только чтение). Себестоимость — столбец J Google Sheet; план WB-затрат — <code>wb_fee</code>. Все подписи с префиксом <b>WB</b>.</div>
    <div class="grid kpi" style="margin:12px 0">
      <div class="card"><div class="label">WB карточек</div><div class="value" id="wbCards">__WB_N_CARDS__</div><div class="delta">уникальных nmID</div></div>
      <div class="card"><div class="label">WB продано</div><div class="value good" id="wbQty">__WB_QTY__</div><div class="delta">шт за период</div></div>
      <div class="card"><div class="label">WB выручка</div><div class="value accent" id="wbRev">__WB_REV__ ₽</div><div class="delta">salePrice / план</div></div>
      <div class="card"><div class="label">WB Take %</div><div class="value warn" id="wbTake">__WB_TAKE__%</div><div class="delta">забор площадки</div></div>
    </div>
    <div class="filters">
      <input id="wbSearch" type="search" placeholder="Поиск WB (артикул / название)...">
      <select id="wbMargin">
        <option value="">Любая маржа WB</option>
        <option value="neg">WB убыточные (маржа ≤ 0)</option>
        <option value="low">WB маржа &lt; 20%</option>
        <option value="ok">WB маржа ≥ 20%</option>
      </select>
      <button type="button" id="wbReset">Сброс фильтров</button>
      <button type="button" class="ghost btn-xls" data-xls="wb">Excel</button>
      <div class="col-picker" id="colPickerWb">
        <button type="button" class="col-picker-btn" data-toggle="colMenuWb">Столбцы ▾</button>
        <div class="col-menu" id="colMenuWb"></div>
      </div>
    </div>
    <div class="tbl-wrap">
      <table id="wbTable">
        <thead><tr>
          <th>WB артикул</th>
          <th>WB название</th>
          <th>WB предмет</th>
          <th class="num">WB продано</th>
          <th class="num">WB заказано</th>
          <th class="num">WB цена ₽</th>
          <th class="num">WB выручка ₽</th>
          <th class="num">WB забор %</th>
          <th class="num">WB выплата/шт</th>
          <th class="num">Себест. J ₽</th>
          <th class="num">WB план P ₽</th>
          <th class="num">WB прибыль/шт</th>
          <th class="num">WB маржа %</th>
          <th>WB источник</th>
        </tr></thead>
        <tbody></tbody>
      </table>
    </div>
    <div class="mini" style="margin-top:8px" id="wbCount">—</div>
  </div>
</section>

<!-- COMPARE Ozon vs WB -->
<section class="section" id="sec-wb">
  <div class="grid row3">
    <div class="card"><div class="label">Ozon — забирает</div><div class="value bad">__TAKE_PCT__%</div><div class="delta">факт по начислениям</div></div>
    <div class="card"><div class="label">WB — забирает</div><div class="value good">__WB_TAKE__%</div><div class="delta">факт API / план</div></div>
    <div class="card"><div class="label">Разница Take</div><div class="value warn">__DELTA_TAKE__ п.п.</div><div class="delta">Ozon − WB</div></div>
  </div>
  <div class="grid row2" style="margin-top:14px">
    <div class="card">
      <h3>Сравнение Ozon vs WB — затраты, % от выручки</h3>
      <div class="chart-box tall"><canvas id="chartWbCompare"></canvas></div>
    </div>
    <div class="card">
      <h3>Ozon vs WB — ключевые показатели</h3>
      <div class="tbl-wrap" style="max-height:420px">
        <table id="cmpTable">
          <thead><tr>
            <th>Показатель</th>
            <th class="num">Ozon</th>
            <th class="num">WB</th>
            <th class="num">Δ (Ozon − WB)</th>
          </tr></thead>
          <tbody id="cmpBody"></tbody>
        </table>
      </div>
      <div class="mini" style="margin-top:10px">
        <b>Ozon</b> — факт из «Отчёта по начислениям». <b>WB</b> — statistics-api (продажи) + план <code>wb_fee</code> из Google Sheet.
        Показатели с префиксом <b>WB</b> относятся только к Wildberries.
      </div>
    </div>
  </div>
  <div class="card" style="margin-top:14px">
    <h3>Сравнение по артикулам (совпадение vendor / offer)</h3>
    <div class="filters">
      <input id="cmpSearch" type="search" placeholder="Поиск по артикулу...">
      <select id="cmpOnly">
        <option value="">Все совпадения</option>
        <option value="both">Есть на Ozon и WB</option>
        <option value="ozon">Только Ozon</option>
        <option value="wb">Только WB</option>
      </select>
      <button type="button" id="cmpReset">Сброс фильтров</button>
      <button type="button" class="ghost btn-xls" data-xls="cmp">Excel</button>
    </div>
    <div class="tbl-wrap" style="max-height:480px">
      <table id="cmpSkuTable">
        <thead><tr>
          <th>Артикул</th>
          <th>Название</th>
          <th class="num">Ozon цена</th>
          <th class="num">WB цена</th>
          <th class="num">Ozon продано</th>
          <th class="num">WB продано</th>
          <th class="num">Ozon выплата/шт</th>
          <th class="num">WB выплата/шт</th>
          <th class="num">Ozon прибыль/шт</th>
          <th class="num">WB прибыль/шт</th>
          <th class="num">Ozon Take %</th>
          <th class="num">WB Take %</th>
          <th>Площадки</th>
        </tr></thead>
        <tbody></tbody>
      </table>
    </div>
    <div class="mini" style="margin-top:8px" id="cmpCount">—</div>
  </div>
</section>

<!-- COSTS -->
<section class="section" id="sec-costs">
  <div class="card">
    <h3>Себестоимость (столбец J), план затрат Ozon (столбец P) и маржа</h3>
    <div class="filters">
      <input id="cSearch" type="search" placeholder="Поиск...">
      <select id="cMargin">
        <option value="">Любая маржа</option>
        <option value="neg">Убыточные (маржа ≤ 0)</option>
        <option value="low">Маржа &lt; 20%</option>
        <option value="ok">Маржа ≥ 20%</option>
      </select>
      <button type="button" id="cReset">Сброс фильтров</button>
      <button type="button" class="ghost btn-xls" data-xls="cost">Excel</button>
      <div class="col-picker" id="colPickerCost">
        <button type="button" class="col-picker-btn" data-toggle="colMenuCost">Столбцы ▾</button>
        <div class="col-menu" id="colMenuCost"></div>
      </div>
    </div>
    <div class="tbl-wrap" style="max-height:520px">
      <table id="costTable">
        <thead><tr>
          <th>Артикул</th><th>Название</th>
          <th class="num">Себест. J, ₽</th>
          <th class="num">План P, ₽</th>
          <th class="num">Факт, ₽/шт</th>
          <th class="num">Δ P−факт</th>
          <th class="num">Цена</th>
          <th class="num">Выплата/шт</th>
          <th class="num">Прибыль/шт</th>
          <th class="num">Маржа %</th>
          <th class="num">Цена в табл.</th>
        </tr></thead>
        <tbody></tbody>
      </table>
    </div>
    <div class="mini" style="margin-top:8px" id="costCount">—</div>
  </div>
</section>

<div class="foot">Пуговицнет · аналитика Ozon/WB · только чтение · данные из Ozon + Google Sheets</div>
</div>

<script>
"use strict";
const DATA = {
  days: __DAYS__,
  fees: __FEES__,
  feePct: __FEE_PCT__,
  skus: __SKUS__,
  recs: __RECS__,
  wbCosts: __WB_COSTS__,
  totals: __TOTALS__,
  planFact: __PFACT__,
  takePct: __TAKE_PCT_NUM__,
  wbTake: __WB_TAKE_NUM__,
  commPct: __COMM_PCT_NUM__,
  logPct: __LOG_PCT_NUM__,
  svcPct: __SVC_PCT_NUM__,
  miscPct: __MISC_PCT_NUM__,
  wb: __WB_ECON__,
  wbTotals: __WB_TOTALS__,
  ozonTotals: {gross: __GROSS_NUM__, fees: __FEES_NUM__, payout: __PAYOUT_NUM__, take: __TAKE_PCT_NUM__, qty: __QTY_NUM__}
};

/* full filtered rows for Excel export (not the on-screen 200-row cap) */
const EXPORT_STATE = { sku: [], rec: [], cost: [], fee: [] };

const XLS_DEFS = {
  sku: {
    tableId: 'skuTable',
    sheet: 'По артикулам',
    file: 'pugovitsnet_sku',
    cols: [
      {h:'Артикул', k:'offer_id'},
      {h:'Название', k:'name'},
      {h:'Кол-во', k:'qty_sold'},
      {h:'Цена Ozon ₽', k:'price_ozon'},
      {h:'Цена конкурента ₽', k:'competitor_price'},
      {h:'Конкурент / источник', k:'competitor_display'},
      {h:'Выручка ₽', k:'gross_product'},
      {h:'Затраты Ozon ₽', k:'total_fees'},
      {h:'% забора', k:'ozon_take_pct'},
      {h:'Выплата ₽', k:'payout'},
      {h:'Себест. ₽', k:'cost_rub'},
      {h:'План P ₽/шт', k:'ozon_fee_plan'},
      {h:'Затраты озон на шт', k:'ozon_fee_actual_unit'},
      {h:'Δ план/факт', k:'ozon_fee_diff'},
      {h:'Прибыль ₽/шт', k:'profit_unit'},
      {h:'Рекомендованная цена', k:'price_rec_for_margin_k'},
      {h:'Рекомендация', k:'_action'}
    ]
  },
  rec: {
    tableId: 'recTable',
    sheet: 'Цены и конкуренты',
    file: 'pugovitsnet_prices',
    cols: [
      {h:'Артикул', k:'offer_id'},
      {h:'Название', k:'name'},
      {h:'Цена Ozon', k:'current_price_ozon'},
      {h:'Ср. цена продажи', k:'avg_sale_price'},
      {h:'Себест.', k:'cost_rub'},
      {h:'Цена конкурента', k:'competitor_price'},
      {h:'Конкурент / источник', k:'competitor_display'},
      {h:'% забора', k:'ozon_take_pct'},
      {h:'Выплата/шт', k:'payout_per_unit'},
      {h:'Прибыль/шт', k:'profit_unit'},
      {h:'Маржа %', k:'margin_on_payout_pct'},
      {h:'Действие', k:'action'},
      {h:'Цена к применению', k:'suggested_price'},
      {h:'Причина', k:'reason'}
    ]
  },
  cost: {
    tableId: 'costTable',
    sheet: 'Себестоимость',
    file: 'pugovitsnet_costs',
    cols: [
      {h:'Артикул', k:'offer_id'},
      {h:'Название', k:'name'},
      {h:'Себест. J, ₽', k:'cost_rub'},
      {h:'План P, ₽', k:'ozon_fee_plan'},
      {h:'Факт, ₽/шт', k:'ozon_fee_actual_unit'},
      {h:'Δ P−факт', k:'ozon_fee_diff'},
      {h:'Цена', k:'price_ozon'},
      {h:'Выплата/шт', k:'_payout_unit'},
      {h:'Прибыль/шт', k:'profit_unit'},
      {h:'Маржа %', k:'margin_on_payout_pct'},
      {h:'Цена в табл.', k:'ozon_final_price'}
    ]
  },
  fee: {
    tableId: null,
    sheet: 'Затраты Ozon',
    file: 'pugovitsnet_fees',
    cols: [
      {h:'Статья', k:'article'},
      {h:'Сумма ₽', k:'amount'},
      {h:'% от выручки', k:'pct'}
    ]
  },
  wb: {
    tableId: 'wbTable',
    sheet: 'Аналитика WB',
    file: 'pugovitsnet_wb',
    cols: [
      {h:'WB артикул', k:'offer_id'},
      {h:'WB название', k:'name'},
      {h:'WB предмет', k:'subject'},
      {h:'WB продано', k:'qty_sold'},
      {h:'WB заказано', k:'qty_ordered'},
      {h:'WB цена ₽', k:'wb_avg_price'},
      {h:'WB выручка ₽', k:'wb_revenue'},
      {h:'WB забор %', k:'wb_take_pct'},
      {h:'WB выплата/шт', k:'wb_payout_unit'},
      {h:'Себест. J ₽', k:'cost_rub'},
      {h:'WB план P ₽', k:'wb_fee_plan'},
      {h:'WB прибыль/шт', k:'profit_unit'},
      {h:'WB маржа %', k:'margin_on_payout_pct'},
      {h:'WB источник', k:'sales_source'}
    ]
  },
  cmp: {
    tableId: 'cmpSkuTable',
    sheet: 'Ozon vs WB',
    file: 'pugovitsnet_ozon_vs_wb',
    cols: [
      {h:'Артикул', k:'offer_id'},
      {h:'Название', k:'name'},
      {h:'Ozon цена', k:'ozon_price'},
      {h:'WB цена', k:'wb_price'},
      {h:'Ozon продано', k:'ozon_qty'},
      {h:'WB продано', k:'wb_qty'},
      {h:'Ozon выплата/шт', k:'ozon_pay'},
      {h:'WB выплата/шт', k:'wb_pay'},
      {h:'Ozon прибыль/шт', k:'ozon_profit'},
      {h:'WB прибыль/шт', k:'wb_profit'},
      {h:'Ozon Take %', k:'ozon_take'},
      {h:'WB Take %', k:'wb_take'},
      {h:'Площадки', k:'places'}
    ]
  }
};

function xmlEsc(s){
  return String(s==null?'':s)
    .replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;')
    .replace(/"/g,'&quot;').replace(/'/g,'&apos;');
}

function colLetter(n){
  let s = '';
  n = n + 1;
  while(n > 0){
    const m = (n - 1) % 26;
    s = String.fromCharCode(65 + m) + s;
    n = Math.floor((n - 1) / 26);
  }
  return s;
}

function crc32(buf){
  let crc = 0xffffffff;
  for(let i=0;i<buf.length;i++){
    let c = (crc ^ buf[i]) & 0xff;
    for(let k=0;k<8;k++) c = (c & 1) ? (0xedb88320 ^ (c >>> 1)) : (c >>> 1);
    crc = (crc >>> 8) ^ c;
  }
  return (crc ^ 0xffffffff) >>> 0;
}

function zipStore(files){
  const enc = new TextEncoder();
  const chunks = [];
  const central = [];
  let offset = 0;
  files.forEach(function(f){
    const name = enc.encode(f.name);
    const data = typeof f.data === 'string' ? enc.encode(f.data) : f.data;
    const crc = crc32(data);
    const local = new Uint8Array(30 + name.length);
    const dv = new DataView(local.buffer);
    dv.setUint32(0, 0x04034b50, true);
    dv.setUint16(4, 20, true);
    dv.setUint16(6, 0x0800, true); // UTF-8
    dv.setUint16(8, 0, true); // store
    dv.setUint16(10, 0, true);
    dv.setUint16(12, 0, true);
    dv.setUint32(14, crc, true);
    dv.setUint32(18, data.length, true);
    dv.setUint32(22, data.length, true);
    dv.setUint16(26, name.length, true);
    dv.setUint16(28, 0, true);
    local.set(name, 30);
    chunks.push(local, data);

    const cen = new Uint8Array(46 + name.length);
    const cv = new DataView(cen.buffer);
    cv.setUint32(0, 0x02014b50, true);
    cv.setUint16(4, 20, true);
    cv.setUint16(6, 20, true);
    cv.setUint16(8, 0x0800, true);
    cv.setUint16(10, 0, true);
    cv.setUint16(12, 0, true);
    cv.setUint16(14, 0, true);
    cv.setUint32(16, crc, true);
    cv.setUint32(20, data.length, true);
    cv.setUint32(24, data.length, true);
    cv.setUint16(28, name.length, true);
    cv.setUint16(30, 0, true);
    cv.setUint16(32, 0, true);
    cv.setUint16(34, 0, true);
    cv.setUint16(36, 0, true);
    cv.setUint32(38, 0, true);
    cv.setUint32(42, offset, true);
    cen.set(name, 46);
    central.push(cen);
    offset += local.length + data.length;
  });
  let cenSize = 0;
  central.forEach(c => { cenSize += c.length; });
  const end = new Uint8Array(22);
  const ev = new DataView(end.buffer);
  ev.setUint32(0, 0x06054b50, true);
  ev.setUint16(8, files.length, true);
  ev.setUint16(10, files.length, true);
  ev.setUint32(12, cenSize, true);
  ev.setUint32(16, offset, true);
  return new Blob([...chunks, ...central, end], {
    type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
  });
}

function xlsxVal(v){
  if(v==null || v==='') return null;
  if(typeof v === 'number' && isFinite(v)) return {n: v};
  const s = String(v).trim();
  if(s !== '' && /^-?\\d+(\\.\\d+)?$/.test(s)) return {n: Number(s)};
  return {s: String(v)};
}

function buildXlsxBlob(sheetName, headers, matrix){
  const sheetRows = [];
  function cellXml(ref, val, style){
    const parsed = xlsxVal(val);
    const st = style ? ' s="'+style+'"' : '';
    if(parsed == null) return '<c r="'+ref+'"'+st+'/>';
    if(parsed.n != null && parsed.s == null) return '<c r="'+ref+'"'+st+'><v>'+parsed.n+'</v></c>';
    return '<c r="'+ref+'" t="inlineStr"'+st+'><is><t xml:space="preserve">'+xmlEsc(parsed.s)+'</t></is></c>';
  }
  let r = 1;
  sheetRows.push('<row r="1">'+headers.map((h,i)=>cellXml(colLetter(i)+'1', h, 1)).join('')+'</row>');
  for(let ri=0; ri<matrix.length; ri++){
    const row = matrix[ri];
    r = ri + 2;
    sheetRows.push('<row r="'+r+'">'+row.map((v,i)=>cellXml(colLetter(i)+r, v, 0)).join('')+'</row>');
  }

  const sheetXml = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'+
    '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'+
    '<sheetData>'+sheetRows.join('')+'</sheetData></worksheet>';

  const contentTypes = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'+
    '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'+
    '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'+
    '<Default Extension="xml" ContentType="application/xml"/>'+
    '<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'+
    '<Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'+
    '<Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/>'+
    '</Types>';

  const rootRels = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'+
    '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'+
    '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>'+
    '</Relationships>';

  const workbook = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'+
    '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'+
    '<sheets><sheet name="'+xmlEsc((sheetName||'Sheet').slice(0,28))+'" sheetId="1" r:id="rId1"/></sheets></workbook>';

  const wbRels = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'+
    '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'+
    '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/>'+
    '<Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>'+
    '</Relationships>';

  const styles = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'+
    '<styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'+
    '<fonts count="2"><font><sz val="11"/><name val="Calibri"/></font>'+
    '<font><b/><sz val="11"/><name val="Calibri"/></font></fonts>'+
    '<fills count="2"><fill><patternFill patternType="none"/></fill>'+
    '<fill><patternFill patternType="gray125"/></fill></fills>'+
    '<borders count="1"><border/></borders>'+
    '<cellStyleXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/></cellStyleXfs>'+
    '<cellXfs count="2">'+
    '<xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0"/>'+
    '<xf numFmtId="0" fontId="1" fillId="0" borderId="0" xfId="0" applyFont="1"/>'+
    '</cellXfs></styleSheet>';

  return zipStore([
    {name: '[Content_Types].xml', data: contentTypes},
    {name: '_rels/.rels', data: rootRels},
    {name: 'xl/workbook.xml', data: workbook},
    {name: 'xl/_rels/workbook.xml.rels', data: wbRels},
    {name: 'xl/styles.xml', data: styles},
    {name: 'xl/worksheets/sheet1.xml', data: sheetXml}
  ]);
}

function visibleColIndexes(tableId, nCols){
  const table = document.getElementById(tableId);
  if(!table) return Array.from({length:nCols}, (_,i)=>i);
  const ths = [...table.querySelectorAll('thead th')];
  const idx = [];
  for(let i=0;i<nCols;i++){
    const th = ths[i];
    if(!th || !th.classList.contains('col-hidden')) idx.push(i);
  }
  return idx.length ? idx : Array.from({length:nCols}, (_,i)=>i);
}

function exportExcel(which){
  const def = XLS_DEFS[which];
  if(!def){ showErr('Unknown export '+which); return; }
  let rows = (EXPORT_STATE[which]||[]).slice();
  if(which==='fee' && !rows.length){
    renderFeeTable();
    rows = (EXPORT_STATE.fee||[]).slice();
  }
  if(!rows.length){ alert('Нет строк для выгрузки'); return; }

  const cols = def.cols;
  const keep = def.tableId ? visibleColIndexes(def.tableId, cols.length) : cols.map((_,i)=>i);
  const headers = keep.map(i => cols[i].h);
  const fields = keep.map(i => cols[i].k);

  function cellVal(r, key){
    if(key==='_action'){
      const rec = findRec(r.offer_id) || {};
      return rec.action || (r.price_recommendation && r.price_recommendation.action) || '';
    }
    if(key==='_payout_unit'){
      const q = Math.max(r.qty_sold||1, 1);
      return (r.payout!=null) ? Math.round((r.payout/q)*100)/100 : '';
    }
    if(key==='competitor_display'){
      return r.competitor_display || r.competitor_source || r.competitor_seller || '';
    }
    if(key==='competitor_price') return r.competitor_price;
    if(key==='current_price_ozon') return r.current_price_ozon != null ? r.current_price_ozon : r.price_ozon;
    return r[key];
  }

  const matrix = rows.map(function(r){
    return fields.map(k => cellVal(r, k));
  });

  const blob = buildXlsxBlob(def.sheet, headers, matrix);
  const date = (DATA.period_to || new Date().toISOString().slice(0,10) || '').replace(/[^0-9]/g,'') || new Date().toISOString().slice(0,10).replace(/-/g,'');
  const fname = def.file + '_' + date + '.xlsx';
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  a.download = fname;
  document.body.appendChild(a);
  a.click();
  setTimeout(function(){
    URL.revokeObjectURL(a.href);
    a.remove();
  }, 1500);
}

function initExcelExport(){
  document.querySelectorAll('.btn-xls').forEach(function(btn){
    btn.addEventListener('click', function(){
      try{ exportExcel(btn.getAttribute('data-xls')); }
      catch(err){ showErr('export: '+err.message); }
    });
  });
}

/* ---------- WB + COMPARISON ---------- */
function renderWb(){
  const q = ((document.getElementById('wbSearch')||{}).value||'').toLowerCase().trim();
  const mg = ((document.getElementById('wbMargin')||{}).value)||'';
  let rows = (DATA.wb||[]).slice();
  if(q) rows = rows.filter(r => ((r.offer_id||'')+' '+(r.name||'')+' '+(r.subject||'')).toLowerCase().indexOf(q)>=0);
  if(mg==='neg') rows = rows.filter(r => r.profit_unit!=null && r.profit_unit<=0);
  else if(mg==='low') rows = rows.filter(r => r.margin_on_payout_pct!=null && r.margin_on_payout_pct<20 && r.margin_on_payout_pct>=0);
  else if(mg==='ok') rows = rows.filter(r => r.margin_on_payout_pct!=null && r.margin_on_payout_pct>=20);
  EXPORT_STATE.wb = rows;
  const tb = document.querySelector('#wbTable tbody');
  if(!tb) return;
  tb.innerHTML = rows.map(function(r){
    const profit = r.profit_unit;
    const pCls = (profit==null)?'':(profit<0?'bad':'good');
    const mCls = (r.margin_on_payout_pct==null)?'':(r.margin_on_payout_pct<0?'bad':(r.margin_on_payout_pct<20?'warn':'good'));
    return '<tr>'+
      '<td><b>'+esc(r.offer_id)+'</b></td>'+
      '<td class="clip-name" title="'+esc(r.name)+'">'+esc(r.name||'—')+'</td>'+
      '<td class="mini">'+esc(r.subject||'—')+'</td>'+
      '<td class="num">'+fmt0(r.qty_sold)+'</td>'+
      '<td class="num">'+fmt0(r.qty_ordered)+'</td>'+
      '<td class="num">'+fmt0(r.wb_avg_price || r.wb_final_price)+'</td>'+
      '<td class="num">'+fmt0(r.wb_revenue)+'</td>'+
      '<td class="num">'+fmt(r.wb_take_pct)+'%</td>'+
      '<td class="num">'+fmt0(r.wb_payout_unit)+'</td>'+
      '<td class="num">'+fmt0(r.cost_rub)+'</td>'+
      '<td class="num">'+fmt0(r.wb_fee_plan)+'</td>'+
      '<td class="num '+pCls+'">'+fmt(profit)+'</td>'+
      '<td class="num '+mCls+'">'+fmt(r.margin_on_payout_pct)+'%</td>'+
      '<td class="mini">'+esc(r.sales_source==='wb_api'?'WB API продажи':'план gsheet')+'</td>'+
      '</tr>';
  }).join('');
  const el = document.getElementById('wbCount');
  if(el) el.textContent = 'WB: показано '+rows.length+' из '+(DATA.wb||[]).length+' карточек';
  applyColVisibility('wbTable');
  applyColWidths('wbTable');
}

function renderCmpBody(){
  const tb = document.getElementById('cmpBody');
  if(!tb) return;
  const oz = DATA.ozonTotals||{};
  const wb = DATA.wbTotals||{};
  const planMode = wb.data_mode === 'plan';
  const wbRev = planMode ? wb.wb_plan_revenue_sum : wb.wb_revenue;
  const wbPay = planMode ? wb.wb_plan_payout_sum : wb.wb_payout;
  const wbTake = planMode ? (wb.wb_plan_take_pct != null ? wb.wb_plan_take_pct : wb.wb_take_pct) : wb.wb_take_pct;
  const wbQty = planMode ? null : wb.qty_sold;
  const rows = [
    ['Выручка, ₽', oz.gross, wbRev],
    ['Затраты площадки, ₽', oz.fees, (wbRev!=null && wbPay!=null)?Math.round((wbRev-wbPay)*100)/100:null],
    ['Выплата продавцу, ₽', oz.payout, wbPay],
    ['Take %', oz.take, wbTake],
    ['Продано, шт', oz.qty, wbQty],
    ['SKU / карточек', (DATA.skus||[]).length, wb.n_cards],
    ['Ср. себестоимость J, ₽', null, null]
  ];
  function avgCost(arr, k){
    let s=0,n=0; (arr||[]).forEach(r=>{ if(r.cost_rub!=null){ s+=r.cost_rub; n++; } });
    return n?Math.round(s/n*100)/100:null;
  }
  rows[6][1] = avgCost(DATA.skus);
  rows[6][2] = avgCost(DATA.wb);
  tb.innerHTML = rows.map(function(r){
    const a=r[1], b=r[2];
    const d = (a!=null && b!=null) ? Math.round((a-b)*100)/100 : null;
    return '<tr><td><b>'+esc(r[0])+'</b></td>'+
      '<td class="num">'+(a==null?'—':fmt(a))+'</td>'+
      '<td class="num">'+(b==null?'—':fmt(b))+'</td>'+
      '<td class="num">'+(d==null?'—':fmt(d))+'</td></tr>';
  }).join('') +
  (planMode ? '<tr><td colspan="4" class="mini">WB: план gsheet (wb_final_price − wb_fee) — sales API пока без данных / rate-limit</td></tr>' : '');
}

function renderCmpSkus(){
  const q = ((document.getElementById('cmpSearch')||{}).value||'').toLowerCase().trim();
  const only = ((document.getElementById('cmpOnly')||{}).value)||'';
  const ozMap = {};
  (DATA.skus||[]).forEach(function(r){
    const k = (r.offer_id||'').toUpperCase();
    if(k) ozMap[k] = r;
  });
  const wbMap = {};
  (DATA.wb||[]).forEach(function(r){
    const k = (r.offer_id||'').toUpperCase();
    if(k) wbMap[k] = r;
  });
  const keys = {};
  Object.keys(ozMap).forEach(k => keys[k]=1);
  Object.keys(wbMap).forEach(k => keys[k]=1);
  let rows = Object.keys(keys).map(function(k){
    const o = ozMap[k], w = wbMap[k];
    return {
      offer_id: k,
      name: (o&&o.name) || (w&&w.name) || k,
      ozon_price: o ? (o.price_ozon != null ? o.price_ozon : o.avg_sale_price) : null,
      wb_price: w ? (w.wb_avg_price != null ? w.wb_avg_price : w.wb_final_price) : null,
      ozon_qty: o ? o.qty_sold : null,
      wb_qty: w ? w.qty_sold : null,
      ozon_pay: o ? (o.qty_sold ? Math.round(((o.payout||0)/Math.max(o.qty_sold,1))*100)/100 : null) : null,
      wb_pay: w ? w.wb_payout_unit : null,
      ozon_profit: o ? o.profit_unit : null,
      wb_profit: w ? w.profit_unit : null,
      ozon_take: o ? o.ozon_take_pct : null,
      wb_take: w ? w.wb_take_pct : null,
      places: (o&&w) ? 'Ozon+WB' : (o ? 'Ozon' : 'WB')
    };
  });
  if(q) rows = rows.filter(r => r.offer_id.toLowerCase().indexOf(q)>=0 || (r.name||'').toLowerCase().indexOf(q)>=0);
  if(only==='both') rows = rows.filter(r => r.places==='Ozon+WB');
  else if(only==='ozon') rows = rows.filter(r => r.places==='Ozon');
  else if(only==='wb') rows = rows.filter(r => r.places==='WB');
  EXPORT_STATE.cmp = rows;
  const tb = document.querySelector('#cmpSkuTable tbody');
  if(!tb) return;
  const show = rows.slice(0,200);
  tb.innerHTML = show.map(function(r){
    const chip = r.places==='Ozon+WB' ? 'accent' : (r.places==='WB' ? 'good' : '');
    return '<tr>'+
      '<td><b>'+esc(r.offer_id)+'</b></td>'+
      '<td class="clip-name">'+esc(r.name)+'</td>'+
      '<td class="num">'+fmt0(r.ozon_price)+'</td>'+
      '<td class="num">'+fmt0(r.wb_price)+'</td>'+
      '<td class="num">'+fmt0(r.ozon_qty)+'</td>'+
      '<td class="num">'+fmt0(r.wb_qty)+'</td>'+
      '<td class="num">'+fmt0(r.ozon_pay)+'</td>'+
      '<td class="num">'+fmt0(r.wb_pay)+'</td>'+
      '<td class="num">'+fmt(r.ozon_profit)+'</td>'+
      '<td class="num">'+fmt(r.wb_profit)+'</td>'+
      '<td class="num">'+fmt(r.ozon_take)+'%</td>'+
      '<td class="num">'+fmt(r.wb_take)+'%</td>'+
      '<td><span class="chip '+chip+'">'+esc(r.places)+'</span></td>'+
      '</tr>';
  }).join('');
  const el = document.getElementById('cmpCount');
  if(el) el.textContent = 'Показано '+show.length+' из '+rows.length+' позиций (Ozon+WB)';
}

function showErr(msg){
  const el = document.getElementById('jsError');
  if(!el) return;
  el.style.display = 'block';
  el.textContent = 'JS: ' + msg;
}
window.addEventListener('error', e => showErr(e.message + ' @ ' + (e.filename||'') + ':' + (e.lineno||'')));

const fmt = n => (n==null || isNaN(n)) ? '—' : Number(n).toLocaleString('ru-RU',{maximumFractionDigits:1});
const fmt0 = n => (n==null || isNaN(n)) ? '—' : Number(n).toLocaleString('ru-RU',{maximumFractionDigits:0});
const esc = s => String(s==null?'':s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');

/* ---------- CHART REGISTRY (prevent "canvas already in use") ---------- */
const CHARTS = {};
function safeChart(id, config){
  try{
    const el = document.getElementById(id);
    if(!el){ showErr('no canvas '+id); return null; }
    if(typeof Chart === 'undefined'){ showErr('Chart.js not loaded'); return null; }
    if(CHARTS[id]){ try{ CHARTS[id].destroy(); }catch(e){} CHARTS[id]=null; }
    const chart = new Chart(el, config);
    CHARTS[id] = chart;
    return chart;
  }catch(err){
    showErr('chart '+id+': '+err.message);
    return null;
  }
}

/* ---------- TABS ---------- */
const TAB_CHARTS = {
  overview: ['chartDays','chartFees','chartTop','chartCompare'],
  fees: ['chartPlanFact'],
  prices: ['chartIndex'],
  wb: ['chartWbCompare']
};
const TAB_BUILDERS = {};
function initTabs(){
  const bar = document.getElementById('tabs');
  if(!bar) return;
  bar.onclick = function(e){
    const b = e.target.closest('button[data-tab]');
    if(!b) return;
    document.querySelectorAll('#tabs button').forEach(x => x.classList.remove('active'));
    b.classList.add('active');
    document.querySelectorAll('.section').forEach(s => s.classList.remove('active'));
    const sec = document.getElementById('sec-' + b.dataset.tab);
    if(sec) sec.classList.add('active');
    const tab = b.dataset.tab;
    requestAnimationFrame(function(){
      try{
        if(TAB_BUILDERS[tab]){ TAB_BUILDERS[tab](); TAB_BUILDERS[tab]=null; }
        (TAB_CHARTS[tab]||[]).forEach(function(id){
          const c = CHARTS[id];
          if(c){ try{ c.resize(); }catch(e){} }
        });
        window.dispatchEvent(new Event('resize'));
      }catch(err){ showErr('tab '+tab+': '+err.message); }
    });
  };
}

/* ---------- FILTERS: SKU ---------- */
function actionPill(a){
  if(!a) return '<span class="pill hold">—</span>';
  if(String(a).indexOf('ПОВЫСИТЬ')>=0) return '<span class="pill up">ПОВЫСИТЬ</span>';
  if(String(a).indexOf('СНИЗИТЬ')>=0) return '<span class="pill down">СНИЗИТЬ</span>';
  return '<span class="pill hold">УДЕРЖАТЬ</span>';
}

/* Recommended price so net profit = K (required_markup), using real Ozon costs */
function recPriceCell(r, rec){
  const p = r.price_rec_for_margin_k || (rec && rec.price_rec_for_margin_k) || (rec && rec.suggested_price);
  if(p==null || p==='') return '<span class="mini">—</span>';
  const k = r.target_margin_k != null ? r.target_margin_k : (r.required_markup != null ? r.required_markup : null);
  const tip = 'Цена = (J + K + прочие затраты Ozon/шт) / (1 − комиссия%); целевая чистая прибыль K=' +
    (k!=null ? fmt0(k)+' ₽' : 'н/д');
  return '<span title="'+esc(tip)+'">'+fmt0(p)+' ₽</span>' +
    (k!=null ? '<div class="mini">K='+fmt0(k)+' ₽</div>' : '');
}

function findRec(offer){
  const recs = DATA.recs || [];
  for(let i=0;i<recs.length;i++) if(recs[i].offer_id===offer) return recs[i];
  return null;
}

/* ---------- COLUMN VISIBILITY + RESIZE ---------- */
function colStoreKey(tableId){ return 'colvis_v1__' + tableId; }
function colWidthKey(tableId){ return 'colw_v1__' + tableId; }

function loadJSON(key, fallback){
  try{
    const raw = localStorage.getItem(key);
    if(!raw) return fallback;
    const v = JSON.parse(raw);
    return v == null ? fallback : v;
  }catch(e){ return fallback; }
}
function saveJSON(key, val){
  try{ localStorage.setItem(key, JSON.stringify(val)); }catch(e){}
}

function setColVisible(table, idx, visible){
  const cells = table.querySelectorAll('tr');
  cells.forEach(function(tr){
    const cell = tr.children[idx];
    if(cell) cell.classList.toggle('col-hidden', !visible);
  });
}

function applyColVisibility(tableId){
  const table = document.getElementById(tableId);
  if(!table) return;
  const ths = [...table.querySelectorAll('thead th')];
  const saved = loadJSON(colStoreKey(tableId), null);
  ths.forEach(function(th, i){
    const vis = !saved || saved[i] !== false;
    th.classList.toggle('col-hidden', !vis);
  });
  // body rows
  const n = ths.length;
  table.querySelectorAll('tbody tr').forEach(function(tr){
    for(let i=0;i<n;i++){
      if(tr.children[i]) tr.children[i].classList.toggle('col-hidden', ths[i].classList.contains('col-hidden'));
    }
  });
}

function setColWidth(table, idx, w){
  const ths = table.querySelectorAll('thead th');
  const th = ths[idx];
  if(!th) return;
  th.style.width = w + 'px';
  th.style.minWidth = w + 'px';
  th.style.maxWidth = w + 'px';
  table.style.width = 'max-content';
  table.querySelectorAll('tbody tr').forEach(function(tr){
    const cell = tr.children[idx];
    if(!cell) return;
    cell.style.width = w + 'px';
    cell.style.minWidth = w + 'px';
    cell.style.maxWidth = w + 'px';
  });
}

function applyColWidths(tableId){
  const table = document.getElementById(tableId);
  if(!table) return;
  const w = loadJSON(colWidthKey(tableId), {});
  let any = false;
  Object.keys(w).forEach(function(k){
    const i = parseInt(k, 10);
    const px = w[k];
    if(!isNaN(i) && px != null && px > 40){
      setColWidth(table, i, px);
      any = true;
    }
  });
  if(any) table.style.width = 'max-content';
}

function buildColMenu(tableId, menuId){
  const table = document.getElementById(tableId);
  const menu = document.getElementById(menuId);
  if(!table || !menu) return;
  const ths = [...table.querySelectorAll('thead th')];
  menu.innerHTML = '';
  ths.forEach(function(th, i){
    const lab = document.createElement('label');
    const cb = document.createElement('input');
    cb.type = 'checkbox';
    cb.checked = !th.classList.contains('col-hidden');
    cb.addEventListener('change', function(){
      setColVisible(table, i, cb.checked);
      // also body cells (in case new rows rendered later)
      table.querySelectorAll('tbody tr').forEach(function(tr){
        if(tr.children[i]) tr.children[i].classList.toggle('col-hidden', !cb.checked);
      });
      const saved = loadJSON(colStoreKey(tableId), {});
      saved[i] = cb.checked;
      saveJSON(colStoreKey(tableId), saved);
    });
    const span = document.createElement('span');
    span.textContent = th.innerText.trim() || ('Col ' + (i+1));
    lab.appendChild(cb);
    lab.appendChild(span);
    menu.appendChild(lab);
  });
  const actions = document.createElement('div');
  actions.className = 'col-actions';
  const btnAll = document.createElement('button');
  btnAll.type = 'button';
  btnAll.textContent = 'Все';
  btnAll.addEventListener('click', function(){
    ths.forEach(function(th, i){
      th.classList.remove('col-hidden');
      table.querySelectorAll('tbody tr').forEach(function(tr){
        if(tr.children[i]) tr.children[i].classList.remove('col-hidden');
      });
    });
    menu.querySelectorAll('input[type=checkbox]').forEach(function(cb){ cb.checked = true; });
    saveJSON(colStoreKey(tableId), {});
  });
  const btnDefault = document.createElement('button');
  btnDefault.type = 'button';
  btnDefault.textContent = 'Сброс';
  btnDefault.addEventListener('click', function(){
    try{ localStorage.removeItem(colStoreKey(tableId)); localStorage.removeItem(colWidthKey(tableId)); }catch(e){}
    ths.forEach(function(th, i){
      th.classList.remove('col-hidden');
      th.style.width = '';
      th.style.minWidth = '';
      th.style.maxWidth = '';
      table.querySelectorAll('tbody tr').forEach(function(tr){
        if(tr.children[i]){
          tr.children[i].classList.remove('col-hidden');
          tr.children[i].style.width = '';
          tr.children[i].style.minWidth = '';
          tr.children[i].style.maxWidth = '';
        }
      });
    });
    table.style.width = '';
    menu.querySelectorAll('input[type=checkbox]').forEach(function(cb){ cb.checked = true; });
    buildColMenu(tableId, menuId);
  });
  actions.appendChild(btnAll);
  actions.appendChild(btnDefault);
  menu.appendChild(actions);
}

function initColResize(tableId){
  const table = document.getElementById(tableId);
  if(!table) return;
  const ths = [...table.querySelectorAll('thead th')];
  ths.forEach(function(th, idx){
    th.style.position = th.style.position || 'sticky';
    const grip = document.createElement('div');
    grip.className = 'resizer';
    grip.title = 'Потяните для ширины столбца';
    th.appendChild(grip);

    grip.addEventListener('mousedown', function(e){
      e.preventDefault();
      e.stopPropagation();
      const startX = e.clientX;
      const startW = th.getBoundingClientRect().width;
      th.classList.add('active');
      table.classList.add('col-resizing');
      document.body.style.cursor = 'col-resize';
      document.body.style.userSelect = 'none';

      function onMove(ev){
        const dx = ev.clientX - startX;
        const w = Math.max(48, Math.round(startW + dx));
        setColWidth(table, idx, w);
      }
      function onUp(){
        document.removeEventListener('mousemove', onMove);
        document.removeEventListener('mouseup', onUp);
        th.classList.remove('active');
        table.classList.remove('col-resizing');
        document.body.style.cursor = '';
        document.body.style.userSelect = '';
        const w = Math.round(th.getBoundingClientRect().width);
        setColWidth(table, idx, w);
        const saved = loadJSON(colWidthKey(tableId), {});
        saved[idx] = w;
        saveJSON(colWidthKey(tableId), saved);
      }
      document.addEventListener('mousemove', onMove);
      document.addEventListener('mouseup', onUp);
    });
  });
}

function initColTools(tableId, menuId, toggleBtnSel){
  applyColVisibility(tableId);
  applyColWidths(tableId);
  buildColMenu(tableId, menuId);
  initColResize(tableId);

  const btn = document.querySelector(toggleBtnSel || ('[data-toggle="' + menuId + '"]'));
  const menu = document.getElementById(menuId);
  if(btn && menu){
    btn.addEventListener('click', function(e){
      e.stopPropagation();
      // rebuild checkbox state
      const table = document.getElementById(tableId);
      if(table){
        const ths = [...table.querySelectorAll('thead th')];
        menu.querySelectorAll('label input[type=checkbox]').forEach(function(cb, i){
          if(ths[i]) cb.checked = !ths[i].classList.contains('col-hidden');
        });
      }
      menu.classList.toggle('open');
    });
  }
}

document.addEventListener('click', function(e){
  document.querySelectorAll('.col-menu.open').forEach(function(m){
    if(!m.contains(e.target) && !(e.target.classList && e.target.classList.contains('col-picker-btn'))){
      m.classList.remove('open');
    }
  });
});

function initAllColTools(){
  initColTools('skuTable', 'colMenuSku');
  initColTools('recTable', 'colMenuRec');
  initColTools('costTable', 'colMenuCost');
}


function renderSkus(){
  const q = (document.getElementById('fSearch').value||'').toLowerCase().trim();
  const act = document.getElementById('fAction').value;
  const takeF = document.getElementById('fTake').value;
  const profF = document.getElementById('fProfit').value;
  const sort = document.getElementById('fSort').value;
  let rows = (DATA.skus||[]).slice();
  if(q) rows = rows.filter(r => ((r.offer_id||'')+' '+(r.name||'')+' '+(r.sheet_name||'')).toLowerCase().indexOf(q)>=0);
  if(act) rows = rows.filter(r => {
    const rec = findRec(r.offer_id);
    return rec && String(rec.action||'').indexOf(act)>=0;
  });
  if(takeF==='high') rows = rows.filter(r => (r.ozon_take_pct||0) >= 70);
  else if(takeF==='mid') rows = rows.filter(r => (r.ozon_take_pct||0) >= 50 && (r.ozon_take_pct||0) < 70);
  else if(takeF==='low') rows = rows.filter(r => (r.ozon_take_pct||0) < 50);
  if(profF==='neg') rows = rows.filter(r => (r.profit_unit!=null && r.profit_unit<=0));
  else if(profF==='ok') rows = rows.filter(r => (r.profit_unit!=null && r.profit_unit>0));

  rows.sort(function(a,b){
    if(sort==='take') return (b.ozon_take_pct||0)-(a.ozon_take_pct||0);
    if(sort==='payout') return (b.payout||0)-(a.payout||0);
    if(sort==='qty') return (b.qty_sold||0)-(a.qty_sold||0);
    if(sort==='profit') return (a.profit_unit==null?99999:a.profit_unit)-(b.profit_unit==null?99999:b.profit_unit);
    if(sort==='diff') return Math.abs(b.ozon_fee_diff||0)-Math.abs(a.ozon_fee_diff||0);
    return (b.gross_product||0)-(a.gross_product||0);
  });

  EXPORT_STATE.sku = rows;
  const tb = document.querySelector('#skuTable tbody');
  if(!tb) return;
  const show = rows.slice(0,200);
  tb.innerHTML = show.map(function(r){
    const take = r.ozon_take_pct||0;
    const color = take>=70?'#ef4444':take>=50?'#f59e0b':'#22c55e';
    const rec = findRec(r.offer_id) || r.price_recommendation || {};
    const diff = r.ozon_fee_diff;
    const diffCls = (diff==null) ? '' : (diff>0 ? 'bad' : 'good');
    const profit = r.profit_unit;
    const profitCls = (profit==null) ? '' : (profit<0 ? 'bad' : 'good');
    return '<tr>'+
      '<td><b>'+esc(r.offer_id)+'</b></td>'+
      '<td class="clip-name" title="'+esc(r.name)+'">'+esc(r.name||'—')+'</td>'+
      '<td class="num">'+fmt0(r.qty_sold)+'</td>'+
      '<td class="num"><b>'+fmt0(r.price_ozon)+'</b></td>'+
      '<td class="num">'+(r.competitor_price?fmt0(r.competitor_price):'—')+'</td>'+
      '<td class="mini wrap-cell" title="'+esc(r.competitor_display||r.competitor_source||'')+'">'+esc(r.competitor_display||'—').replace(/\\n/g,'<br>')+'</td>'+
      '<td class="num">'+fmt0(r.gross_product)+'</td>'+
      '<td class="num bad">'+fmt0(r.total_fees)+'</td>'+
      '<td class="num"><div class="bar"><i style="width:'+Math.min(take,100)+'%;background:'+color+'"></i></div><span class="mini">'+fmt(take)+'%</span></td>'+
      '<td class="num good">'+fmt0(r.payout)+'</td>'+
      '<td class="num">'+fmt0(r.cost_rub)+'</td>'+
      '<td class="num">'+fmt0(r.ozon_fee_plan)+'</td>'+
      '<td class="num">'+fmt0(r.ozon_fee_actual_unit)+'</td>'+
      '<td class="num '+diffCls+'">'+(diff==null?'—':(diff>0?'+':'')+fmt(diff))+'</td>'+
      '<td class="num '+profitCls+'">'+fmt(profit)+'</td>'+
      '<td class="num"><b>'+recPriceCell(r, rec)+'</b></td>'+
      '<td>'+actionPill(rec.action)+'</td>'+
      '</tr>';
  }).join('');
  const el = document.getElementById('skuCount');
  if(el) el.textContent = 'Показано '+show.length+' из '+rows.length+' отфильтрованных (всего '+ (DATA.skus||[]).length +' SKU в выгрузке)';
  applyColVisibility('skuTable');
  applyColWidths('skuTable');
}

/* ---------- RECS ---------- */
function renderRecs(){
  const q = (document.getElementById('rSearch').value||'').toLowerCase().trim();
  const act = document.getElementById('rAction').value;
  const mg = (document.getElementById('rMargin')||{}).value || '';
  const mk = (document.getElementById('rMarket')||{}).value || '';
  let rows = (DATA.recs||[]).slice();
  if(q) rows = rows.filter(r => ((r.offer_id||'')+' '+(r.name||'')).toLowerCase().indexOf(q)>=0);
  if(act) rows = rows.filter(r => String(r.action||'')===act);
  if(mg==='neg') rows = rows.filter(r => r.profit_unit!=null && r.profit_unit<=0);
  else if(mg==='low') rows = rows.filter(r => r.margin_on_payout_pct!=null && r.margin_on_payout_pct<20 && r.margin_on_payout_pct>=0);
  else if(mg==='ok') rows = rows.filter(r => r.margin_on_payout_pct!=null && r.margin_on_payout_pct>=20);
  if(mk){
    rows = rows.filter(function(r){
      const price = r.current_price_ozon != null ? r.current_price_ozon : r.price_ozon;
      const market = r.competitor_price;
      const hasMarket = market!=null && market!=='' && !isNaN(market) && market>0;
      const hasPrice = price!=null && price!=='' && !isNaN(price);
      if(mk==='no_index') return !hasMarket;
      if(!hasMarket || !hasPrice) return false;
      if(mk==='cheap') return price < market;
      if(mk==='dear') return price > market;
      if(mk==='not_dear') return price <= market;
      return true;
    });
  }
  EXPORT_STATE.rec = rows;
  const tb = document.querySelector('#recTable tbody');
  if(!tb) return;
  const show = rows.slice(0,150);
  tb.innerHTML = show.map(function(r){
    const profit = r.profit_unit;
    const profitCls = (profit==null)?'':(profit<0?'bad':'good');
    return '<tr>'+
      '<td><b>'+esc(r.offer_id)+'</b></td>'+
      '<td class="clip-name">'+esc(r.name||'')+'</td>'+
      '<td class="num"><b>'+fmt0(r.current_price_ozon)+'</b></td>'+
      '<td class="num mini">'+fmt0(r.avg_sale_price)+'</td>'+
      '<td class="num">'+fmt0(r.cost_rub)+'</td>'+
      '<td class="num">'+(r.competitor_price?fmt0(r.competitor_price):'—')+'</td>'+
      '<td class="mini wrap-cell">'+esc(r.competitor_display||'—').replace(/\\n/g,'<br>')+'</td>'+
      '<td class="num">'+fmt(r.ozon_take_pct)+'%</td>'+
      '<td class="num">'+fmt0(r.payout_per_unit)+'</td>'+
      '<td class="num '+profitCls+'">'+fmt(profit)+'</td>'+
      '<td>'+actionPill(r.action)+'</td>'+
      '<td class="num"><b>'+(r.suggested_price?fmt0(r.suggested_price)+' ₽':'—')+'</b></td>'+
      '<td class="mini" style="white-space:normal;max-width:240px">'+esc(r.reason||'')+'</td>'+
      '</tr>';
  }).join('');
  const el = document.getElementById('recCount');
  if(el) el.textContent = 'Показано '+show.length+' из '+rows.length;
  applyColVisibility('recTable');
  applyColWidths('recTable');
}

/* ---------- COSTS ---------- */
function renderCosts(){
  const q = (document.getElementById('cSearch').value||'').toLowerCase().trim();
  const mg = document.getElementById('cMargin').value;
  let rows = (DATA.skus||[]).filter(r => r.cost_rub!=null || r.ozon_fee_plan!=null);
  if(q) rows = rows.filter(r => ((r.offer_id||'')+' '+(r.name||'')+' '+(r.sheet_name||'')).toLowerCase().indexOf(q)>=0);
  if(mg==='neg') rows = rows.filter(r => r.profit_unit!=null && r.profit_unit<=0);
  else if(mg==='low') rows = rows.filter(r => r.margin_on_payout_pct!=null && r.margin_on_payout_pct<20 && r.margin_on_payout_pct>=0);
  else if(mg==='ok') rows = rows.filter(r => r.margin_on_payout_pct!=null && r.margin_on_payout_pct>=20);
  rows.sort((a,b)=>(b.qty_sold||0)-(a.qty_sold||0));
  EXPORT_STATE.cost = rows;
  const tb = document.querySelector('#costTable tbody');
  if(!tb) return;
  const show = rows.slice(0,200);
  tb.innerHTML = show.map(function(r){
    const profit = r.profit_unit;
    const margin = r.margin_on_payout_pct;
    const profitCls = (profit==null)?'':(profit<0?'bad':'good');
    const marginCls = (margin==null)?'':(margin<0?'bad':(margin<20?'warn':'good'));
    const diff = r.ozon_fee_diff;
    const diffCls = (diff==null)?'':(diff>0?'bad':'good');
    return '<tr>'+
      '<td><b>'+esc(r.offer_id)+'</b></td>'+
      '<td class="clip-name">'+esc(r.name||r.sheet_name||'')+'</td>'+
      '<td class="num">'+fmt0(r.cost_rub)+'</td>'+
      '<td class="num">'+fmt0(r.ozon_fee_plan)+'</td>'+
      '<td class="num">'+fmt0(r.ozon_fee_actual_unit)+'</td>'+
      '<td class="num '+diffCls+'">'+(diff==null?'—':fmt(diff))+'</td>'+
      '<td class="num">'+fmt0(r.price_ozon)+'</td>'+
      '<td class="num">'+fmt0((r.payout||0)/Math.max(r.qty_sold||1,1))+'</td>'+
      '<td class="num '+profitCls+'">'+fmt(profit)+'</td>'+
      '<td class="num '+marginCls+'">'+fmt(margin)+'%</td>'+
      '<td class="num">'+fmt0(r.ozon_final_price || r.retail)+'</td>'+
      '</tr>';
  }).join('');
  const el = document.getElementById('costCount');
  if(el) el.textContent = 'Показано '+show.length+' из '+rows.length+' SKU с себестоимостью';
  applyColVisibility('costTable');
  applyColWidths('costTable');
}

/* ---------- FEE TABLE ---------- */
function renderFeeTable(){
  const ft = document.querySelector('#feeTable');
  if(!ft) return;
  const feeLabels = {
    commission:'Комиссия за продажу', logistics:'Логистика', last_mile:'Последняя миля',
    acquiring:'Эквайринг', premium:'Premium Pro', stars:'Звёздные товары',
    review_mgmt:'Управление отзывами', reverse_logistics:'Обратная логистика',
    dropoff:'Drop-off / СЦ', packaging:'Упаковка', returns_fee:'Возвраты/отмены',
    first_reviews:'Сбор отзывов', other_fees:'Прочее'
  };
  const entries = Object.entries(DATA.fees||{}).sort((a,b)=>b[1]-a[1]);
  EXPORT_STATE.fee = entries.map(function(e){
    const k=e[0], v=e[1];
    const pct = (DATA.feePct||{})[k]||0;
    return {article: feeLabels[k]||k, amount: v, pct: pct};
  });
  ft.innerHTML = entries.map(function(e){
    const k=e[0], v=e[1];
    const pct = (DATA.feePct||{})[k]||0;
    return '<tr><td>'+(feeLabels[k]||k)+'</td><td class="num">'+fmt0(v)+' ₽</td><td class="num">'+fmt(pct)+'%</td>'+
      '<td><div class="bar"><i style="width:'+Math.min(pct*2,100)+'%;background:#5b8cff"></i></div></td></tr>';
  }).join('');
}

/* ---------- CHARTS ---------- */
function buildCharts(){
  const days = DATA.days||[];
  const dayLabels = days.map(d => (d.date||'').slice(5));
  safeChart('chartDays', {
    type:'bar',
    data:{
      labels: dayLabels,
      datasets:[
        { type:'line', label:'Выручка, ₽', data: days.map(d=>d.revenue), borderColor:'#5b8cff', backgroundColor:'rgba(91,140,255,.15)', tension:.3, yAxisID:'y', fill:true },
        { type:'bar', label:'Продажи, шт', data: days.map(d=>d.ordered_units), backgroundColor:'rgba(34,197,94,.55)', yAxisID:'y1' }
      ]
    },
    options:{
      responsive:true, maintainAspectRatio:false,
      plugins:{ legend:{ labels:{ color:'#8fa3c1' } } },
      scales:{
        x:{ ticks:{ color:'#8fa3c1', maxTicksLimit:12 }, grid:{ color:'#243552' } },
        y:{ ticks:{ color:'#8fa3c1' }, grid:{ color:'#243552' } },
        y1:{ position:'right', ticks:{ color:'#8fa3c1' }, grid:{ drawOnChartArea:false } }
      }
    }
  });

  const feeLabels = {
    commission:'Комиссия', logistics:'Логистика', last_mile:'Последняя миля',
    acquiring:'Эквайринг', premium:'Premium Pro', stars:'Звёздные',
    review_mgmt:'Отзывы', reverse_logistics:'Обр. логистика',
    dropoff:'Drop-off', packaging:'Упаковка', returns_fee:'Возвраты',
    first_reviews:'Сбор отзывов', other_fees:'Прочее'
  };
  const feeEntries = Object.entries(DATA.fees||{}).sort((a,b)=>b[1]-a[1]);
  safeChart('chartFees', {
    type:'doughnut',
    data:{
      labels: feeEntries.map(e=>feeLabels[e[0]]||e[0]),
      datasets:[{
        data: feeEntries.map(e=>Math.round(e[1])),
        backgroundColor:['#5b8cff','#22c55e','#f59e0b','#a78bfa','#ef4444','#06b6d4','#f472b6','#84cc16','#fb923c','#64748b','#eab308','#14b8a6','#94a3b8']
      }]
    },
    options:{ responsive:true, maintainAspectRatio:false, plugins:{ legend:{ position:'right', labels:{ color:'#8fa3c1', boxWidth:12, font:{size:11} } } } }
  });

  const top = (DATA.skus||[]).slice(0,15);
  safeChart('chartTop', {
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

  safeChart('chartCompare', {
    type:'bar',
    data:{
      labels:['Ozon','Wildberries'],
      datasets:[{ label:'% забора', data:[DATA.takePct, DATA.wbTake], backgroundColor:['#5b8cff','#22c55e'] }]
    },
    options:{
      responsive:true, maintainAspectRatio:false,
      plugins:{ legend:{ display:false } },
      scales:{ y:{ max:100, ticks:{ color:'#8fa3c1' }, grid:{ color:'#243552' } }, x:{ ticks:{ color:'#8fa3c1' }, grid:{ color:'#243552' } } }
    }
  });

  TAB_BUILDERS.fees = function(){
    const pf = DATA.planFact||{};
    safeChart('chartPlanFact', {
      type:'bar',
      data:{
        labels:['План (столбец P)','Факт (начисления Ozon)'],
        datasets:[{
          label:'Средние затраты, ₽/шт',
          data:[pf.avg_plan_fee||0, pf.avg_fact_fee||0],
          backgroundColor:['rgba(91,140,255,.55)','rgba(239,68,68,.55)'],
          borderColor:['#5b8cff','#ef4444'],
          borderWidth:1
        }]
      },
      options:{
        responsive:true, maintainAspectRatio:false,
        plugins:{ legend:{ labels:{ color:'#8fa3c1' } } },
        scales:{ y:{ ticks:{ color:'#8fa3c1' }, grid:{ color:'#243552' } }, x:{ ticks:{ color:'#8fa3c1' }, grid:{ color:'#243552' } } }
      }
    });
  };

  TAB_BUILDERS.prices = function(){
    const idx = {GREEN:0, RED:0, SUPER:0, OTHER:0};
    (DATA.skus||[]).forEach(function(s){
      const c = s.price_index_color||'OTHER';
      if(idx[c]==null) idx.OTHER++; else idx[c]++;
    });
    safeChart('chartIndex', {
      type:'doughnut',
      data:{
        labels:['GREEN — не дороже рынка','RED — дороже рынка','SUPER — дешевле рынка','Без индекса'],
        datasets:[{ data:[idx.GREEN, idx.RED, idx.SUPER, idx.OTHER], backgroundColor:['#22c55e','#ef4444','#5b8cff','#64748b'] }]
      },
      options:{ responsive:true, maintainAspectRatio:false, plugins:{ legend:{ labels:{ color:'#8fa3c1' } } } }
    });
    const ist = document.getElementById('indexStats');
    if(ist) ist.innerHTML =
      '<div class="chip good">GREEN: '+idx.GREEN+'</div>'+
      '<div class="chip bad">RED: '+idx.RED+'</div>'+
      '<div class="chip accent">SUPER: '+idx.SUPER+'</div>'+
      '<div class="chip">Без индекса: '+idx.OTHER+'</div>';
  };

  TAB_BUILDERS.wb = function(){
    const wbTake = (DATA.wbTotals && DATA.wbTotals.wb_take_pct != null) ? DATA.wbTotals.wb_take_pct : DATA.wbTake;
    safeChart('chartWbCompare', {
      type:'radar',
      data:{
        labels:['Комиссия','Логистика','Маркетинг/сервисы','Прочее','Итого take %'],
        datasets:[
          { label:'Ozon', data:[DATA.commPct, DATA.logPct, DATA.svcPct, DATA.miscPct, DATA.takePct], borderColor:'#5b8cff', backgroundColor:'rgba(91,140,255,.2)' },
          { label:'WB', data:[Math.round(wbTake*0.75*10)/10, Math.round(wbTake*0.2*10)/10, 1, Math.round(wbTake*0.05*10)/10, wbTake], borderColor:'#22c55e', backgroundColor:'rgba(34,197,94,.2)' }
        ]
      },
      options:{
        responsive:true, maintainAspectRatio:false,
        plugins:{ legend:{ labels:{ color:'#8fa3c1' } } },
        scales:{ r:{ max:70, ticks:{ color:'#8fa3c1', backdropColor:'transparent' }, grid:{ color:'#243552' }, pointLabels:{ color:'#8fa3c1' } } }
      }
    });
    renderCmpBody();
    renderCmpSkus();
  };
}

/* ---------- PERIOD FILTER (days chart) ---------- */
function filterDaysByPeriod(){
  const from = document.getElementById('dFrom').value;
  const to = document.getElementById('dTo').value;
  let days = (DATA.days||[]).slice();
  if(from) days = days.filter(d => d.date >= from);
  if(to) days = days.filter(d => d.date <= to);
  const rev = days.reduce((s,d)=>s+(d.revenue||0),0);
  const qty = days.reduce((s,d)=>s+(d.ordered_units||0),0);
  const elG = document.getElementById('kGross');
  // note: gross is product price sum, revenue is cash part — show period sales
  const elQ = document.getElementById('kQty');
  if(elQ) elQ.textContent = fmt0(qty) + ' шт';
  // rebuild days chart only (safeChart destroys previous instance)
  safeChart('chartDays', {
    type:'bar',
    data:{
      labels: days.map(d=>(d.date||'').slice(5)),
      datasets:[
        { type:'line', label:'Выручка, ₽', data: days.map(d=>d.revenue), borderColor:'#5b8cff', backgroundColor:'rgba(91,140,255,.15)', tension:.3, yAxisID:'y', fill:true },
        { type:'bar', label:'Продажи, шт', data: days.map(d=>d.ordered_units), backgroundColor:'rgba(34,197,94,.55)', yAxisID:'y1' }
      ]
    },
    options:{
      responsive:true, maintainAspectRatio:false,
      plugins:{ legend:{ labels:{ color:'#8fa3c1' } } },
      scales:{
        x:{ ticks:{ color:'#8fa3c1', maxTicksLimit:12 }, grid:{ color:'#243552' } },
        y:{ ticks:{ color:'#8fa3c1' }, grid:{ color:'#243552' } },
        y1:{ position:'right', ticks:{ color:'#8fa3c1' }, grid:{ drawOnChartArea:false } }
      }
    }
  });
  const info = document.getElementById('skuCount');
  if(info) info.textContent = 'Период: '+ (from||'…') +' — '+ (to||'…') +', дней '+days.length+', выручка '+fmt0(rev)+' ₽, продажи '+fmt0(qty)+' шт';
}

/* ---------- INIT ---------- */
function initFilters(){
  const bind = (id, ev, fn) => {
    const el = document.getElementById(id);
    if(el) el.addEventListener(ev, fn);
  };
  bind('fSearch','input', renderSkus);
  bind('fAction','change', renderSkus);
  bind('fTake','change', renderSkus);
  bind('fProfit','change', renderSkus);
  bind('fSort','change', renderSkus);
  bind('fReset','click', function(){
    document.getElementById('fSearch').value='';
    document.getElementById('fAction').value='';
    document.getElementById('fTake').value='';
    document.getElementById('fProfit').value='';
    document.getElementById('fSort').value='gross';
    renderSkus();
  });
  bind('rSearch','input', renderRecs);
  bind('rAction','change', renderRecs);
  bind('rMargin','change', renderRecs);
  bind('rMarket','change', renderRecs);
  bind('rReset','click', function(){
    const rSearch = document.getElementById('rSearch');
    const rAction = document.getElementById('rAction');
    const rMargin = document.getElementById('rMargin');
    const rMarket = document.getElementById('rMarket');
    if(rSearch) rSearch.value='';
    if(rAction) rAction.value='';
    if(rMargin) rMargin.value='';
    if(rMarket) rMarket.value='';
    renderRecs();
  });
  bind('cSearch','input', renderCosts);
  bind('cMargin','change', renderCosts);
  bind('cReset','click', function(){
    const cSearch = document.getElementById('cSearch');
    const cMargin = document.getElementById('cMargin');
    if(cSearch) cSearch.value='';
    if(cMargin) cMargin.value='';
    renderCosts();
  });
  bind('wbSearch','input', renderWb);
  bind('wbMargin','change', renderWb);
  bind('wbReset','click', function(){
    const a=document.getElementById('wbSearch'), b=document.getElementById('wbMargin');
    if(a) a.value=''; if(b) b.value='';
    renderWb();
  });
  bind('cmpSearch','input', renderCmpSkus);
  bind('cmpOnly','change', renderCmpSkus);
  bind('cmpReset','click', function(){
    const a=document.getElementById('cmpSearch'), b=document.getElementById('cmpOnly');
    if(a) a.value=''; if(b) b.value='';
    renderCmpSkus();
  });
  bind('btnPeriod','click', filterDaysByPeriod);
  bind('btnPeriodReset','click', function(){
    document.getElementById('dFrom').value='__DATE_FROM__';
    document.getElementById('dTo').value='__DATE_TO__';
    filterDaysByPeriod();
  });
  // sortable headers
  document.querySelectorAll('#skuTable th[data-k]').forEach(function(th){
    th.addEventListener('click', function(){
      const k = th.getAttribute('data-k');
      const sel = document.getElementById('fSort');
      const map = {qty_sold:'qty', gross_product:'gross', total_fees:'gross', ozon_take_pct:'take',
        payout:'payout', profit_unit:'profit', ozon_fee_diff:'diff', offer_id:'gross', name:'gross',
        cost_rub:'profit', ozon_fee_plan:'diff', ozon_fee_actual_unit:'diff'};
      if(map[k]){ sel.value = map[k]; renderSkus(); }
    });
  });
}

document.addEventListener('DOMContentLoaded', function(){
  try{
    initTabs();
    initFilters();
    initExcelExport();
    renderSkus();
    renderRecs();
    renderCosts();
    renderFeeTable();
    renderWb();
    renderCmpBody();
    renderCmpSkus();
    initAllColTools();
    initColTools('wbTable', 'colMenuWb');
    buildCharts();
  }catch(err){
    showErr(err.message);
  }
});
</script>
</body>
</html>
"""

repl = {
    "__CHARTJS__": chart_js,
    "__PERIOD__": web.get("period", "2026-09-14 — 2026-10-14"),
    "__DATE_FROM__": days[0]["date"] if days else "2026-09-07",
    "__DATE_TO__": days[-1]["date"] if days else "2026-10-14",
    "__N_SKU__": str(totals.get("skus_sold", 0)),
    "__MATCHED__": str(pvf.get("n_matched", 0)),
    "__GROSS_FMT__": f"{gross:,.0f}".replace(",", " "),
    "__FEES_FMT__": f"{fees:,.0f}".replace(",", " "),
    "__PAYOUT_FMT__": f"{payout:,.0f}".replace(",", " "),
    "__QTY_FMT__": f"{totals.get('qty_sold',0):,.0f}".replace(",", " "),
    "__TAKE_PCT__": str(take_pct),
    "__PAYOUT_PCT__": str(payout_pct),
    "__COMM_PCT__": str(comm_pct),
    "__LOG_PCT__": str(log_pct),
    "__PREM_PCT__": str(fee_pct.get("premium", 0)),
    "__STARS_PCT__": str(fee_pct.get("stars", 0)),
    "__MILE_PCT__": str(fee_pct.get("last_mile", 0)),
    "__ACQ_PCT__": str(fee_pct.get("acquiring", 0)),
    "__OTHER_PCT__": str(round(100 - comm_pct - log_pct - fee_pct.get("premium", 0) - fee_pct.get("stars", 0) - fee_pct.get("last_mile", 0) - fee_pct.get("acquiring", 0), 2)),
    "__AVG_TAKE__": str(round(sum(s.get("ozon_take_pct") or 0 for s in skus_slim) / max(len(skus_slim), 1), 2)),
    "__AVG_COST__": str(avg_cost),
    "__WB_TAKE__": str(wb_totals.get("wb_take_pct", comparison.get("wb", {}).get("assumed_wb_take_pct", 20))),
    "__DELTA_TAKE__": str(round(take_pct - float(wb_totals.get("wb_take_pct", 20)), 2)),
    "__WB_N_CARDS__": str(wb_totals.get("n_cards", 0)),
    "__WB_QTY__": str(wb_totals.get("qty_sold", 0)),
    "__WB_REV__": f"{wb_totals.get('wb_revenue', 0):,.0f}".replace(",", " "),
    "__WB_ECON__": json.dumps(wb_skus, ensure_ascii=False),
    "__WB_TOTALS__": json.dumps(wb_totals, ensure_ascii=False),
    "__GROSS_NUM__": str(gross),
    "__FEES_NUM__": str(fees),
    "__PAYOUT_NUM__": str(payout),
    "__QTY_NUM__": str(totals.get("qty_sold", 0)),
    "__VERDICT__": comparison.get("verdict", ""),
    "__PLAN_FEE__": str(pvf.get("avg_plan_fee", "—")),
    "__FACT_FEE__": str(pvf.get("avg_fact_fee", "—")),
    "__PVF_DIFF__": str(pvf.get("avg_diff", "—")),
    "__PVF_DIFF_PCT__": str(pvf.get("avg_diff_pct", "—")),
    "__PVF_N__": str(pvf.get("n_matched", 0)),
    "__PVF_CLS__": ("good" if (pvf.get("avg_diff") or 0) <= 0 else "bad"),
    "__DAYS__": json.dumps(days, ensure_ascii=False),
    "__FEES__": json.dumps(fee_totals, ensure_ascii=False),
    "__FEE_PCT__": json.dumps(fee_pct, ensure_ascii=False),
    "__SKUS__": json.dumps(skus_slim, ensure_ascii=False),
    "__RECS__": json.dumps(recs, ensure_ascii=False),
    "__WB_COSTS__": json.dumps(wb_costs[:80], ensure_ascii=False),
    "__TOTALS__": json.dumps(totals, ensure_ascii=False),
    "__PFACT__": json.dumps(pvf, ensure_ascii=False),
    "__TAKE_PCT_NUM__": str(take_pct),
    "__WB_TAKE_NUM__": str(wb_totals.get("wb_take_pct", comparison.get("wb", {}).get("assumed_wb_take_pct", 20))),
    "__COMM_PCT_NUM__": str(comm_pct),
    "__LOG_PCT_NUM__": str(log_pct),
    "__SVC_PCT_NUM__": str(round(fee_pct.get("premium", 0) + fee_pct.get("stars", 0) + fee_pct.get("review_mgmt", 0) + fee_pct.get("dropoff", 0), 2)),
    "__MISC_PCT_NUM__": str(round(take_pct - comm_pct - log_pct - (fee_pct.get("premium", 0) + fee_pct.get("stars", 0) + fee_pct.get("review_mgmt", 0) + fee_pct.get("dropoff", 0)), 2)),
}

for k, v in repl.items():
    html = html.replace(k, v)

out = OUT / "index.html"
out.write_text(html, encoding="utf-8")
print("WROTE", out, "bytes", out.stat().st_size)
# sanity
import re
print("leftover", set(re.findall(r"__[A-Z0-9_]+__", html)) - {"__CHARTJS__"})
print("has Chart constructor", "class Chart" in html or "function Chart" in html or "Chart=" in html)
print("DOM loaded", "DOMContentLoaded" in html)
print("initTabs", "initTabs()" in html)
