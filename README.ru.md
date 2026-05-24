# bitgn-ecom-run

[English](README.en.md) | [Main](README.md)

`bitgn-ecom-run` - code-only runner для BitGN ECOM/PAC1. Текущая версия решает
задачи детерминированными алгоритмами, без вызовов LLM. Один CLI умеет
переключаться между ECOM dev, PAC1 dev и PAC1 prod.

## Установка

### Требования

- Linux/macOS shell с `bash`.
- Rust toolchain: `cargo`, `rustc`, `rustfmt`.
- Python 3.
- `uv` для запуска Python bridge через изолированный project runner.
- Локальный ignored snapshot адаптера BitGN harness:
  `reference/bitgn-ecom-localbench-env/`.
- Доступ к BitGN harness и, для leaderboard, BitGN API key.

### Быстрый старт

```bash
cd /srv/aika-os/bitgn/code/bitgn-ecom-run

# Если Rust еще не установлен:
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh
. "$HOME/.cargo/env"

# Если uv еще не установлен:
curl -LsSf https://astral.sh/uv/install.sh | sh

# Проверка сборки:
cargo test
python3 -m py_compile tools/bitgn_bridge.py tools/pac1_solver.py
scripts/check_code_limits.py
```

### Локальный reference snapshot

`reference/bitgn-ecom-localbench-env/` не хранится в git и закрыт `.gitignore`.
Он нужен только локально как adapter/runtime bridge к BitGN harness. Если каталога
нет, восстанови его из локального соседнего workspace, не коммить содержимое:

```bash
mkdir -p reference
rsync -a --delete \
  /srv/aika-os/bitgn/code/bitgn-ecom-localbench-env/ \
  reference/bitgn-ecom-localbench-env/
```

### Leaderboard credentials

Leaderboard submit включается только явно через `--leaderboard true`. Ключ можно
передать окружением или стандартным локальным файлом BitGN. Не печатай и не
коммить секреты.

## Статус замеров

| Benchmark | Run id | Tasks | Result | Workers | Leaderboard | Wall sum |
| --- | --- | ---: | ---: | ---: | --- | ---: |
| ECOM dev | `main-ecom-dev-001` | 44 | `44/44` | 10 | no | `58.203s` |
| PAC1 dev | `main-pac1-dev-003` | 43 | `43/43` | 10 | no | `170.699s` |
| PAC1 prod blind | `pac1-prod-blind-002` | 104 | `20/104` | 10 | no | `182.606s` |
| ECOM leaderboard | `leaderboard-shmygolet-v006-002` | 44 | `44/44` | 10 | yes | `26.412s` local, `0:23` leaderboard |

ECOM leaderboard name: `[@skifmax]-[code-without-llm]-[shmygolet]-[v006]`.
PAC1 prod был слепым прогоном по `t000..t103`; строка фиксирует результат этого
замера, последующие dev-stability правки в него не включены.

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
│   ├── bridge.rs      # Rust -> Python bridge boundary
│   ├── artifacts.rs   # run_config, manifest, summary artifacts
│   └── types.rs       # TaskResult contract
├── tools/
│   ├── bitgn_bridge.py # BitGN harness bridge and ECOM deterministic solver
│   └── pac1_solver.py  # PAC1 deterministic solver
├── rules/             # rule selector names passed into run config
├── scripts/           # local quality checks
└── reference/bitgn-ecom-localbench-env/  # ignored local harness adapter snapshot
```

Основной цикл:

1. Rust CLI читает конфигурацию запуска.
2. `runner.rs` распределяет задачи по worker-потокам.
3. `bridge.rs` вызывает `tools/bitgn_bridge.py` через `uv run`.
4. Python bridge стартует trial, гидратит workspace, выбирает deterministic solver
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
python3 -m py_compile tools/bitgn_bridge.py tools/pac1_solver.py
cargo fmt -- --check
cargo test
scripts/check_code_limits.py
```
