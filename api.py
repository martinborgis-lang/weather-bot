import sys
import io

# Force UTF-8 sur Windows pour éviter les UnicodeEncodeError cp1252
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace', line_buffering=True)
    # sys.stderr non wrappé : conflit avec argparse / logging stderr handlers
    # Les émojis dans stderr peuvent être moches mais le script fonctionne

from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
import json
import asyncio
import os
from pathlib import Path
from datetime import datetime
from config import Config

app = FastAPI(title="Weather Bot API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

DATA_DIR = Path(Config.DATA_DIR)
LOGS_PATH = Path("logs/bot.log")
BOT_STATUS_FILE = DATA_DIR / "bot_status.json"
PAUSE_FILE = DATA_DIR / ".pause"
FORCE_CYCLE_FILE = DATA_DIR / ".force_cycle"


def read_json(filename):
    f = DATA_DIR / filename
    if f.exists():
        try:
            return json.loads(f.read_text())
        except:
            return []
    return []


@app.get("/")
def root():
    return {"status": "Weather Bot API running"}


@app.get("/health")
def health():
    return {"status": "ok", "data_dir": str(DATA_DIR)}


@app.get("/positions")
def positions():
    return read_json("positions.json")


@app.get("/signals")
def signals():
    data = read_json("signals.json")
    return data[-200:]  # 200 derniers


@app.get("/trades")
def trades():
    data = read_json("trade_history.json")
    return data[-200:]


@app.get("/positions-detailed")
def positions_detailed():
    positions = read_json("positions.json")
    now = datetime.utcnow()

    enriched = []
    for p in positions:
        item = dict(p) if isinstance(p, dict) else p.__dict__

        resolution = item.get('resolution_datetime')
        if resolution:
            try:
                if isinstance(resolution, str):
                    res_dt = datetime.fromisoformat(resolution.replace('Z', '+00:00'))
                else:
                    res_dt = resolution

                delta = res_dt - now
                seconds = delta.total_seconds()

                if seconds > 0:
                    hours = int(seconds / 3600)
                    minutes = int((seconds % 3600) / 60)
                    item['time_to_resolution'] = f"{hours}h{minutes:02d}"
                    item['resolution_status'] = 'pending'
                else:
                    item['time_to_resolution'] = 'expired'
                    item['resolution_status'] = 'resolved'
            except Exception:
                item['time_to_resolution'] = 'unknown'
                item['resolution_status'] = 'unknown'
        else:
            item['time_to_resolution'] = 'unknown'
            item['resolution_status'] = 'unknown'

        enriched.append(item)

    # Trier par heure de résolution (les plus proches en premier)
    enriched.sort(
        key=lambda x: x.get('resolution_datetime', '9999-99-99'),
        reverse=False
    )

    return enriched


@app.get("/stats")
def stats():
    trades = read_json("trade_history.json")
    positions = read_json("positions.json")

    exposure = sum(
        p.get('size_usdc', 0) if isinstance(p, dict) else getattr(p, 'size_usdc', 0)
        for p in positions
    )

    return {
        "total_trades": len(trades),
        "open_positions": len(positions),
        "total_exposure": round(exposure, 2),
        "bankroll": Config.BANKROLL_USDC,
        "dry_run": Config.DRY_RUN,
    }


@app.get("/api/bot/status")
def bot_status():
    """Retourne le statut live du bot lu depuis data/bot_status.json"""
    try:
        if BOT_STATUS_FILE.exists():
            with open(BOT_STATUS_FILE) as f:
                status = json.load(f)
            # Ajoute des infos calculées
            status["paused"] = PAUSE_FILE.exists()
            return status
        return {
            "running": False,
            "last_cycle_at": None,
            "uptime_seconds": 0,
            "next_scan_at": None,
            "dry_run": Config.DRY_RUN,
            "errors_24h": 0,
            "paused": PAUSE_FILE.exists(),
            "bankroll_usdc": Config.BANKROLL_USDC,
            "max_position_usdc": Config.MAX_POSITION_USDC,
            "edge_minimum": Config.EDGE_MINIMUM,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/markets")
def get_markets():
    """Retourne les marchés scannés actuellement"""
    try:
        markets_file = DATA_DIR / "current_markets.json"
        if markets_file.exists():
            with open(markets_file) as f:
                return json.load(f)
        return []
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/forecasts")
def get_forecasts():
    """Retourne les prévisions météo actives"""
    try:
        forecasts_file = DATA_DIR / "forecast_log.json"
        if forecasts_file.exists():
            with open(forecasts_file) as f:
                return json.load(f)
        return []
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/bot/pause")
def pause_bot():
    """Met le bot en pause (il skip les cycles tant que le fichier existe)"""
    PAUSE_FILE.touch()
    return {"status": "paused", "timestamp": datetime.now().isoformat()}


@app.post("/api/bot/resume")
def resume_bot():
    """Retire la pause"""
    if PAUSE_FILE.exists():
        PAUSE_FILE.unlink()
    return {"status": "resumed", "timestamp": datetime.now().isoformat()}


@app.post("/api/bot/force-cycle")
def force_cycle():
    """Force un nouveau cycle immédiatement"""
    FORCE_CYCLE_FILE.touch()
    return {"status": "cycle forced", "timestamp": datetime.now().isoformat()}


@app.get("/api/logs/stream")
async def stream_logs():
    """SSE stream des logs bot.log en temps réel (tail -f)"""
    async def log_generator():
        if not LOGS_PATH.exists():
            yield f"data: {json.dumps({'error': 'log file not found'})}\n\n"
            return

        with open(LOGS_PATH, "r", encoding='utf-8') as f:
            # Skip to end for tail -f behavior
            f.seek(0, 2)
            while True:
                line = f.readline()
                if line:
                    yield f"data: {json.dumps({'line': line.strip(), 'ts': datetime.now().isoformat()})}\n\n"
                else:
                    await asyncio.sleep(0.5)

    return StreamingResponse(log_generator(), media_type="text/event-stream")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)