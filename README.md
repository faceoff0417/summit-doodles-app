# Summit Doodles -- Breeder App

A real, running app for Summit Doodles covering every module: dog
profiles, health & genetics, breeding (heat cycles, pregnancy tracking,
pairing/compatibility tool, semen bank), litters & puppies, a buyer CRM
with matching, reservations with invoicing and e-signature, a customer
portal per puppy family (with an after-pickup lifetime profile), a
go-home binder, business/financials, marketing, a document vault, and
the two real fillable forms from summitdoodles.com (the puppy
application and the contact form). Python/Flask + SQLite, no external
services required.

## Run it

```bash
cd webapp
pip3 install -r requirements.txt
python3 seed.py        # first time only: creates instance/summitdoodles.db and loads your real dogs/litters
python3 app.py          # starts the server at http://localhost:5050
```

If you already have a database from an earlier version of the app,
run the non-destructive migration instead of `seed.py` (which wipes
everything):

```bash
python3 migrate.py     # adds new tables/columns, keeps all your existing data & photos
```

Breeder sign-in: go to `http://localhost:5050/`, password is `summit2026`
(change it by setting the `SUMMIT_ADMIN_PASSWORD` environment variable
before running `app.py`).

Public pages -- no login needed, safe to link from your real site or share directly:
- `/apply` -- the puppy application form
- `/contact` -- the contact form
- `/puppies` -- public listing of available puppies by litter
- `/portal/<token>` -- a family's private puppy portal (the link is
  generated per-reservation on the Reservation page and is unguessable,
  but isn't password protected -- don't post it publicly)

## Every module, and where to find it

| Module | Where |
|---|---|
| Dog Profiles | Dogs |
| Health & Genetics | Health & Genetics (reminders, carrier/clear matrix, doc vault) |
| Breeding | Breeding (heat cycles, pregnancies, pairing tool, semen bank) |
| Genetics | Breeding &rarr; Pairing Tool (carrier/clear compatibility, manual COI entry) |
| Litters | Litters |
| Customers | Applications, Contacts, notes/tasks on each |
| Sales | Reservations (deposits, balances, invoices) |
| Matching | Matching |
| Customer App | `/portal/<token>` |
| Go-Home | Reservation detail &rarr; Go-Home Binder (also shown on the family's portal) |
| After Sale | Reservation detail &rarr; Lifetime Profile; ongoing updates/messages on the portal |
| Business | Business (revenue, expenses, profit by litter, acquisition sources) |
| Marketing | Marketing (public listings link, campaign log, referral tracking) |
| Documents | Documents (vault + templates reference) |

## What's real vs. what's still a placeholder

Real: the database, every form, photo uploads, weight logs, health
reminders, heat-cycle & semen tracking, the genetic-compatibility
pairing tool, buyer matching, invoices, expenses, the document vault,
and a typed e-signature on the purchase agreement (buyer signs from
their portal) -- all of it persists to `instance/summitdoodles.db`.

Not yet wired up: actual payment processing (deposits/balances/invoices
are recorded manually, nothing charges a card), legally-binding
e-signature (the "signature" is typed text, not DocuSign-grade), a
true multi-generation pedigree/COI calculator (COI is entered manually
from your own pedigree software), and outbound email/SMS/social
posting (the Marketing campaign log and the notification-worthy events
like new applications/messages show up in the app but nothing is
actually sent for you).

## Resetting the data

`python3 seed.py` drops and recreates every table, so re-run it any
time you want to start fresh with the seeded sample data. **This
deletes everything, including uploaded photos' database records** (the
image files themselves stay in `static/uploads/` but nothing will
point to them anymore) -- use `python3 migrate.py` instead if you just
want to pick up schema changes without losing your data.
