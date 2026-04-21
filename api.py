from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import json
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


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)