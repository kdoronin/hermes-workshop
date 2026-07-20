# Задание Hermes-агенту: настрой универсальную LLM Wiki

Ты — уже работающий Hermes Agent. Настрой для текущего пользователя человекочитаемую долговременную память на базе Markdown/Obsidian и skill `llm-wiki`.

Это **инструкция агенту, а не руководство по установке Hermes**. Не объясняй, как устанавливать Hermes, запускать setup wizard или выбирать модель. Используй доступные инструменты и доведи настройку до проверенного результата.

## Цель

После выполнения:

- LLM Wiki является каноническим долговечным источником персонального контекста;
- Wiki хранится в обычных Markdown-файлах и совместима с Obsidian;
- Hermes ориентируется по Wiki перед персональными ответами;
- важные знания сохраняются в тематические страницы, а не только в скрытую память или историю чатов;
- текущее состояние отделено от истории, план — от подтверждённого факта, синтез — от сырого источника;
- `SCHEMA.md`, `index.md`, `log.md` и lint поддерживают целостность базы.

## Границы задачи

Не делай следующее:

- не устанавливай и не переустанавливай Hermes;
- не меняй модель, provider, gateway или интеграции, не связанные с Wiki;
- не копируй имена, пути, проекты или другие персональные данные из примеров;
- не перезаписывай существующую Wiki шаблонами;
- не удаляй существующую память без резервной копии;
- не заявляй об успехе без чтения созданных файлов и реального запуска проверок.

Если Wiki уже существует, сначала прочитай её правила и сделай резервную копию перед структурными изменениями.

## 0. Сначала запросить параметры у пользователя

Не начинай настройку с догадок о пользовательской файловой системе и политике памяти. Сначала одним компактным сообщением запроси обязательные параметры.

Задай пользователю следующие вопросы:

1. **Где находится или должна находиться папка LLM Wiki?** Попроси абсолютный путь к `WIKI_PATH`.
2. **Является ли эта папка самостоятельным Obsidian vault или находится внутри другого vault?** Если внутри — попроси абсолютный `OBSIDIAN_VAULT_PATH`.
3. **Wiki уже существует или её нужно создать с нуля?**
4. **Нужен ли режим `wiki-only`?** Объясни кратко: в этом режиме внешние memory-provider’ы отключаются, а Wiki становится единственным каноническим долговечным слоем.
5. **Разрешено ли изменить `.env` и `SOUL.md` активного Hermes-профиля?**
6. **Какой основной язык Wiki и какие 3–7 областей она должна покрывать?** Например: проекты, работа, исследования, здоровье, решения, люди, источники.
7. **Какой нейтральный slug использовать для страницы пользователя?** Например: `user-profile`, либо предложи безопасный вариант сам и попроси подтвердить.

Используй инструмент уточнения, если он доступен. Не задавай повторно вопрос, если пользователь уже дал ответ в текущем сообщении или приложенном контексте.

Первое сообщение пользователю может выглядеть так:

```text
Чтобы настроить LLM Wiki без догадок, мне нужны параметры:

1. Абсолютный путь к папке LLM Wiki.
2. Это отдельный Obsidian vault или папка внутри vault? Если внутри — путь к корню vault.
3. Wiki уже существует или её нужно создать?
4. Делать ли Wiki единственным каноническим долговечным слоем и отключать внешние memory-provider’ы?
5. Можно ли изменить `.env` и `SOUL.md` текущего Hermes-профиля?
6. Основной язык Wiki и её главные области.
7. Какой slug использовать для страницы профиля пользователя?
```

После ответа покажи короткое резюме параметров и запроси подтверждение только для действий, меняющих существующую Wiki, `.env`, `SOUL.md` или memory-provider. Создание новой Wiki в явно указанной пустой папке можно выполнять сразу, если пользователь уже прямо попросил настройку.

Если пользователь не знает путь, помоги выбрать его: покажи 2–3 типовых варианта для его ОС, но не выбирай молча. Если указан относительный путь или `~`, разреши его до абсолютного пути и покажи пользователю итоговое значение перед записью в конфигурацию.

