"""Fetch actual ERA5 hourly-derived daily weather for AEP study area, offline training only.
Run: pip install requests pandas; python build_weather_dataset.py
"""
import csv, json, math, time
from pathlib import Path
from collections import Counter
import requests
ROOT=Path(__file__).resolve().parent
API='https://archive-api.open-meteo.com/v1/archive'
VARIABLES='wind_gusts_10m_max,precipitation_sum,temperature_2m_min,snowfall_sum'
# Fixed point representative of supplied AEP Vinton customer, NOT precise weather at every damage report
POINTS={'vinton_customer':(37.288572519,-79.736609841), 'west_area':(37.25,-80.12),'north_area':(37.42,-79.85),'south_area':(37.08,-79.88)}

def fetch(lat,lon):
    params={'latitude':lat,'longitude':lon,'start_date':'2022-01-01','end_date':'2026-08-31','daily':VARIABLES,'temperature_unit':'fahrenheit','wind_speed_unit':'mph','precipitation_unit':'inch','timezone':'America/New_York','models':'era5'}
    for i in range(3):
        try:
            r=requests.get(API,params=params,timeout=90);r.raise_for_status();data=r.json()
            if 'daily' not in data: raise ValueError(str(data)[:200])
            return data,r.url
        except Exception:
            if i==2:raise
            time.sleep(2*(i+1))

def main():
    output=[];sources=[]
    for label,(lat,lon) in POINTS.items():
        obj,url=fetch(lat,lon);sources.append({'location':label,'source_url':url,'model':'ERA5','timezone':'America/New_York','coordinates_requested':[lat,lon],'coordinates_returned':[obj.get('latitude'),obj.get('longitude')],'daily_units':obj.get('daily_units')})
        d=obj['daily']
        for j,day in enumerate(d['time']):
            output.append({'location':label,'date':day,'wind_gust_mph':d['wind_gusts_10m_max'][j],'precip_in':d['precipitation_sum'][j],'min_temp_f':d['temperature_2m_min'][j],'snowfall_cm':d['snowfall_sum'][j]})
    with (ROOT/'historical_weather_era5.csv').open('w',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=list(output[0]));writer.writeheader();writer.writerows(output)
    (ROOT/'weather_sources.json').write_text(json.dumps(sources,indent=2))
    # Merge on REPORT date, NOT proven date that storm damage occurred
    byday={(r['location'],r['date']):r for r in output}
    with (ROOT/'aep_arcos_damage_events.csv').open(newline='') as f:damage=list(csv.DictReader(f))
    matched=[]
    for d in damage:
        la=float(d['latitude']);lo=float(d['longitude'])
        label=min(POINTS,key=lambda k:(POINTS[k][0]-la)**2+((POINTS[k][1]-lo)*math.cos(math.radians(la)))**2)
        w=byday.get((label,d['report_date']))
        if w:matched.append({**d, 'weather_grid_point':label,'wind_gust_mph':w['wind_gust_mph'],'precip_in':w['precip_in'],'min_temp_f':w['min_temp_f'],'snowfall_cm':w['snowfall_cm']})
    if matched:
        with (ROOT/'arcos_weather_join.csv').open('w',newline='') as f:
            writer=csv.DictWriter(f,fieldnames=list(matched[0]));writer.writeheader();writer.writerows(matched)
    print('Downloaded',len(output),'ERA5 daily observations across',len(POINTS),'weather points')
    print('Joined',len(matched),'of',len(damage),'ARCOS records to reporting-date weather')
    print('Weather units: mph, inches (water equivalent), F, centimeters (snowfall)')
    print('IMPORTANT: raw join is exploratory; sampled ARCOS records do NOT establish no-damage outcomes or outage probabilities.')
if __name__=='__main__':main()
