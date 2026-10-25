"""Build a queryable network-impact SQLite database from AEP topology and customer GIS."""
import argparse
import sqlite3
from pathlib import Path
from collections import defaultdict
import shapefile


def create_database(upstream, customer_shp, output):
    output.parent.mkdir(parents=True, exist_ok=True)
    if output.exists(): output.unlink()
    con = sqlite3.connect(output)
    con.executescript('''
    PRAGMA journal_mode=OFF;
    PRAGMA synchronous=OFF;
    CREATE TABLE premises (premise_id TEXT PRIMARY KEY, longitude REAL, latitude REAL, circuit_id TEXT);
    CREATE TABLE devices (device_key TEXT PRIMARY KEY, device_type TEXT, location_id TEXT, source_type TEXT, source_id TEXT);
    CREATE TABLE dependencies (device_key TEXT NOT NULL, premise_id TEXT NOT NULL, PRIMARY KEY(device_key,premise_id));
    CREATE INDEX idx_dependency_premise ON dependencies(premise_id);
    CREATE INDEX idx_device_location ON devices(location_id);
    ''')
    r = shapefile.Reader(str(customer_shp))
    names=[f[0] for f in r.fields[1:]]
    prem_idx=names.index('premise_nu')
    circuit_idx=names.index('circuit_id')
    records=[]
    for sr in r.iterShapeRecords():
        vals=sr.record
        coord=sr.shape.points[0] if sr.shape.points else (None,None)
        records.append((str(vals[prem_idx]).strip(), coord[0],coord[1],str(vals[circuit_idx]).strip()))
    con.executemany('INSERT OR IGNORE INTO premises VALUES (?,?,?,?)',records)
    con.commit()
    devices={}
    batch=[]
    with upstream.open('r',encoding='utf-8-sig',errors='replace') as f:
        for line in f:
            parts=line.rstrip('\r\n').split('\t')
            premise=parts[0].strip()
            if not premise:continue
            seen=set()
            for token in parts[1:]:
                bits=token.split('*',3)
                if len(bits)!=4: continue
                source_type,source_id,device_type,loc=bits
                key=f'{source_type}*{source_id}'
                if key in seen:continue
                seen.add(key)
                devices[key]=(key,device_type,loc,source_type,source_id)
                batch.append((key,premise))
            if len(batch)>=100_000:
                con.executemany('INSERT OR IGNORE INTO dependencies VALUES (?,?)',batch)
                batch=[]
        if batch: con.executemany('INSERT OR IGNORE INTO dependencies VALUES (?,?)',batch)
    con.executemany('INSERT INTO devices VALUES (?,?,?,?,?)',devices.values())
    con.execute('CREATE INDEX idx_dependency_device ON dependencies(device_key)')
    con.commit()
    print('Premises:',con.execute('SELECT COUNT(*) FROM premises').fetchone()[0])
    print('Indexed devices:',con.execute('SELECT COUNT(*) FROM devices').fetchone()[0])
    print('Dependencies:',con.execute('SELECT COUNT(*) FROM dependencies').fetchone()[0])
    print('Top devices by dependent premises:')
    for x in con.execute('''SELECT d.device_key,d.device_type,COUNT(*) count FROM devices d JOIN dependencies dp USING(device_key) GROUP BY d.device_key ORDER BY count DESC LIMIT 5'''):
        print(x)
    con.close()

if __name__=='__main__':
    p=argparse.ArgumentParser()
    p.add_argument('--upstream',type=Path,required=True)
    p.add_argument('--customers',type=Path,required=True)
    p.add_argument('--out',type=Path,default=Path('network.db'))
    a=p.parse_args()
    create_database(a.upstream,a.customers,a.out)
