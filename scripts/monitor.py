#!/usr/bin/env python3
"""
Hyperliquid Perp Monitor - Monitors OI, whale positions, funding, liquidations, volume, volatility
Sends Telegram alerts when thresholds are breached.
"""

import asyncio
import json
import os
import time
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import httpx
from dotenv import load_dotenv

load_dotenv()

# Configuration
API_URL = os.getenv("HYPERLIQUID_API_URL", "https://api.hyperliquid.xyz")
ALERT_CHANNEL = os.getenv("ALERT_CHANNEL", "")

# Thresholds
OI_SPIKE_THRESHOLD = float(os.getenv("OI_SPIKE_THRESHOLD", 10))  # %
WHALE_SIZE_THRESHOLD = float(os.getenv("WHALE_SIZE_THRESHOLD", 100000))  # $
FUNDING_SPIKE_THRESHOLD = float(os.getenv("FUNDING_SPIKE_THRESHOLD", 50))  # %
LIQUIDATION_THRESHOLD = float(os.getenv("LIQUIDATION_THRESHOLD", 50000))  # $
VOLUME_SPIKE_THRESHOLD = float(os.getenv("VOLUME_SPIKE_THRESHOLD", 200))  # %
VOLATILITY_SPIKE_THRESHOLD = float(os.getenv("VOLATILITY_SPIKE_THRESHOLD", 3))  # %

POLL_INTERVAL = 60  # seconds


