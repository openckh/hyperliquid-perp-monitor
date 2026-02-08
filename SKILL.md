---
name: hyperliquid-perp-monitor
description: Monitor Hyperliquid perpetual futures for OI spikes, whale positions, funding rate spikes, large liquidations, and volume anomalies. Triggers proactive Telegram alerts when thresholds are breached.
---

# Hyperliquid Perp Monitor

Monitors Hyperliquid perpetual futures exchange and sends Telegram alerts when significant market events occur.

## Alert Thresholds

Configure these thresholds in the skill environment:

- **OI_SPIKE_THRESHOLD**: OI change >10% on exchange (default: 10)
- **WHALE_SIZE_THRESHOLD**: Position size >$100K (default: 100000)
- **FUNDING_SPIKE_THRESHOLD**: Funding rate change >50% (default: 50)
- **LIQUIDATION_THRESHOLD**: Single liquidation >$50K (default: 50000)
- **VOLUME_SPIKE_THRESHOLD**: Volume increase >200% vs 1h average (default: 200)
- **VOLATILITY_SPIKE_THRESHOLD**: Price move >3% in 1 min (default: 3)

## Polling

Polls Hyperliquid API every 60 seconds.

## Triggers

Alerts are sent to Telegram when:
1. Open Interest increases or decreases by >10%
2. Any position >$100K opens or changes significantly
3. Funding rate spikes >50%
4. Single liquidation >$50K occurs
5. Volume spikes >200% vs hourly average
6. Price moves >3% in 1 minute

## Configuration

Set these environment variables:
- `HYPERLIQUID_API_URL`: Hyperliquid API endpoint (default: https://api.hyperliquid.xyz)
- `ALERT_CHANNEL`: Telegram channel or user ID for alerts

## Usage

### Run as OpenClaw Agent
The skill can be invoked by OpenClaw's cron system for automated monitoring:

```bash
# Set up cron job for 1-minute polling
openclaw cron add --name "hyperliquid-monitor" \
  --schedule '{"kind": "every", "everyMs": 60000}' \
  --payload '{"kind": "systemEvent", "text": "Run hyperliquid perp monitor check"}' \
  --sessionTarget "main"
```

### Run Standalone
```bash
cd skills/hyperliquid-perp-monitor
python3 scripts/monitor.py
```

### Environment Variables
Configure via `.env` or environment:
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

## Integration

- Uses OpenClaw's `message send` CLI for Telegram delivery
- Follows HEARTBEAT.md alert patterns
- Can be triggered via OpenClaw cron or run as background process

## Reference

See [API.md](references/API.md) for Hyperliquid API documentation patterns.
