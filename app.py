import os
import datetime
from functools import wraps

from flask import (Flask, render_template, request, redirect, url_for, session,
                    flash, abort, send_from_directory)
from werkzeug.utils import secure_filename

from db import get_db, init_db, new_token, DATA_DIR, INSTANCE_DIR, DB_PATH
import migrate

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# DATA_DIR (from db.py) points at a persistent disk's mount path when one is
# configured (e.g. Render -- see DEPLOY.md), so uploaded photos/documents
# live alongside the database and survive a redeploy together. Locally
# (DATA_DIR unset) uploads stay exactly where they've always been.
UPLOAD_DIR = (os.path.join(DATA_DIR, "uploads") if os.environ.get("DATA_DIR")
              else os.path.join(BASE_DIR, "static", "uploads"))
ALLOWED_EXT = {"png", "jpg", "jpeg", "gif", "webp"}

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 8 * 1024 * 1024  # 8 MB uploads

# --- one-time setup on a fresh persistent disk: create the schema if the
# database doesn't exist yet. Runs at import time so it fires under gunicorn
# too, not just `python3 app.py`. Never overwrites an existing database. ---
os.makedirs(UPLOAD_DIR, exist_ok=True)
if not os.path.exists(DB_PATH):
    init_db()
# --- always bring an existing database up to the latest schema too, so a
# new table/column added in a later release just appears -- no manual
# migration step needed on redeploy. Every statement is idempotent. ---
migrate.run()

# --- secret key: persisted alongside the database so sessions survive a
# restart/redeploy (and everyone using the app isn't logged out each time) ---
_secret_path = os.path.join(INSTANCE_DIR, "secret_key.txt")
if not os.path.exists(_secret_path):
    with open(_secret_path, "w") as f:
        f.write(os.urandom(32).hex())
with open(_secret_path) as f:
    app.secret_key = f.read().strip()

ADMIN_PASSWORD = os.environ.get("SUMMIT_ADMIN_PASSWORD", "summit2026")
if ADMIN_PASSWORD == "summit2026" and os.environ.get("RENDER"):
    # Never run a public deploy on the default password -- fail loudly rather
    # than silently leave the breeder dashboard guessable.
    raise RuntimeError(
        "Set the SUMMIT_ADMIN_PASSWORD environment variable to a real "
        "password before deploying -- refusing to start with the default."
    )


# ---------------------------------------------------------------- helpers --
def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get("is_admin"):
            return redirect(url_for("login", next=request.path))
        return view(*args, **kwargs)
    return wrapped


def open_counts():
    conn = get_db()
    app_count = conn.execute(
        "SELECT COUNT(*) c FROM applications WHERE status IN ('New','Screening')"
    ).fetchone()["c"]
    contact_count = conn.execute(
        "SELECT COUNT(*) c FROM contacts WHERE status = 'New'"
    ).fetchone()["c"]
    meeting_count = conn.execute(
        "SELECT COUNT(*) c FROM meeting_requests WHERE status = 'Requested'"
    ).fetchone()["c"]
    conn.close()
    return app_count, contact_count, meeting_count


@app.context_processor
def inject_counts():
    if session.get("is_admin"):
        a, c, m = open_counts()
        return dict(open_application_count=a, open_contact_count=c, open_meeting_count=m)
    return dict(open_application_count=0, open_contact_count=0, open_meeting_count=0)


def get_setting(key, default=None):
    conn = get_db()
    row = conn.execute("SELECT value FROM site_settings WHERE key=?", (key,)).fetchone()
    conn.close()
    return row["value"] if row else default


def set_setting(key, value):
    conn = get_db()
    conn.execute(
        "INSERT INTO site_settings (key, value) VALUES (?, ?) "
        "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
        (key, value),
    )
    conn.commit()
    conn.close()


def guardian_lifetime_count():
    # Manual baseline (older placements this app never tracked) + every dog
    # that has actually transitioned into the Guardian Program since --
    # stamped automatically in dog_edit() below, so this grows on its own.
    baseline = int(get_setting("guardian_lifetime_baseline", "12"))
    conn = get_db()
    new_since = conn.execute(
        "SELECT COUNT(*) c FROM dogs WHERE guardian_placed_at IS NOT NULL"
    ).fetchone()["c"]
    conn.close()
    return baseline + new_since


def save_upload(file_storage, subdir, id_prefix):
    if not file_storage or not file_storage.filename:
        return None
    ext = file_storage.filename.rsplit(".", 1)[-1].lower() if "." in file_storage.filename else ""
    if ext not in ALLOWED_EXT:
        flash("That file type isn't supported -- please use a JPG, PNG, GIF, or WEBP.", "error")
        return None
    folder = os.path.join(UPLOAD_DIR, subdir)
    os.makedirs(folder, exist_ok=True)
    fname = secure_filename(f"{id_prefix}_{int(datetime.datetime.now().timestamp())}.{ext}")
    file_storage.save(os.path.join(folder, fname))
    return f"{subdir}/{fname}"


def age_str(dob_str):
    if not dob_str:
        return None
    dob = datetime.date.fromisoformat(dob_str)
    today = datetime.date.today()
    days = (today - dob).days
    if days < 0:
        return None
    if days < 60:
        weeks = days // 7
        return f"{weeks} week{'s' if weeks != 1 else ''} old"
    years = days // 365
    months = (days % 365) // 30
    if years < 1:
        return f"{months} month{'s' if months != 1 else ''} old"
    return f"{years} yr{'s' if years != 1 else ''} old"


app.jinja_env.filters["age"] = age_str


@app.template_filter("money")
def money(v):
    if v is None:
        return "$0"
    return f"${v:,.0f}"


@app.template_filter("dateread")
def dateread(v):
    if not v:
        return "TBD"
    try:
        d = datetime.date.fromisoformat(str(v)[:10])
        return d.strftime("%b %-d, %Y")
    except Exception:
        return v


PILL_MAP = {
    "Available": "pill-green", "On Hold": "pill-amber", "Reserved": "pill-purple", "Sold": "pill-gray",
    "New": "pill-blue", "Screening": "pill-amber", "Approved": "pill-green", "Waitlisted": "pill-gray",
    "Declined": "pill-red", "Replied": "pill-blue", "Closed": "pill-gray",
    "Planned": "pill-gray", "Expecting": "pill-purple", "Whelped": "pill-blue", "Reserving": "pill-green",
    "Complete": "pill-gray",
    "Requested": "pill-amber", "Confirmed": "pill-green", "Completed": "pill-gray",
}
app.jinja_env.globals["pill_class"] = lambda status: PILL_MAP.get(status, "pill-gray")


# -------------------------------------------------------------------- auth --
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        if request.form.get("password") == ADMIN_PASSWORD:
            session["is_admin"] = True
            flash("Welcome back, Tara.", "success")
            return redirect(request.args.get("next") or url_for("dashboard"))
        flash("That password isn't right -- try again.", "error")
    return render_template("login.html")


@app.route("/logout")
def logout():
    session.pop("is_admin", None)
    return redirect(url_for("login"))


@app.route("/")
def public_home():
    if session.get("is_admin"):
        return redirect(url_for("dashboard"))
    return render_template("public_home.html", pub_active="home",
                            guardian_lifetime=guardian_lifetime_count())


@app.route("/about")
def about_public():
    about_photo = get_setting("about_photo")
    return render_template("about.html", pub_active="about", about_photo=about_photo)


@app.route("/about/edit", methods=["GET", "POST"])
@login_required
def about_edit():
    if request.method == "POST":
        fn = save_upload(request.files.get("photo"), "about", "about-family")
        if fn:
            set_setting("about_photo", fn)
            flash("About page photo updated.", "success")
        return redirect(url_for("about_edit"))
    about_photo = get_setting("about_photo")
    return render_template("about_edit.html", nav_active="about", about_photo=about_photo)


# --------------------------------------------------------------- dashboard --
@app.route("/dashboard")
@login_required
def dashboard():
    conn = get_db()
    active_litters = conn.execute(
        "SELECT COUNT(*) c FROM litters WHERE status != 'Complete'"
    ).fetchone()["c"]
    available_puppies = conn.execute(
        "SELECT COUNT(*) c FROM puppies WHERE status = 'Available'"
    ).fetchone()["c"]
    open_apps = conn.execute(
        "SELECT COUNT(*) c FROM applications WHERE status IN ('New','Screening')"
    ).fetchone()["c"]
    deposits_held = conn.execute(
        "SELECT COALESCE(SUM(deposit_paid),0) s FROM reservations"
    ).fetchone()["s"]
    recent_apps = conn.execute(
        "SELECT * FROM applications ORDER BY submitted_at DESC LIMIT 4"
    ).fetchall()
    recent_contacts = conn.execute(
        "SELECT * FROM contacts ORDER BY submitted_at DESC LIMIT 3"
    ).fetchall()
    litters = conn.execute(
        "SELECT * FROM litters WHERE status != 'Complete' ORDER BY dob IS NULL, dob DESC"
    ).fetchall()
    upcoming = conn.execute(
        "SELECT r.*, p.name as puppy_name FROM reservations r JOIN puppies p ON p.id = r.puppy_id "
        "WHERE r.pickup_date IS NOT NULL ORDER BY r.pickup_date ASC LIMIT 4"
    ).fetchall()
    conn.close()

    # --- sales metrics: placeholders for now (Tara will provide updated
    # totals until this is wired up to compute automatically off actual
    # sold/delivered puppies + per-puppy revenue and cost tracking). ---
    def with_averages(sold, revenue, profit):
        return dict(sold=sold, revenue=revenue, profit=profit,
                     avg_revenue=(revenue / sold) if sold else 0,
                     avg_profit=(profit / sold) if sold else 0)

    sales_ytd = with_averages(sold=40, revenue=140000, profit=50000)
    sales_lifetime = with_averages(sold=200, revenue=680000, profit=242857)

    return render_template("dashboard.html", nav_active="dashboard",
                            active_litters=active_litters, available_puppies=available_puppies,
                            open_apps=open_apps, deposits_held=deposits_held,
                            recent_apps=recent_apps, recent_contacts=recent_contacts,
                            litters=litters, upcoming=upcoming,
                            sales_ytd=sales_ytd, sales_lifetime=sales_lifetime)


