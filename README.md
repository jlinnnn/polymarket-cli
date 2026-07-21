# Polymarket CLI

A fast, read-only terminal interface for [Polymarket](https://polymarket.com) prediction markets — browse markets, inspect events, and run quantitative trade signals against live price history. No API key, account, or wallet required.

Every command renders a clean [rich](https://github.com/Textualize/rich) table in a terminal and **automatically switches to JSON when piped**, so it works equally well as a human tool and as a data source for scripts and agents.

```bash
polymarket dashboard                       # top markets by 24h volume, with price deltas
polymarket recommend -s composite --top 5  # ranked trade signals from an ensemble of strategies
polymarket markets --limit 5 | jq '.[].title'
```

---

## Install

Requires Python 3.11+.

```bash
git clone https://github.com/jlinnnn/polymarket-cli.git
cd polymarket-cli
pip install -e .
polymarket --help
```

---

## Commands

| Command | What it does |
|---------|--------------|
| [`dashboard`](#dashboard) | Top markets by 24h volume, with live price deltas |
| [`markets`](#markets) | List markets sorted by volume |
| [`market <slug>`](#market-slug) | Full detail view for a single event |
| [`search <query>`](#search-query) | Search active markets by title |
| [`recommend`](#recommend) | Quant trade signals (momentum, SMA, mean-reversion, cross-market, composite) |
| [`backtest`](#backtest) | Replay strategies over historical prices and measure hit rate |
| [`whales <slug>`](#whales-slug) | Largest trader positions on an event |
| [`cache`](#cache) | Inspect and clear the local price cache |

Add `--format json` to any command to force JSON output in a terminal; when output is piped, JSON is emitted automatically.

---

### `dashboard`

Top markets by 24-hour volume with a per-outcome price delta (how much each outcome moved in the last day). The number of outcome columns adapts to your terminal width.

```bash
polymarket dashboard
polymarket dashboard --limit 20
polymarket dashboard --no-deltas          # skip the price-history fetch — loads in <1s
polymarket dashboard --sort liquidity
```

| Flag | Default | Description |
|------|---------|-------------|
| `--limit / -n` | `10` | Number of markets |
| `--sort` | `volume_24hr` | `volume_24hr`, `volume`, or `liquidity` |
| `--no-deltas` | off | Skip the CLOB price-history fetch |
| `--format` | `table` | `table` or `json` |

### `markets`

Lists markets sorted by total lifetime volume — good for finding large, established markets.

```bash
polymarket markets --sort volume_24hr --limit 5
polymarket markets --sort end_date --limit 50
```

### `market <slug>`

Full detail for a single event: every market, outcome, price, and 24h delta. The slug is the last segment of the Polymarket URL — `polymarket.com/event/who-wins-the-2028-election` → `who-wins-the-2028-election`.

```bash
polymarket market who-will-trump-nominate-as-fed-chair
polymarket market presidential-election-winner-2028 --no-deltas
```

### `search <query>`

Search active, open markets by title.

```bash
polymarket search "bitcoin"
polymarket search "election" --limit 20
```

### `recommend`

Scans the top markets, scores every outcome with a chosen strategy, and surfaces the strongest trade signals — each with a direction (BUY/SELL), a confidence bar, and a plain-English rationale.

```bash
polymarket recommend                          # composite ensemble, top 3
polymarket recommend -s momentum --top 5      # single strategy
polymarket recommend -s cross-market          # cross-market divergence
polymarket recommend --limit 50               # scan more markets
```

| Flag | Default | Description |
|------|---------|-------------|
| `--strategy / -s` | `composite` | `composite`, `momentum`, `sma`, `mean-reversion`, `cross-market` |
| `--top / -n` | `3` | Number of signals to surface |
| `--limit` | `30` | Markets to scan |

See [Strategies](#strategies) for how each one works.

### `backtest`

Replays the strategies over ~28 days of historical hourly prices and reports how often each signal pointed the right way.

```bash
polymarket backtest                           # all strategies
polymarket backtest -s momentum --horizon 6   # single strategy, 6h lookahead
polymarket backtest --limit 30 --step 3       # more markets, finer granularity
```

| Flag | Default | Description |
|------|---------|-------------|
| `--strategy / -s` | `all` | Strategy to test, or `all` |
| `--horizon / -h` | `12` | Hours ahead to check the outcome |
| `--step` | `6` | Hours between simulated signals |
| `--limit` | `20` | Markets to scan |
| `--runs / -r` | `1` | Runs to average |

### `whales <slug>`

Ranks the largest trader positions on an event by USD volume, using Polymarket's public trade data.

```bash
polymarket whales presidential-election-winner-2028
polymarket whales presidential-election-winner-2028 --limit 10
```

### `cache`

Price history is cached locally (in `~/.polymarket/`) so repeated `recommend`/`backtest` runs are fast.

```bash
polymarket cache stats     # size, point count, date range
polymarket cache clear     # wipe the cache
```

---

## JSON & piping

Every command emits JSON when its output is piped, making it easy to compose with `jq`, shell scripts, or an LLM agent:

```bash
# Titles of the top 5 markets
polymarket markets --limit 5 | jq '.[].title'

# All outcomes for a specific event
polymarket market presidential-election-winner-2028 | jq '.markets[].outcomes'

# Alert on any top market with > $500k of 24h volume
polymarket markets --limit 10 --format json \
  | jq '.[] | select(.volume_24hr > 500000) | .title'
```

---

## Strategies

`recommend` and `backtest` share a pluggable strategy system. Each strategy takes an event, an outcome, and its recent price series, and returns a `TradeSignal` (direction, confidence, score, rationale).

| Strategy | Idea |
|----------|------|
| **Momentum** | Linear-regression slope over the recent window; R² measures how clean the trend is. |
| **SMA** | 6h vs 24h simple-moving-average crossover, with the gap normalized by volatility. |
| **Mean reversion** | Z-score versus a 72h rolling mean; fast moves (likely news) are penalized. |
| **Cross-market** | Detects when the outcome prices of a grouped event (e.g. price brackets) sum away from 1.0, implying a mispricing. |
| **Composite** | A regime-aware ensemble: it detects the current volatility regime, weights the base strategies accordingly, and ranks signals by confidence × how many strategies agree. |

> **Not financial advice.** These are heuristic signals for exploration and learning, not trading recommendations.

---

## Architecture

```
src/polymarket_cli/
├── main.py              # Typer app + command registration
├── models.py            # Event / Market / Outcome dataclasses
├── cache.py             # local SQLite price cache
├── api/
│   ├── gamma.py         # Gamma API — markets, volume, search
│   ├── clob.py          # CLOB API — price history, batched concurrently
│   └── subgraph.py      # trade data for `whales`
├── commands/            # one module per CLI command
├── strategies/          # momentum, sma, mean_reversion, cross_market, regime, composite
└── display/             # rich table builders + number formatters
tests/                   # unit tests (strategies + cache), no network required
```

Two public Polymarket APIs are used, both without authentication:

| API | Base URL | Used for |
|-----|----------|----------|
| Gamma | `gamma-api.polymarket.com` | events, markets, volume, search |
| CLOB | `clob.polymarket.com` | hourly price history for deltas, signals, and backtests |

---

## Development

```bash
pip install -e .          # editable install
pytest tests/             # run the unit tests (no network needed)
```

Strategy tests run against synthetic price series, so the full suite is deterministic and offline.

---

## License

[MIT](LICENSE)
