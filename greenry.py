@app.route("/")
def home():
    @app.route("/google52086bdcf5486b7c.html")
    def google_verification():
        return "google-site-verification: google52086bdcf5486b7c.html"

from flask import Flask, render_template_string, request, redirect, url_for, session, send_file
from datetime import datetime, timedelta
import sqlite3
import random
import time
import os
import shutil
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = "change-this-secret-key"
DB_NAME = "cooperative.db"

ADMIN_PHONE = "08000000000"
ADMIN_PASSWORD = generate_password_hash("admin123")
ADMIN_KEY = "supersecurekey"
CUSTOMER_PASSWORD = "12345"


def get_db():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS staff (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            phone TEXT NOT NULL UNIQUE,
            password TEXT NOT NULL
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS customers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            phone TEXT NOT NULL UNIQUE,
            address TEXT NOT NULL,
            plan TEXT NOT NULL
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS contributions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_id INTEGER NOT NULL,
            customer_name TEXT NOT NULL,
            type TEXT NOT NULL,
            period TEXT NOT NULL,
            amount REAL NOT NULL,
            date TEXT NOT NULL,
            staff TEXT NOT NULL,
            FOREIGN KEY(customer_id) REFERENCES customers(id)
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS loans (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_id INTEGER NOT NULL,
            customer_name TEXT NOT NULL,
            loan_amount REAL NOT NULL,
            amount_owing REAL NOT NULL,
            date_given TEXT NOT NULL,
            note TEXT,
            FOREIGN KEY(customer_id) REFERENCES customers(id)
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        )
    """)

    defaults = {
        "admin_phone": ADMIN_PHONE,
        "admin_password": ADMIN_PASSWORD,
        "admin_key": ADMIN_KEY
    }

    for key, value in defaults.items():
        cur.execute("SELECT key FROM settings WHERE key = ?", (key,))
        if not cur.fetchone():
            cur.execute("INSERT INTO settings (key, value) VALUES (?, ?)", (key, value))

    cur.execute("SELECT id FROM staff WHERE phone = ?", ("08111111111",))
    if not cur.fetchone():
        cur.execute(
            "INSERT INTO staff (name, phone, password) VALUES (?, ?, ?)",
            ("Default Staff", "08111111111", generate_password_hash("staff123"))
        )

    conn.commit()
    conn.close()


otp_store = {}
OTP_EXPIRY_SECONDS = 300


def save_otp(phone, otp):
    otp_store[phone] = {"otp": otp, "expires_at": time.time() + OTP_EXPIRY_SECONDS}


def verify_otp(phone, otp):
    saved = otp_store.get(phone)
    if not saved:
        return False
    if time.time() > saved["expires_at"]:
        del otp_store[phone]
        return False
    if saved["otp"] != otp:
        return False
    del otp_store[phone]
    return True


def auto_backup():
    if not os.path.exists(DB_NAME):
        return
    os.makedirs("backups", exist_ok=True)
    today = datetime.now().strftime("%Y-%m-%d")
    backup_file = os.path.join("backups", f"backup_{today}.db")
    if not os.path.exists(backup_file):
        shutil.copy(DB_NAME, backup_file)


def parse_period_date(period):
    try:
        if " to " in period:
            return datetime.strptime(period.split(" to ")[0], "%Y-%m-%d").date()
        if len(period) == 7:
            return datetime.strptime(period + "-01", "%Y-%m-%d").date()
        return datetime.strptime(period, "%Y-%m-%d").date()
    except Exception:
        return None


def get_customer_status(customer_id, plan):
    conn = get_db()
    records = conn.execute("SELECT * FROM contributions WHERE customer_id = ?", (customer_id,)).fetchall()
    loan_row = conn.execute("SELECT COALESCE(SUM(amount_owing), 0) AS owing FROM loans WHERE customer_id = ?", (customer_id,)).fetchone()
    conn.close()

    owing = loan_row["owing"] if loan_row else 0
    if not records:
        return {"last_payment": "No payment yet", "missed_payment": "Yes", "inactive": "Yes", "eligible": "No", "owing": owing, "trust": "Low"}

    dates = [parse_period_date(row["period"]) for row in records]
    dates = [d for d in dates if d]
    if not dates:
        return {"last_payment": "Unknown", "missed_payment": "Unknown", "inactive": "Unknown", "eligible": "No", "owing": owing, "trust": "Low"}

    today = datetime.now().date()
    first_payment = min(dates)
    last_payment = max(dates)
    days_since = (today - last_payment).days
    active_days = (today - first_payment).days

    if plan == "Daily":
        missed = days_since > 1
    elif plan == "Weekly":
        missed = days_since > 7
    else:
        missed = days_since > 31

    inactive = days_since > 30
    eligible = active_days >= 180 and not inactive and owing == 0

    if eligible and len(records) >= 20:
        trust = "High"
    elif len(records) >= 8 and not inactive:
        trust = "Medium"
    else:
        trust = "Low"

    return {"last_payment": last_payment.strftime("%Y-%m-%d"), "missed_payment": "Yes" if missed else "No", "inactive": "Yes" if inactive else "No", "eligible": "Yes" if eligible else "No", "owing": owing, "trust": trust}

BASE_STYLE = """
<style>
    body { margin: 0; font-family: Arial, sans-serif; background: #f3faf5; color: #123524; }
    .navbar { background: #0f6b3f; color: white; padding: 16px 32px; display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 12px; }
    .navbar a { color: white; text-decoration: none; margin-left: 16px; font-weight: bold; }
    .container { max-width: 1100px; margin: 32px auto; padding: 0 20px; }
    .card { background: white; border-radius: 14px; padding: 24px; box-shadow: 0 8px 24px rgba(0,0,0,0.08); margin-bottom: 24px; }
    .login-box { max-width: 520px; margin: 80px auto; text-align: center; }
    h1, h2, h3 { color: #0f5132; }
    input, select, button { width: 100%; padding: 14px; margin-top: 8px; margin-bottom: 16px; border-radius: 10px; border: 1px solid #b8d8c4; box-sizing: border-box; font-size: 16px; }
    button { background: #0f6b3f; color: white; border: none; cursor: pointer; font-weight: bold; min-height: 48px; }
    button:hover { background: #0b5431; }
    .table-wrap { overflow-x: auto; width: 100%; }
    table { width: 100%; border-collapse: collapse; background: white; min-width: 760px; }
    th, td { padding: 12px; border-bottom: 1px solid #dcefe3; text-align: left; }
    th { background: #e1f3e8; color: #0f5132; }
    .stats { display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 16px; }
    .stat-box { background: white; padding: 22px; border-radius: 14px; box-shadow: 0 8px 24px rgba(0,0,0,0.06); }
    .small-link { color: #0f6b3f; font-weight: bold; text-decoration: none; }
    .login-logo { width: 110px; height: 110px; border-radius: 50%; object-fit: cover; border: 4px solid #0f6b3f; box-shadow: 0 8px 20px rgba(15,107,63,0.25); animation: logoPop 0.8s ease-out; }
    .navbar-logo { width: 42px; height: 42px; border-radius: 50%; object-fit: cover; border: 2px solid white; background: white; }
    @keyframes logoPop { 0% { opacity: 0; transform: scale(0.6) translateY(-20px); } 100% { opacity: 1; transform: scale(1) translateY(0); } }
    @media (max-width: 700px) {
        .container { margin: 18px auto; padding: 0 12px; }
        .card { padding: 16px; }
        .navbar { padding: 14px; }
        .navbar a { display: inline-block; margin: 6px 8px 0 0; }
        h1 { font-size: 24px; }
        h2 { font-size: 20px; }
        .stat-box { padding: 16px; }
    }
</style>
"""

LOGIN_HTML = """
<div class="login-box card">
    <div style="text-align:center;">
        <img src="/static/logo.png" class="login-logo" alt="Company Logo">
        <h1>Greenery Multipurpose Cooperative Society</h1>
    </div>

    {% if error %}<p style="color:red;">{{ error }}</p>{% endif %}

    <form method="POST">
        <label>Login Type</label>
        <select name="login_type" id="loginType" onchange="toggleAdminKey()" required>
            <option value="staff">Staff Login</option>
            <option value="admin">Admin Login (Only Authorized User)</option>
            <option value="customer">Customer Login</option>
        </select>

        <label>Phone Number</label>
        <input type="text" name="phone" placeholder="Enter registered phone number" required>

        <label>Password</label>
        <input type="password" name="password" placeholder="Enter password" required>

        <div id="adminKeyField" style="display:none;">
            <label>Admin Security Key</label>
            <input type="password" name="admin_key" placeholder="Enter admin key">
        </div>

        <button type="submit">Login</button>
    </form>

    <p id="createStaffLink"><a class="small-link" href="{{ url_for('create_staff_account') }}">Create staff account</a></p>
    <p><a class="small-link" href="{{ url_for('forgot_password') }}">Forgot password?</a></p>
</div>
<script>
function toggleAdminKey() {
    const type = document.getElementById('loginType').value;
    document.getElementById('adminKeyField').style.display = type === 'admin' ? 'block' : 'none';
    document.getElementById('createStaffLink').style.display = type === 'staff' ? 'block' : 'none';
}
toggleAdminKey();
</script>
"""


def nav():
    return """
    <div class="navbar">
        <div style="display:flex; align-items:center; gap:10px;">
            <img src="/static/logo.png" class="navbar-logo" alt="Company Logo">
            <b>Greenery Multipurpose Cooperative Society</b>
        </div>
        <div>
            <a href="/dashboard">Dashboard</a>
            <a href="/add-customer">Add Customer</a>
            <a href="/add-contribution">Add Contribution</a>
            {% if session.get('role') == 'admin' %}<a href="/admin-reports">Reports</a>{% endif %}
            <a href="/change-password">Change Password</a>
            {% if session.get('role') == 'admin' %}<a href="/backup">Backup</a>{% endif %}
            <a href="/logout">Logout</a>
        </div>
    </div>
    """


def get_setting(key):
    conn = get_db()
    row = conn.execute("SELECT value FROM settings WHERE key = ?", (key,)).fetchone()
    conn.close()
    return row["value"] if row else ""


def set_setting(key, value):
    conn = get_db()
    conn.execute("UPDATE settings SET value = ? WHERE key = ?", (value, key))
    conn.commit()
    conn.close()


def login_required():
    return session.get("role") in ["admin", "staff"]


def calculate_customer_total(customer_id):
    conn = get_db()
    total = conn.execute("SELECT COALESCE(SUM(amount), 0) AS total FROM contributions WHERE customer_id = ?", (customer_id,)).fetchone()["total"]
    conn.close()
    return total


@app.route("/")
def home():
    return redirect(url_for("login"))


@app.route("/login", methods=["GET", "POST"])
def login():
    error = ""
    if request.method == "POST":
        phone = request.form["phone"].strip()
        password = request.form["password"].strip()
        login_type = request.form["login_type"]
        admin_key = request.form.get("admin_key", "").strip()

        conn = get_db()

        if login_type == "admin":
            if phone == get_setting("admin_phone") and check_password_hash(get_setting("admin_password"), password) and admin_key == get_setting("admin_key"):
                session["role"] = "admin"
                session["username"] = "Admin"
                conn.close()
                return redirect(url_for("dashboard"))
            error = "Invalid admin login details."

        elif login_type == "staff":
            staff = conn.execute("SELECT * FROM staff WHERE phone = ?", (phone,)).fetchone()
            if staff and check_password_hash(staff["password"], password):
                session["role"] = "staff"
                session["username"] = staff["name"]
                conn.close()
                return redirect(url_for("dashboard"))
            error = "Invalid staff login details."

        elif login_type == "customer":
            customer = conn.execute("SELECT * FROM customers WHERE phone = ?", (phone,)).fetchone()
            if not customer:
                error = "Customer not registered. Please contact the cooperative office."
            elif password != CUSTOMER_PASSWORD:
                error = "Invalid customer password."
            else:
                session["role"] = "customer"
                session["customer_id"] = customer["id"]
                conn.close()
                return redirect(url_for("customer_dashboard"))

        conn.close()

    return render_template_string("""
<head>
    <meta name="google-site-verification" content="<meta name="google-site-verification" content="l-xfiurJJjidapxNGy3kYxCoERc8vtlaQoAI4A3ZjyA" />" />
</head>
""" + BASE_STYLE + LOGIN_HTML, error=error)

@app.route("/create-staff-account", methods=["GET", "POST"])
def create_staff_account():
    error = ""
    if request.method == "POST":
        name = request.form["staff_name"].strip()
        phone = request.form["phone"].strip()
        password = request.form["password"].strip()
        confirm = request.form["confirm_password"].strip()

        conn = get_db()
        if password != confirm:
            error = "Passwords do not match."
        elif conn.execute("SELECT id FROM staff WHERE phone = ?", (phone,)).fetchone():
            error = "This phone number is already registered."
        elif conn.execute("SELECT id FROM staff WHERE LOWER(name) = LOWER(?)", (name,)).fetchone():
            error = "This staff name is already registered. Use a different name."
        else:
            conn.execute("INSERT INTO staff (name, phone, password) VALUES (?, ?, ?)", (name, phone, generate_password_hash(password)))
            conn.commit()
            conn.close()
            return redirect(url_for("login"))
        conn.close()

    return render_template_string(BASE_STYLE + """
    <div class="login-box card">
        <h1>Create Staff Account</h1>
        {% if error %}<p style="color:red;">{{ error }}</p>{% endif %}
        <form method="POST">
            <label>Staff Name</label><input type="text" name="staff_name" required>
            <label>Phone Number</label><input type="text" name="phone" required>
            <label>Password</label><input type="password" name="password" required>
            <label>Confirm Password</label><input type="password" name="confirm_password" required>
            <button type="submit">Create Staff Account</button>
        </form>
        <p><a class="small-link" href="{{ url_for('login') }}">Back to login</a></p>
    </div>
    """, error=error)


@app.route("/forgot-password", methods=["GET", "POST"])
def forgot_password():
    message = error = generated_otp = ""
    if request.method == "POST":
        phone = request.form["phone"].strip()
        conn = get_db()
        staff = conn.execute("SELECT * FROM staff WHERE phone = ?", (phone,)).fetchone()
        conn.close()
        if staff or phone == ADMIN_PHONE:
            generated_otp = str(random.randint(100000, 999999))
            save_otp(phone, generated_otp)
            message = "OTP generated successfully. Use the OTP below to reset your password."
        else:
            error = "Phone number not found."

    return render_template_string(BASE_STYLE + """
    <div class="login-box card">
        <h1>Forgot Password</h1>
        {% if error %}<p style="color:red;">{{ error }}</p>{% endif %}
        {% if message %}<p style="color:green;">{{ message }}</p><h2>Your OTP: {{ generated_otp }}</h2><a class="small-link" href="{{ url_for('reset_password') }}">Continue to reset password</a>{% endif %}
        <form method="POST"><label>Phone Number</label><input type="text" name="phone" required><button type="submit">Send OTP</button></form>
        <p><a class="small-link" href="{{ url_for('login') }}">Back to login</a></p>
    </div>
    """, message=message, error=error, generated_otp=generated_otp)


@app.route("/reset-password", methods=["GET", "POST"])
def reset_password():
    message = error = ""
    if request.method == "POST":
        phone = request.form["phone"].strip()
        otp = request.form["otp"].strip()
        new_password = request.form["new_password"].strip()

        if verify_otp(phone, otp):
            if phone == ADMIN_PHONE:
                error = "Admin password is protected in the code. Change ADMIN_PASSWORD manually."
            else:
                conn = get_db()
                conn.execute("UPDATE staff SET password = ? WHERE phone = ?", (generate_password_hash(new_password), phone))
                conn.commit()
                conn.close()
                message = "Password reset successful. You can now login."
        else:
            error = "Invalid OTP or phone number."

    return render_template_string(BASE_STYLE + """
    <div class="login-box card">
        <h1>Reset Password</h1>
        {% if error %}<p style="color:red;">{{ error }}</p>{% endif %}
        {% if message %}<p style="color:green;">{{ message }}</p>{% endif %}
        <form method="POST">
            <label>Phone Number</label><input type="text" name="phone" required>
            <label>OTP</label><input type="text" name="otp" required>
            <label>New Password</label><input type="password" name="new_password" required>
            <button type="submit">Reset Password</button>
        </form>
        <p><a class="small-link" href="{{ url_for('login') }}">Back to login</a></p>
    </div>
    """, message=message, error=error)


@app.route("/change-password", methods=["GET", "POST"])
def change_password():
    if not login_required():
        return redirect(url_for("login"))

    message = ""
    error = ""
    generated_otp = ""
    role = session.get("role")

    if request.method == "POST":
        action = request.form.get("action")
        phone = request.form["phone"].strip()

        if role == "admin":
            correct_phone = get_setting("admin_phone")
        else:
            correct_phone = None
            conn = get_db()
            staff = conn.execute("SELECT * FROM staff WHERE name = ? AND phone = ?", (session.get("username"), phone)).fetchone()
            conn.close()
            if staff:
                correct_phone = staff["phone"]

        if phone != correct_phone:
            error = "Phone number does not match your account."
        elif action == "send_otp":
            generated_otp = str(random.randint(100000, 999999))
            save_otp(phone, generated_otp)
            message = "OTP generated successfully. Use it below to change your password."
        elif action == "change_password":
            otp = request.form["otp"].strip()
            new_password = request.form["new_password"].strip()
            confirm_password = request.form["confirm_password"].strip()

            if otp_store.get(phone) != otp:
                error = "Invalid OTP."
            elif new_password != confirm_password:
                error = "Passwords do not match."
            else:
                if role == "admin":
                    set_setting("admin_password", generate_password_hash(new_password))
                else:
                    conn = get_db()
                    conn.execute("UPDATE staff SET password = ? WHERE phone = ?", (generate_password_hash(new_password), phone))
                    conn.commit()
                    conn.close()

                message = "Password changed successfully. Please login again."
                session.clear()
                return redirect(url_for("login"))

    return render_template_string(BASE_STYLE + nav() + """
    <div class="container card">
        <h1>Change Password</h1>

        {% if error %}<p style="color:red;">{{ error }}</p>{% endif %}
        {% if message %}<p style="color:green;">{{ message }}</p>{% endif %}
        {% if generated_otp %}<h2>Your OTP: {{ generated_otp }}</h2>{% endif %}

        <form method="POST">
            <input type="hidden" name="action" value="send_otp">
            <label>Registered Phone Number</label>
            <input type="text" name="phone" required>
            <button type="submit">Send OTP</button>
        </form>

        <form method="POST">
            <input type="hidden" name="action" value="change_password">
            <label>Registered Phone Number</label>
            <input type="text" name="phone" required>

            <label>OTP</label>
            <input type="text" name="otp" required>

            <label>New Password</label>
            <input type="password" name="new_password" required>

            <label>Confirm New Password</label>
            <input type="password" name="confirm_password" required>

            <button type="submit">Change Password</button>
        </form>
    </div>
    """, message=message, error=error, generated_otp=generated_otp)


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.route("/dashboard")
def dashboard():
    if not login_required():
        return redirect(url_for("login"))

    conn = get_db()
    customers = conn.execute("""
        SELECT customers.*, COALESCE(SUM(contributions.amount), 0) AS total
        FROM customers
        LEFT JOIN contributions ON customers.id = contributions.customer_id
        GROUP BY customers.id
        ORDER BY customers.name
    """).fetchall()
    contributions = conn.execute("SELECT * FROM contributions ORDER BY id DESC").fetchall()
    total_customers = conn.execute("SELECT COUNT(*) AS count FROM customers").fetchone()["count"]
    total_contributions = conn.execute("SELECT COALESCE(SUM(amount), 0) AS total FROM contributions").fetchone()["total"]
    total_records = conn.execute("SELECT COUNT(*) AS count FROM contributions").fetchone()["count"]
    conn.close()

    return render_template_string(BASE_STYLE + nav() + """
    <div class="container">
        <h1>Dashboard</h1>
        <div class="stats">
            <div class="stat-box"><h3>Total Customers</h3><h2>{{ total_customers }}</h2></div>
            <div class="stat-box"><h3>Total Contribution</h3><h2>₦{{ total_contributions }}</h2></div>
            <div class="stat-box"><h3>Contribution Records</h3><h2>{{ total_records }}</h2></div>
        </div>
        <div class="card">
            <h2>Customers</h2>

            <input type="text" id="customerSearch" placeholder="Search by customer name or phone number..." onkeyup="filterDashboardCustomers()">

            <select id="planFilter" onchange="filterDashboardCustomers()">
                <option value="">All Plans</option>
                <option value="daily">Daily</option>
                <option value="weekly">Weekly</option>
                <option value="monthly">Monthly</option>
            </select>

            <div class="table-wrap"><table id="customersTable">
                <tr><th>Name</th><th>Phone</th><th>Plan</th><th>Total Contributed</th><th>Action</th></tr>
                {% for customer in customers %}
                <tr>
                    <td>{{ customer.name }}</td><td>{{ customer.phone }}</td><td>{{ customer.plan }}</td><td>₦{{ customer.total }}</td>
                    <td><a class="small-link" href="{{ url_for('customer_record', customer_id=customer.id) }}">View</a> | <a class="small-link" href="{{ url_for('edit_customer', customer_id=customer.id) }}">Edit</a>{% if role == 'admin' %} | <a class="small-link" onclick="return confirm('Delete this customer and all records?')" href="{{ url_for('delete_customer', customer_id=customer.id) }}">Delete</a>{% endif %}</td>
                </tr>
                {% endfor %}
            </table></div>
        </div>

        <script>
        function filterDashboardCustomers() {
            const search = document.getElementById('customerSearch').value.toLowerCase();
            const plan = document.getElementById('planFilter').value.toLowerCase();
            const table = document.getElementById('customersTable');
            const rows = table.getElementsByTagName('tr');

            for (let i = 1; i < rows.length; i++) {
                const name = rows[i].cells[0].textContent.toLowerCase();
                const phone = rows[i].cells[1].textContent.toLowerCase();
                const customerPlan = rows[i].cells[2].textContent.toLowerCase();

                const matchesSearch = name.includes(search) || phone.includes(search);
                const matchesPlan = plan === '' || customerPlan === plan;

                rows[i].style.display = matchesSearch && matchesPlan ? '' : 'none';
            }
        }
        </script>

        {% if role == 'admin' %}
        <div class="card">
            <h2>Admin Monitoring</h2>
            <table>
                <tr><th>Date</th><th>Customer</th><th>Type</th><th>Period</th><th>Amount</th><th>Recorded By</th><th>Action</th></tr>
                {% for item in contributions %}
                <tr><td>{{ item.date }}</td><td>{{ item.customer_name }}</td><td>{{ item.type }}</td><td>{{ item.period }}</td><td>₦{{ item.amount }}</td><td>{{ item.staff }}</td><td><a class="small-link" href="{{ url_for('edit_contribution', contribution_id=item.id) }}">Edit</a> | <a class="small-link" onclick="return confirm('Delete this contribution?')" href="{{ url_for('delete_contribution', contribution_id=item.id) }}">Delete</a></td></tr>
                {% endfor %}
            </table>
        </div>
        {% endif %}
    </div>
    """, customers=customers, contributions=contributions, total_customers=total_customers, total_contributions=total_contributions, total_records=total_records, role=session.get("role"))


@app.route("/backup")
def backup():
    if session.get("role") != "admin":
        return redirect(url_for("dashboard"))
    return send_file(DB_NAME, as_attachment=True, download_name="greenery_cooperative_backup.db")


@app.route("/admin-reports")
def admin_reports():
    if session.get("role") != "admin":
        return redirect(url_for("dashboard"))

    conn = get_db()
    daily_total = conn.execute("SELECT COALESCE(SUM(amount), 0) AS total FROM contributions WHERE type = 'Daily'").fetchone()["total"]
    weekly_total = conn.execute("SELECT COALESCE(SUM(amount), 0) AS total FROM contributions WHERE type = 'Weekly'").fetchone()["total"]
    monthly_total = conn.execute("SELECT COALESCE(SUM(amount), 0) AS total FROM contributions WHERE type = 'Monthly'").fetchone()["total"]

    today_total = conn.execute("SELECT COALESCE(SUM(amount), 0) AS total FROM contributions WHERE date(date) = date('now')").fetchone()["total"]
    this_week_total = conn.execute("SELECT COALESCE(SUM(amount), 0) AS total FROM contributions WHERE date(date) >= date('now', '-6 days')").fetchone()["total"]
    this_month_total = conn.execute("SELECT COALESCE(SUM(amount), 0) AS total FROM contributions WHERE strftime('%Y-%m', date) = strftime('%Y-%m', 'now')").fetchone()["total"]

    staff_totals = conn.execute("""
        SELECT staff, COUNT(*) AS records, COALESCE(SUM(amount), 0) AS total
        FROM contributions
        GROUP BY staff
        ORDER BY total DESC
    """).fetchall()

    all_customers = conn.execute("SELECT * FROM customers ORDER BY name").fetchall()
    missed_customers = []
    inactive_customers = []
    eligible_customers = []

    for customer in all_customers:
        status = get_customer_status(customer["id"], customer["plan"])
        row = dict(customer)
        row.update(status)

        if status["missed_payment"] == "Yes":
            missed_customers.append(row)
        if status["inactive"] == "Yes":
            inactive_customers.append(row)
        if status["eligible"] == "Yes":
            eligible_customers.append(row)

    daily_records = conn.execute("SELECT * FROM contributions WHERE type = 'Daily' ORDER BY id DESC").fetchall()
    weekly_records = conn.execute("SELECT * FROM contributions WHERE type = 'Weekly' ORDER BY id DESC").fetchall()
    monthly_records = conn.execute("SELECT * FROM contributions WHERE type = 'Monthly' ORDER BY id DESC").fetchall()
    conn.close()

    return render_template_string(BASE_STYLE + nav() + """
    <div class="container">
        <h1>Admin Contribution Reports</h1>

        <div class="stats">
            <div class="stat-box"><h3>Today’s Total</h3><h2>₦{{ today_total }}</h2></div>
            <div class="stat-box"><h3>This Week Total</h3><h2>₦{{ this_week_total }}</h2></div>
            <div class="stat-box"><h3>This Month Total</h3><h2>₦{{ this_month_total }}</h2></div>
        </div>

        <div class="stats">
            <div class="stat-box"><h3>Daily Total</h3><h2>₦{{ daily_total }}</h2></div>
            <div class="stat-box"><h3>Weekly Total</h3><h2>₦{{ weekly_total }}</h2></div>
            <div class="stat-box"><h3>Monthly Total</h3><h2>₦{{ monthly_total }}</h2></div>
        </div>

        <div class="card">
            <h2>Customers Who Missed Payments</h2>
            <div class="table-wrap">
            <table>
                <tr><th>Name</th><th>Phone</th><th>Plan</th><th>Last Payment</th><th>Trust Level</th><th>Loan Owing</th></tr>
                {% for customer in missed_customers %}
                <tr><td>{{ customer.name }}</td><td>{{ customer.phone }}</td><td>{{ customer.plan }}</td><td>{{ customer.last_payment }}</td><td>{{ customer.trust }}</td><td>₦{{ customer.owing }}</td></tr>
                {% endfor %}
            </table>
            </div>
        </div>

        <div class="card">
            <h2>Inactive Customers</h2>
            <div class="table-wrap">
            <table>
                <tr><th>Name</th><th>Phone</th><th>Plan</th><th>Last Payment</th><th>Trust Level</th><th>Loan Owing</th></tr>
                {% for customer in inactive_customers %}
                <tr><td>{{ customer.name }}</td><td>{{ customer.phone }}</td><td>{{ customer.plan }}</td><td>{{ customer.last_payment }}</td><td>{{ customer.trust }}</td><td>₦{{ customer.owing }}</td></tr>
                {% endfor %}
            </table>
            </div>
        </div>

        <div class="card">
            <h2>Loan Eligible Customers</h2>
            <p>Customers become eligible after 6 months of active contributions, no inactivity, and no unpaid loan balance.</p>
            <div class="table-wrap">
            <table>
                <tr><th>Name</th><th>Phone</th><th>Plan</th><th>Last Payment</th><th>Trust Level</th><th>Loan Owing</th></tr>
                {% for customer in eligible_customers %}
                <tr><td>{{ customer.name }}</td><td>{{ customer.phone }}</td><td>{{ customer.plan }}</td><td>{{ customer.last_payment }}</td><td>{{ customer.trust }}</td><td>₦{{ customer.owing }}</td></tr>
                {% endfor %}
            </table>
            </div>
        </div>

        <div class="card">
            <h2>Staff Performance</h2>
            <div class="table-wrap">
            <table>
                <tr><th>Staff</th><th>Records Entered</th><th>Total Amount Recorded</th></tr>
                {% for item in staff_totals %}
                <tr><td>{{ item.staff }}</td><td>{{ item.records }}</td><td>₦{{ item.total }}</td></tr>
                {% endfor %}
            </table>
            </div>
        </div>

        <div class="card">
            <h2>Daily Contributions</h2>
            <div class="table-wrap"><table>
                <tr><th>Date Recorded</th><th>Customer</th><th>Period</th><th>Amount</th><th>Staff</th></tr>
                {% for item in daily_records %}
                <tr><td>{{ item.date }}</td><td>{{ item.customer_name }}</td><td>{{ item.period }}</td><td>₦{{ item.amount }}</td><td>{{ item.staff }}</td></tr>
                {% endfor %}
            </table></div>
        </div>

        <div class="card">
            <h2>Weekly Contributions</h2>
            <div class="table-wrap"><table>
                <tr><th>Date Recorded</th><th>Customer</th><th>Week</th><th>Amount</th><th>Staff</th></tr>
                {% for item in weekly_records %}
                <tr><td>{{ item.date }}</td><td>{{ item.customer_name }}</td><td>{{ item.period }}</td><td>₦{{ item.amount }}</td><td>{{ item.staff }}</td></tr>
                {% endfor %}
            </table></div>
        </div>

        <div class="card">
            <h2>Monthly Contributions</h2>
            <div class="table-wrap"><table>
                <tr><th>Date Recorded</th><th>Customer</th><th>Month</th><th>Amount</th><th>Staff</th></tr>
                {% for item in monthly_records %}
                <tr><td>{{ item.date }}</td><td>{{ item.customer_name }}</td><td>{{ item.period }}</td><td>₦{{ item.amount }}</td><td>{{ item.staff }}</td></tr>
                {% endfor %}
            </table></div>
        </div>
    </div>
    """, daily_total=daily_total, weekly_total=weekly_total, monthly_total=monthly_total,
       today_total=today_total, this_week_total=this_week_total, this_month_total=this_month_total,
       staff_totals=staff_totals, daily_records=daily_records, weekly_records=weekly_records,
       monthly_records=monthly_records, missed_customers=missed_customers,
       inactive_customers=inactive_customers, eligible_customers=eligible_customers)


@app.route("/delete-customer/<int:customer_id>")
def delete_customer(customer_id):
    if session.get("role") != "admin":
        return redirect(url_for("dashboard"))
    conn = get_db()
    conn.execute("DELETE FROM contributions WHERE customer_id = ?", (customer_id,))
    conn.execute("DELETE FROM loans WHERE customer_id = ?", (customer_id,))
    conn.execute("DELETE FROM customers WHERE id = ?", (customer_id,))
    conn.commit()
    conn.close()
    return redirect(url_for("dashboard"))


@app.route("/delete-contribution/<int:contribution_id>")
def delete_contribution(contribution_id):
    if session.get("role") != "admin":
        return redirect(url_for("dashboard"))
    conn = get_db()
    conn.execute("DELETE FROM contributions WHERE id = ?", (contribution_id,))
    conn.commit()
    conn.close()
    return redirect(url_for("dashboard"))


@app.route("/customer-dashboard")
def customer_dashboard():
    if session.get("role") != "customer":
        return redirect(url_for("login"))
    customer_id = session.get("customer_id")
    conn = get_db()
    customer = conn.execute("SELECT * FROM customers WHERE id = ?", (customer_id,)).fetchone()
    records = conn.execute("SELECT * FROM contributions WHERE customer_id = ? ORDER BY id DESC", (customer_id,)).fetchall()
    total = conn.execute("SELECT COALESCE(SUM(amount), 0) AS total FROM contributions WHERE customer_id = ?", (customer_id,)).fetchone()["total"]
    conn.close()
    if not customer:
        return redirect(url_for("login"))
    return render_template_string(BASE_STYLE + """
    <div class="navbar"><div style="display:flex; align-items:center; gap:10px;"><img src="/static/logo.png" class="navbar-logo"><b>Greenery Multipurpose Cooperative Society</b></div><div><a href="/logout">Logout</a></div></div>
    <div class="container">
        <h1>Customer Dashboard</h1>
        <div class="stats"><div class="stat-box"><h3>Name</h3><h2>{{ customer.name }}</h2></div><div class="stat-box"><h3>Plan</h3><h2>{{ customer.plan }}</h2></div><div class="stat-box"><h3>Total Contributed</h3><h2>₦{{ total }}</h2></div></div>
        <div class="card"><h2>My Contribution Records</h2><table><tr><th>Date</th><th>Type</th><th>Period</th><th>Amount</th><th>Recorded By</th></tr>{% for item in records %}<tr><td>{{ item.date }}</td><td>{{ item.type }}</td><td>{{ item.period }}</td><td>₦{{ item.amount }}</td><td>{{ item.staff }}</td></tr>{% endfor %}</table></div>
    </div>
    """, customer=customer, records=records, total=total)


@app.route("/customer-record/<int:customer_id>")
def customer_record(customer_id):
    if not login_required():
        return redirect(url_for("login"))
    conn = get_db()
    customer = conn.execute("SELECT * FROM customers WHERE id = ?", (customer_id,)).fetchone()
    records = conn.execute("SELECT * FROM contributions WHERE customer_id = ? ORDER BY id DESC", (customer_id,)).fetchall()
    total = conn.execute("SELECT COALESCE(SUM(amount), 0) AS total FROM contributions WHERE customer_id = ?", (customer_id,)).fetchone()["total"]
    conn.close()
    return render_template_string(BASE_STYLE + nav() + """
    <div class="container"><h1>{{ customer.name }} Contribution Record</h1>
    <div class="stats"><div class="stat-box"><h3>Phone</h3><h2>{{ customer.phone }}</h2></div><div class="stat-box"><h3>Plan</h3><h2>{{ customer.plan }}</h2></div><div class="stat-box"><h3>Total</h3><h2>₦{{ total }}</h2></div></div>
    <div class="card"><h2>Individual Contribution History</h2><table><tr><th>Date</th><th>Type</th><th>Period</th><th>Amount</th><th>Recorded By</th></tr>{% for item in records %}<tr><td>{{ item.date }}</td><td>{{ item.type }}</td><td>{{ item.period }}</td><td>₦{{ item.amount }}</td><td>{{ item.staff }}</td></tr>{% endfor %}</table></div></div>
    """, customer=customer, records=records, total=total)


@app.route("/add-customer", methods=["GET", "POST"])
def add_customer():
    if not login_required():
        return redirect(url_for("login"))
    error = ""
    if request.method == "POST":
        try:
            conn = get_db()
            conn.execute("INSERT INTO customers (name, phone, address, plan) VALUES (?, ?, ?, ?)", (request.form["name"], request.form["phone"], request.form["address"], request.form["plan"]))
            conn.commit()
            conn.close()
            return redirect(url_for("dashboard"))
        except sqlite3.IntegrityError:
            error = "This customer phone number is already registered."
    return render_template_string(BASE_STYLE + nav() + """
    <div class="container card"><h1>Add Customer</h1>{% if error %}<p style="color:red;">{{ error }}</p>{% endif %}<form method="POST">
        <label>Customer Name</label><input type="text" name="name" required>
        <label>Phone Number</label><input type="text" name="phone" required>
        <label>Address</label><input type="text" name="address" required>
        <label>Contribution Plan</label><select name="plan" required><option value="Daily">Daily</option><option value="Weekly">Weekly</option><option value="Monthly">Monthly</option></select>
        <button type="submit">Save Customer</button></form></div>
    """, error=error)


@app.route("/edit-customer/<int:customer_id>", methods=["GET", "POST"])
def edit_customer(customer_id):
    if not login_required():
        return redirect(url_for("login"))
    conn = get_db()
    if request.method == "POST":
        conn.execute("UPDATE customers SET name=?, phone=?, address=?, plan=? WHERE id=?", (request.form["name"], request.form["phone"], request.form["address"], request.form["plan"], customer_id))
        conn.commit()
        conn.close()
        return redirect(url_for("dashboard"))
    customer = conn.execute("SELECT * FROM customers WHERE id = ?", (customer_id,)).fetchone()
    conn.close()
    return render_template_string(BASE_STYLE + nav() + """
    <div class="container card"><h1>Edit Customer</h1><form method="POST">
        <label>Customer Name</label><input type="text" name="name" value="{{ customer.name }}" required>
        <label>Phone Number</label><input type="text" name="phone" value="{{ customer.phone }}" required>
        <label>Address</label><input type="text" name="address" value="{{ customer.address }}" required>
        <label>Contribution Plan</label><select name="plan" required><option value="Daily" {% if customer.plan == 'Daily' %}selected{% endif %}>Daily</option><option value="Weekly" {% if customer.plan == 'Weekly' %}selected{% endif %}>Weekly</option><option value="Monthly" {% if customer.plan == 'Monthly' %}selected{% endif %}>Monthly</option></select>
        <button type="submit">Update Customer</button></form></div>
    """, customer=customer)


@app.route("/add-contribution", methods=["GET", "POST"])
def add_contribution():
    if not login_required():
        return redirect(url_for("login"))
    conn = get_db()
    if request.method == "POST":
        customer_id = int(request.form["customer_id"])
        customer = conn.execute("SELECT * FROM customers WHERE id = ?", (customer_id,)).fetchone()
        contribution_type = request.form["type"]
        if contribution_type == "Daily":
            period = request.form["daily_date"]
        elif contribution_type == "Weekly":
            period = request.form["week_start"] + " to " + request.form["week_end"]
        else:
            period = request.form["month"]
        conn.execute("INSERT INTO contributions (customer_id, customer_name, type, period, amount, date, staff) VALUES (?, ?, ?, ?, ?, ?, ?)", (customer_id, customer["name"], contribution_type, period, float(request.form["amount"]), datetime.now().strftime("%Y-%m-%d %H:%M"), session.get("username")))
        conn.commit()
        conn.close()
        return redirect(url_for("dashboard"))
    customers = conn.execute("SELECT * FROM customers ORDER BY name").fetchall()
    conn.close()
    return render_template_string(BASE_STYLE + nav() + """
    <div class="container card"><h1>Add Customer Contribution</h1><form method="POST">
        <label>Search Customer</label><input type="text" id="customerSearch" placeholder="Type customer name..." onkeyup="filterCustomers()">
        <label>Select Customer</label><select name="customer_id" id="customerSelect" required>{% for customer in customers %}<option value="{{ customer.id }}">{{ customer.name }} - {{ customer.plan }}</option>{% endfor %}</select>
        <label>Contribution Type</label><select name="type" id="contributionType" onchange="showContributionDateFields()" required><option value="Daily">Daily</option><option value="Weekly">Weekly</option><option value="Monthly">Monthly</option></select>
        <div id="dailyField"><label>Contribution Date</label><input type="date" name="daily_date"></div>
        <div id="weeklyField" style="display:none;"><label>Week Start Date</label><input type="date" name="week_start"><label>Week End Date</label><input type="date" name="week_end"></div>
        <div id="monthlyField" style="display:none;"><label>Contribution Month</label><input type="month" name="month"></div>
        <label>Amount</label><input type="number" name="amount" min="0" step="0.01" required><button type="submit">Record Contribution</button></form></div>
    <script>
        function filterCustomers(){const input=document.getElementById('customerSearch').value.toLowerCase();const options=document.getElementById('customerSelect').options;for(let i=0;i<options.length;i++){options[i].style.display=options[i].text.toLowerCase().includes(input)?'':'none';}}
        function showContributionDateFields(){const type=document.getElementById('contributionType').value;document.getElementById('dailyField').style.display=type==='Daily'?'block':'none';document.getElementById('weeklyField').style.display=type==='Weekly'?'block':'none';document.getElementById('monthlyField').style.display=type==='Monthly'?'block':'none';}
        showContributionDateFields();
    </script>
    """, customers=customers)


@app.route("/edit-contribution/<int:contribution_id>", methods=["GET", "POST"])
def edit_contribution(contribution_id):
    if session.get("role") != "admin":
        return redirect(url_for("dashboard"))
    conn = get_db()
    if request.method == "POST":
        contribution_type = request.form["type"]
        if contribution_type == "Daily":
            period = request.form["daily_date"]
        elif contribution_type == "Weekly":
            period = request.form["week_start"] + " to " + request.form["week_end"]
        else:
            period = request.form["month"]
        conn.execute("UPDATE contributions SET type=?, period=?, amount=? WHERE id=?", (contribution_type, period, float(request.form["amount"]), contribution_id))
        conn.commit()
        conn.close()
        return redirect(url_for("dashboard"))
    contribution = conn.execute("SELECT * FROM contributions WHERE id = ?", (contribution_id,)).fetchone()
    conn.close()
    return render_template_string(BASE_STYLE + nav() + """
    <div class="container card"><h1>Edit Contribution</h1><form method="POST">
        <label>Contribution Type</label><select name="type" id="contributionType" onchange="showContributionDateFields()" required><option value="Daily" {% if contribution.type == 'Daily' %}selected{% endif %}>Daily</option><option value="Weekly" {% if contribution.type == 'Weekly' %}selected{% endif %}>Weekly</option><option value="Monthly" {% if contribution.type == 'Monthly' %}selected{% endif %}>Monthly</option></select>
        <div id="dailyField"><label>Contribution Date</label><input type="date" name="daily_date"></div>
        <div id="weeklyField" style="display:none;"><label>Week Start Date</label><input type="date" name="week_start"><label>Week End Date</label><input type="date" name="week_end"></div>
        <div id="monthlyField" style="display:none;"><label>Contribution Month</label><input type="month" name="month"></div>
        <label>Amount</label><input type="number" name="amount" value="{{ contribution.amount }}" min="0" step="0.01" required><button type="submit">Update Contribution</button></form><p><b>Current recorded period:</b> {{ contribution.period }}</p></div>
    <script>function showContributionDateFields(){const type=document.getElementById('contributionType').value;document.getElementById('dailyField').style.display=type==='Daily'?'block':'none';document.getElementById('weeklyField').style.display=type==='Weekly'?'block':'none';document.getElementById('monthlyField').style.display=type==='Monthly'?'block':'none';}showContributionDateFields();</script>
    """, contribution=contribution)


if __name__ == "__main__":
    init_db()
    auto_backup()

    import os
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
