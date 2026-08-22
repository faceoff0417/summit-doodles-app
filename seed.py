"""Seeds the database with Summit Doodles' real dogs/litters (pulled from
summitdoodles.com) plus a handful of illustrative sample applications,
a contact message, and one active reservation so the app has something
to look at on first run. Run with: python3 seed.py
"""
import datetime
from db import init_db, get_db, new_token

DOGS = [
    dict(name="Apollo", sex="Male", role="Stud", breed="Australian Bernedoodle",
         color="Tricolor Merle", coat="Fully Furnished, Straight", dob="2024-07-04",
         weight_lbs=35, sire_name="Honeybee Lane Mr. Steal Your Girl Bentley", dam_name="Shady Oak Apple",
         coi_percent=4.1, bio="A free spirit filled with love, joy, and excitement for life.",
         hips="Good", elbows="Normal", eic="Carrier", dm="Clear", vwd="Clear", pra="Clear"),
    dict(name="Luca", sex="Male", role="Stud", breed="Australian Bernedoodle",
         color="Red & White Tuxedo", coat="Fully Furnished, Straight", dob="2024-02-03",
         weight_lbs=35, sire_name="Doodles of Oz Australian Gentleman Humphrey", dam_name="Shady Oak Apple",
         coi_percent=3.2, bio="A happy-go-lucky guy that loves everyone.",
         hips="Good", elbows="Normal", eic="Clear", dm="Clear", vwd="Clear", pra="Clear"),
    dict(name="Foxtrot", sex="Female", role="Dam", breed="Multigenerational Bernedoodle",
         color="Red & White Tuxedo", coat="Fully Furnished, Wavy", dob="2023-02-17",
         weight_lbs=35, coi_percent=2.8,
         bio="Quiet-natured and gentle; produces our service-dog lines.",
         hips="Good", elbows="Normal", eic="Clear", dm="Clear", vwd="Clear", pra="Clear"),
    dict(name="London", sex="Female", role="Dam", breed="Cockapoo (Mini)",
         color="Chocolate Merle Roan", coat="Fully Furnished, Wavy", dob="2024-08-17",
         weight_lbs=20, coi_percent=3.9,
         bio="The sweetest soul, loves everyone -- an exceptional mother.",
         hips="Good", elbows="Normal", eic="Clear", dm="Clear", vwd="Clear", pra="Clear"),
    dict(name="Trixxi", sex="Female", role="Dam", breed="Australian Bernedoodle",
         color="Tricolor", coat="Fully Furnished, Straight", dob="2024-07-04",
         weight_lbs=35, sire_name="Honeybee Lane Mr. Steal Your Girl Bentley", dam_name="Shady Oak Apple",
         coi_percent=4.1, bio="An intelligent free spirit who loves water and snow.",
         hips="Good", elbows="Normal", eic="Carrier", dm="Clear", vwd="Clear", pra="Clear"),
    dict(name="Sunshine", sex="Female", role="Dam", breed="Australian Bernedoodle",
         color="Red & White Tuxedo Roan", coat="Fully Furnished, Straight", dob="2025-03-03",
         weight_lbs=35, coi_percent=3.4,
         bio="An incredible girl filled with brains and beauty; completed advanced training.",
         hips="Good", elbows="Normal", eic="Clear", dm="Clear", vwd="Clear", pra="Clear"),
    dict(name="Roxy", sex="Female", role="Dam", breed="Australian Bernedoodle",
         color="Red & White Tuxedo", coat="Fully Furnished, Straight", dob="2024-08-17",
         weight_lbs=30, sire_name='ASD Companion Weasley "Echo"', dam_name="Summit Doodles Charlie",
         bio="A sweet and gentle girl who has completed training.",
         hips="Pending", elbows="Pending", eic="Clear", dm="Clear", vwd="Clear", pra="Clear"),
    dict(name="Juliet", sex="Female", role="Dam", breed="Cockapoo (Micro)",
         color="Chocolate Tricolor Merle", coat="Fully Furnished, Wavy", dob="2024-11-01",
         weight_lbs=15, coi_percent=2.1,
         bio="A beautiful ball of joy and highly intelligent.",
         hips="Excellent", elbows="Normal", eic="Clear", dm="Clear", vwd="Clear", pra="Clear"),
    dict(name="Willow", sex="Female", role="Guardian Home", breed="Australian Bernedoodle",
         color="Red & White Tuxedo", coat="Fully Furnished, Wavy", dob="2023-07-18",
         weight_lbs=30, sire_name="Fairytale Lane Mickey Mouse", dam_name="Summit Doodles Whiskey",
         coi_percent=3.6, bio="With the Bennett Family since September 2023.",
         hips="Good", elbows="Normal", eic="Clear", dm="Carrier", vwd="Clear", pra="Clear",
         guardian_family="Bennett Family"),
]

