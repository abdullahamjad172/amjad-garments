from flask import Flask, request, redirect, url_for, session, flash, render_template_string, abort
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
import sqlite3
import sys
from getpass import getpass
from pathlib import Path

app = Flask(__name__)
app.config["SECRET_KEY"] = "CHANGE-THIS-TO-A-LONG-RANDOM-SECRET-BEFORE-PUBLISHING"
DB_PATH = Path(__file__).with_name("amjad_garments.db")

def db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with db() as con:
        con.execute("""CREATE TABLE IF NOT EXISTS users(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL, email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL, is_admin INTEGER NOT NULL DEFAULT 0)""")
        con.execute("""CREATE TABLE IF NOT EXISTS products(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL, category TEXT NOT NULL DEFAULT 'General',
            description TEXT NOT NULL DEFAULT '', price INTEGER NOT NULL,
            stock INTEGER NOT NULL DEFAULT 0, emoji TEXT NOT NULL DEFAULT '👕',
            active INTEGER NOT NULL DEFAULT 1)""")
        con.execute("""CREATE TABLE IF NOT EXISTS orders(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER, customer_name TEXT NOT NULL, phone TEXT NOT NULL,
            address TEXT NOT NULL, items TEXT NOT NULL, total INTEGER NOT NULL,
            status TEXT NOT NULL DEFAULT 'Pending',
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)""")
        count = con.execute("SELECT COUNT(*) FROM products").fetchone()[0]
        if count == 0:
            con.executemany("""INSERT INTO products(name,category,description,price,stock,emoji)
                VALUES(?,?,?,?,?,?)""", [
                ("Baby Clothes","Baby Wear","Soft and comfortable baby wear.",1200,20,"🍼"),
                ("Kids Collection","Everyday Wear","Everyday style for kids.",1800,15,"👕"),
                ("Winter Wear","Seasonal","Warm and cosy clothing.",2500,10,"🧥"),
                ("Special Wear","Occasion Wear","Clothes for special occasions.",2000,12,"🎉")
            ])
init_db()

def current_user():
    uid = session.get("user_id")
    if not uid:
        return None
    with db() as con:
        return con.execute("SELECT id,name,email,is_admin FROM users WHERE id=?", (uid,)).fetchone()

def admin_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        user = current_user()
        if not user or not user["is_admin"]:
            flash("Admin access required. Sign in with an admin account.")
            return redirect(url_for("login"))
        return fn(*args, **kwargs)
    return wrapper