class HyperliquidMonitor:
    def __init__(self):
        self.client = httpx.AsyncClient(timeout=30.0)
        self.last_oi: Dict[str, float] = {}
        self.last_funding: Dict[str, float] = {}
        self.last_prices: Dict[str, float] = {}
        self.last_hour_volume: Dict[str, float] = {}
        self.last_check: Dict[str, Any] = {}

    async def close(self):
        await self.client.aclose()

    async def get_all_market_stats(self) -> Dict[str, Any]:
        """Fetch all perpetual market statistics using metaAndAssetCtxs."""
        try:
            response = await self.client.post(
                f"{API_URL}/info",
                json={"type": "metaAndAssetCtxs"},
                timeout=30.0
            )
            response.raise_for_status()
            data = response.json()
            # Parse: [meta, assetContexts] where meta has universe list
            if isinstance(data, list) and len(data) >= 2:
                meta, asset_ctxs = data[0], data[1]
                universe = meta.get("universe", [])
                markets = {}
                for i, asset in enumerate(asset_ctxs):
                    coin = universe[i].get("name", f"COIN_{i}") if i < len(universe) else f"COIN_{i}"
                    mark_px = float(asset.get("markPx", 0))
                    oi_raw = float(asset.get("openInterest", 0))
                    markets[coin] = {
                        "openInterest": oi_raw,
                        "openInterestUsd": oi_raw * mark_px,  # USD value
                        "fundingRate": float(asset.get("funding", 0)),
                        "markPx": mark_px,
                        "dayNtlVlm": float(asset.get("dayNtlVlm", 0)),  # Already in USD
                        "prevDayPx": float(asset.get("prevDayPx", 0)),
                    }
                return markets
            return {}
        except Exception as e:
            print(f"Error fetching market stats: {e}")
            return {}

    async def get_funding_history(self, coin: str, horizon: int = 24) -> List[Dict]:
        """Get funding history for a coin."""
        try:
            response = await self.client.post(
                f"{API_URL}/info",
                json={
                    "type": "fundingHistory",
                    "coin": coin,
                    "horizon": horizon
                },
                timeout=30.0
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            return []

    async def get_liquidations(self, coin: Optional[str] = None) -> List[Dict]:
        """Get recent liquidations."""
        try:
            payload: Dict[str, Any] = {"type": "liquidations"}
            if coin:
                payload["coin"] = coin
            response = await self.client.post(
                f"{API_URL}/info",
                json=payload,
                timeout=30.0
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            return []

    async def send_alert(self, message: str):
        """Send Telegram alert via OpenClaw CLI."""
        import subprocess
        timestamp = datetime.now().isoformat()
        full_message = f"[HL Monitor] {timestamp}\n{message}"
        try:
            subprocess.run([
                "openclaw", "message", "send",
                "--channel", "telegram",
                "--message", full_message
            ], capture_output=True, timeout=10)
            print(f"[SENT] {message}")
        except Exception as e:
            print(f"[ALERT] {message}")
            print(f"[ERROR sending via OpenClaw: {e}]")

    def calculate_size_usd(self, position: Dict) -> float:
        """Calculate position size in USD."""
        size = abs(position.get("szi", 0))
        price = position.get("markPx", 0)
        return size * price

    async def check_oi_spikes(self, markets: Dict[str, Any]) -> List[str]:
        """Check for OI spikes > threshold."""
        alerts = []
        for coin, data in markets.items():
            current_oi = data.get("openInterest", 0)
            if coin in self.last_oi:
                change_pct = ((current_oi - self.last_oi[coin]) / self.last_oi[coin]) * 100
                if abs(change_pct) >= OI_SPIKE_THRESHOLD:
                    direction = "↑" if change_pct > 0 else "↓"
                    alerts.append(
                        f"{direction} OI SPIKE: {coin} OI changed {change_pct:.1f}% "
                        f"(now: {current_oi:,.0f})"
                    )
            self.last_oi[coin] = current_oi
        return alerts

    async def check_whale_positions(self, positions: List[Dict]) -> List[str]:
        """Check for large positions > threshold."""
        alerts = []
        for pos in positions:
            size_usd = self.calculate_size_usd(pos)
            if size_usd >= WHALE_SIZE_THRESHOLD:
                coin = pos.get("coin", "UNKNOWN")
                direction = "↑" if pos.get("szi", 0) > 0 else "↓"
                alerts.append(
                    f"🐋 WHALE: {direction} {coin} ${size_usd:,.0f} "
                    f"(entry: {pos.get('entryPx', 'N/A')})"
                )
        return alerts

    async def check_funding_spikes(self, markets: Dict[str, Any]) -> List[str]:
        """Check for funding rate spikes."""
        alerts = []
        for coin, data in markets.items():
            current_funding = data.get("fundingRate", 0)
            if coin in self.last_funding:
                prev = self.last_funding[coin]
                change_pct = ((current_funding - prev) / abs(prev) * 100) if prev != 0 else 0
                if abs(change_pct) >= FUNDING_SPIKE_THRESHOLD:
                    direction = "↑" if change_pct > 0 else "↓"
                    alerts.append(
                        f"📊 FUNDING SPIKE: {coin} funding {direction} {change_pct:.1f}% "
                        f"(now: {current_funding:.6f})"
                    )
            self.last_funding[coin] = current_funding
        return alerts

    async def check_price_volatility(self, markets: Dict[str, Any]) -> List[str]:
        """Check for significant price moves."""
        alerts = []
        for coin, data in markets.items():
            current_price = data.get("markPx", 0)
            if coin in self.last_prices:
                change_pct = ((current_price - self.last_prices[coin]) / self.last_prices[coin]) * 100
                if abs(change_pct) >= VOLATILITY_SPIKE_THRESHOLD:
                    direction = "↑" if change_pct > 0 else "↓"
                    alerts.append(
                        f"📈 VOLATILITY: {coin} {direction} {change_pct:.2f}% in 1min "
                        f"(now: ${current_price:,.2f})"
                    )
            self.last_prices[coin] = current_price
        return alerts

    async def run_once(self) -> List[str]:
        """Run monitoring check once."""
        all_alerts = []

        # Get market data
        markets = await self.get_all_market_stats()
        if not markets:
            return ["Error: Could not fetch market data"]

        # Run all checks
        all_alerts.extend(await self.check_oi_spikes(markets))
        all_alerts.extend(await self.check_funding_spikes(markets))
        all_alerts.extend(await self.check_price_volatility(markets))

        # Check liquidations
        liquidations = await self.get_liquidations()
        for liq in liquidations:
            size_usd = liq.get("size", 0) * liq.get("price", 0)
            if size_usd >= LIQUIDATION_THRESHOLD:
                all_alerts.append(
                    f"💥 LIQUIDATION: {liq.get('coin', 'UNKNOWN')} "
                    f"${size_usd:,.0f} @ ${liq.get('price', 0):,.2f}"
                )

        # Send alerts
        for alert in all_alerts:
            await self.send_alert(alert)

        return all_alerts

    async def run_forever(self):
        """Run monitoring loop indefinitely."""
        print(f"Starting Hyperliquid monitor (poll: {POLL_INTERVAL}s)")
        print(f"Thresholds: OI>{OI_SPIKE_THRESHOLD}%, Whale>${WHALE_SIZE_THRESHOLD/1000:.0f}K, "
              f"Funding>{FUNDING_SPIKE_THRESHOLD}%, Liq>${LIQUIDATION_THRESHOLD/1000:.0f}K")
        while True:
            try:
                alerts = await self.run_once()
                if alerts:
                    print(f"  Generated {len(alerts)} alerts")
                else:
                    print(f"  [{datetime.now().isoformat()}] No alerts")
            except Exception as e:
                print(f"Error in monitoring loop: {e}")
            await asyncio.sleep(POLL_INTERVAL)


async def main():
    monitor = HyperliquidMonitor()
    try:
        await monitor.run_forever()
    finally:
        await monitor.close()


if __name__ == "__main__":
    asyncio.run(main())
