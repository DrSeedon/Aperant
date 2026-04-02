# TODO

## Приоритет 2 — средняя сложность

- [ ] **Per-task provider selection** — каждая задача юзает свой API профиль. Актуально при 2+ аккаунтах или API credits.

## Приоритет 3 — на потом

- [ ] **Auto-Shutdown** — мониторит задачи, шатдаунит систему когда всё done. Адаптировать под Linux.
- [ ] **Watchdog** — внешний процесс-надзиратель. Проще через systemd unit.
- [ ] Kanban reconciliation — auto-heal stuck задач (паттерн из BMAD-Studio)
- [ ] Third-party auth — reuse Claude CLI токена (паттерн из Auto-Claude-Chinese)
