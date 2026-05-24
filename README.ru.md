# bitgn-ecom-run

[English](README.en.md)

`bitgn-ecom-run` - code-only runner для BitGN ECOM/PAC1. Текущая версия решает
задачи детерминированными алгоритмами, без вызовов LLM. Один CLI умеет
переключаться между ECOM dev, PAC1 dev и PAC1 prod.

## Установка

### Требования

- Linux/macOS shell с `bash`.
- Rust toolchain: `cargo`, `rustc`, `rustfmt`.
- Python 3.
- `uv` для запуска Python bridge с официальными BitGN generated packages.
- Доступ к BitGN harness и, для leaderboard, BitGN API key.

### Быстрый старт

```bash
cd bitgn-ecom-run

# Если Rust еще не установлен:
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh
. "$HOME/.cargo/env"

# Если uv еще не установлен:
curl -LsSf https://astral.sh/uv/install.sh | sh

# Проверка сборки:
cargo test
uv run python -m py_compile tools/bitgn_bridge.py tools/bitgn_runtime.py tools/pac1_solver.py
scripts/check_code_limits.py
```

### Leaderboard credentials

Leaderboard submit включается только явно через `--leaderboard true`. Ключ можно
передать окружением или стандартным локальным файлом BitGN. Не печатай и не
коммить секреты.

## Статус замеров

| Benchmark | Env | Run id | Tasks | Result | Workers | Leaderboard | Wall sum |
| --- | --- | --- | ---: | ---: | ---: | --- | ---: |
| `pac1_dev` | dev | `decouple-pac1-dev-001` | 43 | `43/43` | 10 | no | `89.142s` local |
| `ecom1_dev` | dev | `decouple-ecom-dev-002` | 44 | `44/44` | 10 | yes | `48.020s` local; `0:23` leaderboard |
| `pac1_prod` | prod blind | `pac1-prod-blind-003` | 104 | `20/104` | 10 | no | `184.323s` |

PAC1 prod был слепым прогоном по `t000..t103` без leaderboard submit.

## Срез времени

Замер снят по последним локальным dev-прогонам без leaderboard submit. `Task wall` - сумма `wall_seconds` по задачам. Tool-этапы считаются из `tool_calls.jsonl`; `Overhead` - остаток внутри task wall: локальный solver, файловые артефакты, закрытие trial и scoring.

| Benchmark | Run id | Tasks | Workers | Task wall sum | Avg task | Median | P95 | Tool calls sum | Read/search stage | Action stage | Completion stage | Overhead |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `ecom1_dev` | `decouple-ecom-dev-002` | 44 | 10 | `48.020s` | `1.091s` | `0.569s` | `1.312s` | `32.870s` | `11.740s` | `19.108s` | `2.022s` | `15.150s` |
| `pac1_dev` | `decouple-pac1-dev-001` | 43 | 10 | `89.142s` | `2.073s` | `1.523s` | `4.523s` | `86.056s` | `77.463s` | `4.142s` | `4.451s` | `3.086s` |

Для ECOM видимый tool-window был около `65.856s`, что больше task wall sum: старт trials и часть очереди сейчас не входят в `wall_seconds`. Для PAC1 видимый tool-window был около `16.655s`, потому что задачи реально легли на 10 worker-потоков.

### Важное ограничение

Это решение является сильным code overfit под известные dev-задачи, без LLM и без
обобщающего агентского reasoning. Это осознанный эксперимент: проверить, сколько
можно закрыть чистым кодом и правилами. Контраст хорошо виден на PAC1: `43/43`
на PAC1 dev против `20/104` на слепом PAC1 prod. Поэтому текущие dev-результаты
нельзя трактовать как доказательство высокой переносимости на новые задачи.

## Архитектура

```text
bitgn-ecom-run
├── src/
│   ├── main.rs        # CLI entrypoint
│   ├── config.rs      # env/tasks/workers/leaderboard/fail-fast/run limits
│   ├── runner.rs      # parallel task execution and guarded leaderboard submit
│   ├── bridge.rs      # Rust -> local Python BitGN API boundary
│   ├── artifacts.rs   # run_config, manifest, summary artifacts
│   └── types.rs       # TaskResult contract
├── tools/
│   ├── bitgn_bridge.py  # CLI bridge and ECOM deterministic solver
│   ├── bitgn_runtime.py # local BitGN API client, adapters, gateway, workspace
│   └── pac1_solver.py   # PAC1 deterministic solver
├── rules/              # rule selector names passed into run config
└── scripts/            # local quality checks
```

Основной цикл:

1. Rust CLI читает конфигурацию запуска.
2. `runner.rs` распределяет задачи по worker-потокам.
3. `bridge.rs` вызывает локальный `tools/bitgn_bridge.py` через `uv run`.
4. Python bridge через официальные BitGN packages стартует trial, гидратит workspace, выбирает deterministic solver
   по benchmark env, отправляет completion и закрывает trial.
5. Rust собирает `TaskResult`, пишет артефакты и делает leaderboard submit только
   при включенном `--leaderboard true` и прохождении gate-условий.

## Переключение benchmark

Поддерживаемые значения:

- `--env ecom` -> `bitgn/ecom1-dev`
- `--env pac1` -> `bitgn/pac1-dev`
- `--env pac1-prod` -> `bitgn/pac1-prod`

`BENCHMARK_ID` можно задать явно в окружении, если нужен нестандартный benchmark.

## Запуск

ECOM dev:

```bash
TASKS=$(printf 't%02d,' $(seq 1 44)); TASKS=${TASKS%,}
cargo run -- run \
  --env ecom \
  --run-id ecom-dev-local \
  --leaderboard false \
  --fail-fast false \
  --workers 10 \
  --tasks "$TASKS" \
  --artifact-dir runs
```

PAC1 dev:

```bash
TASKS=$(printf 't%02d,' $(seq 1 43)); TASKS=${TASKS%,}
cargo run -- run \
  --env pac1 \
  --run-id pac1-dev-local \
  --leaderboard false \
  --fail-fast false \
  --workers 10 \
  --tasks "$TASKS" \
  --artifact-dir runs
```

PAC1 prod blind:

```bash
TASKS=$(printf 't%03d,' $(seq 0 103)); TASKS=${TASKS%,}
cargo run -- run \
  --env pac1-prod \
  --run-id pac1-prod-blind-local \
  --leaderboard false \
  --fail-fast false \
  --workers 10 \
  --tasks "$TASKS" \
  --artifact-dir runs
```

## Проверки

```bash
uv run python -m py_compile tools/bitgn_bridge.py tools/bitgn_runtime.py tools/pac1_solver.py
cargo fmt -- --check
cargo test
scripts/check_code_limits.py
```
