# Пуговицнет — Аналитика Ozon vs Wildberries

Одностраничный дашборд с реальными затратами Ozon по каждому артикулу, себестоимостью из Google Sheets, планом/фактом, конкурентами и рекомендациями по ценам.

## Открыть дашборд

`index.html` — готовый статический сайт (данные и Chart.js вшиты). Можно открыть локально в браузере.

## Функции

- Вкладки: Обзор · По артикулам · Затраты Ozon · Цены и конкуренты · Ozon vs WB · Себестоимость и маржа
- Фильтры, период, сортировка, графики (Chart.js локально)
- **Цена Ozon** — живая из `/v3/product/info/list` (не средняя продажи, не план)
- **Затраты озон на шт** — реальные начисления Ozon
- **Рекомендованная цена** — `(J + K + прочие затраты Ozon) / (1 − комиссия%)`, чистая прибыль = K
- **Конкуренты** — индексы Ozon (внешние МП / продавцы Ozon / Ozon Retail)
- **Столбцы:** ручная ширина (потяните правый край заголовка) + фильтр видимости «Столбцы ▾» (по умолчанию все)
- ТОЛЬКО ЧТЕНИЕ Ozon / Google Sheets

## Данные

| Источник | Что берём |
|---|---|
| Excel «Отчёт по начислениям» Ozon | реальные затраты / шт |
| Ozon Seller API `/v3/product/info/list` | текущая цена |
| Ozon `/v5/product/info/prices` + `price_indexes` | комиссии, индексы конкурентов |
| Google Sheet (колонка **J**) | себестоимость |
| Google Sheet (колонка **P**) | плановая комиссия+логистика |
| Google Sheet (колонка **K**) | целевая наценка (чистая прибыль) |

## Сборка

```bash
# 1) положить ключи в ozon_config.json (см. ozon_config.example.json)
# 2) собрать данные (read-only)
python fetch_ozon.py
python fetch_live_prices.py
python fetch_analytics.py
# 3) обновить экономику и HTML
python unify_prices.py
python calc_price_rec.py
python build_site2.py
# 4) проверки
python smoke_test.py
python test_col_tools.py
```

## Конфигурация

Скопируйте `ozon_config.example.json` → `ozon_config.json` и впишите API-ключи Ozon.
**`ozon_config.json` не коммитить** (секреты).

## Стек

Python 3.12 · Playwright (smoke) · Chart.js 4.4 (локально в `chart.umd.min.js`) · один `index.html` без сервера.