LITTERS = [
    dict(litter_name="Zulu x Yankee", dam_name_text="Zulu", sire_name_text="Yankee",
         breed="Australian Labradoodle", status="Reserving",
         bred_date="2026-04-25", dob="2026-06-30", go_home_date="2026-08-25", waitlist_count=2,
         puppies=[
             dict(name="Ouray", sex="Male", color="Chocolate Roan", birth_weight_oz=14, current_weight_lbs=4.8, status="Available", price=2800),
             dict(name="Gunner", sex="Male", color="Tricolor Roan", birth_weight_oz=15, current_weight_lbs=5.1, status="Available", price=2800),
             dict(name="Boulder", sex="Male", color="Chocolate", birth_weight_oz=15, current_weight_lbs=5.4, status="Available", price=2800),
             dict(name="Aspen", sex="Female", color="Red & White Tuxedo", birth_weight_oz=13, current_weight_lbs=4.6, status="Available", price=3200),
             dict(name="Telluride", sex="Female", color="Chocolate Tricolor", birth_weight_oz=14, current_weight_lbs=4.9, status="On Hold", price=3200),
             dict(name="Durango", sex="Male", color="Chocolate Roan", birth_weight_oz=15, current_weight_lbs=5.3, status="On Hold", price=2800),
             dict(name="Breck", sex="Female", color="Tricolor Roan", birth_weight_oz=13, current_weight_lbs=4.7, status="Reserved", price=3200),
             dict(name="Monty", sex="Male", color="Red & White", birth_weight_oz=14, current_weight_lbs=5.0, status="Reserved", price=2800),
         ]),
    dict(litter_name="London x Yankee", dam_name="London", sire_name_text="Yankee",
         breed="Infusion Australian Labradoodle", status="Whelped",
         bred_date="2026-05-20", dob="2026-07-25", go_home_date="2026-09-19", waitlist_count=1,
         puppies=[
             dict(name="Sundance", sex="Male", color="Chocolate Merle", birth_weight_oz=8, current_weight_lbs=2.2, status="Available", price=2600),
             dict(name="Ridge", sex="Male", color="Chocolate Roan", birth_weight_oz=8, current_weight_lbs=2.0, status="Available", price=2600),
             dict(name="Cascade", sex="Female", color="Chocolate Merle Roan", birth_weight_oz=7, current_weight_lbs=1.9, status="Available", price=2900),
             dict(name="Juniper", sex="Female", color="Chocolate Tuxedo", birth_weight_oz=7, current_weight_lbs=2.1, status="Reserved", price=2900),
             dict(name="Canyon", sex="Male", color="Chocolate", birth_weight_oz=8, current_weight_lbs=2.3, status="Available", price=2600),
             dict(name="Sierra", sex="Female", color="Chocolate Merle", birth_weight_oz=7, current_weight_lbs=2.0, status="Available", price=2900),
         ]),
    dict(litter_name="Sunshine x Romeo", dam_name="Sunshine", sire_name_text="Romeo",
         breed="Australian Bernedoodle", status="Expecting",
         bred_date="2026-07-20", dob=None, go_home_date=None, waitlist_count=14,
         puppies=[]),
    dict(litter_name="Juliet x Yankee", dam_name="Juliet", sire_name_text="Yankee",
         breed="Infusion Australian Labradoodle", status="Planned",
         bred_date=None, dob=None, go_home_date=None, waitlist_count=9,
         puppies=[]),
]

