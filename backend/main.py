from fastapi import FastAPI, Depends, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from typing import List
import csv
from io import StringIO
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
import asyncio
import os
import datetime

import database
from scanner import ScannerListener
from pydantic import BaseModel

app = FastAPI(title="Enhanced Scanning Console", description="ESC Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

database.init_db()

class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        for connection in list(self.active_connections):
            try:
                await connection.send_json(message)
            except Exception:
                self.active_connections.remove(connection)

manager = ConnectionManager()

async def process_scan(barcode: str):
    db: Session = next(database.get_db())
    try:
        # Check if barcode already exists
        existing_scan = db.query(database.ScanEvent).filter(database.ScanEvent.barcode_data == barcode).first()
        
        if existing_scan:
            existing_scan.count += 1
            existing_scan.timestamp = datetime.datetime.utcnow()
            db.commit()
            db.refresh(existing_scan)
            scan_obj = existing_scan
        else:
            new_scan = database.ScanEvent(barcode_data=barcode, count=1)
            db.add(new_scan)
            db.commit()
            db.refresh(new_scan)
            scan_obj = new_scan
        
        await manager.broadcast({
            "type": "new_scan",
            "scan": {
                "id": scan_obj.id,
                "barcode_data": scan_obj.barcode_data,
                "count": scan_obj.count,
                "timestamp": scan_obj.timestamp.isoformat()
            }
        })
    finally:
        db.close()

scanner_listener = ScannerListener(callback=process_scan, device_name_substr="Zebra")

@app.on_event("startup")
async def startup_event():
    asyncio.create_task(scanner_listener.run())

@app.get("/api/scans")
def get_scans(db: Session = Depends(database.get_db)):
    scans = db.query(database.ScanEvent).order_by(database.ScanEvent.timestamp.desc()).all()
    return [
        {
            "id": s.id,
            "barcode_data": s.barcode_data,
            "count": getattr(s, 'count', 1),
            "timestamp": s.timestamp.isoformat()
        }
        for s in scans
    ]

class ScanRequest(BaseModel):
    barcode_data: str

@app.post("/api/scans")
async def create_scan(scan: ScanRequest):
    # Process it identically to how the hardware scanner would. 
    # process_scan connects to db, saves, and broadcasts to ALL websockets.
    await process_scan(scan.barcode_data)
    return {"status": "success"}

@app.delete("/api/scans/{scan_id}")
async def delete_scan(scan_id: int, db: Session = Depends(database.get_db)):
    scan = db.query(database.ScanEvent).filter(database.ScanEvent.id == scan_id).first()
    if not scan:
        raise HTTPException(status_code=404, detail="Scan not found")
    
    db.delete(scan)
    db.commit()
    
    await manager.broadcast({"type": "delete_scan", "id": scan_id})
    return {"status": "deleted"}

@app.delete("/api/scans")
async def delete_all_scans(db: Session = Depends(database.get_db)):
    db.query(database.ScanEvent).delete()
    db.commit()
    
    await manager.broadcast({"type": "clear_all"})
    return {"status": "all deleted"}

@app.get("/api/export")
def export_scans_csv(db: Session = Depends(database.get_db)):
    scans = db.query(database.ScanEvent).order_by(database.ScanEvent.timestamp.desc()).all()
    
    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(["ID", "Barcode Data", "Count", "Last Scanned Timestamp"])
    for s in scans:
        writer.writerow([s.id, s.barcode_data, getattr(s, 'count', 1), s.timestamp.isoformat()])
        
    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=scans_export.csv"}
    )

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)

# --- Serve SPA (React Build) ---
frontend_path = os.path.join(os.path.dirname(__file__), "static")
if os.path.exists(frontend_path):
    app.mount("/", StaticFiles(directory=frontend_path, html=True), name="spa")