# --------------------------------------------------------------------- dogs --
@app.route("/dogs")
@login_required
def dogs_list():
    conn = get_db()
    q = request.args.get("role", "")
    if q:
        dogs = conn.execute("SELECT * FROM dogs WHERE role = ? ORDER BY name", (q,)).fetchall()
    else:
        dogs = conn.execute("SELECT * FROM dogs ORDER BY role, name").fetchall()
    conn.close()
    return render_template("dogs_list.html", nav_active="dogs", dogs=dogs, filter_role=q)


@app.route("/dogs/new", methods=["GET", "POST"])
@login_required
def dog_new():
    if request.method == "POST":
        conn = get_db()
        cur = conn.execute("""
            INSERT INTO dogs (name, sex, role, breed, color, coat, dob, weight_lbs, akc_number,
                microchip, sire_name, dam_name, bio, hips, elbows, eic, dm, vwd, pra)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """, (request.form["name"], request.form["sex"], request.form["role"],
              request.form.get("breed"), request.form.get("color"), request.form.get("coat"),
              request.form.get("dob") or None, request.form.get("weight_lbs") or None,
              request.form.get("akc_number"), request.form.get("microchip"),
              request.form.get("sire_name"), request.form.get("dam_name"), request.form.get("bio"),
              request.form.get("hips"), request.form.get("elbows"), request.form.get("eic"),
              request.form.get("dm"), request.form.get("vwd"), request.form.get("pra")))
        dog_id = cur.lastrowid
        conn.commit()
        conn.close()
        flash(f"{request.form['name']} was added.", "success")
        return redirect(url_for("dog_detail", dog_id=dog_id))
    return render_template("dog_form.html", nav_active="dogs", dog=None)


@app.route("/dogs/<int:dog_id>")
@login_required
def dog_detail(dog_id):
    conn = get_db()
    dog = conn.execute("SELECT * FROM dogs WHERE id = ?", (dog_id,)).fetchone()
    if not dog:
        abort(404)
    weights = conn.execute(
        "SELECT * FROM weight_logs WHERE dog_id = ? ORDER BY log_date", (dog_id,)
    ).fetchall()
    litters = conn.execute(
        "SELECT * FROM litters WHERE sire_id = ? OR dam_id = ? ORDER BY dob DESC", (dog_id, dog_id)
    ).fetchall()
    conn.close()
    return render_template("dog_detail.html", nav_active="dogs", dog=dog, weights=weights, litters=litters)


@app.route("/dogs/<int:dog_id>/edit", methods=["GET", "POST"])
@login_required
def dog_edit(dog_id):
    conn = get_db()
    dog = conn.execute("SELECT * FROM dogs WHERE id = ?", (dog_id,)).fetchone()
    if not dog:
        abort(404)
    if request.method == "POST":
        new_guardian_family = request.form.get("guardian_family")
        # First time this dog gets placed with a guardian family, stamp it --
        # this is what drives the public "Guardian Program lifetime" count.
        # Never overwritten once set, so later edits to the family name (or
        # a later retirement) don't lose the original placement date.
        guardian_placed_at = dog["guardian_placed_at"]
        if not guardian_placed_at and new_guardian_family and new_guardian_family.strip():
            guardian_placed_at = datetime.datetime.now().isoformat()
        conn.execute("""
            UPDATE dogs SET name=?, sex=?, role=?, breed=?, color=?, coat=?, dob=?, weight_lbs=?,
                akc_number=?, microchip=?, sire_name=?, dam_name=?, bio=?, hips=?, elbows=?, eic=?,
                dm=?, vwd=?, pra=?, guardian_family=?, guardian_placed_at=?
            WHERE id=?
        """, (request.form["name"], request.form["sex"], request.form["role"],
              request.form.get("breed"), request.form.get("color"), request.form.get("coat"),
              request.form.get("dob") or None, request.form.get("weight_lbs") or None,
              request.form.get("akc_number"), request.form.get("microchip"),
              request.form.get("sire_name"), request.form.get("dam_name"), request.form.get("bio"),
              request.form.get("hips"), request.form.get("elbows"), request.form.get("eic"),
              request.form.get("dm"), request.form.get("vwd"), request.form.get("pra"),
              new_guardian_family, guardian_placed_at, dog_id))
        if "photo" in request.files:
            fn = save_upload(request.files["photo"], "dogs", f"dog{dog_id}")
            if fn:
                conn.execute("UPDATE dogs SET photo_filename=? WHERE id=?", (fn, dog_id))
        conn.commit()
        conn.close()
        flash("Profile updated.", "success")
        return redirect(url_for("dog_detail", dog_id=dog_id))
    conn.close()
    return render_template("dog_form.html", nav_active="dogs", dog=dog)


@app.route("/dogs/<int:dog_id>/weight", methods=["POST"])
@login_required
def dog_weight_add(dog_id):
    conn = get_db()
    conn.execute("INSERT INTO weight_logs (dog_id, log_date, weight_lbs) VALUES (?,?,?)",
                 (dog_id, request.form["log_date"], request.form["weight_lbs"]))
    conn.execute("UPDATE dogs SET weight_lbs=? WHERE id=?", (request.form["weight_lbs"], dog_id))
    conn.commit()
    conn.close()
    flash("Weight logged.", "success")
    return redirect(url_for("dog_detail", dog_id=dog_id))


@app.route("/dogs/<int:dog_id>/delete", methods=["POST"])
@login_required
def dog_delete(dog_id):
    conn = get_db()
    conn.execute("DELETE FROM dogs WHERE id=?", (dog_id,))
    conn.commit()
    conn.close()
    flash("Dog removed.", "info")
    return redirect(url_for("dogs_list"))


# ------------------------------------------------------------------ litters --
@app.route("/litters")
@login_required
def litters_list():
    conn = get_db()
    litters = conn.execute("""
        SELECT l.*,
            (SELECT COUNT(*) FROM puppies p WHERE p.litter_id = l.id) as puppy_count,
            (SELECT COUNT(*) FROM puppies p WHERE p.litter_id = l.id AND p.status='Available') as available_count,
            COALESCE((SELECT d.name FROM dogs d WHERE d.id = l.dam_id), l.dam_name_text) as dam_name,
            COALESCE((SELECT d.name FROM dogs d WHERE d.id = l.sire_id), l.sire_name_text) as sire_name
        FROM litters l ORDER BY l.dob IS NULL, l.dob DESC
    """).fetchall()
    conn.close()
    return render_template("litters_list.html", nav_active="litters", litters=litters)


@app.route("/litters/new", methods=["GET", "POST"])
@login_required
def litter_new():
    conn = get_db()
    if request.method == "POST":
        cur = conn.execute("""
            INSERT INTO litters (litter_name, sire_name_text, dam_name_text, breed, status,
                bred_date, dob, go_home_date, waitlist_count, notes)
            VALUES (?,?,?,?,?,?,?,?,?,?)
        """, (request.form["litter_name"], request.form.get("sire_name_text"),
              request.form.get("dam_name_text"), request.form.get("breed"),
              request.form.get("status", "Planned"), request.form.get("bred_date") or None,
              request.form.get("dob") or None, request.form.get("go_home_date") or None,
              request.form.get("waitlist_count") or 0, request.form.get("notes")))
        litter_id = cur.lastrowid
        conn.commit()
        conn.close()
        flash("Litter created.", "success")
        return redirect(url_for("litter_detail", litter_id=litter_id))
    dogs = conn.execute("SELECT * FROM dogs ORDER BY name").fetchall()
    conn.close()
    return render_template("litter_form.html", nav_active="litters", litter=None, dogs=dogs)


