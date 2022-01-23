#!/bin/env/python

import sqlite3
import csv


db = sqlite3.connect("dev.db")

cur = db.cursor()
id_map = {}

street_n = 1
with open("current_street_update.csv","r") as f:
    reader = csv.DictReader(f)

    for row in reader:
        row['Suffix_Direction'] = row['Suffix Direction']
        row['min_address'] = row['Min Address']
        row['max_address'] = row['Max Address']
        row['id'] = street_n
        #print(row)
        cur.execute("""INSERT INTO streets (id, street_id, direction, name, suffix, suffix_direction, 
                        current, historical_note, text, grid_location, grid_direction, min_address, max_address) VALUES (:id, :entry_uid, :Direction, :Street, :Suffix, 
                        :Suffix_Direction, True, :Note, :text, :grid_location, :grid_direction, :min_address, :max_address)
        """, row)
        id_map[row['entry_uid']] = street_n
        street_n += 1

with open("chs_withdrawn_streets.csv",'r') as f:
    reader = csv.DictReader(f)

    for row in reader:
        row['Suffix_Direction'] = row['Suffix Direction']
        row['id'] = street_n
        #print(row)
        cur.execute("""INSERT INTO streets (id, street_id, direction, name, suffix, suffix_direction, 
                        current, historical_note, text, grid_location, grid_direction) VALUES (:id, :entry_uid, :Direction, :Street, :Suffix, 
                        :Suffix_Direction, False, :Note, :text, :grid_location, :grid_direction)
        """, row)
        id_map[row['entry_uid']] = street_n
        street_n += 1


with open("chs_withdrawn_xrefs.csv","r") as f:
    reader = csv.reader(f)
    map_id = 1
    for row in reader:
        entry_id = id_map[row[0]]
        for mapping in row[1:]:
            d = {"id": map_id, "entry_id":entry_id, "to_id":id_map[mapping]}
            cur.execute("""INSERT INTO streetchange (id, type, note, from_id, to_id) VALUES (:id, "REPLACE", "from CHS listing", :entry_id, :to_id);""", d)
            map_id += 1

db.commit()