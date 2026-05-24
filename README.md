# bitgn-ecom-pac-lab

[English](README.en.md)

`bitgn-ecom-pac-lab` - экспериментальная лаборатория для BitGN-бенчмарков ECOM/PAC1. Проект проверяет разные стратегии решения benchmark-задач; текущая основная стратегия использует заранее написанный детерминированный код без AI/LLM-вызовов во время выполнения задач.

Короткая навигация: подробная [установка и проверка окружения](#установка-и-проверка-окружения) вынесена в конец README.

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

## Результаты Python-only

| Benchmark | Env | Run id | Tasks | Result | Workers | Leaderboard | Wall sum |
| --- | --- | --- | ---: | ---: | ---: | --- | ---: |
| `ecom1_dev` | dev | `leaderboard-ecom-dev-eniki-beniki-v007` | 44 | `44/44` | 10 | yes | `30.181s` |
| `pac1_dev` | dev | `leaderboard-pac1-dev-eniki-beniki-v007` | 43 | `43/43` | 10 | yes | `93.619s` |
| `pac1_prod` | prod blind | `pac1-prod-blind-eniki-beniki-v007` | 104 | `21/104` | 10 | no | `92.666s` |

Для dev-строк `Leaderboard=yes` означает, что это свежие leaderboard-прогоны с именем `[@skifmax]-[code-without-llm]-[eniki-beniki]-[v007]`. `pac1_prod` - слепой прогон без leaderboard.

## Срез времени Python-only

| Benchmark | Run id | Tasks | Workers | Task wall sum | Avg task | Median | P95 | Tool calls sum | Read/search stage | Action stage | Completion stage | Overhead |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `ecom1_dev` | `leaderboard-ecom-dev-eniki-beniki-v007` | 44 | 10 | `30.181s` | `0.686s` | `0.417s` | `1.081s` | `21.985s` | `9.280s` | `11.347s` | `1.358s` | `8.196s` |
| `pac1_dev` | `leaderboard-pac1-dev-eniki-beniki-v007` | 43 | 10 | `93.619s` | `2.177s` | `1.532s` | `4.733s` | `89.348s` | `80.916s` | `4.025s` | `4.407s` | `4.271s` |
| `pac1_prod` | `pac1-prod-blind-eniki-beniki-v007` | 104 | 10 | `92.666s` | `0.891s` | `0.570s` | `1.685s` | `85.058s` | `74.438s` | `0.000s` | `10.620s` | `7.608s` |

## Архитектура

```text
bitgn-ecom-pac-lab
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

## Файлы интереса

Если хочется посмотреть на накопленные эвристики, правила и инструкции, которые сейчас реально ведут решение задач, начните с этих файлов:

- [tools/ecom_solver.py](tools/ecom_solver.py) - deterministic solver для ECOM-задач.
- [tools/pac1_solver.py](tools/pac1_solver.py) - deterministic solver для PAC1-задач.
- [tools/bitgn_runtime.py](tools/bitgn_runtime.py) - общий gateway к BitGN tools и запись артефактов.

## Важное ограничение

Это сильный code overfit под известные dev-задачи, без LLM и без обобщающего
reasoning. Контраст с PAC1 prod остается главным индикатором: dev-результаты не
доказывают переносимость на новые задачи.

## Установка и проверка окружения

Эта секция справочная: установка не является основной целью репозитория, но по ней можно быстро поднять локальный запуск.

### Требования

- Linux/macOS shell с `bash`.
- `git` и `curl`.
- `uv` для управления Python и зависимостями.
- Доступ к BitGN harness.
- BitGN API key для ECOM и leaderboard-запусков. PAC1 playground обычно стартует без ключа, но общий runner умеет читать тот же ключ.

### 1. Получить репозиторий

```bash
git clone https://github.com/ai-babai/bitgn-ecom-pac-lab.git
cd bitgn-ecom-pac-lab
```

Если локальная копия была сделана до переименования репозитория:

```bash
git remote set-url origin https://github.com/ai-babai/bitgn-ecom-pac-lab.git
```

### 2. Установить uv и Python

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
uv python install 3.14
uv sync
```

`uv sync` поставит зависимости из `pyproject.toml` и `uv.lock`, включая официальные generated packages BitGN.

### 3. Передать BitGN API key

Можно использовать переменную окружения:

```bash
export BITGN_API_KEY="..."
```

Или стандартный локальный файл:

```bash
mkdir -p ~/.bitgn
printf '%s\n' '...' > ~/.bitgn/bitgn-api-key
chmod 600 ~/.bitgn/bitgn-api-key
```

Также поддерживаются `BITGN_ECOM_API_KEY`, `BITGN_API_KEY_FILE` и `BITGN_ECOM_API_KEY_FILE`. Секреты нельзя коммитить и нельзя печатать в логи.

### 4. Проверить окружение

```bash
uv run python -m py_compile bitgn_run/*.py tools/*.py
scripts/check_code_limits.py
```

Минимальный smoke-run без leaderboard:

```bash
uv run python -m bitgn_run.cli run \
  --env pac1 \
  --run-id smoke-pac1-t01 \
  --leaderboard false \
  --fail-fast true \
  --workers 1 \
  --tasks t01 \
  --artifact-dir runs
```

Артефакты пишутся в `runs/`, этот каталог намеренно не коммитится.