APPLICATIONS = [
    dict(first_name="Reid", last_name="Family", city="Denver", state="CO", zip="80202",
         how_heard="Referral", phone="303-555-0142", email="reidfamily@example.com",
         preferred_contact="Text", timeframe="Immediate", current_dogs="Yes (one)",
         puppy_choice_1="Female, tuxedo/tricolor", gender_preference="Female",
         delivery_pref="In-person pickup", training_interest="Yes", training_package="Silver",
         notify_future_litters=1, contract_agree=1, signature_text="Jamie Reid",
         signature_date="2026-07-14", comments="So excited -- our kids have been asking for a doodle for years!",
         status="Approved", star_rating=5, submitted_at="2026-07-12 14:20:00"),
    dict(first_name="Morales", last_name="Family", city="Colorado Springs", state="CO", zip="80903",
         how_heard="Facebook/Instagram", phone="719-555-0188", email="moralesfam@example.com",
         preferred_contact="Phone Call", timeframe="0-3 months", current_dogs="No",
         puppy_choice_1="Male or female, calm temperament", gender_preference="Don't care",
         delivery_pref="In-person pickup", training_interest="Yes", training_package="Bronze",
         notify_future_litters=1, contract_agree=1, signature_text="Ana Morales",
         signature_date="2026-08-03", comments="First time doodle owners, two kids ages 6 and 9, fenced yard.",
         status="Screening", star_rating=4, submitted_at="2026-08-03 09:05:00"),
    dict(first_name="Patel", last_name="Family", city="Boulder", state="CO", zip="80301",
         how_heard="Google Search/Ad", phone="303-555-0199", email="patel.household@example.com",
         preferred_contact="Email", timeframe="6-12 months", current_dogs="Yes (two)",
         puppy_choice_1="Male, low-shed", gender_preference="Male",
         delivery_pref="Delivery needed", training_interest="No", training_package="",
         notify_future_litters=1, contract_agree=1, signature_text="Raj Patel",
         signature_date="2026-08-10", comments="",
         status="New", star_rating=3, submitted_at="2026-08-10 18:40:00"),
    dict(first_name="Chen", last_name="Family", city="Fort Collins", state="CO", zip="80521",
         how_heard="Nextdoor", phone="970-555-0121", email="chenhome@example.com",
         preferred_contact="Text", timeframe="Greater than a year", current_dogs="Yes (3+)",
         puppy_choice_1="Female", gender_preference="Female",
         delivery_pref="In-person pickup", training_interest="Yes", training_package="Basic",
         notify_future_litters=1, contract_agree=1, signature_text="Lin Chen",
         signature_date="2026-06-28", comments="Waiting for a fall or winter litter, no rush.",
         status="Waitlisted", star_rating=2, submitted_at="2026-06-28 11:15:00"),
]

CONTACTS = [
    dict(name="Sarah Whitfield", email="sarahw@example.com", phone="720-555-0177",
         city_state="Aurora, CO", subject="Guardian Home Program",
         how_heard="Referral", message="Hi! We'd love to learn more about becoming a guardian home for a future litter. We're within 20 miles of Colorado Springs.",
         status="New", submitted_at="2026-08-18 10:12:00"),
]