@app.route("/litters/<int:litter_id>")
@login_required
def litter_detail(litter_id):
    conn = get_db()
    litter = conn.execute("""
        SELECT l.*,
            COALESCE((SELECT d.name FROM dogs d WHERE d.id = l.dam_id), l.dam_name_text) as dam_name,
            COALESCE((SELECT d.name FROM dogs d WHERE d.id = l.sire_id), l.sire_name_text) as sire_name
        FROM litters l WHERE l.id = ?
    """, (litter_id,)).fetchone()
    if not litter:
        abort(404)
    puppies = conn.execute("SELECT * FROM puppies WHERE litter_id = ? ORDER BY name", (litter_id,)).fetchall()
    conn.close()
    return render_template("litter_detail.html", nav_active="litters", litter=litter, puppies=puppies)


@app.route("/litters/<int:litter_id>/edit", methods=["GET", "POST"])
@login_required
def litter_edit(litter_id):
    conn = get_db()
    litter = conn.execute("SELECT * FROM litters WHERE id = ?", (litter_id,)).fetchone()
    if not litter:
        abort(404)
    if request.method == "POST":
        conn.execute("""
            UPDATE litters SET litter_name=?, sire_name_text=?, dam_name_text=?, breed=?, status=?,
                bred_date=?, dob=?, go_home_date=?, waitlist_count=?, notes=?
            WHERE id=?
        """, (request.form["litter_name"], request.form.get("sire_name_text"),
              request.form.get("dam_name_text"), request.form.get("breed"),
              request.form.get("status"), request.form.get("bred_date") or None,
              request.form.get("dob") or None, request.form.get("go_home_date") or None,
              request.form.get("waitlist_count") or 0, request.form.get("notes"), litter_id))
        if "photo" in request.files:
            fn = save_upload(request.files["photo"], "litters", f"litter{litter_id}")
            if fn:
                conn.execute("UPDATE litters SET photo_filename=? WHERE id=?", (fn, litter_id))
        conn.commit()
        conn.close()
        flash("Litter updated.", "success")
        return redirect(url_for("litter_detail", litter_id=litter_id))
    dogs = conn.execute("SELECT * FROM dogs ORDER BY name").fetchall()
    conn.close()
    return render_template("litter_form.html", nav_active="litters", litter=litter, dogs=dogs)


@app.route("/litters/<int:litter_id>/puppies/new", methods=["POST"])
@login_required
def puppy_new(litter_id):
    conn = get_db()
    conn.execute("""
        INSERT INTO puppies (litter_id, name, sex, color, birth_weight_oz, current_weight_lbs, status, price)
        VALUES (?,?,?,?,?,?,?,?)
    """, (litter_id, request.form["name"], request.form["sex"], request.form.get("color"),
          request.form.get("birth_weight_oz") or None, request.form.get("current_weight_lbs") or None,
          request.form.get("status", "Available"), request.form.get("price") or None))
    conn.commit()
    conn.close()
    flash(f"{request.form['name']} added to the litter.", "success")
    return redirect(url_for("litter_detail", litter_id=litter_id))


@app.route("/puppies/<int:puppy_id>/edit", methods=["GET", "POST"])
@login_required
def puppy_edit(puppy_id):
    conn = get_db()
    puppy = conn.execute("SELECT * FROM puppies WHERE id = ?", (puppy_id,)).fetchone()
    if not puppy:
        abort(404)
    if request.method == "POST":
        conn.execute("""
            UPDATE puppies SET name=?, sex=?, color=?, birth_weight_oz=?, current_weight_lbs=?,
                status=?, price=?, microchip=?, akc_number=?, notes=?
            WHERE id=?
        """, (request.form["name"], request.form["sex"], request.form.get("color"),
              request.form.get("birth_weight_oz") or None, request.form.get("current_weight_lbs") or None,
              request.form.get("status"), request.form.get("price") or None,
              request.form.get("microchip"), request.form.get("akc_number"),
              request.form.get("notes"), puppy_id))
        if "photo" in request.files:
            fn = save_upload(request.files["photo"], "puppies", f"pup{puppy_id}")
            if fn:
                conn.execute("UPDATE puppies SET photo_filename=? WHERE id=?", (fn, puppy_id))
        conn.commit()
        conn.close()
        flash("Puppy updated.", "success")
        return redirect(url_for("litter_detail", litter_id=puppy["litter_id"]))
    conn.close()
    return render_template("puppy_form.html", nav_active="litters", puppy=puppy)


@app.route("/puppies/<int:puppy_id>/weight", methods=["POST"])
@login_required
def puppy_weight_add(puppy_id):
    conn = get_db()
    puppy = conn.execute("SELECT * FROM puppies WHERE id = ?", (puppy_id,)).fetchone()
    conn.execute("INSERT INTO weight_logs (puppy_id, log_date, weight_lbs) VALUES (?,?,?)",
                 (puppy_id, request.form["log_date"], request.form["weight_lbs"]))
    conn.execute("UPDATE puppies SET current_weight_lbs=? WHERE id=?", (request.form["weight_lbs"], puppy_id))
    conn.commit()
    conn.close()
    flash("Weight logged.", "success")
    return redirect(url_for("litter_detail", litter_id=puppy["litter_id"]))


# ---------------------------------------------------------- health & genetics --
CARRIER_TRAITS = ["eic", "dm", "vwd", "pra"]


@app.route("/health")
@login_required
def health():
    conn = get_db()
    reminders = conn.execute("""
        SELECT r.*,
            CASE r.entity_type WHEN 'dog' THEN (SELECT name FROM dogs WHERE id=r.entity_id)
                                ELSE (SELECT name FROM puppies WHERE id=r.entity_id) END as entity_name
        FROM reminders r ORDER BY r.done, r.due_date IS NULL, r.due_date
    """).fetchall()
    dogs = conn.execute("SELECT * FROM dogs ORDER BY role, name").fetchall()
    documents = conn.execute("SELECT * FROM documents ORDER BY uploaded_at DESC LIMIT 8").fetchall()
    doc_count = conn.execute("SELECT COUNT(*) c FROM documents").fetchone()["c"]
    tested_count = conn.execute(
        "SELECT COUNT(*) c FROM dogs WHERE hips IS NOT NULL AND hips != ''"
    ).fetchone()["c"]
    conn.close()
    open_reminders = [r for r in reminders if not r["done"]]
    return render_template("health.html", nav_active="health", reminders=reminders,
                            open_reminders=open_reminders, dogs=dogs, documents=documents,
                            doc_count=doc_count, tested_count=tested_count, traits=CARRIER_TRAITS)


@app.route("/reminders/new", methods=["POST"])
@login_required
def reminder_new():
    f = request.form
    conn = get_db()
    conn.execute("INSERT INTO reminders (entity_type, entity_id, title, due_date) VALUES (?,?,?,?)",
                 (f["entity_type"], f["entity_id"], f["title"], f.get("due_date") or None))
    conn.commit()
    conn.close()
    flash("Reminder added.", "success")
    return redirect(request.referrer or url_for("health"))


@app.route("/reminders/<int:reminder_id>/toggle", methods=["POST"])
@login_required
def reminder_toggle(reminder_id):
    conn = get_db()
    row = conn.execute("SELECT done FROM reminders WHERE id=?", (reminder_id,)).fetchone()
    conn.execute("UPDATE reminders SET done=? WHERE id=?", (0 if row["done"] else 1, reminder_id))
    conn.commit()
    conn.close()
    return redirect(request.referrer or url_for("health"))


# ------------------------------------------------------------------ breeding --
def compatibility_warnings(sire, dam):
    warnings = []
    clears = []
    for trait in CARRIER_TRAITS:
        s, d = (sire[trait] or "").strip(), (dam[trait] or "").strip()
        label = trait.upper() if trait != "vwd" else "vWD"
        if s == "Carrier" and d == "Carrier":
            warnings.append(f"Both carry {label} -- 25% of puppies could be affected. Test all puppies.")
        elif "Affected" in (s, d):
            warnings.append(f"{label}: one parent is Affected -- consult your vet before pairing.")
        elif s and d:
            clears.append(label)
    return warnings, clears


@app.route("/breeding")
@login_required
def breeding():
    conn = get_db()
    heats = conn.execute("""
        SELECT h.*, d.name as dog_name FROM heat_cycles h JOIN dogs d ON d.id = h.dog_id
        ORDER BY h.start_date DESC LIMIT 6
    """).fetchall()
    expecting = conn.execute("SELECT * FROM litters WHERE status='Expecting'").fetchall()
    history = conn.execute("""
        SELECT l.*,
            COALESCE((SELECT d.name FROM dogs d WHERE d.id=l.dam_id), l.dam_name_text) as dam_name,
            COALESCE((SELECT d.name FROM dogs d WHERE d.id=l.sire_id), l.sire_name_text) as sire_name
        FROM litters l ORDER BY l.bred_date IS NULL, l.bred_date DESC LIMIT 8
    """).fetchall()
    semen = conn.execute("""
        SELECT s.*, d.name as dog_name FROM semen_inventory s JOIN dogs d ON d.id=s.dog_id ORDER BY s.created_at DESC
    """).fetchall()
    dogs = conn.execute("SELECT * FROM dogs ORDER BY role, name").fetchall()
    conn.close()
    preg = []
    for l in expecting:
        if l["bred_date"]:
            bred = datetime.date.fromisoformat(l["bred_date"])
            day = (datetime.date.today() - bred).days
            due = bred + datetime.timedelta(days=63)
            preg.append(dict(litter=l, day=max(day, 0), due=due))
    return render_template("breeding.html", nav_active="breeding", heats=heats, preg=preg,
                            history=history, semen=semen, dogs=dogs)


