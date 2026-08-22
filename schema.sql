-- Summit Doodles -- database schema

PRAGMA foreign_keys = ON;

DROP TABLE IF EXISTS campaigns;
DROP TABLE IF EXISTS expenses;
DROP TABLE IF EXISTS invoices;
DROP TABLE IF EXISTS notes;
DROP TABLE IF EXISTS documents;
DROP TABLE IF EXISTS semen_inventory;
DROP TABLE IF EXISTS heat_cycles;
DROP TABLE IF EXISTS reminders;
DROP TABLE IF EXISTS messages;
DROP TABLE IF EXISTS updates;
DROP TABLE IF EXISTS reservations;
DROP TABLE IF EXISTS weight_logs;
DROP TABLE IF EXISTS puppies;
DROP TABLE IF EXISTS litters;
DROP TABLE IF EXISTS applications;
DROP TABLE IF EXISTS contacts;
DROP TABLE IF EXISTS dogs;

CREATE TABLE dogs (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    name            TEXT NOT NULL,
    sex             TEXT NOT NULL CHECK (sex IN ('Male','Female')),
    role            TEXT NOT NULL DEFAULT 'Stud' CHECK (role IN ('Stud','Dam','Guardian Home','Retired')),
    breed           TEXT,
    color           TEXT,
    coat            TEXT,
    dob             TEXT,               -- ISO date
    weight_lbs      REAL,
    akc_number      TEXT,
    microchip       TEXT,
    sire_name       TEXT,
    dam_name        TEXT,
    sire_sire       TEXT,
    sire_dam        TEXT,
    dam_sire        TEXT,
    dam_dam         TEXT,
    coi_percent     REAL,
    bio             TEXT,
    hips            TEXT,
    elbows          TEXT,
    eic             TEXT,
    dm              TEXT,
    vwd             TEXT,
    pra             TEXT,
    guardian_family TEXT,
    photo_filename  TEXT,
    created_at      TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE litters (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    litter_name     TEXT NOT NULL,          -- e.g. "Zulu x Yankee"
    sire_id         INTEGER REFERENCES dogs(id),
    dam_id          INTEGER REFERENCES dogs(id),
    sire_name_text  TEXT,                   -- fallback free-text if sire not in dogs table
    dam_name_text   TEXT,
    breed           TEXT,
    status          TEXT NOT NULL DEFAULT 'Planned' CHECK (status IN ('Planned','Expecting','Whelped','Reserving','Complete')),
    bred_date       TEXT,
    dob             TEXT,                   -- birth date, null until whelped
    go_home_date    TEXT,
    waitlist_count  INTEGER DEFAULT 0,
    notes           TEXT,
    photo_filename  TEXT,
    coi_percent     REAL,                   -- breeder-entered estimated COI for this pairing
    coi_notes       TEXT,
    created_at      TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE puppies (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    litter_id       INTEGER NOT NULL REFERENCES litters(id) ON DELETE CASCADE,
    name            TEXT NOT NULL,
    sex             TEXT NOT NULL CHECK (sex IN ('Male','Female')),
    color            TEXT,
    birth_weight_oz REAL,
    current_weight_lbs REAL,
    status          TEXT NOT NULL DEFAULT 'Available' CHECK (status IN ('Available','On Hold','Reserved','Sold')),
    price            REAL,
    microchip       TEXT,
    akc_number      TEXT,
    notes           TEXT,
    photo_filename  TEXT,
    created_at      TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE weight_logs (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    dog_id      INTEGER REFERENCES dogs(id) ON DELETE CASCADE,
    puppy_id    INTEGER REFERENCES puppies(id) ON DELETE CASCADE,
    log_date    TEXT NOT NULL,
    weight_lbs  REAL NOT NULL,
    CHECK ((dog_id IS NOT NULL AND puppy_id IS NULL) OR (dog_id IS NULL AND puppy_id IS NOT NULL))
);

-- Mirrors the real summitdoodles.com/application form fields
CREATE TABLE applications (
    id                      INTEGER PRIMARY KEY AUTOINCREMENT,
    first_name              TEXT NOT NULL,
    last_name               TEXT NOT NULL,
    address_line1           TEXT,
    address_line2           TEXT,
    city                    TEXT,
    state                   TEXT,
    zip                     TEXT,
    how_heard               TEXT,
    phone                   TEXT NOT NULL,
    email                   TEXT NOT NULL,
    preferred_contact       TEXT,
    referral_source         TEXT,
    timeframe               TEXT,
    current_dogs            TEXT,
    puppy_choice_1          TEXT,
    puppy_choice_2          TEXT,
    puppy_choice_3          TEXT,
    notify_future_litters   INTEGER DEFAULT 0,
    gender_preference       TEXT,
    delivery_pref           TEXT,
    training_interest       TEXT,
    training_package        TEXT,
    contract_agree          INTEGER DEFAULT 0,
    signature_text          TEXT,
    signature_date          TEXT,
    comments                TEXT,
    status                  TEXT NOT NULL DEFAULT 'New' CHECK (status IN ('New','Screening','Approved','Waitlisted','Declined')),
    star_rating              INTEGER DEFAULT 0,
    submitted_at             TEXT NOT NULL DEFAULT (datetime('now'))
);

-- Mirrors the real summitdoodles.com contact form
CREATE TABLE contacts (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    name            TEXT NOT NULL,
    email           TEXT NOT NULL,
    phone           TEXT,
    city_state      TEXT,
    subject         TEXT,
    how_heard       TEXT,
    message         TEXT,
    status          TEXT NOT NULL DEFAULT 'New' CHECK (status IN ('New','Replied','Closed')),
    submitted_at    TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE reservations (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    puppy_id        INTEGER NOT NULL REFERENCES puppies(id) ON DELETE CASCADE,
    buyer_name      TEXT NOT NULL,
    buyer_email     TEXT NOT NULL,
    buyer_phone     TEXT,
    portal_token    TEXT NOT NULL UNIQUE,
    total_price     REAL,
    deposit_paid    REAL DEFAULT 0,
    balance_due     REAL DEFAULT 0,
    contract_signed INTEGER DEFAULT 0,
    health_guarantee_ready INTEGER DEFAULT 0,
    pickup_date     TEXT,
    pickup_notes    TEXT,
    buyer_signature TEXT,                   -- typed e-signature on the purchase agreement
    buyer_signature_date TEXT,
    feeding_schedule TEXT,
    training_notes  TEXT,
    registration_status TEXT NOT NULL DEFAULT 'Pending' CHECK (registration_status IN ('Pending','Submitted','Complete')),
    go_home_sent    INTEGER DEFAULT 0,
    created_at      TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE updates (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    reservation_id  INTEGER NOT NULL REFERENCES reservations(id) ON DELETE CASCADE,
    body            TEXT NOT NULL,
    photo_filename  TEXT,
    created_at      TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE messages (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    reservation_id  INTEGER NOT NULL REFERENCES reservations(id) ON DELETE CASCADE,
    sender          TEXT NOT NULL CHECK (sender IN ('breeder','buyer')),
    body            TEXT NOT NULL,
    created_at      TEXT NOT NULL DEFAULT (datetime('now'))
);

-- Health & Genetics: reminders for a dog or a puppy (vaccines, re-evals, exams...)
CREATE TABLE reminders (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    entity_type     TEXT NOT NULL CHECK (entity_type IN ('dog','puppy')),
    entity_id       INTEGER NOT NULL,
    title           TEXT NOT NULL,
    due_date        TEXT,
    done            INTEGER NOT NULL DEFAULT 0,
    created_at      TEXT NOT NULL DEFAULT (datetime('now'))
);

-- Breeding: heat cycle log per dam
CREATE TABLE heat_cycles (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    dog_id          INTEGER NOT NULL REFERENCES dogs(id) ON DELETE CASCADE,
    start_date      TEXT NOT NULL,
    progesterone    REAL,
    notes           TEXT,
    created_at      TEXT NOT NULL DEFAULT (datetime('now'))
);

-- Breeding: semen bank
CREATE TABLE semen_inventory (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    dog_id          INTEGER NOT NULL REFERENCES dogs(id) ON DELETE CASCADE,
    kind            TEXT NOT NULL CHECK (kind IN ('Fresh','Chilled','Frozen')),
    quantity        INTEGER DEFAULT 1,
    location        TEXT,
    collected_date  TEXT,
    notes           TEXT,
    created_at      TEXT NOT NULL DEFAULT (datetime('now'))
);

-- Document vault: contracts, guarantees, health records, litter/dog paperwork
CREATE TABLE documents (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    entity_type     TEXT NOT NULL CHECK (entity_type IN ('dog','litter','reservation','general')),
    entity_id       INTEGER,
    title           TEXT NOT NULL,
    category        TEXT,
    filename        TEXT NOT NULL,
    uploaded_at     TEXT NOT NULL DEFAULT (datetime('now'))
);

-- Lightweight tasks/notes attached to an application, reservation, or contact
CREATE TABLE notes (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    entity_type     TEXT NOT NULL CHECK (entity_type IN ('application','reservation','contact')),
    entity_id       INTEGER NOT NULL,
    body            TEXT NOT NULL,
    due_date        TEXT,
    done            INTEGER NOT NULL DEFAULT 0,
    created_at      TEXT NOT NULL DEFAULT (datetime('now'))
);

-- Sales: invoices/receipts tied to a reservation
CREATE TABLE invoices (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    reservation_id  INTEGER NOT NULL REFERENCES reservations(id) ON DELETE CASCADE,
    description     TEXT NOT NULL,
    amount          REAL NOT NULL,
    status          TEXT NOT NULL DEFAULT 'Due' CHECK (status IN ('Due','Paid')),
    due_date        TEXT,
    paid_at         TEXT,
    created_at      TEXT NOT NULL DEFAULT (datetime('now'))
);

-- Business: expenses, optionally tagged to a litter for profit-by-litter reporting
CREATE TABLE expenses (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    category        TEXT NOT NULL,
    description     TEXT,
    amount          REAL NOT NULL,
    expense_date    TEXT NOT NULL,
    litter_id       INTEGER REFERENCES litters(id) ON DELETE SET NULL,
    created_at      TEXT NOT NULL DEFAULT (datetime('now'))
);

-- Marketing: an internal log of social/email campaigns (nothing is actually sent)
CREATE TABLE campaigns (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    channel         TEXT NOT NULL CHECK (channel IN ('Social','Email')),
    title           TEXT NOT NULL,
    body            TEXT,
    status          TEXT NOT NULL DEFAULT 'Draft' CHECK (status IN ('Draft','Scheduled','Sent')),
    scheduled_for   TEXT,
    sent_at         TEXT,
    created_at      TEXT NOT NULL DEFAULT (datetime('now'))
);
