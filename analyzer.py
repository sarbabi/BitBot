import json
import pandas as pd

records = []
with open('log.txt', 'r') as f:
    for l in f.readlines():
        record = json.loads(l)
        if not record['action'] == 'sentOrder':
            records.append(record)

df = pd.DataFrame(records)
df.to_csv('log.csv')