@app.route("/breeding/heat/new", methods=["POST"])
@login_required
def heat_new():
    f = request.form
    conn = get_db()
    conn.execute("INSERT INTO heat_cycles (dog_id, start_date, progesterone, notes) VALUES (?,?,?,?)",
                 (f["dog_id"], f["start_date"], f.get("progesterone") or None, f.get("notes")))
    conn.commit()
    conn.close()
    flash("Heat cycle logged.", "success")
    return redirect(url_for("breeding"))


@app.route("/breeding/semen/new", methods=["POST"])
@login_required
def semen_new():
    f = request.form
    conn = get_db()
    conn.execute("""
        INSERT INTO semen_inventory (dog_id, kind, quantity, location, collected_date, notes)
        VALUES (?,?,?,?,?,?)
    """, (f["dog_id"], f["kind"], f.get("quantity") or 1, f.get("location"),
          f.get("collected_date") or None, f.get("notes")))
    conn.commit()
    conn.close()
    flash("Added to the semen bank.", "success")
    return redirect(url_for("breeding"))


@app.route("/breeding/pairing", methods=["GET", "POST"])
@login_required
def breeding_pairing():
    conn = get_db()
    dogs = conn.execute("SELECT * FROM dogs WHERE role != 'Retired' ORDER BY role, name").fetchall()
    result = None
    sire_id = request.values.get("sire_id", type=int)
    dam_id = request.values.get("dam_id", type=int)
    if sire_id and dam_id:
        sire = conn.execute("SELECT * FROM dogs WHERE id=?", (sire_id,)).fetchone()
        dam = conn.execute("SELECT * FROM dogs WHERE id=?", (dam_id,)).fetchone()
        if sire and dam:
            warnings, clears = compatibility_warnings(sire, dam)
            result = dict(sire=sire, dam=dam, warnings=warnings, clears=clears)
    if request.method == "POST" and request.form.get("action") == "save_litter":
        f = request.form
        cur = conn.execute("""
            INSERT INTO litters (litter_name, sire_id, dam_id, breed, status, coi_percent, coi_notes)
            VALUES (?,?,?,?,?,?,?)
        """, (f["litter_name"], sire_id, dam_id, f.get("breed"), "Planned",
              f.get("coi_percent") or None, f.get("coi_notes")))
        litter_id = cur.lastrowid
        conn.commit()
        conn.close()
        flash("Planned litter created from this pairing.", "success")
        return redirect(url_for("litter_detail", litter_id=litter_id))
    conn.close()
    return render_template("breeding_pairing.html", nav_active="breeding", dogs=dogs, result=result,
                            sire_id=sire_id, dam_id=dam_id)


# ------------------------------------------------------------------ matching --
def score_application(app_row, puppy_row):
    score = 0
    reasons = []
    if app_row["gender_preference"] and app_row["gender_preference"] != "Don't care":
        if app_row["gender_preference"] == puppy_row["sex"]:
            score += 40
            reasons.append(f"Wants a {puppy_row['sex'].lower()}")
        else:
            score -= 20
    else:
        score += 20
        reasons.append("No gender preference")
    choices = " ".join(filter(None, [app_row["puppy_choice_1"], app_row["puppy_choice_2"], app_row["puppy_choice_3"]]))
    if puppy_row["name"] and puppy_row["name"] in choices:
        score += 35
        reasons.append("Named this puppy as a choice")
    if app_row["timeframe"] in ("Immediate", "0-3 months"):
        score += 15
        reasons.append("Ready now")
    if puppy_row["status"] == "Available":
        score += 10
    return max(min(score, 99), 5), reasons


@app.route("/matching", methods=["GET"])
@login_required
def matching():
    conn = get_db()
    applications = conn.execute(
        "SELECT * FROM applications WHERE status IN ('New','Screening','Approved') ORDER BY submitted_at DESC"
    ).fetchall()
    app_id = request.args.get("application_id", type=int)
    chosen = None
    matches = []
    if app_id:
        chosen = conn.execute("SELECT * FROM applications WHERE id=?", (app_id,)).fetchone()
        puppies = conn.execute("""
            SELECT p.*, l.litter_name FROM puppies p JOIN litters l ON l.id=p.litter_id
            WHERE p.status IN ('Available','On Hold') ORDER BY p.name
        """).fetchall()
        for p in puppies:
            score, reasons = score_application(chosen, p)
            matches.append(dict(puppy=p, score=score, reasons=reasons))
        matches.sort(key=lambda m: -m["score"])
    conn.close()
    return render_template("matching.html", nav_active="matching", applications=applications,
                            chosen=chosen, matches=matches)


# ------------------------------------------------------------------- notes --
@app.route("/notes/new", methods=["POST"])
@login_required
def note_new():
    f = request.form
    conn = get_db()
    conn.execute("INSERT INTO notes (entity_type, entity_id, body, due_date) VALUES (?,?,?,?)",
                 (f["entity_type"], f["entity_id"], f["body"], f.get("due_date") or None))
    conn.commit()
    conn.close()
    return redirect(request.referrer or url_for("dashboard"))


@app.route("/notes/<int:note_id>/toggle", methods=["POST"])
@login_required
def note_toggle(note_id):
    conn = get_db()
    row = conn.execute("SELECT done FROM notes WHERE id=?", (note_id,)).fetchone()
    conn.execute("UPDATE notes SET done=? WHERE id=?", (0 if row["done"] else 1, note_id))
    conn.commit()
    conn.close()
    return redirect(request.referrer or url_for("dashboard"))


# --------------------------------------------------------------------- documents --
@app.route("/documents", methods=["GET", "POST"])
@login_required
def documents():
    conn = get_db()
    if request.method == "POST":
        f = request.form
        fn = save_upload(request.files.get("file"), "documents", "doc")
        if fn:
            conn.execute("""
                INSERT INTO documents (entity_type, entity_id, title, category, filename)
                VALUES (?,?,?,?,?)
            """, (f.get("entity_type", "general"), f.get("entity_id") or None, f["title"],
                  f.get("category"), fn))
            conn.commit()
            flash("Document uploaded to the vault.", "success")
        conn.close()
        return redirect(request.referrer or url_for("documents"))
    docs = conn.execute("SELECT * FROM documents ORDER BY uploaded_at DESC").fetchall()
    conn.close()
    return render_template("documents.html", nav_active="documents", docs=docs)


@app.route("/documents/<int:doc_id>/delete", methods=["POST"])
@login_required
def document_delete(doc_id):
    conn = get_db()
    conn.execute("DELETE FROM documents WHERE id=?", (doc_id,))
    conn.commit()
    conn.close()
    return redirect(request.referrer or url_for("documents"))


# --------------------------------------------------------------------- business --
@app.route("/business", methods=["GET"])
@login_required
def business():
    conn = get_db()
    revenue_mtd = conn.execute("""
        SELECT COALESCE(SUM(deposit_paid),0) s FROM reservations
        WHERE strftime('%Y-%m', created_at) = strftime('%Y-%m', 'now')
    """).fetchone()["s"]
    paid_invoices = conn.execute("SELECT COALESCE(SUM(amount),0) s FROM invoices WHERE status='Paid'").fetchone()["s"]
    due_invoices = conn.execute("SELECT COALESCE(SUM(amount),0) s FROM invoices WHERE status='Due'").fetchone()["s"]
    expenses_total = conn.execute("SELECT COALESCE(SUM(amount),0) s FROM expenses").fetchone()["s"]
    expenses_mtd = conn.execute("""
        SELECT COALESCE(SUM(amount),0) s FROM expenses WHERE strftime('%Y-%m', expense_date) = strftime('%Y-%m', 'now')
    """).fetchone()["s"]
    ar = conn.execute("SELECT COALESCE(SUM(balance_due),0) s FROM reservations").fetchone()["s"]
    litters = conn.execute("SELECT * FROM litters ORDER BY dob IS NULL, dob DESC").fetchall()
    profit_by_litter = []
    for l in litters:
        rev = conn.execute("""
            SELECT COALESCE(SUM(r.total_price),0) s FROM reservations r JOIN puppies p ON p.id=r.puppy_id
            WHERE p.litter_id=?
        """, (l["id"],)).fetchone()["s"]
        exp = conn.execute("SELECT COALESCE(SUM(amount),0) s FROM expenses WHERE litter_id=?", (l["id"],)).fetchone()["s"]
        profit_by_litter.append(dict(litter=l, revenue=rev, expenses=exp, profit=rev - exp))
    sources = conn.execute("""
        SELECT how_heard, COUNT(*) c FROM applications WHERE how_heard IS NOT NULL AND how_heard != ''
        GROUP BY how_heard ORDER BY c DESC
    """).fetchall()
    total_leads = sum(s["c"] for s in sources) or 1
    expense_rows = conn.execute("SELECT * FROM expenses ORDER BY expense_date DESC LIMIT 10").fetchall()
    conn.close()
    return render_template("business.html", nav_active="business", revenue_mtd=revenue_mtd,
                            paid_invoices=paid_invoices, due_invoices=due_invoices,
                            expenses_total=expenses_total, expenses_mtd=expenses_mtd, ar=ar,
                            profit_by_litter=profit_by_litter, sources=sources, total_leads=total_leads,
                            expense_rows=expense_rows)


