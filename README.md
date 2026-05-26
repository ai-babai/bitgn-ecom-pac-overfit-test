# bitgn-ecom-run rust wrapper

[English](README.en.md) | [Русский](README.ru.md)

`bitgn-ecom-run` в этой ветке - Rust-wrapper вариант code-only runner для BitGN.
Текущий фокус ветки: ECOM dev. Решение закрывает задачи детерминированным кодом,
без вызовов LLM и без агентского reasoning loop. Это осознанный overfit-эксперимент
под известный dev-набор: он полезен как быстрый baseline, но не доказывает переносимость
на новые скрытые задачи.

## Статус

| Benchmark | Env | Run id | Tasks | Result | Workers | Leaderboard | Wall sum |
| --- | --- | --- | ---: | ---: | ---: | --- | ---: |
| `ecom1_dev` | dev | `rust-ecom-dev-47-stable-004` | 47 | `47/47` | 4 | no | `12.267s` local |
| `ecom1_dev` | dev | `rust-ecom-leaderboard-v012` | 47 | `47/47` | 4 | yes | `12.254s` local |

Успешная запись на leaderboard:

```text
[@skifmax]-[code-without-llm]-[eniki-beniki]-[v011]
[@skifmax]-[code-without-llm]-[eniki-beniki]-[v012]
```

`Wall sum` - сумма `wall_seconds` по всем задачам. Видимое время на сайте BitGN
считается сервером от lifecycle `start_run`/`submit_run`, поэтому оно может отличаться
от локальной суммы по задачам. Для ECOM leaderboard в этой ветке важно использовать
trial-id-only prepare: не стартовать все trials заранее до worker execution.

## Срез времени

Замер: `rust-ecom-dev-47-stable-004`, ECOM dev `t01..t47`, без leaderboard.

| Benchmark | Run id | Tasks | Workers | Task wall sum | Avg task | Median | P95 | Slowest | Tool calls sum | Read/search/sql | Action | Completion | Overhead |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `ecom1_dev` | `rust-ecom-dev-47-stable-004` | 47 | 4 | `12.267s` | `0.261s` | `0.181s` | `0.555s` | `0.642s` | not recomputed | not recomputed | not recomputed | not recomputed | not recomputed |

Самые дорогие задачи в этом срезе - inventory/count и quote-check классы; максимум в сохраненном прогоне ниже `0.7s` на задачу.

## Архитектура

```text
bitgn-ecom-run-rust
├── src/
│   ├── main.rs        # CLI entrypoint
│   ├── config.rs      # env/tasks/workers/leaderboard/fail-fast/run limits
│   ├── runner.rs      # parallel task execution and guarded leaderboard submit
│   ├── bridge.rs      # Rust -> local Python BitGN API boundary
│   ├── artifacts.rs   # run_config, manifest, summary artifacts
│   └── types.rs       # TaskResult contract
├── tools/
│   ├── bitgn_bridge.py  # Python CLI bridge between Rust and BitGN runtime
│   ├── bitgn_runtime.py # BitGN clients, adapters, gateway, workspace helpers
│   ├── ecom_solver.py   # ECOM deterministic solver families
│   └── pac1_solver.py   # PAC1 deterministic solver kept from baseline
├── rules/              # rule selector names passed into run config
├── scripts/            # local quality checks
└── docs/               # principles and saved result summary
```

Основной поток:

1. Rust CLI читает конфигурацию запуска.
2. Для ECOM runner подготавливает общий BitGN run и trial-id-only seeds.
3. `runner.rs` распределяет задачи по worker-потокам.
4. `bridge.rs` вызывает `.venv/bin/python tools/bitgn_bridge.py`.
5. Python bridge стартует trial, создает workspace, вызывает deterministic solver,
   отправляет completion и закрывает trial.
6. Rust пишет артефакты и делает leaderboard submit только если включен
   `--leaderboard true`, все задачи прошли, и `--max-wall-sum-seconds` не нарушен.

## Почему Rust и Python вместе

Rust отвечает за внешний runner: CLI, worker-потоки, fail-fast, артефакты,
агрегацию `TaskResult` и gate перед leaderboard submit. Python оставлен на границе
BitGN runtime, потому что generated packages и VM clients используются из Python.
Для ускорения Rust вызывает `.venv/bin/python` напрямую, без `uv run` на каждую задачу.

## Важные нюансы leaderboard

- ECOM leaderboard должен готовиться через trial-id-only seeds.
- Нельзя заранее вызывать `start_trial` для всех ECOM tasks до worker execution:
  это раздувает серверное время leaderboard.
- Перед submit нужен локальный non-leaderboard прогон `t01..t47` с `47/47`.
- Для текущей ветки рабочий шаблон имени:

```text
[@skifmax]-[code-without-llm]-[eniki-beniki]-[vNNN]
```

## Установка

```bash
cd /srv/aika-os/bitgn/code/bitgn-ecom-run-rust

# Rust, если еще не установлен:
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh
. "$HOME/.cargo/env"

# uv, если еще не установлен:
curl -LsSf https://astral.sh/uv/install.sh | sh

# Python env и зависимости:
uv sync

# Сборка runner:
cargo build
```

Для leaderboard нужен BitGN API key через окружение или локальный стандартный файл.
Не печатай и не коммить ключи. `runs/`, `.venv/`, `target/` и cache-директории
намеренно игнорируются git.

## Запуск

ECOM dev без leaderboard:

```bash
TASKS=$(printf 't%02d,' $(seq 1 47)); TASKS=${TASKS%,}
target/debug/bitgn-ecom-run run \
  --env ecom \
  --run-id ecom-dev-local \
  --leaderboard false \
  --fail-fast false \
  --workers 4 \
  --tasks "$TASKS" \
  --artifact-dir runs
```

ECOM dev leaderboard submit с gate по сумме времени:

```bash
TASKS=$(printf 't%02d,' $(seq 1 47)); TASKS=${TASKS%,}
target/debug/bitgn-ecom-run run \
  --env ecom \
  --run-id rust-ecom-leaderboard-vNNN \
  --run-name '[@skifmax]-[code-without-llm]-[eniki-beniki]-[vNNN]' \
  --leaderboard true \
  --fail-fast true \
  --workers 4 \
  --tasks "$TASKS" \
  --artifact-dir runs \
  --max-wall-sum-seconds 47
```

PAC1 commands still exist in the CLI, but this branch was last validated for ECOM dev.
Use the Python-only mainline for current PAC1 docs/results unless this branch is
explicitly revalidated.

## Проверки

```bash
.venv/bin/python -m py_compile tools/bitgn_bridge.py tools/bitgn_runtime.py tools/ecom_solver.py tools/pac1_solver.py
cargo fmt -- --check
cargo test
scripts/check_code_limits.py
```

## Security hygiene

- Do not commit API keys, `.env`, local key files, `.venv/`, `runs/`, or `target/`.
- Before pushing, run a secret-oriented grep over tracked files.
- Keep leaderboard names free of credentials or local paths.
