#!/bin/env/python

import csv

import psycopg2


def int_or_none(string):
    try:
        return int(string)
    except ValueError:
        return None


def fix_text_note(text):
    if not text:
        return ""
    else:
        return """* CHS "Chicago Streets" Document:\n> «{}»""".format(text)


if __name__ == "__main__":
    db = psycopg2.connect("postgresql://hello_flask:hello_flask@db:5432/chicagodir_dev")

    cur = db.cursor()
    id_map = {}

    street_n = 1
    with open("current_street_update.csv", "r") as f:
        reader = csv.DictReader(f)

        for row in reader:
            row["Suffix_Direction"] = row["Suffix Direction"] or None
            row["min_address"] = int_or_none(row["Min Address"])
            row["max_address"] = int_or_none(row["Max Address"])
            row["grid_location"] = int_or_none(row["grid_location"])
            row["id"] = street_n
            row["text"] = fix_text_note(row["text"])
            # print(row)
            cur.execute(
                """INSERT INTO streets (id, street_id, direction, name, suffix, suffix_direction, 
                            current, historical_note, text, grid_location, grid_direction, min_address, 
                            max_address) VALUES (%(id)s, %(entry_uid)s, %(Direction)s, 
                            %(Street)s, %(Suffix)s, 
                            %(Suffix_Direction)s, True, %(Note)s, %(text)s, %(grid_location)s, 
                            %(grid_direction)s, %(min_address)s, %(max_address)s)
            """,
                row,
            )
            if row["text"]:
                cur.execute(
                    """INSERT INTO streets_edits (street_id, user_id, note) VALUES 
                    (%(id)s, 1, 'imported from city data portal and CHS "Street Names" document');""",
                    row,
                )
            else:
                cur.execute(
                    """INSERT INTO streets_edits (street_id, user_id, note) VALUES
                     (%(id)s, 1, 'imported from city data portal and CHS "Street Names" document');""",
                    row,
                )

            id_map[row["entry_uid"]] = street_n
            street_n += 1

    with open("chs_withdrawn_streets.csv", "r") as f:
        reader = csv.DictReader(f)

        for row in reader:
            row["Suffix_Direction"] = row["Suffix Direction"]
            row["min_address"] = int_or_none(row["Min Address"])
            row["max_address"] = int_or_none(row["Max Address"])
            row["grid_location"] = int_or_none(row["grid_location"])
            row["Suffix"] = row["Suffix"][:15]  # if this is bad, cut it off
            row["text"] = fix_text_note(row["text"])

            row["id"] = street_n
            # print(row)
            cur.execute(
                """INSERT INTO streets (id, street_id, direction, name, suffix, suffix_direction, 
                            current, historical_note, text, grid_location, grid_direction) 
                            VALUES (%(id)s, %(entry_uid)s, %(Direction)s, %(Street)s, %(Suffix)s, 
                            %(Suffix_Direction)s, False, %(Note)s, %(text)s, %(grid_location)s, %(grid_direction)s)
            """,
                row,
            )
            cur.execute(
                """INSERT INTO streets_edits (street_id, user_id, note) 
                VALUES (%(id)s, 1, 'imported from CHS "Street Names" document');""",
                row,
            )
            id_map[row["entry_uid"]] = street_n
            street_n += 1

    cur.execute(
        """select setval('public."streets_id_seq"', (SELECT MAX(id) from streets));"""
    )

    with open("chs_withdrawn_xrefs.csv", "r") as f:
        reader = csv.reader(f)
        map_id = 1
        for row in reader:
            entry_id = id_map[row[0]]
            for mapping in row[1:]:
                d = {"entry_id": entry_id, "to_id": id_map[mapping]}
                cur.execute(
                    """INSERT INTO streetchange (type, note, from_id, to_id) 
                    VALUES ('REPLACE', 'from CHS listing', %(entry_id)s, %(to_id)s);""",
                    d,
                )
                map_id += 1

    cur.execute(
        """select setval('public."streetchange_id_seq"', (SELECT MAX(id) from streetchange));"""
    )
    db.commit()