def _fmt_metric(value, kind):
    if kind == "money":
        return f"${value:,.0f}"
    if kind == "percent":
        return f"{value:.1f}%"
    if kind == "decimal1":
        return f"{value:.1f}"
    return f"{value:g}"  # plain number -- 5 not 5.0


def _metric_row(label, actual, target, kind):
    diff = actual - target
    return dict(
        label=label,
        actual=_fmt_metric(actual, kind),
        target=_fmt_metric(target, kind),
        variance=("(" + _fmt_metric(abs(diff), kind) + ")") if diff < 0 else _fmt_metric(diff, kind),
        variance_positive=diff >= 0,
    )


# Lifetime actuals are placeholders for now -- same pattern as the dashboard's
# YTD/Lifetime sales metrics. Tara/Tom can send updated numbers anytime;
# targets are the goals they've set for the business.
BUSINESS_METRICS = [
    ("Financial", [
        ("Average Puppy Selling Price", 3250, 3000, "money"),
        ("Revenue per Litter", 13000, 12500, "money"),
        ("Gross Profit per Litter", 7800, 7500, "money"),
        ("Revenue per Puppy Born", 2000, 2200, "money"),
        ("Gross Profit per Puppy", 2000, 2000, "money"),
        ("Revenue per Puppy -- Female", 3500, 3000, "money"),
        ("Revenue per Puppy -- Male", 2500, 2500, "money"),
        ("Gross Profit per Puppy -- Female", 2100, 2000, "money"),
        ("Gross Profit per Puppy -- Male", 1500, 1500, "money"),
        ("Cost per Puppy", 750, 750, "money"),
        ("Veterinary Cost per Puppy", 500, 500, "money"),
        ("Customer Acquisition Cost", 500, 500, "money"),
        ("Deposit Conversion Rate", 50.0, 40.0, "percent"),
        ("Waitlist Conversion Rate", 50.0, 60.0, "percent"),
        ("Litters per Year", 5, 5, "int"),
    ]),
    ("Demand", [
        ("Waitlist Size (# of Litters)", 1, 1, "int"),
        ("Months of Demand", 4.2, 4, "decimal1"),
        ("Pre-Birth Placement %", 50.0, 50.0, "percent"),
    ]),
    ("Breeding", [
        ("Average Litter Size", 5, 5, "int"),
        ("Live Birth Rate", 98.0, 95.0, "percent"),
        ("Puppy Survival Rate", 98.0, 95.0, "percent"),
        ("Successful Pregnancy Rate", 80.0, 85.0, "percent"),
        ("Dam Litter Frequency/Year", 1.5, 1.0, "decimal1"),
    ]),
    ("Health", [
        ("Genetic Testing Compliance", 98.0, 100.0, "percent"),
        ("Health Screening Compliance", 98.0, 100.0, "percent"),
    ]),
]


@app.route("/business/metrics")
@login_required
def business_metrics():
    sections = [
        dict(name=name, rows=[_metric_row(label, actual, target, kind)
                               for label, actual, target, kind in rows])
        for name, rows in BUSINESS_METRICS
    ]
    return render_template("business_metrics.html", nav_active="business_metrics", sections=sections)


@app.route("/expenses/new", methods=["POST"])
@login_required
def expense_new():
    f = request.form
    conn = get_db()
    conn.execute("""
        INSERT INTO expenses (category, description, amount, expense_date, litter_id)
        VALUES (?,?,?,?,?)
    """, (f["category"], f.get("description"), f["amount"], f["expense_date"], f.get("litter_id") or None))
    conn.commit()
    conn.close()
    flash("Expense logged.", "success")
    return redirect(url_for("business"))


# -------------------------------------------------------------------- marketing --
@app.route("/marketing")
@login_required
def marketing():
    conn = get_db()
    available_count = conn.execute("SELECT COUNT(*) c FROM puppies WHERE status='Available'").fetchone()["c"]
    campaigns = conn.execute("SELECT * FROM campaigns ORDER BY created_at DESC").fetchall()
    referrals = conn.execute("""
        SELECT referral_source, COUNT(*) c FROM applications
        WHERE referral_source IS NOT NULL AND referral_source != '' GROUP BY referral_source ORDER BY c DESC
    """).fetchall()
    waitlist_total = conn.execute("SELECT COALESCE(SUM(waitlist_count),0) s FROM litters").fetchone()["s"]
    conn.close()
    return render_template("marketing.html", nav_active="marketing", available_count=available_count,
                            campaigns=campaigns, referrals=referrals, waitlist_total=waitlist_total)


@app.route("/campaigns/new", methods=["POST"])
@login_required
def campaign_new():
    f = request.form
    conn = get_db()
    conn.execute("""
        INSERT INTO campaigns (channel, title, body, status, scheduled_for)
        VALUES (?,?,?,?,?)
    """, (f["channel"], f["title"], f.get("body"), f.get("status", "Draft"), f.get("scheduled_for") or None))
    conn.commit()
    conn.close()
    flash("Campaign saved.", "success")
    return redirect(url_for("marketing"))


@app.route("/campaigns/<int:campaign_id>/mark-sent", methods=["POST"])
@login_required
def campaign_mark_sent(campaign_id):
    conn = get_db()
    conn.execute("UPDATE campaigns SET status='Sent', sent_at=datetime('now') WHERE id=?", (campaign_id,))
    conn.commit()
    conn.close()
    return redirect(url_for("marketing"))


# --------------------------------------------------------------- our dogs --
@app.route("/our-dogs")
def our_dogs_public():
    conn = get_db()
    studs = conn.execute("SELECT * FROM dogs WHERE role='Stud' ORDER BY name").fetchall()
    dams = conn.execute("SELECT * FROM dogs WHERE role='Dam' ORDER BY name").fetchall()
    conn.close()
    return render_template("our_dogs.html", studs=studs, dams=dams, pub_active="our_dogs")


# ------------------------------------------------------------- guardian program --
@app.route("/guardian")
def guardian_public():
    conn = get_db()
    guardians = conn.execute(
        "SELECT * FROM dogs WHERE role='Guardian Home' ORDER BY name"
    ).fetchall()
    conn.close()
    return render_template("guardian.html", guardians=guardians, pub_active="guardian")


# --------------------------------------------------------- pricing & training --
@app.route("/pricing-training")
def pricing_public():
    return render_template("pricing.html", pub_active="pricing")


# --------------------------------------------------------- public puppy listings --
@app.route("/puppies")
def puppies_public():
    conn = get_db()
    litters = conn.execute("""
        SELECT * FROM litters WHERE status IN ('Reserving','Whelped') ORDER BY dob IS NULL, dob DESC
    """).fetchall()
    litter_puppies = {}
    for l in litters:
        litter_puppies[l["id"]] = conn.execute(
            "SELECT * FROM puppies WHERE litter_id=? ORDER BY status, name", (l["id"],)
        ).fetchall()
    conn.close()
    return render_template("puppies_public.html", litters=litters, litter_puppies=litter_puppies,
                            pub_active="puppies")


# ----------------------------------------------------------- future litters --
@app.route("/future-litters")
def future_litters_public():
    conn = get_db()
    litters = conn.execute("""
        SELECT * FROM litters WHERE status IN ('Planned','Expecting') ORDER BY bred_date IS NULL, bred_date
    """).fetchall()
    conn.close()
    return render_template("future_litters_public.html", litters=litters, pub_active="future")


# ------------------------------------------------------------- applications --
PUPPY_CHOICE_LABEL = "{litter} -- {name} ({sex}, {color})"