def run():
    init_db()
    conn = get_db()
    cur = conn.cursor()

    dog_ids = {}
    for d in DOGS:
        cur.execute("""
            INSERT INTO dogs (name, sex, role, breed, color, coat, dob, weight_lbs, akc_number,
                microchip, sire_name, dam_name, coi_percent, bio, hips, elbows, eic, dm, vwd, pra, guardian_family)
            VALUES (:name, :sex, :role, :breed, :color, :coat, :dob, :weight_lbs, NULL,
                NULL, :sire_name, :dam_name, :coi_percent, :bio, :hips, :elbows, :eic, :dm, :vwd, :pra, :guardian_family)
        """, {**{k: d.get(k) for k in [
            "name","sex","role","breed","color","coat","dob","weight_lbs","sire_name","dam_name",
            "coi_percent","bio","hips","elbows","eic","dm","vwd","pra","guardian_family"]}})
        dog_ids[d["name"]] = cur.lastrowid

    litter_ids = {}
    for l in LITTERS:
        dam_id = dog_ids.get(l.get("dam_name"))
        sire_id = dog_ids.get(l.get("sire_name"))
        cur.execute("""
            INSERT INTO litters (litter_name, sire_id, dam_id, sire_name_text, dam_name_text, breed,
                status, bred_date, dob, go_home_date, waitlist_count)
            VALUES (?,?,?,?,?,?,?,?,?,?,?)
        """, (l["litter_name"], sire_id, dam_id, l.get("sire_name_text"), l.get("dam_name_text"),
              l["breed"], l["status"], l.get("bred_date"), l.get("dob"), l.get("go_home_date"),
              l.get("waitlist_count", 0)))
        litter_id = cur.lastrowid
        litter_ids[l["litter_name"]] = litter_id
        for p in l["puppies"]:
            cur.execute("""
                INSERT INTO puppies (litter_id, name, sex, color, birth_weight_oz, current_weight_lbs,
                    status, price)
                VALUES (?,?,?,?,?,?,?,?)
            """, (litter_id, p["name"], p["sex"], p["color"], p.get("birth_weight_oz"),
                  p.get("current_weight_lbs"), p["status"], p.get("price")))

    for a in APPLICATIONS:
        cols = ["first_name","last_name","city","state","zip","how_heard","phone","email",
                "preferred_contact","timeframe","current_dogs","puppy_choice_1","gender_preference",
                "delivery_pref","training_interest","training_package","notify_future_litters",
                "contract_agree","signature_text","signature_date","comments","status","star_rating",
                "submitted_at"]
        placeholders = ",".join("?" for _ in cols)
        cur.execute(f"INSERT INTO applications ({','.join(cols)}) VALUES ({placeholders})",
                    tuple(a.get(c) for c in cols))

    for c in CONTACTS:
        cols = ["name","email","phone","city_state","subject","how_heard","message","status","submitted_at"]
        placeholders = ",".join("?" for _ in cols)
        cur.execute(f"INSERT INTO contacts ({','.join(cols)}) VALUES ({placeholders})",
                    tuple(c.get(k) for k in cols))

    # Demo reservations tied to specific puppies, with a portal token, messages & updates
    cur.execute("SELECT id FROM puppies WHERE name = 'Breck'")
    breck_id = cur.fetchone()["id"]
    reid_token = new_token()
    cur.execute("""
        INSERT INTO reservations (puppy_id, buyer_name, buyer_email, buyer_phone, portal_token,
            total_price, deposit_paid, balance_due, contract_signed, health_guarantee_ready, pickup_date)
        VALUES (?,?,?,?,?,?,?,?,?,?,?)
    """, (breck_id, "Reid Family", "reidfamily@example.com", "303-555-0142", reid_token,
          3200, 500, 2700, 1, 0, "2026-08-25"))
    reid_res_id = cur.lastrowid
    cur.execute("UPDATE puppies SET status='Reserved' WHERE id=?", (breck_id,))

    cur.execute("SELECT id FROM puppies WHERE name = 'Monty'")
    monty_id = cur.fetchone()["id"]
    ellison_token = new_token()
    cur.execute("""
        INSERT INTO reservations (puppy_id, buyer_name, buyer_email, buyer_phone, portal_token,
            total_price, deposit_paid, balance_due, contract_signed, health_guarantee_ready, pickup_date)
        VALUES (?,?,?,?,?,?,?,?,?,?,?)
    """, (monty_id, "Ellison Family", "ellisons@example.com", "719-555-0166", ellison_token,
          2800, 500, 2300, 0, 0, "2026-08-25"))
    cur.execute("UPDATE puppies SET status='Reserved' WHERE id=?", (monty_id,))

    cur.execute("""INSERT INTO updates (reservation_id, body, created_at) VALUES
        (?, 'Breck aced her first temperament evaluation today -- confident, food-motivated, loves people!', '2026-08-19 16:00:00')""",
        (reid_res_id,))
    cur.execute("""INSERT INTO messages (reservation_id, sender, body, created_at) VALUES
        (?, 'buyer', 'We are SO excited, thank you for the update!! Is there anything special we should bring on pickup day?', '2026-08-19 17:30:00')""",
        (reid_res_id,))
    cur.execute("""INSERT INTO messages (reservation_id, sender, body, created_at) VALUES
        (?, 'breeder', 'So happy to hear it! Just bring a crate or car seat for the ride home -- we will send you home with food, a blanket that smells like mom, and her go-home binder.', '2026-08-19 18:10:00')""",
        (reid_res_id,))

    # Health & Genetics
    apollo_id, roxy_id, willow_id, foxtrot_id = dog_ids["Apollo"], dog_ids["Roxy"], dog_ids["Willow"], dog_ids["Foxtrot"]
    cur.executemany(
        "INSERT INTO reminders (entity_type, entity_id, title, due_date, done) VALUES (?,?,?,?,?)",
        [
            ("dog", apollo_id, "Bordetella booster", "2026-09-03", 0),
            ("dog", roxy_id, "OFA elbow re-eval (eligible at 24mo)", "2026-10-15", 0),
            ("dog", willow_id, "Annual wellness exam", "2026-09-12", 0),
            ("dog", foxtrot_id, "Post-heat wellness check", "2026-09-05", 0),
            ("puppy", breck_id, "6-week vet exam & microchip", "2026-08-11", 1),
        ],
    )

    # Breeding: a heat cycle for Foxtrot, semen banked from both studs
    cur.execute(
        "INSERT INTO heat_cycles (dog_id, start_date, progesterone, notes) VALUES (?,?,?,?)",
        (foxtrot_id, "2026-08-16", 2.4, "Fertile window days 3-9. Next progesterone draw tomorrow."),
    )
    cur.executemany(
        "INSERT INTO semen_inventory (dog_id, kind, quantity, location, collected_date, notes) VALUES (?,?,?,?,?,?)",
        [
            (apollo_id, "Frozen", 6, "Tank B-14", "2026-02-10", "6 straws collected and banked."),
            (dog_ids["Luca"], "Frozen", 4, "Tank A-02", "2026-05-05", "4 straws collected and banked."),
        ],
    )

    # Sales: invoices for the two active reservations
    cur.executemany(
        "INSERT INTO invoices (reservation_id, description, amount, status, due_date, paid_at) VALUES (?,?,?,?,?,?)",
        [
            (reid_res_id, "Deposit -- Breck", 500, "Paid", None, "2026-08-12"),
            (reid_res_id, "Balance due -- Breck", 2700, "Due", "2026-08-25", None),
        ],
    )

    # Business: a few expenses tagged to the Zulu x Yankee litter
    cur.executemany(
        "INSERT INTO expenses (category, description, amount, expense_date, litter_id) VALUES (?,?,?,?,?)",
        [
            ("Veterinary", "6-week vet exams & vaccines -- Zulu x Yankee litter", 960, "2026-08-11", litter_ids["Zulu x Yankee"]),
            ("Supplies", "Whelping supplies -- Zulu x Yankee litter", 210, "2026-06-28", litter_ids["Zulu x Yankee"]),
            ("Testing", "Progesterone testing -- Foxtrot heat cycle", 340, "2026-08-18", None),
            ("Registration", "Microchips (x8) -- Zulu x Yankee litter", 200, "2026-08-11", litter_ids["Zulu x Yankee"]),
        ],
    )

    # Marketing: campaign log
    cur.executemany(
        "INSERT INTO campaigns (channel, title, body, status, scheduled_for, sent_at) VALUES (?,?,?,?,?,?)",
        [
            ("Social", "Boulder & Aspen puppy reel", "Reel featuring Boulder and Aspen playing in the yard.",
             "Scheduled", "2026-08-22 17:00", None),
            ("Email", "Zulu x Yankee puppies available", "Announcing our exciting new litter -- now accepting applications!",
             "Sent", None, "2026-08-01 09:00"),
        ],
    )

    # CRM: a couple of notes/tasks
    patel_app_id = cur.execute("SELECT id FROM applications WHERE last_name='Family' AND first_name='Patel'").fetchone()[0]
    cur.executemany(
        "INSERT INTO notes (entity_type, entity_id, body, due_date, done) VALUES (?,?,?,?,?)",
        [
            ("application", patel_app_id, "Call to discuss fenced-yard requirement and follow up on vet reference.", "2026-08-24", 0),
            ("reservation", reid_res_id, "Confirm pickup time with Reid family and prep go-home binder.", "2026-08-24", 0),
        ],
    )

    conn.commit()
    conn.close()
    print("Database initialized and seeded at instance/summitdoodles.db")
    print(f"Reid Family portal:    /portal/{reid_token}")
    print(f"Ellison Family portal: /portal/{ellison_token}")


if __name__ == "__main__":
    run()