## 1. Загрузить нужные skills

Сначала загрузи:

- `llm-wiki` — правила Wiki, ingest, query и lint;
- `hermes-agent` — только для корректного изменения конфигурации текущего Hermes.

Проверь наличие `llm-wiki`. Если bundled skill отсутствует или повреждён, восстанови штатную копию доступным способом. Не изменяй сам skill, если для задачи достаточно настройки Wiki и policy.

## 2. Проверить и зафиксировать указанные пути

Используй пути, которые сообщил или подтвердил пользователь:

```text
OBSIDIAN_VAULT_PATH=<корень Obsidian vault>
WIKI_PATH=<каталог LLM Wiki внутри vault или отдельный каталог Wiki>
```

Предпочтительная структура:

```text
<OBSIDIAN_VAULT_PATH>/
└── Hermes/                 # WIKI_PATH; имя каталога можно адаптировать
    ├── SCHEMA.md
    ├── index.md
    ├── log.md
    ├── _meta/
    │   ├── templates/
    │   └── scripts/
    ├── concepts/
    ├── areas/
    ├── projects/
    │   ├── active/
    │   ├── ideas/
    │   └── archive/
    ├── entities/
    ├── decisions/
    ├── events/
    ├── metrics/
    ├── reviews/
    │   ├── daily/
    │   └── weekly/
    ├── queries/
    ├── source-notes/
    └── raw/
        ├── articles/
        ├── papers/
        ├── transcripts/
        └── assets/
```

Порядок проверки:

1. Разреши сообщённые пути до абсолютных.
2. Проверь, существуют ли эти каталоги и доступны ли они для чтения/записи.
3. Если `WIKI_PATH` уже содержит `SCHEMA.md`, `index.md` или другие Markdown-страницы, считай Wiki существующей и не инициализируй её поверх данных.
4. Сравни подтверждённые пути с текущими `WIKI_PATH` и `OBSIDIAN_VAULT_PATH` в окружении Hermes.
5. Если конфигурация указывает на другой каталог, покажи расхождение и запроси подтверждение перед заменой.
6. Не сканируй произвольно всю домашнюю папку в поисках «подходящей» Wiki, если пользователь уже указал путь.
7. Используй абсолютные пути; не записывай `~` в `.env`.

`OBSIDIAN_VAULT_PATH` может указывать на корень vault, а `WIKI_PATH` — на вложенный каталог. Они не обязаны совпадать. Если сама папка Wiki является отдельным Obsidian vault, оба значения могут совпадать — это должен подтвердить пользователь.

## 3. Зафиксировать пути в окружении Hermes

Найди `.env` активного Hermes-профиля и запиши:

```dotenv
WIKI_PATH=/absolute/path/to/wiki
OBSIDIAN_VAULT_PATH=/absolute/path/to/vault
```

Сохрани остальные переменные без изменений. Не выводи секреты из `.env` в чат или отчёт.

Если работа идёт в named profile, изменяй только этот профиль. Не трогай другие профили без прямого указания пользователя.

## 4. Настроить модель памяти

Целевая модель:

1. **LLM Wiki** — канонический человекочитаемый долговечный слой.
2. **Session search** — исторический поиск по разговорам, но не источник текущей истины.
3. **Runtime context** — временный контекст текущей сессии.
4. **Внешние memory-provider’ы** — не используются как параллельная каноническая база.

Только если пользователь явно выбрал режим `wiki-only`, отключи внешний memory-provider штатной командой Hermes и проверь статус. Не меняй memory policy по умолчанию без ответа пользователя. Ожидаемая семантика:

```text
Provider: (none — built-in only)
```

Не выдавай встроенную инфраструктуру Hermes за отдельную каноническую память. Важные пользовательские знания должны сохраняться в Wiki.

Не отключай `session_search`: он полезен как вторичный источник того, что было сказано раньше.

## 5. Добавить grounding policy