@app.route("/apply", methods=["GET", "POST"])
def apply():
    conn = get_db()
    if request.method == "POST":
        f = request.form
        cur = conn.execute("""
            INSERT INTO applications (first_name, last_name, address_line1, address_line2, city,
                state, zip, how_heard, phone, email, preferred_contact, referral_source, timeframe,
                current_dogs, puppy_choice_1, puppy_choice_2, puppy_choice_3, notify_future_litters,
                gender_preference, delivery_pref, training_interest, training_package, contract_agree,
                signature_text, signature_date, comments)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """, (f["first_name"], f["last_name"], f.get("address_line1"), f.get("address_line2"),
              f.get("city"), f.get("state"), f.get("zip"), f.get("how_heard"), f["phone"], f["email"],
              f.get("preferred_contact"), f.get("referral_source"), f.get("timeframe"),
              f.get("current_dogs"), f.get("puppy_choice_1"), f.get("puppy_choice_2"),
              f.get("puppy_choice_3"), 1 if f.get("notify_future_litters") else 0,
              f.get("gender_preference"), f.get("delivery_pref"), f.get("training_interest"),
              f.get("training_package"), 1 if f.get("contract_agree") else 0,
              f.get("signature_text"), f.get("signature_date"), f.get("comments")))
        app_id = cur.lastrowid
        # Arrived via a specific puppy's "Join the Waitlist" link -- the
        # application is also an entry on that puppy's waitlist, in the
        # order applications come in (first come, first served).
        waitlist_puppy_id = f.get("waitlist_puppy_id")
        if waitlist_puppy_id:
            conn.execute("""
                INSERT INTO puppy_waitlist (puppy_id, name, email, phone, notes, application_id)
                VALUES (?,?,?,?,?,?)
            """, (waitlist_puppy_id, f"{f['first_name']} {f['last_name']}", f["email"], f.get("phone"),
                  f.get("comments"), app_id))
        conn.commit()
        conn.close()
        return redirect(url_for("apply_thanks"))

    puppy_rows = conn.execute("""
        SELECT p.id, p.name, p.sex, p.color, p.status, l.litter_name
        FROM puppies p JOIN litters l ON l.id = p.litter_id
        WHERE p.status IN ('Available','On Hold') ORDER BY l.dob, p.name
    """).fetchall()
    puppy_choices = [PUPPY_CHOICE_LABEL.format(litter=r["litter_name"], name=r["name"],
                                                sex=r["sex"], color=r["color"]) for r in puppy_rows]

    # Arrived from a specific puppy's Reserve / Join Waitlist link -- pre-pick
    # that puppy. It may not be in puppy_choices above (e.g. a Sold puppy
    # someone wants to waitlist for), so add it as its own option if needed.
    preselect_id = request.args.get("puppy_id", type=int)
    preselect_choice, waitlist_puppy_id, waitlist_puppy_label = None, None, None
    if preselect_id:
        p = conn.execute("""
            SELECT p.id, p.name, p.sex, p.color, p.status, l.litter_name
            FROM puppies p JOIN litters l ON l.id = p.litter_id WHERE p.id=?
        """, (preselect_id,)).fetchone()
        if p:
            preselect_choice = PUPPY_CHOICE_LABEL.format(litter=p["litter_name"], name=p["name"],
                                                           sex=p["sex"], color=p["color"])
            if preselect_choice not in puppy_choices:
                puppy_choices.insert(0, preselect_choice)
            if request.args.get("waitlist"):
                waitlist_puppy_id = p["id"]
                waitlist_puppy_label = f"{p['name']} ({p['litter_name']})"
    conn.close()
    return render_template("apply.html", puppy_choices=puppy_choices, today=datetime.date.today().isoformat(),
                            pub_active="apply", preselect_choice=preselect_choice,
                            waitlist_puppy_id=waitlist_puppy_id, waitlist_puppy_label=waitlist_puppy_label)


@app.route("/apply/thanks")
def apply_thanks():
    return render_template("apply_thanks.html", pub_active="apply")


# ------------------------------------------------------- schedule a meeting --
@app.route("/schedule")
def schedule_index():
    conn = get_db()
    litters = conn.execute("""
        SELECT DISTINCT l.* FROM litters l JOIN puppies p ON p.litter_id = l.id
        ORDER BY l.dob IS NULL, l.dob DESC
    """).fetchall()
    litter_puppies = {}
    for l in litters:
        litter_puppies[l["id"]] = conn.execute(
            "SELECT * FROM puppies WHERE litter_id=? ORDER BY (status != 'Available'), name", (l["id"],)
        ).fetchall()
    conn.close()
    return render_template("schedule_index.html", litters=litters, litter_puppies=litter_puppies,
                            pub_active="schedule")


@app.route("/schedule/puppy/<int:puppy_id>", methods=["GET", "POST"])
def schedule_puppy(puppy_id):
    conn = get_db()
    p = conn.execute("""
        SELECT p.*, l.litter_name FROM puppies p JOIN litters l ON l.id = p.litter_id WHERE p.id = ?
    """, (puppy_id,)).fetchone()
    if not p:
        conn.close()
        abort(404)
    if request.method == "POST":
        f = request.form
        conn.execute("""
            INSERT INTO meeting_requests (puppy_id, name, email, phone, requested_date, requested_time, notes)
            VALUES (?,?,?,?,?,?,?)
        """, (puppy_id, f["name"], f["email"], f.get("phone"), f["requested_date"], f["requested_time"],
              f.get("notes")))
        conn.commit()
        conn.close()
        return redirect(url_for("schedule_thanks"))
    conn.close()
    return render_template("schedule_form.html", pub_active="schedule", puppy=p, litter=None,
                            today=datetime.date.today().isoformat())


@app.route("/schedule/litter/<int:litter_id>", methods=["GET", "POST"])
def schedule_litter(litter_id):
    conn = get_db()
    l = conn.execute("SELECT * FROM litters WHERE id = ?", (litter_id,)).fetchone()
    if not l:
        conn.close()
        abort(404)
    if request.method == "POST":
        f = request.form
        conn.execute("""
            INSERT INTO meeting_requests (litter_id, name, email, phone, requested_date, requested_time, notes)
            VALUES (?,?,?,?,?,?,?)
        """, (litter_id, f["name"], f["email"], f.get("phone"), f["requested_date"], f["requested_time"],
              f.get("notes")))
        conn.commit()
        conn.close()
        return redirect(url_for("schedule_thanks"))
    conn.close()
    return render_template("schedule_form.html", pub_active="schedule", puppy=None, litter=l,
                            today=datetime.date.today().isoformat())


@app.route("/schedule/thanks")
def schedule_thanks():
    return render_template("schedule_thanks.html", pub_active="schedule")


@app.route("/applications")
@login_required
def applications_list():
    conn = get_db()
    status = request.args.get("status", "")
    if status:
        rows = conn.execute("SELECT * FROM applications WHERE status=? ORDER BY submitted_at DESC", (status,)).fetchall()
    else:
        rows = conn.execute("SELECT * FROM applications ORDER BY submitted_at DESC").fetchall()
    conn.close()
    return render_template("applications_list.html", nav_active="applications", applications=rows, filter_status=status)


@app.route("/applications/<int:app_id>", methods=["GET", "POST"])
@login_required
def application_detail(app_id):
    conn = get_db()
    if request.method == "POST":
        conn.execute("UPDATE applications SET status=?, star_rating=? WHERE id=?",
                     (request.form["status"], request.form.get("star_rating", 0), app_id))
        conn.commit()
        flash("Application updated.", "success")
    row = conn.execute("SELECT * FROM applications WHERE id=?", (app_id,)).fetchone()
    notes = conn.execute(
        "SELECT * FROM notes WHERE entity_type='application' AND entity_id=? ORDER BY done, due_date IS NULL, due_date",
        (app_id,)
    ).fetchall()
    conn.close()
    if not row:
        abort(404)
    return render_template("application_detail.html", nav_active="applications", a=row, notes=notes)


# -------------------------------------------------------- meeting requests --
@app.route("/meeting-requests")
@login_required
def meeting_requests_list():
    conn = get_db()
    rows = conn.execute("""
        SELECT m.*, p.name as puppy_name, COALESCE(pl.litter_name, ll.litter_name) as litter_name
        FROM meeting_requests m
        LEFT JOIN puppies p ON p.id = m.puppy_id
        LEFT JOIN litters pl ON pl.id = p.litter_id
        LEFT JOIN litters ll ON ll.id = m.litter_id
        ORDER BY m.status='Requested' DESC, m.requested_date, m.requested_time
    """).fetchall()
    conn.close()
    return render_template("meeting_requests_list.html", nav_active="meeting_requests", requests=rows)


@app.route("/meeting-requests/<int:req_id>/update", methods=["POST"])
@login_required
def meeting_request_update(req_id):
    conn = get_db()
    conn.execute("UPDATE meeting_requests SET status=? WHERE id=?", (request.form["status"], req_id))
    conn.commit()
    conn.close()
    flash("Meeting request updated.", "success")
    return redirect(url_for("meeting_requests_list"))


@app.route("/meeting-requests/<int:req_id>/delete", methods=["POST"])
@login_required
def meeting_request_delete(req_id):
    conn = get_db()
    conn.execute("DELETE FROM meeting_requests WHERE id=?", (req_id,))
    conn.commit()
    conn.close()
    flash("Meeting request removed.", "info")
    return redirect(url_for("meeting_requests_list"))


# --------------------------------------------------------------- waitlist --
@app.route("/waitlist")
@login_required
def waitlist_admin():
    conn = get_db()
    puppies = conn.execute("""
        SELECT DISTINCT p.id, p.name, p.status, l.litter_name
        FROM puppy_waitlist w JOIN puppies p ON p.id = w.puppy_id JOIN litters l ON l.id = p.litter_id
        ORDER BY l.dob IS NULL, l.dob DESC, p.name
    """).fetchall()
    groups = []
    for p in puppies:
        entries = conn.execute(
            "SELECT * FROM puppy_waitlist WHERE puppy_id=? ORDER BY created_at", (p["id"],)
        ).fetchall()
        groups.append(dict(puppy=p, entries=entries))
    conn.close()
    return render_template("waitlist_admin.html", nav_active="waitlist", groups=groups)


