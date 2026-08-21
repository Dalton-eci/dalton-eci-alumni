from flask import Flask, render_template, request, redirect, url_for, flash, session, send_file, abort
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
import sqlite3
import os
import csv
import io
import secrets
from datetime import datetime, timezone

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "alumni.db")
DATABASE_URL = os.environ.get("DATABASE_URL", "").strip()

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "change-this-secret-key-before-production")
app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
    SESSION_COOKIE_SECURE=os.environ.get("COOKIE_SECURE", "1") == "1",
)

ADMIN_USERNAME = os.environ.get("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD_HASH = os.environ.get("ADMIN_PASSWORD_HASH")
if not ADMIN_PASSWORD_HASH:
    ADMIN_PASSWORD_HASH = generate_password_hash(os.environ.get("ADMIN_PASSWORD", "DaltonECI2026!"))

IS_POSTGRES = DATABASE_URL.startswith("postgres://") or DATABASE_URL.startswith("postgresql://")


def get_db():
    if IS_POSTGRES:
        import psycopg2
        from psycopg2.extras import RealDictCursor
        return psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor, sslmode="require")
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def db_execute(conn, sql, params=()):
    if IS_POSTGRES:
        sql = sql.replace("?", "%s")
    cur = conn.cursor()
    cur.execute(sql, params)
    return cur


def init_db():
    conn = get_db()
    if IS_POSTGRES:
        db_execute(conn, '''
            CREATE TABLE IF NOT EXISTS alumni (
                id BIGSERIAL PRIMARY KEY,
                first_name TEXT NOT NULL,
                last_name TEXT NOT NULL,
                preferred_name TEXT,
                year_started TEXT,
                year_left TEXT,
                email TEXT NOT NULL,
                phone TEXT,
                current_location TEXT,
                occupation TEXT,
                memories TEXT,
                willing_to_support TEXT,
                support_area TEXT,
                consent INTEGER NOT NULL DEFAULT 0,
                membership_fee INTEGER NOT NULL DEFAULT 2000,
                payment_reference TEXT,
                payment_status TEXT NOT NULL DEFAULT 'Pending',
                membership_status TEXT NOT NULL DEFAULT 'Pending Review',
                created_at TEXT NOT NULL,
                updated_at TEXT
            )
        ''')
    else:
        db_execute(conn, '''
            CREATE TABLE IF NOT EXISTS alumni (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                first_name TEXT NOT NULL,
                last_name TEXT NOT NULL,
                preferred_name TEXT,
                year_started TEXT,
                year_left TEXT,
                email TEXT NOT NULL,
                phone TEXT,
                current_location TEXT,
                occupation TEXT,
                memories TEXT,
                willing_to_support TEXT,
                support_area TEXT,
                consent INTEGER NOT NULL DEFAULT 0,
                membership_fee INTEGER NOT NULL DEFAULT 2000,
                payment_reference TEXT,
                payment_status TEXT NOT NULL DEFAULT 'Pending',
                membership_status TEXT NOT NULL DEFAULT 'Pending Review',
                created_at TEXT NOT NULL,
                updated_at TEXT
            )
        ''')
    conn.commit()
    conn.close()


def csrf_token():
    if "csrf_token" not in session:
        session["csrf_token"] = secrets.token_urlsafe(32)
    return session["csrf_token"]


app.jinja_env.globals["csrf_token"] = csrf_token


def validate_csrf():
    token = request.form.get("csrf_token", "")
    if not token or token != session.get("csrf_token"):
        abort(400, description="Invalid form token. Please refresh the page and try again.")


def admin_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get("is_admin"):
            flash("Administrator access is required.", "error")
            return redirect(url_for("admin_login"))
        return view(*args, **kwargs)
    return wrapped


@app.before_request
def ensure_database():
    if not getattr(app, "_database_ready", False):
        init_db()
        app._database_ready = True