BASE = r"""
<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{{ title }} | Amjad Garments</title>
<style>
:root{--green:#123b2b;--gold:#d5ad52;--cream:#f6f3eb;--ink:#20372b;--muted:#69766d;--white:#fff}
*{box-sizing:border-box}body{margin:0;background:var(--cream);color:var(--ink);font-family:Arial,sans-serif}
header{background:var(--green);color:#fff;padding:18px max(5%,calc((100% - 1100px)/2));display:flex;align-items:center;justify-content:space-between;gap:16px;flex-wrap:wrap}
.brand{font-size:22px;font-weight:800;letter-spacing:.4px}.brand span{color:var(--gold)}
nav{display:flex;align-items:center;gap:13px;flex-wrap:wrap}nav a{color:#fff;text-decoration:none;font-size:14px}
main{max-width:1100px;margin:28px auto;padding:0 18px}.hero{background:linear-gradient(120deg,#e8dfc6,#f8f3e6);padding:50px 20px;text-align:center}
.hero h1{font-size:clamp(30px,5vw,48px);margin:0 0 12px}.hero p{color:#536457;font-size:17px}
h2{margin-top:0}.muted{color:var(--muted)}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(215px,1fr));gap:18px}
.card,.panel,.stat{background:#fff;padding:22px;border-radius:14px;box-shadow:0 5px 22px #142c1c0d}
.card{border-bottom:4px solid var(--gold)}.emoji{font-size:45px}.price{font-size:21px;font-weight:800}
.btn{display:inline-block;background:var(--gold);color:#173b2c;padding:11px 16px;border:0;border-radius:7px;font-weight:700;text-decoration:none;cursor:pointer}
.btn.dark{background:var(--green);color:#fff}.btn.light{background:#ece9e0}.btn.danger{background:#f4d8d4;color:#8a2018}
input,textarea,select{width:100%;padding:12px;margin:6px 0 15px;border:1px solid #d6d9d3;border-radius:7px;font:inherit;background:#fff}
label{font-size:14px;font-weight:700}form.inline{display:inline}form.inline input{width:auto}
.panel{max-width:540px;margin:25px auto}.flash{max-width:1100px;margin:14px auto;padding:12px 18px;background:#fff4d7;border-radius:8px;color:#634b12}
.row{display:flex;justify-content:space-between;align-items:center;gap:12px;flex-wrap:wrap}
.table-wrap{overflow-x:auto;background:#fff;border-radius:12px;padding:10px}table{width:100%;border-collapse:collapse;min-width:650px}th,td{text-align:left;padding:12px;border-bottom:1px solid #e6e8e3;vertical-align:top}th{background:#f6f3eb}
footer{text-align:center;background:var(--green);color:#fff;padding:22px;margin-top:45px}
.badge{display:inline-block;background:#eee9d8;border-radius:20px;padding:5px 9px;font-size:12px}
.search{display:flex;gap:10px;max-width:650px;margin:18px auto}.search input{margin:0}
@media(max-width:550px){header{padding:16px}nav{gap:10px}.hero{padding:35px 15px}.card,.panel{padding:18px}}
</style></head><body>
<header><a class="brand" style="color:white;text-decoration:none" href="{{ url_for('home') }}">AG <span>| AMJAD GARMENTS</span></a>
<nav><a href="{{ url_for('home') }}">Home</a><a href="{{ url_for('home') }}#shop">Shop</a><a href="{{ url_for('cart_page') }}">Cart ({{ cart_count }})</a>
{% if user %}<a href="{{ url_for('my_orders') }}">My Orders</a>{% if user['is_admin'] %}<a href="{{ url_for('admin') }}">Admin</a>{% endif %}<a href="{{ url_for('logout') }}">Logout</a>
{% else %}<a href="{{ url_for('login') }}">Login</a><a href="{{ url_for('register') }}">Register</a>{% endif %}</nav></header>
{% for msg in get_flashed_messages() %}<div class="flash">{{ msg }}</div>{% endfor %}
{% block body %}{% endblock %}
<footer>© 2026 Amjad Garments · Style, comfort and quality</footer>
</body></html>
"""

def page(template, **context):
    user = current_user()
    cart = session.get("cart", {})
    return render_template_string(
        BASE.replace("{% block body %}{% endblock %}", template),
        title=context.pop("title", "Home"), user=user,
        cart_count=sum(int(q) for q in cart.values()), **context
    )

HOME = r"""
<section class="hero"><h1>Welcome to Amjad Garments</h1>
<p>Thoughtful clothing for every little moment.</p><a class="btn dark" href="#shop">Explore Collection</a></section>
<main id="shop"><div class="row"><div><h2>Our Collection</h2><p class="muted">Find something special for your family.</p></div>
<form class="search" method="get"><input name="q" value="{{ q }}" placeholder="Search clothing..."><button class="btn" type="submit">Search</button></form></div>
<div class="grid">{% for p in products %}<article class="card"><div class="emoji">{{ p['emoji'] }}</div><span class="badge">{{ p['category'] }}</span>
<h3>{{ p['name'] }}</h3><p class="muted">{{ p['description'] }}</p><p class="price">Rs. {{ "{:,}".format(p['price']) }}</p>
<p class="muted">{% if p['stock'] > 0 %}In stock: {{ p['stock'] }}{% else %}Currently out of stock{% endif %}</p>
<form method="post" action="{{ url_for('add_to_cart', product_id=p['id']) }}"><label>Quantity</label><input type="number" name="qty" min="1" max="{{ p['stock'] }}" value="1" {% if p['stock'] < 1 %}disabled{% endif %}>
<button class="btn" {% if p['stock'] < 1 %}disabled{% endif %}>Add to Cart</button></form></article>
{% else %}<p>No products found.</p>{% endfor %}</div></main>
"""

