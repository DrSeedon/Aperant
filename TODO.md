# TODO

## Портировать из Aperant-MCP (topemalheiro/Aperant-MCP)

Референс: https://github.com/topemalheiro/Aperant-MCP (v2.7.6-beta.5, совместим с нашей базой)

### Приоритет 1 — быстро, большая отдача

- [ ] **exitReason tracking** — `_save_exit_reason()` в `coder.py` и `planner.py` (~80 строк). Пишет причину падения в `implementation_plan.json`. Без этого непонятно почему задача сдохла.

- [ ] **Per-task provider selection** — каждая задача может юзать свой API профиль. Читает `providerId` из `task_metadata.json`, передаёт env агенту. 17 файлов но изолированная фича, не ломает остальное.

- [ ] **Project Index Cache** — 5-мин TTL кэш с threading.Lock в `core/client.py` (+49 строк). Ускоряет создание агентских сессий, 0 side effects.

### Приоритет 2 — средняя сложность

- [ ] **Python MCP-сервер** — внешний MCP-сервер (FastMCP) чтобы Claude Code мог управлять задачами напрямую: create_task, start_batch, get_status, recover_stuck. У них на TypeScript (3750 строк), нам переписать на Python.

- [ ] **RDR система (упрощённая)** — автовосстановление застрявших задач. У них 6 уровней эскалации (2876 строк монолит). Нам хватит 2-3 уровня: auto-continue, auto-recover, request changes.

- [ ] **Skill-файлы для Claude Code** — `.claude/skills/` с инструкциями как управлять задачами через MCP и чинить упавшие. Это просто markdown, адаптировать под наш workflow.

### Приоритет 3 — на потом

- [ ] **Auto-Shutdown** — мониторит задачи, шатдаунит систему когда всё done. Полезно для overnight runs. Адаптировать `shutdown` команду под Linux.

- [ ] **Watchdog** — внешний процесс-надзиратель, рестартует Electron при краше. У нас проще через systemd unit.

- [ ] **Auto-Refresh UI** — chokidar следит за plan-файлами, пушит обновления в renderer. Задачи обновляются в реальном времени без ручного рефреша.

### Не портировать

- **Window Manager** — Windows-only, PowerShell, слепой paste через Ctrl+V
- **Output Monitor** — читает JSONL internals Claude Code через regex, хрупко
- **MiniMax preset** — специфичный провайдер, у нас другие приоритеты
- **HuggingFace OAuth** — не нужен пока

## Другие идеи

- [ ] Посмотреть kanban reconciliation fix из **Sallvainian/BMAD-Studio** — auto-heal stuck задач
- [ ] Посмотреть third-party auth паттерн из **tytsxai/Auto-Claude-Chinese** — reuse Claude CLI токена
