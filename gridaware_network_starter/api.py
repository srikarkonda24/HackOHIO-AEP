"""Simple read-only network impact API. pip install fastapi uvicorn"""
import os
import sqlite3
from env_loader import load_gridaware_env
from fastapi import FastAPI, HTTPException, Query

load_gridaware_env()
from gis_api import GIS_DB, router as gis_router
from scenario_api import configure as configure_scenario_router
from network_context_api import configure as configure_network_context_router
from risk_assessment_api import configure as configure_risk_router
from restoration_api import router as restoration_router
from assistant_api import configure as configure_assistant_router
from alerts_api import configure as configure_alerts_router

DB=os.getenv('NETWORK_DB','network.db')
app=FastAPI(title='GridAware Network Impact API')
app.include_router(gis_router)
app.include_router(configure_scenario_router(DB))
app.include_router(configure_network_context_router(DB))
app.include_router(configure_risk_router(DB))
app.include_router(restoration_router)
app.include_router(configure_assistant_router(DB))
app.include_router(configure_alerts_router(DB))

def connect():
    con=sqlite3.connect(DB)
    con.row_factory=sqlite3.Row
    return con

@app.get('/health')
def health():
    with connect() as con:
        payload={'status':'ok','premises':con.execute('SELECT COUNT(*) FROM premises').fetchone()[0]}
    payload['gis_db']=GIS_DB.exists()
    return payload

@app.get('/devices/search')
def devices_search(q: str = Query(..., min_length=2), limit: int=20):
    with connect() as con:
        rows=con.execute('''SELECT d.device_key,d.device_type,d.location_id, COUNT(dp.premise_id) AS dependent_premises
            FROM devices d LEFT JOIN dependencies dp ON d.device_key=dp.device_key
            WHERE d.device_key LIKE ? OR d.location_id LIKE ?
            GROUP BY d.device_key LIMIT ?''',(f'%{q}%',f'%{q}%',min(limit,100))).fetchall()
        return {'devices':[dict(r) for r in rows]}

@app.get('/devices/impact')
def device_impact(device_key: str, limit: int=1000):
    with connect() as con:
        device=con.execute('SELECT * FROM devices WHERE device_key=?',(device_key,)).fetchone()
        if not device:raise HTTPException(status_code=404,detail='Device not found')
        count=con.execute('SELECT COUNT(*) FROM dependencies WHERE device_key=?',(device_key,)).fetchone()[0]
        customers=con.execute('''SELECT p.premise_id,p.longitude,p.latitude,p.circuit_id
            FROM dependencies dp JOIN premises p ON p.premise_id=dp.premise_id
            WHERE dp.device_key=? LIMIT ?''',(device_key,min(limit,5000))).fetchall()
        return {'device':dict(device),'potentially_dependent_premises':count,
                'returned_customer_points':len(customers), 'customers':[dict(r) for r in customers],
                'note':'Dependency paths only; not a verified outage or safe switching analysis.'}

@app.get('/premises/{premise_id}/upstream')
def premise_upstream(premise_id:str):
    with connect() as con:
        premise=con.execute('SELECT * FROM premises WHERE premise_id=?',(premise_id,)).fetchone()
        if not premise:raise HTTPException(status_code=404,detail='Premise not found')
        upstream=con.execute('''SELECT d.* FROM devices d JOIN dependencies dp ON d.device_key=dp.device_key
            WHERE dp.premise_id=?''',(premise_id,)).fetchall()
        return {'premise':dict(premise),'upstream':[dict(r) for r in upstream]}