Найди `SOUL.md` активного профиля и добавь или аккуратно объедини следующий раздел. Не удаляй существующие правила характера и взаимодействия.

```markdown
## Knowledge grounding

The canonical, primary source of durable information about the user is the LLM Wiki at `WIKI_PATH`. When a request depends on the user's history, preferences, goals, projects, decisions, current priorities, or personal context, consult the wiki before answering instead of relying only on generic memory or prior chat context.

Load the `llm-wiki` skill and orient by reading `SCHEMA.md`, `index.md`, and the recent entries in `log.md`; then read the relevant current-state pages. Prefer fresh user messages and current-state sections over historical or reconstructed claims.

Any link, article, repository, project, message, decision, preference, or reusable conclusion that the user explicitly asks to remember must be ingested into the LLM Wiki. Hidden memory, session history, GBrain, or another database must not become the only durable copy.
```

Не хардкодь имя пользователя или путь конкретного компьютера в переносимый шаблон. В реальном `SOUL.md` можно использовать разрешённый абсолютный `WIKI_PATH`, если это делает grounding надёжнее.

## 6. Инициализировать или адаптировать Wiki

### Если Wiki новая и пользователь подтвердил путь

Убедись, что каталог пуст или не содержит конфликтующих пользовательских файлов. Затем создай каталоги из целевой структуры и три корневых файла:

- `SCHEMA.md` — правила данных и поведения агента;
- `index.md` — каталог актуальных страниц;
- `log.md` — append-only журнал изменений самой Wiki.

### Если Wiki существует

Перед изменением:

1. прочитай `SCHEMA.md`;
2. прочитай `index.md`;
3. прочитай последние 20–30 записей `log.md`;
4. найди существующие страницы про memory, пользователя и assistant preferences;
5. создай резервную копию;
6. адаптируй структуру без потери пользовательского содержания.

Не создавай дубликаты страниц только потому, что их названия отличаются от шаблона.

## 7. Требования к `SCHEMA.md`

Схема должна зафиксировать следующие принципы.

### 7.1. Разделение данных

Wiki разделяет:

1. **что существует** — entities, areas, concepts и projects;
2. **что произошло** — events и source notes;
3. **что сейчас истинно** — Current State и активный frontmatter;
4. **откуда это известно** — sources и `evidenced_by`;
5. **что решено или запланировано** — decisions, next actions и due dates.

### 7.2. Типы страниц

Разреши как минимум:

```text
entity
project
project-idea
area
concept
source-note
event
decision
review
query
```

### 7.3. Общий frontmatter

Используй базовый контракт:

```yaml
---
title: Page Title
type: concept
status: active
created: YYYY-MM-DD
updated: YYYY-MM-DD
valid_from: YYYY-MM-DD
valid_until:
tags: [allowed-tag]
sources: []
confidence: high | medium | low
contested: false
relations:
  related_to: []
  evidenced_by: []
---
```

Смысл дат:

- `created`, `updated` описывают файл;
- `valid_from`, `valid_until` описывают период истинности состояния;
- `observed_at` — когда факт зафиксирован;
- `occurred_at` — когда событие произошло;
- `due_at` или `next_action_due` — срок обязательства;
- `review_after` — когда решение или ожидание нужно пересмотреть.

### 7.4. Current State и Timeline

Для project/area страниц используй:

```markdown
# Title

## Current State
- **Status:**
- **Stage:**
- **Next action:**
- **Due:**
- **Blockers:**

## Why It Matters

## Timeline

### YYYY-MM-DD — Event
- Что произошло.
- Source: [[source-note]]

## Decisions

## Open Loops

## Related
```

Правила:

- `Current State` находится выше истории и обновляется in-place;
- `Timeline` сохраняет историю, новые записи идут сверху;
- прошлый факт не удаляется только потому, что перестал быть текущим;
- новое решение связывается с заменённым через `supersedes`;
- противоречие сохраняется через `contested: true` и `contradicts`.

### 7.5. Типизированные связи

Разреши как минимум:

```text
part_of
supports
depends_on
blocks
related_to
evidenced_by
supersedes
contradicts
involves
uses
produces
```

Значения relations — массивы Obsidian wikilinks.

### 7.6. Raw sources

Файлы в `raw/` неизменяемы после ingest. Используй frontmatter:

```yaml
---
source_url: https://example.com/source
ingested: YYYY-MM-DD
sha256: <hash of body after frontmatter>
---
```

Исправления и синтез хранятся не в raw, а в source notes и тематических страницах.

### 7.7. Tags

Создай ограниченную taxonomy под реальный домен пользователя.

Правила:

- tag описывает тему, а не type/status;
- новый tag сначала добавляется в taxonomy, затем используется;
- не создавай свободный tag для каждого нового источника.

### 7.8. Факты, планы и деньги

- planned/expected/estimated не равны confirmed;
- ожидаемая ценность не записывается как подтверждённая выручка;
- неполные данные не заполняются догадками;
- повторяющиеся числа хранятся в `metrics/` как временные ряды.

## 8. Создать `index.md`

Используй разделы, релевантные пользователю. Базовый вариант:

```markdown
# Wiki Index

> Content catalog for LLM Wiki. Current state lives in project/area pages; history lives in timelines, events and source notes.
> Last updated: YYYY-MM-DD | Total content pages: N

## Core Areas

## Active Projects

## Project Ideas

## Entities

## Concepts

## Active Decisions

## Recent Events

## Metrics

## Reviews

## Queries

## Source Notes
```

Каждая запись — одна строка:

```markdown
- [[path/page-slug|Human Title]] — краткое описание актуального содержания.
```

Каждая content page должна присутствовать в индексе. Обновляй дату и счётчик страниц после изменений.

## 9. Создать `log.md`

`log.md` описывает изменения Wiki, а не копирует всю жизнь пользователя.

Базовый формат:

```markdown
# Wiki Log

> Append-only log of Wiki-level changes.

## [YYYY-MM-DD] create | Wiki initialized

- Created the Wiki structure and root files.
- Configured paths and grounding policy.
```

Логируй:

- ingest;
- create/update/archive;
- schema migration;
- lint;
- source drift;
- значимое исправление структуры.

Не используй `log.md` как замену events, metrics или project timelines.

## 10. Создать стартовые страницы

Создай или адаптируй эквиваленты:

```text
areas/assistant-interaction-preferences.md
areas/agent-memory.md
concepts/llm-wiki.md
concepts/personal-ai-stack.md
entities/<user-slug>.md
```

Названия можно адаптировать к существующей Wiki.

Требования:

- валидный frontmatter;
- осмысленные wikilinks;
- Current State для area/project;
- запись в `index.md`;
- изменение отражено в `log.md`.

На странице про agent memory зафиксируй границы между Wiki, session search и runtime context.

На странице assistant preferences храни устойчивые предпочтения по стилю, формату, исследованию, коду и взаимодействию. Не помещай туда временные задачи.

На entity-странице пользователя храни только подтверждённые устойчивые данные и явно отделяй актуальное состояние от исторических сведений.

## 11. Рабочий протокол Wiki

Перед персональной задачей или операцией с Wiki:

1. загрузи `llm-wiki`;
2. прочитай `SCHEMA.md`;
3. прочитай `index.md`;
4. прочитай последние записи `log.md`;
5. найди релевантные страницы;
6. прочитай Current State до исторических деталей;
7. предпочти свежую реплику пользователя старой реконструкции.

После записи:

1. обнови тематические страницы;
2. обнови Current State и Timeline отдельно;
3. добавь provenance, confidence и relations;
4. обнови `index.md`;
5. дополни `log.md`;
6. запусти lint;
7. сообщи все изменённые файлы и реальные результаты проверки.

## 12. Ingest источников

Когда пользователь просит запомнить ссылку, статью, репозиторий, сообщение или файл:

1. сохрани неизменяемый исходник в подходящий каталог `raw/`;
2. добавь `source_url`, `ingested`, `sha256`;
3. создай source note с контекстом и выводами;
4. найди уже существующие страницы по теме;
5. обнови существующие страницы вместо создания дублей;
6. создай новую страницу только для центральной сущности или устойчивого концепта;
7. отдели утверждения источника от подтверждённых выводов;
8. пометь single-source или спорные claims подходящим confidence;
9. обнови index/log;
10. запусти lint.

Не сохраняй источник только в hidden memory или только в source note без интеграции с релевантными страницами.

## 13. Lint

Создай dependency-free скрипт:

```text
<WIKI_PATH>/_meta/scripts/wiki_lint.py
```

Он должен проверять:

- обязательный frontmatter;
- допустимые type/status/stage;
- неизвестные tags и relation keys;
- broken wikilinks;
- страницы вне `index.md`;
- проекты без concrete next action;
- просроченные next actions;
- raw SHA-256 drift;
- страницы больше 200 строк.

Классификация по умолчанию:

- broken link и отсутствующий обязательный frontmatter — error;
- raw drift, overdue action и oversized page — warning;
- при errors процесс завершается с ненулевым кодом.

После создания реально запусти lint. Не подменяй вывод ожидаемым текстом.

## 14. Проверка результата

### Read-only smoke test

В новой сессии или после reload/restart попроси Hermes:

```text
Загрузи llm-wiki. Определи WIKI_PATH, прочитай SCHEMA.md, index.md и последние записи log.md. Назови стартовые страницы, ничего не изменяя.
```

Проверка пройдена, если Hermes:

- использует правильный `WIKI_PATH`;
- действительно читает ориентационные файлы;
- показывает существующие страницы;
- не пишет файлы при read-only запросе;
- не придумывает персональный контекст.

### Write smoke test

Используй нейтральное тестовое предпочтение, согласованное с пользователем, либо попроси пользователя дать одно реальное предпочтение. Затем дай команду:

```text
Сохрани это предпочтение в LLM Wiki. Покажи изменённые файлы и реальный результат lint.
```

Проверка пройдена, если:

- создана или обновлена корректная thematic page;
- `index.md` обновлён, если страница новая;
- `log.md` дополнен;
- lint реально выполнен;
- предпочтение не осталось только в скрытой памяти.

Не записывай выдуманный тестовый факт как реальное предпочтение пользователя.

## 15. Финальный отчёт

Верни пользователю краткий отчёт:

```markdown
## Настроено
- WIKI_PATH: …
- OBSIDIAN_VAULT_PATH: …
- Memory policy: …
- Grounding policy: …

## Создано или изменено
- path/to/file
- path/to/file

## Проверки
- Skill: PASS/FAIL
- Root files: PASS/FAIL
- Lint: фактический вывод
- Read-only smoke test: PASS/FAIL
- Write smoke test: PASS/FAIL или причина, почему требовалось подтверждение пользователя

## Оставшиеся предупреждения
- …
```

Не включай содержимое секретов. Не скрывай warnings и блокеры.

## Acceptance criteria

- [ ] Определены абсолютные `WIKI_PATH` и `OBSIDIAN_VAULT_PATH`.
- [ ] Загружен и доступен `llm-wiki`.
- [ ] Созданы или адаптированы `SCHEMA.md`, `index.md`, `log.md`.
- [ ] Wiki разделяет current state, history, sources, decisions и metrics.
- [ ] В `SOUL.md` добавлен grounding без удаления существующих правил.
- [ ] Memory policy явно отделяет Wiki от session search и runtime context.
- [ ] Стартовые страницы созданы или сопоставлены с существующими.
- [ ] Raw sources имеют provenance и не редактируются после ingest.
- [ ] `index.md` содержит все content pages.
- [ ] Lint реально запущен и не имеет errors.
- [ ] Read-only smoke test пройден.
- [ ] Write smoke test пройден либо честно отложен до получения реального факта пользователя.
- [ ] Финальный отчёт перечисляет все изменения и предупреждения.
