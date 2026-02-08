# Hyperliquid Perpetual Futures Monitor

OpenClaw skill for monitoring Hyperliquid perpetual futures with Telegram alerts.

## Features

Monitor the following events on Hyperliquid exchange:
- **Open Interest (OI) Spikes** - Alerts when OI changes >10%
- **Whale Positions** - Alerts for positions >$100K
- **Funding Rate Spikes** - Alerts when funding rate changes >50%
- **Large Liquidations** - Alerts for liquidations >$50K
- **Volume Anomalies** - Alerts for volume spikes >200% vs 1h average
- **Price Volatility** - Alerts for price moves >3% in 1 minute

## Installation

```bash
cd skills/hyperliquid-perp-monitor
```

## Configuration

Set environment variables:
```
HYPERLIQUID_API_URL=https://api.hyperliquid.xyz
ALERT_CHANNEL=telegram
OI_SPIKE_THRESHOLD=10
WHALE_SIZE_THRESHOLD=100000
FUNDING_SPIKE_THRESHOLD=50
LIQUIDATION_THRESHOLD=50000
VOLUME_SPIKE_THRESHOLD=200
VOLATILITY_SPIKE_THRESHOLD=3
```

## Usage

### Run Standalone
```bash
python3 scripts/monitor.py
```

### Run with OpenClaw Cron
```bash
openclaw cron add --name "hyperliquid-monitor" \
  --schedule '{"kind": "every", "everyMs": 60000}' \
  --payload '{"kind": "systemEvent", "text": "Run hyperliquid perp monitor check"}' \
  --sessionTarget "main"
```

## Files

- `SKILL.md` - OpenClaw skill documentation
- `scripts/monitor.py` - Main monitoring script

## License

MIT