@app.route("/waitlist/<int:entry_id>/delete", methods=["POST"])
@login_required
def waitlist_entry_delete(entry_id):
    conn = get_db()
    conn.execute("DELETE FROM puppy_waitlist WHERE id=?", (entry_id,))
    conn.commit()
    conn.close()
    flash("Removed from waitlist.", "info")
    return redirect(url_for("waitlist_admin"))


# ------------------------------------------------------------------ contact --
@app.route("/contact", methods=["GET", "POST"])
def contact():
    if request.method == "POST":
        f = request.form
        conn = get_db()
        conn.execute("""
            INSERT INTO contacts (name, email, phone, city_state, subject, how_heard, message)
            VALUES (?,?,?,?,?,?,?)
        """, (f["name"], f["email"], f.get("phone"), f.get("city_state"), f.get("subject"),
              f.get("how_heard"), f.get("message")))
        conn.commit()
        conn.close()
        return redirect(url_for("contact_thanks"))
    return render_template("contact.html", pub_active="contact")


@app.route("/contact/thanks")
def contact_thanks():
    return render_template("contact_thanks.html", pub_active="contact")


@app.route("/contacts")
@login_required
def contacts_list():
    conn = get_db()
    rows = conn.execute("SELECT * FROM contacts ORDER BY submitted_at DESC").fetchall()
    conn.close()
    return render_template("contacts_list.html", nav_active="contacts", contacts=rows)


@app.route("/contacts/<int:contact_id>", methods=["GET", "POST"])
@login_required
def contact_detail(contact_id):
    conn = get_db()
    if request.method == "POST":
        conn.execute("UPDATE contacts SET status=? WHERE id=?", (request.form["status"], contact_id))
        conn.commit()
        flash("Contact updated.", "success")
    row = conn.execute("SELECT * FROM contacts WHERE id=?", (contact_id,)).fetchone()
    conn.close()
    if not row:
        abort(404)
    return render_template("contact_detail.html", nav_active="contacts", c=row)


# ------------------------------------------------------------- reservations --
@app.route("/reservations")
@login_required
def reservations_list():
    conn = get_db()
    rows = conn.execute("""
        SELECT r.*, p.name as puppy_name, l.litter_name
        FROM reservations r
        JOIN puppies p ON p.id = r.puppy_id
        JOIN litters l ON l.id = p.litter_id
        ORDER BY r.created_at DESC
    """).fetchall()
    conn.close()
    return render_template("reservations_list.html", nav_active="reservations", reservations=rows)


@app.route("/reservations/new", methods=["GET", "POST"])
@login_required
def reservation_new():
    conn = get_db()
    if request.method == "POST":
        f = request.form
        token = new_token()
        cur = conn.execute("""
            INSERT INTO reservations (puppy_id, buyer_name, buyer_email, buyer_phone, portal_token,
                total_price, deposit_paid, balance_due, pickup_date)
            VALUES (?,?,?,?,?,?,?,?,?)
        """, (f["puppy_id"], f["buyer_name"], f["buyer_email"], f.get("buyer_phone"), token,
              f.get("total_price") or 0, f.get("deposit_paid") or 0,
              float(f.get("total_price") or 0) - float(f.get("deposit_paid") or 0),
              f.get("pickup_date") or None))
        conn.execute("UPDATE puppies SET status='Reserved' WHERE id=?", (f["puppy_id"],))
        res_id = cur.lastrowid
        conn.commit()
        conn.close()
        flash("Reservation created -- portal link is ready to share.", "success")
        return redirect(url_for("reservation_detail", res_id=res_id))
    puppies = conn.execute("""
        SELECT p.id, p.name, p.price, l.litter_name FROM puppies p
        JOIN litters l ON l.id = p.litter_id WHERE p.status != 'Sold' ORDER BY l.dob, p.name
    """).fetchall()
    preselect = request.args.get("puppy_id", type=int)
    conn.close()
    return render_template("reservation_form.html", nav_active="reservations", puppies=puppies, preselect=preselect)


@app.route("/reservations/<int:res_id>", methods=["GET"])
@login_required
def reservation_detail(res_id):
    conn = get_db()
    r = conn.execute("""
        SELECT r.*, p.name as puppy_name, p.color, p.sex, l.litter_name, l.dob as litter_dob
        FROM reservations r JOIN puppies p ON p.id = r.puppy_id JOIN litters l ON l.id = p.litter_id
        WHERE r.id = ?
    """, (res_id,)).fetchone()
    if not r:
        abort(404)
    updates = conn.execute("SELECT * FROM updates WHERE reservation_id=? ORDER BY created_at DESC", (res_id,)).fetchall()
    messages = conn.execute("SELECT * FROM messages WHERE reservation_id=? ORDER BY created_at", (res_id,)).fetchall()
    invoices = conn.execute("SELECT * FROM invoices WHERE reservation_id=? ORDER BY created_at", (res_id,)).fetchall()
    notes = conn.execute(
        "SELECT * FROM notes WHERE entity_type='reservation' AND entity_id=? ORDER BY done, due_date IS NULL, due_date",
        (res_id,)
    ).fetchall()
    conn.close()
    lifetime = None
    if r["litter_dob"]:
        dob = datetime.date.fromisoformat(r["litter_dob"])
        today = datetime.date.today()
        next_bday = dob.replace(year=today.year)
        if next_bday < today:
            next_bday = dob.replace(year=today.year + 1)
        lifetime = dict(age=age_str(r["litter_dob"]), next_birthday=next_bday)
    return render_template("reservation_detail.html", nav_active="reservations", r=r,
                            updates=updates, messages=messages, invoices=invoices, notes=notes,
                            lifetime=lifetime)


@app.route("/reservations/<int:res_id>/update", methods=["POST"])
@login_required
def reservation_update(res_id):
    f = request.form
    conn = get_db()
    total = float(f.get("total_price") or 0)
    deposit = float(f.get("deposit_paid") or 0)
    conn.execute("""
        UPDATE reservations SET total_price=?, deposit_paid=?, balance_due=?, contract_signed=?,
            health_guarantee_ready=?, pickup_date=?, pickup_notes=?, feeding_schedule=?,
            training_notes=?, registration_status=?
        WHERE id=?
    """, (total, deposit, max(total - deposit, 0), 1 if f.get("contract_signed") else 0,
          1 if f.get("health_guarantee_ready") else 0, f.get("pickup_date") or None,
          f.get("pickup_notes"), f.get("feeding_schedule"), f.get("training_notes"),
          f.get("registration_status", "Pending"), res_id))
    conn.commit()
    conn.close()
    flash("Reservation updated.", "success")
    return redirect(url_for("reservation_detail", res_id=res_id))


@app.route("/reservations/<int:res_id>/go-home/send", methods=["POST"])
@login_required
def reservation_go_home_send(res_id):
    conn = get_db()
    conn.execute("UPDATE reservations SET go_home_sent=1 WHERE id=?", (res_id,))
    conn.commit()
    conn.close()
    flash("Go-home binder is now visible on the family's portal.", "success")
    return redirect(url_for("reservation_detail", res_id=res_id))


@app.route("/reservations/<int:res_id>/invoices/new", methods=["POST"])
@login_required
def invoice_new(res_id):
    f = request.form
    conn = get_db()
    conn.execute("""
        INSERT INTO invoices (reservation_id, description, amount, status, due_date)
        VALUES (?,?,?,?,?)
    """, (res_id, f["description"], f["amount"], f.get("status", "Due"), f.get("due_date") or None))
    conn.commit()
    conn.close()
    flash("Invoice created.", "success")
    return redirect(url_for("reservation_detail", res_id=res_id))


@app.route("/invoices/<int:invoice_id>/mark-paid", methods=["POST"])
@login_required
def invoice_mark_paid(invoice_id):
    conn = get_db()
    row = conn.execute("SELECT reservation_id FROM invoices WHERE id=?", (invoice_id,)).fetchone()
    conn.execute("UPDATE invoices SET status='Paid', paid_at=datetime('now') WHERE id=?", (invoice_id,))
    conn.commit()
    conn.close()
    flash("Invoice marked paid.", "success")
    return redirect(url_for("reservation_detail", res_id=row["reservation_id"]))


@app.route("/reservations/<int:res_id>/updates/new", methods=["POST"])
@login_required
def reservation_update_new(res_id):
    conn = get_db()
    fn = save_upload(request.files.get("photo"), "updates", f"res{res_id}")
    conn.execute("INSERT INTO updates (reservation_id, body, photo_filename) VALUES (?,?,?)",
                 (res_id, request.form["body"], fn))
    conn.commit()
    conn.close()
    flash("Update posted to the family's portal.", "success")
    return redirect(url_for("reservation_detail", res_id=res_id))