@app.route("/health")
def health():
    return {"status": "ok"}, 200


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        validate_csrf()
        first_name = request.form.get("first_name", "").strip()
        last_name = request.form.get("last_name", "").strip()
        email = request.form.get("email", "").strip()
        consent = 1 if request.form.get("consent") == "on" else 0

        if not first_name or not last_name or not email:
            flash("First name, last name, and email are required.", "error")
            return render_template("register.html")
        if not consent:
            flash("Please confirm consent before submitting.", "error")
            return render_template("register.html")

        values = (
            first_name,
            last_name,
            request.form.get("preferred_name", "").strip(),
            request.form.get("year_started", "").strip(),
            request.form.get("year_left", "").strip(),
            email,
            request.form.get("phone", "").strip(),
            request.form.get("current_location", "").strip(),
            request.form.get("occupation", "").strip(),
            request.form.get("memories", "").strip(),
            request.form.get("willing_to_support", "").strip(),
            request.form.get("support_area", "").strip(),
            consent,
            2000,
            request.form.get("payment_reference", "").strip(),
            "Pending",
            "Pending Review",
            datetime.now(timezone.utc).isoformat(timespec="seconds"),
        )
        conn = get_db()
        db_execute(conn, '''
            INSERT INTO alumni (
                first_name, last_name, preferred_name, year_started, year_left,
                email, phone, current_location, occupation, memories,
                willing_to_support, support_area, consent, membership_fee,
                payment_reference, payment_status, membership_status, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', values)
        conn.commit()
        conn.close()
        return redirect(url_for("thank_you"))

    return render_template("register.html")


@app.route("/thank-you")
def thank_you():
    return render_template("thank_you.html")


@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        validate_csrf()
        username = request.form.get("username", "")
        password = request.form.get("password", "")
        if username == ADMIN_USERNAME and check_password_hash(ADMIN_PASSWORD_HASH, password):
            session.clear()
            session["is_admin"] = True
            session["csrf_token"] = secrets.token_urlsafe(32)
            return redirect(url_for("admin_dashboard"))
        flash("Invalid administrator credentials.", "error")
    return render_template("admin_login.html")


@app.route("/admin/logout")
def admin_logout():
    session.clear()
    return redirect(url_for("index"))


@app.route("/admin")
@admin_required
def admin_dashboard():
    q = request.args.get("q", "").strip()
    conn = get_db()
    if q:
        like = f"%{q}%"
        rows = db_execute(conn, '''
            SELECT * FROM alumni
            WHERE first_name LIKE ? OR last_name LIKE ? OR email LIKE ?
               OR year_left LIKE ? OR occupation LIKE ? OR current_location LIKE ?
               OR payment_status LIKE ? OR membership_status LIKE ?
            ORDER BY created_at DESC
        ''', (like, like, like, like, like, like, like, like)).fetchall()
    else:
        rows = db_execute(conn, "SELECT * FROM alumni ORDER BY created_at DESC").fetchall()
    conn.close()
    return render_template("admin_dashboard.html", alumni=rows, q=q)


@app.route("/admin/alumni/<int:alumni_id>")
@admin_required
def admin_alumni_detail(alumni_id):
    conn = get_db()
    person = db_execute(conn, "SELECT * FROM alumni WHERE id = ?", (alumni_id,)).fetchone()
    conn.close()
    if not person:
        flash("Alumni record not found.", "error")
        return redirect(url_for("admin_dashboard"))
    return render_template("admin_detail.html", person=person)


@app.route("/admin/alumni/<int:alumni_id>/status", methods=["POST"])
@admin_required
def admin_update_status(alumni_id):
    validate_csrf()
    payment_status = request.form.get("payment_status", "Pending")
    membership_status = request.form.get("membership_status", "Pending Review")
    allowed_payment = {"Pending", "Verified", "Not Received"}
    allowed_membership = {"Pending Review", "Active", "Inactive", "Declined"}
    if payment_status not in allowed_payment or membership_status not in allowed_membership:
        abort(400)

    conn = get_db()
    db_execute(conn, '''
        UPDATE alumni
        SET payment_status = ?, membership_status = ?, updated_at = ?
        WHERE id = ?
    ''', (payment_status, membership_status, datetime.now(timezone.utc).isoformat(timespec="seconds"), alumni_id))
    conn.commit()
    conn.close()
    flash("Alumni status updated.", "success")
    return redirect(url_for("admin_alumni_detail", alumni_id=alumni_id))


@app.route("/admin/export")
@admin_required
def admin_export():
    conn = get_db()
    rows = db_execute(conn, "SELECT * FROM alumni ORDER BY created_at DESC").fetchall()
    conn.close()
    headers = [
        "id", "first_name", "last_name", "preferred_name", "year_started", "year_left",
        "email", "phone", "current_location", "occupation", "memories", "willing_to_support",
        "support_area", "consent", "membership_fee", "payment_reference", "payment_status",
        "membership_status", "created_at", "updated_at"
    ]
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(headers)
    for row in rows:
        writer.writerow([row[h] for h in headers])
    mem = io.BytesIO(output.getvalue().encode("utf-8"))
    mem.seek(0)
    return send_file(mem, mimetype="text/csv", as_attachment=True, download_name="dalton_eci_alumni.csv")


if __name__ == "__main__":
    init_db()
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=False)