FORM = r"""<main><section class="panel"><h2>{{ heading }}</h2><p class="muted">{{ subtitle }}</p>
<form method="post">{% if form_kind in ['register','checkout'] %}<label>{{ 'Full name' if form_kind=='register' else 'Customer name' }}</label><input name="{{ 'name' if form_kind=='register' else 'customer_name' }}" required maxlength="100" value="{{ values.get('name','') }}">
{% endif %}{% if form_kind=='checkout' %}<label>Phone number</label><input name="phone" type="tel" required maxlength="30">
<label>Delivery address</label><textarea name="address" required maxlength="500" rows="3"></textarea>
{% else %}<label>Email address</label><input name="email" type="email" required maxlength="254" value="{{ values.get('email','') }}">
<label>Password (minimum 8 characters)</label><input name="password" type="password" required minlength="8" maxlength="128">{% endif %}
<button class="btn dark" type="submit">{{ button }}</button></form>
{% if form_kind=='login' %}<p>New here? <a href="{{ url_for('register') }}">Create an account</a></p>{% elif form_kind=='register' %}<p>Already registered? <a href="{{ url_for('login') }}">Login</a></p>{% endif %}
</section></main>"""

CART = r"""<main><h2>Your Shopping Cart</h2>{% if items %}<div class="panel" style="max-width:none">
{% for item in items %}<div class="row" style="border-bottom:1px solid #eee;padding:12px 0"><div><strong>{{ item['name'] }}</strong><p class="muted">Rs. {{ "{:,}".format(item['price']) }} each</p></div>
<form method="post" action="{{ url_for('update_cart', product_id=item['id']) }}"><label>Qty</label><input style="width:85px" type="number" name="qty" min="0" max="{{ item['stock'] }}" value="{{ item['qty'] }}"><button class="btn light">Update</button></form>
<strong>Rs. {{ "{:,}".format(item['price']*item['qty']) }}</strong></div>{% endfor %}
<div class="row"><h2>Total: Rs. {{ "{:,}".format(total) }}</h2><a class="btn dark" href="{{ url_for('checkout') }}">Proceed to Checkout</a></div>
<p class="muted">Payment is arranged directly with the shop; online payment is not enabled.</p></div>{% else %}<section class="panel"><p>Your cart is empty.</p><a class="btn dark" href="{{ url_for('home') }}">Browse Products</a></section>{% endif %}</main>"""

@app.route("/")
def home():
    q = request.args.get("q", "").strip()[:80]
    with db() as con:
        if q:
            products = con.execute("SELECT * FROM products WHERE active=1 AND (name LIKE ? OR category LIKE ? OR description LIKE ?) ORDER BY id DESC",
                                   (f"%{q}%", f"%{q}%", f"%{q}%")).fetchall()
        else:
            products = con.execute("SELECT * FROM products WHERE active=1 ORDER BY id DESC").fetchall()
    return page(HOME, title="Home", products=products, q=q)

@app.route("/register", methods=["GET","POST"])
def register():
    if request.method == "POST":
        name = request.form.get("name","").strip()
        email = request.form.get("email","").strip().lower()
        password = request.form.get("password","")
        if not name or len(password) < 8:
            flash("Enter your name and a password of at least 8 characters.")
        else:
            try:
                with db() as con:
                    con.execute("INSERT INTO users(name,email,password_hash) VALUES(?,?,?)",
                                (name,email,generate_password_hash(password)))
                flash("Account created. Please log in.")
                return redirect(url_for("login"))
            except sqlite3.IntegrityError:
                flash("This email is already registered.")
    return page(FORM, title="Register", form_kind="register", heading="Create Account",
                subtitle="Join Amjad Garments", button="Register", values={"name":"","email":request.form.get("email","")})

