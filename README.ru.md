# bitgn-ecom-run

[English](README.en.md)

`bitgn-ecom-run` - code-only runner для BitGN ECOM/PAC1. Эта ветка переводит
оркестрацию на один язык: Python. Задачи решаются детерминированными алгоритмами,
без вызовов LLM и без Rust-обертки.

## Установка

Требования:

- Linux/macOS shell с `bash`.
- Python 3.14 через `uv`.
- Доступ к BitGN harness.
- BitGN API key нужен для ECOM и только явно включенных leaderboard-запусков.

```bash
cd bitgn-ecom-run
curl -LsSf https://astral.sh/uv/install.sh | sh
uv sync
uv run python -m py_compile bitgn_run/*.py tools/*.py
scripts/check_code_limits.py
```

## Запуск без leaderboard

ECOM dev:

```bash
TASKS=$(printf 't%02d,' $(seq 1 44)); TASKS=${TASKS%,}
uv run python -m bitgn_run.cli run \
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
uv run python -m bitgn_run.cli run \
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
uv run python -m bitgn_run.cli run \
  --env pac1-prod \
  --run-id pac1-prod-blind-local \
  --leaderboard false \
  --fail-fast false \
  --workers 10 \
  --tasks "$TASKS" \
  --artifact-dir runs
```

## Замеры DEV без leaderboard

| Benchmark | Runner | Run id | Tasks | Result | Workers | Leaderboard | Wall sum |
| --- | --- | --- | ---: | ---: | ---: | --- | ---: |
| `ecom1_dev` | Rust wrapper baseline | `decouple-ecom-dev-002` | 44 | `44/44` | 10 | no local, yes artifact | `48.020s` |
| `ecom1_dev` | Python-only | `python-only-ecom-dev-001` | 44 | `44/44` | 10 | no | `49.344s` |
| `pac1_dev` | Rust wrapper baseline | `decouple-pac1-dev-001` | 43 | `43/43` | 10 | no local, yes artifact | `89.142s` |
| `pac1_dev` | Python-only | `python-only-pac1-dev-001` | 43 | `43/43` | 10 | no | `89.099s` |

Итог: Python-only сохраняет качество. По скорости PAC1 практически без изменений
и чуть быстрее по сумме task wall, ECOM стал примерно на `1.324s` медленнее по
сумме task wall.

## Срез времени Python-only

| Benchmark | Run id | Tasks | Workers | Task wall sum | Avg task | Median | P95 | Tool calls sum | Read/search stage | Action stage | Completion stage | Overhead |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `ecom1_dev` | `python-only-ecom-dev-001` | 44 | 10 | `49.344s` | `1.121s` | `0.658s` | `1.406s` | `34.340s` | `12.734s` | `19.171s` | `2.435s` | `15.004s` |
| `pac1_dev` | `python-only-pac1-dev-001` | 43 | 10 | `89.099s` | `2.072s` | `1.498s` | `4.743s` | `85.664s` | `77.458s` | `3.903s` | `4.303s` | `3.435s` |

## Архитектура

```text
bitgn-ecom-run
├── bitgn_run/
│   ├── cli.py        # CLI entrypoint
│   ├── config.py     # env/tasks/workers/leaderboard/fail-fast/run limits
│   ├── runner.py     # parallel task execution and guarded leaderboard submit
│   ├── artifacts.py  # run_config, manifest, summary artifacts
│   └── types.py      # TaskResult contract
├── tools/
│   ├── bitgn_bridge.py  # callable task lifecycle and legacy CLI commands
│   ├── bitgn_runtime.py # BitGN API client, adapters, gateway, workspace
│   ├── ecom_solver.py   # ECOM deterministic solver
│   └── pac1_solver.py   # PAC1 deterministic solver
├── rules/              # rule selector names passed into run config
└── scripts/            # local quality checks
```

Основной цикл: Python CLI читает конфигурацию, распределяет задачи по worker
threads, напрямую вызывает Python task lifecycle, пишет артефакты, а leaderboard
submit делает только при `--leaderboard true` и успешном gate по результатам и
лимиту времени.

## Важное ограничение

Это сильный code overfit под известные dev-задачи, без LLM и без обобщающего
reasoning. Контраст с PAC1 prod остается главным индикатором: dev-результаты не
доказывают переносимость на новые задачи.
