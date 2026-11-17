# Очередь задач — Хостинг Jino (2026-11-18)

## Выполнено

| # | Задача | Статус | Детали |
|---|--------|--------|--------|
| T1 | Убрать секреты из репозиториев | ✅ | alrent, ozon_analytics, mimocode-memory |
| T2 | Перенос alrent.ru на Jino + SSL | ✅ | Тестовая страница, Let's Encrypt wildcard |
| T3 | Полный перенос intensetea.ru | ✅ | 17 509 файлов + БД (222 таблицы) |
| T3.1 | Скачать файлы с shneider-host | ✅ | tar.gz архив 247 МБ через SSH |
| T3.2 | Скачать/перенести БД | ✅ | 222 таблицы, 2.8 МБ дамп |
| T3.3 | Залить файлы и БД на Jino | ✅ | Распаковка через PHP, импорт MySQL |
| T3.4 | Проверить работоспособность | ✅ | Товары, корзина, оформление заказа |
| T5 | Настроить уведомления о заказах | ✅ | PHP mail(), mail.php настроен |

## В очереди (заблокированы)

| # | Задача | Блокер | Что нужно |
|---|--------|--------|-----------|
| T4 | MX-запись для intensetea.ru | Панель Jino (cp.jino.ru) — капча при входе | Добавить MX: `@` → `mail.intensetea.ru` (priority 10). Создать ящик `sales@intensetea.ru` |
| T6 | Cron-задачи на Jino | Нужен доступ к панели | Panel → Cron: `*/5 * * * *` → `/usr/bin/php /home/users/j/j94929750/domains/intensetea.ru/_cron_orders.php` |

## Инфраструктура

### Хостинг Jino (`fcdbfd983987.hosting.myjino.ru`)
- **IP:** 195.161.41.120
- **FTP:** порт 21, логин `j94929750`, пароль `vbkkbfhlZAQ12wsx`
- **SFTP:** порт 2222 (SSH shell закрыт — shared hosting)
- **MySQL:** хост `localhost`, БД `j94929750_intensetea`, пользователь `j94929750_admin`, пароль `vbkkbfhlZAQ12wsx`
- **Панель:** `cp.jino.ru` (требует отдельный пароль + капчу)

### Сайты

| Домен | Статус | SSL | Особенности |
|-------|--------|-----|-------------|
| alrent.ru | ✅ Работает | Let's Encrypt wildcard | Тестовая страница |
| intensetea.ru | ✅ Работает | Let's Encrypt wildcard | Webasyst Shop-Script, 21 товар, 70 заказов |

### Почта intensetea.ru
- **Отправка:** PHP `mail()` через sendmail (SMTP порты закрыты на Jino)
- **MX-записи:** ОТСУТСТВУЮТ — письма на `@intensetea.ru` не доходят
- **Решение:** Добавить MX-запись `mail.intensetea.ru` в DNS-панели Jino
- **Внешняя отправка:** Работает (тест на mail.ru пройден)

### DNS intensetea.ru
- **NS:** ns1–ns4.jino.ru
- **A:** 195.161.41.120 (оба домена)
- **MX:** ❌ Нет (нужно добавить)
- **Регистратор:** RU-CENTER (nic.ru)

## Ссылки
- Репозиторий: https://github.com/omnysmm/mimocode-memory
- Панель Jino: https://cp.jino.ru
- Хостинг: https://hosting.jino.ru