@app.route("/login", methods=["GET","POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email","").strip().lower()
        with db() as con:
            u = con.execute("SELECT * FROM users WHERE email=?", (email,)).fetchone()
        if u and check_password_hash(u["password_hash"], request.form.get("password","")):
            session.clear()
            session["user_id"] = u["id"]
            flash("Welcome back!")
            return redirect(url_for("admin" if u["is_admin"] else "home"))
        flash("Email or password is incorrect.")
    return page(FORM, title="Login", form_kind="login", heading="Welcome Back",
                subtitle="Login to your account", button="Login", values={"name":"","email":request.form.get("email","")})

@app.route("/logout")
def logout():
    session.clear()
    flash("You have logged out.")
    return redirect(url_for("home"))

@app.route("/add/<int:product_id>", methods=["POST"])
def add_to_cart(product_id):
    try:
        qty = int(request.form.get("qty",1))
    except ValueError:
        qty = 0
    with db() as con:
        p = con.execute("SELECT * FROM products WHERE id=? AND active=1", (product_id,)).fetchone()
    if not p or qty < 1 or qty > p["stock"]:
        flash("Please choose a valid quantity and available product.")
        return redirect(url_for("home"))
    cart = session.get("cart", {})
    key = str(product_id)
    new_qty = int(cart.get(key,0)) + qty
    if new_qty > p["stock"]:
        flash("That quantity exceeds available stock.")
    else:
        cart[key] = new_qty
        session["cart"] = cart
        flash("Added to cart.")
    return redirect(request.referrer or url_for("home"))

def cart_items():
    cart = session.get("cart", {})
    items = []
    with db() as con:
        for key, qty in cart.items():
            if not str(key).isdigit():
                continue
            p = con.execute("SELECT * FROM products WHERE id=? AND active=1", (int(key),)).fetchone()
            if p and int(qty) > 0:
                items.append({**dict(p), "qty": int(qty)})
    total = sum(i["price"]*i["qty"] for i in items)
    return items, total

@app.route("/cart")
def cart_page():
    items, total = cart_items()
    return page(CART, title="Cart", items=items, total=total)

@app.route("/cart/update/<int:product_id>", methods=["POST"])
def update_cart(product_id):
    try:
        qty = int(request.form.get("qty",0))
    except ValueError:
        qty = -1
    cart = session.get("cart", {})
    key = str(product_id)
    with db() as con:
        p = con.execute("SELECT stock FROM products WHERE id=? AND active=1", (product_id,)).fetchone()
    if qty == 0:
        cart.pop(key, None)
    elif p and 1 <= qty <= p["stock"]:
        cart[key] = qty
    else:
        flash("Please enter a valid quantity within available stock.")
    session["cart"] = cart
    return redirect(url_for("cart_page"))

@app.route("/checkout", methods=["GET","POST"])
def checkout():
    items, total = cart_items()
    if not items:
        flash("Your cart is empty.")
        return redirect(url_for("cart_page"))
    if request.method == "POST":
        name = request.form.get("customer_name","").strip()[:100]
        phone = request.form.get("phone","").strip()[:30]
        address = request.form.get("address","").strip()[:500]
        if not name or not phone or not address:
            flash("Please complete all checkout fields.")
        else:
            with db() as con:
                # Recheck stock at checkout before recording order.
                for item in items:
                    row = con.execute("SELECT stock,active FROM products WHERE id=?", (item["id"],)).fetchone()
                    if not row or not row["active"] or row["stock"] < item["qty"]:
                        flash(f"Stock changed for {item['name']}. Please review your cart.")
                        return redirect(url_for("cart_page"))
                order_lines = []
                for item in items:
                    con.execute("UPDATE products SET stock=stock-? WHERE id=?", (item["qty"], item["id"]))
                    order_lines.append(f"{item['name']} x {item['qty']} (Rs. {item['price']})")
                cur = con.execute("""INSERT INTO orders(user_id,customer_name,phone,address,items,total)
                    VALUES(?,?,?,?,?,?)""",
                    (session.get("user_id"), name, phone, address, "; ".join(order_lines), total))
                order_id = cur.lastrowid
            session["cart"] = {}
            return page(r"""<main><section class="panel"><h2>Order Received!</h2><p>Your order number is <strong>#{{ order_id }}</strong>.</p>
            <p>Thank you for shopping with Amjad Garments. The shop will contact you to confirm delivery.</p>
            <a class="btn dark" href="{{ url_for('home') }}">Continue Shopping</a></section></main>""",
                title="Order Received", order_id=order_id)
    return page(FORM, title="Checkout", form_kind="checkout", heading="Checkout",
                subtitle=f"Order total: Rs. {total:,}", button="Place Order", values={})

@app.route("/my-orders")
def my_orders():
    user = current_user()
    if not user:
        flash("Please log in to view your orders.")
        return redirect(url_for("login"))
    with db() as con:
        orders = con.execute("SELECT * FROM orders WHERE user_id=? ORDER BY id DESC", (user["id"],)).fetchall()
    template = r"""<main><h2>My Orders</h2>{% if orders %}<div class="table-wrap"><table><tr><th>Order</th><th>Date</th><th>Items</th><th>Total</th><th>Status</th></tr>
    {% for o in orders %}<tr><td>#{{ o['id'] }}</td><td>{{ o['created_at'] }}</td><td>{{ o['items'] }}</td><td>Rs. {{ "{:,}".format(o['total']) }}</td><td>{{ o['status'] }}</td></tr>{% endfor %}</table></div>
    {% else %}<p>You have no orders yet.</p>{% endif %}</main>"""
    return page(template, title="My Orders", orders=orders)

@app.route("/admin")
@admin_required
def admin():
    with db() as con:
        products = con.execute("SELECT * FROM products ORDER BY id DESC").fetchall()
        orders = con.execute("SELECT * FROM orders ORDER BY id DESC LIMIT 100").fetchall()
        stats = {
            "products": con.execute("SELECT COUNT(*) FROM products WHERE active=1").fetchone()[0],
            "orders": con.execute("SELECT COUNT(*) FROM orders").fetchone()[0],
            "pending": con.execute("SELECT COUNT(*) FROM orders WHERE status='Pending'").fetchone()[0],
            "sales": con.execute("SELECT COALESCE(SUM(total),0) FROM orders WHERE status!='Cancelled'").fetchone()[0]
        }
    template = r"""<main><div class="row"><div><h2>Admin Dashboard</h2><p class="muted">Manage products and customer orders.</p></div><a class="btn dark" href="{{ url_for('admin_product_new') }}">+ Add Product</a></div>
    <div class="grid" style="margin:18px 0"><div class="stat"><p class="muted">Active products</p><h2>{{ stats.products }}</h2></div><div class="stat"><p class="muted">Orders</p><h2>{{ stats.orders }}</h2></div><div class="stat"><p class="muted">Pending orders</p><h2>{{ stats.pending }}</h2></div><div class="stat"><p class="muted">Recorded sales (not accounting)</p><h2>Rs. {{ "{:,}".format(stats.sales) }}</h2></div></div>
    <h2>Products</h2><div class="table-wrap"><table><tr><th>Product</th><th>Price</th><th>Stock</th><th>Active</th><th>Manage</th></tr>{% for p in products %}<tr><td>{{ p['emoji'] }} {{ p['name'] }}<br><small>{{ p['category'] }}</small></td><td>Rs. {{ p['price'] }}</td><td>{{ p['stock'] }}</td><td>{{ 'Yes' if p['active'] else 'No' }}</td><td><a class="btn" href="{{ url_for('admin_product_edit', product_id=p['id']) }}">Edit</a></td></tr>{% endfor %}</table></div>
    <h2 style="margin-top:35px">Recent Orders</h2><div class="table-wrap"><table><tr><th>Order</th><th>Customer</th><th>Contact / Address</th><th>Items</th><th>Total</th><th>Status</th></tr>
    {% for o in orders %}<tr><td>#{{ o['id'] }}<br><small>{{ o['created_at'] }}</small></td><td>{{ o['customer_name'] }}</td><td>{{ o['phone'] }}<br>{{ o['address'] }}</td><td>{{ o['items'] }}</td><td>Rs. {{ o['total'] }}</td><td><form method="post" action="{{ url_for('admin_order_status', order_id=o['id']) }}"><select name="status">{% for s in statuses %}<option value="{{ s }}" {% if s==o['status'] %}selected{% endif %}>{{ s }}</option>{% endfor %}</select><button class="btn">Save</button></form></td></tr>{% endfor %}</table></div></main>"""
    return page(template, title="Admin", products=products, orders=orders, stats=stats,
                statuses=["Pending","Confirmed","Shipped","Delivered","Cancelled"])

PRODUCT_FORM = r"""<main><section class="panel"><h2>{{ heading }}</h2><form method="post">
<label>Product name</label><input name="name" required maxlength="100" value="{{ p['name'] if p else '' }}">
<label>Category</label><input name="category" required maxlength="60" value="{{ p['category'] if p else '' }}">
<label>Description</label><textarea name="description" rows="3" maxlength="500">{{ p['description'] if p else '' }}</textarea>
<label>Price (PKR, whole number)</label><input name="price" type="number" min="1" max="10000000" required value="{{ p['price'] if p else '' }}">
<label>Stock quantity</label><input name="stock" type="number" min="0" max="100000" required value="{{ p['stock'] if p else 0 }}">
<label>Emoji / icon</label><input name="emoji" maxlength="8" value="{{ p['emoji'] if p else '👕' }}">
<label><input style="width:auto" type="checkbox" name="active" {% if not p or p['active'] %}checked{% endif %}> Show in shop</label><br><br>
<button class="btn dark">Save Product</button> <a class="btn light" href="{{ url_for('admin') }}">Cancel</a></form></section></main>"""

def save_product(p=None):
    if request.method == "POST":
        name = request.form.get("name","").strip()
        category = request.form.get("category","").strip()
        description = request.form.get("description","").strip()
        emoji = request.form.get("emoji","👕").strip() or "👕"
        active = 1 if request.form.get("active") else 0
        try:
            price = int(request.form.get("price",""))
            stock = int(request.form.get("stock",""))
            if not name or not category or price < 1 or stock < 0:
                raise ValueError
        except ValueError:
            flash("Enter a valid name, category, positive price and non-negative stock.")
            return redirect(request.url)
        with db() as con:
            if p:
                con.execute("UPDATE products SET name=?,category=?,description=?,price=?,stock=?,emoji=?,active=? WHERE id=?",
                            (name,category,description,price,stock,emoji,active,p["id"]))
            else:
                con.execute("INSERT INTO products(name,category,description,price,stock,emoji,active) VALUES(?,?,?,?,?,?,?)",
                            (name,category,description,price,stock,emoji,active))
        flash("Product saved.")
        return redirect(url_for("admin"))
    return page(PRODUCT_FORM, title="Product Editor", heading="Edit Product" if p else "Add Product", p=p)

@app.route("/admin/products/new", methods=["GET","POST"])
@admin_required
def admin_product_new():
    return save_product()

@app.route("/admin/products/<int:product_id>/edit", methods=["GET","POST"])
@admin_required
def admin_product_edit(product_id):
    with db() as con:
        p = con.execute("SELECT * FROM products WHERE id=?", (product_id,)).fetchone()
    if not p:
        abort(404)
    return save_product(p)

@app.route("/admin/orders/<int:order_id>/status", methods=["POST"])
@admin_required
def admin_order_status(order_id):
    status = request.form.get("status","")
    if status not in {"Pending","Confirmed","Shipped","Delivered","Cancelled"}:
        flash("Invalid order status.")
    else:
        with db() as con:
            cur = con.execute("UPDATE orders SET status=? WHERE id=?", (status,order_id))
            if cur.rowcount:
                flash("Order status updated.")
            else:
                flash("Order not found.")
    return redirect(url_for("admin"))

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--create-admin":
        print("Create an Amjad Garments admin account")
        name = input("Admin name: ").strip()
        email = input("Admin email: ").strip().lower()
        password = getpass("Admin password (minimum 12 characters): ")
        if not name or "@" not in email or len(password) < 12:
            print("Invalid details. Use a name, valid email, and password of at least 12 characters.")
            sys.exit(1)
        try:
            with db() as con:
                con.execute(
                    "INSERT INTO users(name,email,password_hash,is_admin) VALUES(?,?,?,1)",
                    (name, email, generate_password_hash(password))
                )
            print("Admin account created. Start the website with: python app.py")
        except sqlite3.IntegrityError:
            print("That email already exists. Use a different email.")
        sys.exit(0)
    # Local development only. Do not expose Flask debug mode on the public internet.
    app.run(host="127.0.0.1", port=5000, debug=True)