def _delete_update(update_id, reservation_id):
    """Delete an update row (and its photo file, if any) -- shared by the
    breeder-side and portal-side delete routes. Caller has already verified
    the update belongs to the given reservation."""
    conn = get_db()
    row = conn.execute("SELECT photo_filename FROM updates WHERE id=? AND reservation_id=?",
                        (update_id, reservation_id)).fetchone()
    if row:
        if row["photo_filename"]:
            path = os.path.join(UPLOAD_DIR, row["photo_filename"])
            if os.path.exists(path):
                try:
                    os.remove(path)
                except OSError:
                    pass
        conn.execute("DELETE FROM updates WHERE id=? AND reservation_id=?", (update_id, reservation_id))
        conn.commit()
    conn.close()
    return bool(row)


@app.route("/reservations/<int:res_id>/updates/<int:update_id>/delete", methods=["POST"])
@login_required
def reservation_update_delete(res_id, update_id):
    _delete_update(update_id, res_id)
    flash("Update removed.", "info")
    return redirect(url_for("reservation_detail", res_id=res_id))


@app.route("/reservations/<int:res_id>/messages/new", methods=["POST"])
@login_required
def reservation_message_new(res_id):
    conn = get_db()
    conn.execute("INSERT INTO messages (reservation_id, sender, body) VALUES (?, 'breeder', ?)",
                 (res_id, request.form["body"]))
    conn.commit()
    conn.close()
    return redirect(url_for("reservation_detail", res_id=res_id))


# --------------------------------------------- customer portal accounts (admin) --
@app.route("/customer-portal")
@login_required
def customer_portal_list():
    conn = get_db()
    rows = conn.execute("""
        SELECT r.*, p.name as puppy_name, l.litter_name
        FROM reservations r
        JOIN puppies p ON p.id = r.puppy_id
        JOIN litters l ON l.id = p.litter_id
        ORDER BY r.created_at DESC
    """).fetchall()
    conn.close()
    return render_template("customer_portal_list.html", nav_active="portal_accounts", accounts=rows)


@app.route("/customer-portal/<int:res_id>/edit", methods=["GET", "POST"])
@login_required
def customer_portal_edit(res_id):
    conn = get_db()
    if request.method == "POST":
        f = request.form
        conn.execute(
            "UPDATE reservations SET buyer_name=?, buyer_email=?, buyer_phone=? WHERE id=?",
            (f["buyer_name"], f["buyer_email"], f.get("buyer_phone"), res_id),
        )
        conn.commit()
        conn.close()
        flash("Customer portal account updated.", "success")
        return redirect(url_for("customer_portal_edit", res_id=res_id))
    r = conn.execute("""
        SELECT r.*, p.name as puppy_name, l.litter_name
        FROM reservations r JOIN puppies p ON p.id = r.puppy_id JOIN litters l ON l.id = p.litter_id
        WHERE r.id = ?
    """, (res_id,)).fetchone()
    conn.close()
    if not r:
        abort(404)
    return render_template("customer_portal_edit.html", nav_active="portal_accounts", r=r)


@app.route("/customer-portal/<int:res_id>/regenerate-token", methods=["POST"])
@login_required
def customer_portal_regenerate_token(res_id):
    conn = get_db()
    conn.execute("UPDATE reservations SET portal_token=? WHERE id=?", (new_token(), res_id))
    conn.commit()
    conn.close()
    flash("New portal link generated -- the old link no longer works.", "success")
    return redirect(url_for("customer_portal_edit", res_id=res_id))


@app.route("/customer-portal/<int:res_id>/delete", methods=["POST"])
@login_required
def customer_portal_delete(res_id):
    conn = get_db()
    r = conn.execute("SELECT puppy_id FROM reservations WHERE id=?", (res_id,)).fetchone()
    if r:
        # updates/messages/invoices cascade via FK; notes use the generic
        # entity_type/entity_id pattern so they need a manual cleanup.
        conn.execute("DELETE FROM notes WHERE entity_type='reservation' AND entity_id=?", (res_id,))
        conn.execute("DELETE FROM reservations WHERE id=?", (res_id,))
        # Free the puppy back up -- but don't touch it if it's already marked
        # Sold through some other flow.
        conn.execute(
            "UPDATE puppies SET status='Available' WHERE id=? AND status='Reserved'",
            (r["puppy_id"],),
        )
        conn.commit()
        flash("Customer portal account deleted.", "info")
    conn.close()
    return redirect(url_for("customer_portal_list"))


# ------------------------------------------------------------ customer portal --
@app.route("/portal-login", methods=["GET", "POST"])
def portal_login():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        conn = get_db()
        matches = conn.execute("""
            SELECT r.portal_token, p.name as puppy_name, l.litter_name
            FROM reservations r JOIN puppies p ON p.id = r.puppy_id JOIN litters l ON l.id = p.litter_id
            WHERE lower(r.buyer_email) = ?
            ORDER BY r.created_at DESC
        """, (email,)).fetchall()
        conn.close()
        if not matches:
            flash("We couldn't find a reservation with that email. Please contact us and we'll help you out.", "error")
            return redirect(url_for("portal_login"))
        if len(matches) == 1:
            return redirect(url_for("portal", token=matches[0]["portal_token"]))
        return render_template("portal_login.html", pub_active="portal_login", matches=matches)
    return render_template("portal_login.html", pub_active="portal_login", matches=None)


@app.route("/portal/<token>")
def portal(token):
    conn = get_db()
    r = conn.execute("""
        SELECT r.*, p.name as puppy_name, p.color, p.sex, p.current_weight_lbs, p.photo_filename as puppy_photo,
               l.litter_name, l.dob as litter_dob
        FROM reservations r JOIN puppies p ON p.id = r.puppy_id JOIN litters l ON l.id = p.litter_id
        WHERE r.portal_token = ?
    """, (token,)).fetchone()
    if not r:
        abort(404)
    updates = conn.execute("SELECT * FROM updates WHERE reservation_id=? ORDER BY created_at DESC", (r["id"],)).fetchall()
    messages = conn.execute("SELECT * FROM messages WHERE reservation_id=? ORDER BY created_at", (r["id"],)).fetchall()
    conn.close()
    days_left = None
    if r["pickup_date"]:
        d = (datetime.date.fromisoformat(r["pickup_date"]) - datetime.date.today()).days
        days_left = d
    lifetime = None
    if r["litter_dob"]:
        dob = datetime.date.fromisoformat(r["litter_dob"])
        today = datetime.date.today()
        next_bday = dob.replace(year=today.year)
        if next_bday < today:
            next_bday = dob.replace(year=today.year + 1)
        lifetime = dict(age=age_str(r["litter_dob"]), next_birthday=next_bday,
                         is_home=(days_left is not None and days_left <= 0))
    photo_updates = [u for u in updates if u["photo_filename"]]
    text_updates = [u for u in updates if not u["photo_filename"]]
    return render_template("portal.html", r=r, updates=updates, photo_updates=photo_updates,
                            text_updates=text_updates, messages=messages, days_left=days_left,
                            token=token, lifetime=lifetime)


@app.route("/portal/<token>/updates/<int:update_id>/delete", methods=["POST"])
def portal_update_delete(token, update_id):
    conn = get_db()
    r = conn.execute("SELECT id FROM reservations WHERE portal_token=?", (token,)).fetchone()
    conn.close()
    if not r:
        abort(404)
    _delete_update(update_id, r["id"])
    return redirect(url_for("portal", token=token))


@app.route("/portal/<token>/messages/new", methods=["POST"])
def portal_message_new(token):
    conn = get_db()
    r = conn.execute("SELECT id FROM reservations WHERE portal_token=?", (token,)).fetchone()
    if not r:
        abort(404)
    conn.execute("INSERT INTO messages (reservation_id, sender, body) VALUES (?, 'buyer', ?)",
                 (r["id"], request.form["body"]))
    conn.commit()
    conn.close()
    return redirect(url_for("portal", token=token))


@app.route("/portal/<token>/sign", methods=["POST"])
def portal_sign(token):
    conn = get_db()
    r = conn.execute("SELECT id FROM reservations WHERE portal_token=?", (token,)).fetchone()
    if not r:
        abort(404)
    conn.execute("""
        UPDATE reservations SET buyer_signature=?, buyer_signature_date=?, contract_signed=1 WHERE id=?
    """, (request.form["buyer_signature"], datetime.date.today().isoformat(), r["id"]))
    conn.commit()
    conn.close()
    flash("Purchase agreement signed -- thank you!", "success")
    return redirect(url_for("portal", token=token))


# --------------------------------------------------------------------- misc --
@app.route("/uploads/<path:filename>")
def uploaded_file(filename):
    return send_from_directory(UPLOAD_DIR, filename)


@app.route("/sw.js")
def service_worker():
    # Served from the root (not /static/sw.js) so its default scope covers
    # the whole site -- required for it to control pages outside /static/.
    resp = send_from_directory(os.path.join(BASE_DIR, "static"), "sw.js")
    resp.headers["Service-Worker-Allowed"] = "/"
    resp.headers["Cache-Control"] = "no-cache"
    return resp


if __name__ == "__main__":
    # Database/upload-dir setup already happened above at import time (so it
    # also runs under gunicorn); this block only starts the local dev server.
    app.run(debug=True, port=5050)
