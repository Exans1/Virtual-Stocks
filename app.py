import os

from cs50 import SQL
from flask import Flask, flash, redirect, render_template, request, session
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.security import check_password_hash, generate_password_hash

from helpers import apology, login_required, lookup, usd

# Configure application
app = Flask(__name__)

# Ensure templates are auto-reloaded
app.config["TEMPLATES_AUTO_RELOAD"] = True

# Custom filter
app.jinja_env.filters["usd"] = usd

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///finance.db")

# Make sure API key is set
if not os.environ.get("API_KEY"):
    raise RuntimeError("API_KEY not set")


@app.after_request
def after_request(response):
    """Ensure responses aren't cached"""
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response


@app.route("/", methods=["GET", "POST"])
@login_required
def index():
    """Show portfolio of stocks"""

    if request.method == "GET":
        owns = shares_owned()
        leaders = leader_board()
        total = 0
        for symbol, shares in owns.items():
            result = lookup(symbol)
            name, price = result["name"], result["price"]
            stock_value = shares * price
            total += stock_value
            owns[symbol] = (name, shares, usd(price), usd(stock_value))
        cash = db.execute("SELECT cash FROM users WHERE id = ? ", session["user_id"])[0]['cash']
        total += cash
        db.execute("UPDATE users SET total = ? WHERE id = ? ", total, session["user_id"])
        change = total - 10000
        if change < 0:
            x = True
        else:
            x = False
        return render_template("index.html", owns = owns, cash = usd(cash), total = usd(total), change = usd(abs(change)), x = x, leaders = leaders)


@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():
    """Buy shares of stock"""
    if request.method == "POST":
        shares = request.form.get("shares")
        sinfo = lookup(request.form.get("symbol"))
        if not sinfo:
            return render_template("buy.html", invalid1=True, symbol = request.form.get("symbol"))
        if not request.form.get("shares"):
            return render_template("buy.html", invalids=True, symbol = "You must enter the number of shares you wish to purchase!")
        if shares.isalpha():
            return render_template("buy.html", invalids=True, symbol = "You must enter a number!")
        if float(shares)%1 != 0:
            return render_template("buy.html", invalids=True, symbol = "You must enter a whole number!")
        if int(shares) <= 0:
            return render_template("buy.html", invalids=True, symbol = "You must enter a positive number!")
        else:
            price = sinfo["price"]
            symbol = sinfo["symbol"]
            shares = int(request.form.get("shares"))
            user_id = session["user_id"]
            cash = db.execute("SELECT cash FROM users WHERE id = ?", user_id)[0]['cash']

            # check if user can afford the purchase
            remain = cash - price * shares
            if remain < 0:
                return render_template("buy.html", nomoney=True, symbol=symbol, cash=usd(cash), remain=usd(-remain), shares=shares, amount= usd(price*shares))

            # deduct order cost from users cash balance
            db.execute("UPDATE users SET cash = ? WHERE id = ?", remain, user_id)

            # create stock file in table stocks
            db.execute("INSERT INTO stocks (user_id, symbol, shares, price) VALUES (?, ?, ?, ?)", user_id, symbol, shares, price)

            return redirect("/")

    else:
        return render_template("buy.html")


@app.route("/history", methods=["GET", "POST"])
@login_required
def history():
    """Show history of transactions"""
    if request.method == "POST":
        leaders = request.form.get("lead")
        leader_ign = request.form.get("lead_ign")
        rows = db.execute("SELECT symbol, shares, price, time_stamp FROM stocks WHERE user_id = ?", leaders )
        return render_template("history.html", rows = rows, name = leader_ign, names=True)
    else:
        rows = db.execute("SELECT symbol, shares, price, time_stamp FROM stocks WHERE user_id = ?", session["user_id"] )
        return render_template("history.html", rows = rows, nots=True)


@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("username"):
            return render_template("login.html", invalids=True, symbol="Username")

        # Ensure password was submitted
        elif not request.form.get("password"):
            return render_template("login.html", invalids=True, symbol="Password")

        # Query database for username
        rows = db.execute("SELECT * FROM users WHERE username LIKE ?", request.form.get("username"))
        if len(rows) != 1:
            return render_template("login.html", invalid=True, symbol="Username")

        # Ensure username exists and password is correct
        if not check_password_hash(rows[0]["hash"], request.form.get("password")):
            return render_template("login.html", invalid=True, symbol="Password")

        # Remember which user has logged in
        session["user_id"] = rows[0]["id"]

        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")


@app.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/")


@app.route("/quote", methods=["GET", "POST"])
@login_required
def quote():
    owns = shares_owned()
    total = 0
    for symbol, shares in owns.items():
        result = lookup(symbol)
        name, price = result["name"], result["price"]
        stock_value = shares * price
        total += stock_value
        owns[symbol] = (name, shares, usd(price), usd(stock_value))
    cash = db.execute("SELECT cash FROM users WHERE id = ? ", session["user_id"])[0]['cash']
    total += cash
    """Get stock quote."""
    if request.method == "POST":
        if not request.form.get("symbol"):
            return render_template("quote.html",owns=owns, cash= usd(cash), total = usd(total))
        else:
            symbol = lookup(request.form.get("symbol"))
            if not symbol:
                symbol = request.form.get("symbol")
                return render_template("quote.html", invalid=True, symbol=symbol,owns=owns, cash= usd(cash), total = usd(total))
            return render_template("quoted.html", symbol=request.form.get("symbol"), price=usd(lookup(request.form.get("symbol"))["price"]), name=lookup(request.form.get("symbol"))["name"],owns=owns, cash= usd(cash), total = usd(total))
    else:

        return render_template("quote.html",owns=owns, cash= usd(cash), total = usd(total))

@app.route("/register", methods=["GET", "POST"])
def register():
    """Registers user"""

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("username"):
            symbol = request.form.get("username")
            return render_template("register.html", invalid=True, symbol="username")

        # Ensure password was submitted
        elif not request.form.get("password"):
            return render_template("register.html", invalid=True, symbol="password")

        elif request.form.get("confirmation") != request.form.get("password"):
            return render_template("register.html", invalid=True, symbol="password confirmation correctly")

        # Ensure password was submitted
        elif not request.form.get("firstname"):
            return render_template("register.html", invalid=True, symbol="firstname")

        # Ensure password was submitted
        elif not request.form.get("lastname"):
            return render_template("register.html", invalid=True, symbol="lastname")

        # Ensure password was submitted
        elif not request.form.get("email"):
            return render_template("register.html", invalid=True, symbol="email")

        # Query database for username
        rows = db.execute("SELECT * FROM users WHERE username LIKE ?", request.form.get("username"))

        #Query database for email
        ezmail = db.execute("SELECT * FROM users WHERE username LIKE ?", request.form.get("email"))

        # Ensure username does not exist                          or not check_password_hash(rows[0]["hash"], request.form.get("password")):
        if len(rows) == 1:
            return render_template("register.html", invalids=True, symbol="this username is taken")

        # Ensure email does not exist
        if len(ezmail) == 1:
            return render_template("register.html", invalids=True, symbol="this email is taken")

        # Create password hash
        password = generate_password_hash(request.form.get("password"))

        # Remember which user has logged in
        db.execute("INSERT INTO users (username, hash, firstname, lastname, email) VALUES(?, ?, ?, ?, ?)", request.form.get("username"), password, request.form.get("firstname"), request.form.get("lastname"), request.form.get("email"))

        # Query database for id
        rows = db.execute("SELECT * FROM users WHERE username LIKE ?", request.form.get("username"))

        # Remember which user has logged in
        session["user_id"] = rows[0]["id"]

        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("register.html")


@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
    """Sell shares of stock"""
    owns = shares_owned()
    if request.method == "POST":
        symbol = request.form.get("symbol")
        shares = int(request.form.get("shares"))

        # check whether there are sufficient shares to sell
        if owns[symbol] < shares:
            return render_template("sell.html", invalid2=True, symbol=symbol, shares=owns[symbol], owns = owns.keys())

        # Execute sell transaction: look up sell price, and add fund to cash,
        result = lookup(symbol)
        user_id = session["user_id"]
        cash = db.execute("SELECT cash FROM users WHERE id = ?", user_id)[0]['cash']
        price = result["price"]
        remain = cash + price * shares
        db.execute("UPDATE users SET cash = ? WHERE id = ?", remain, user_id)

        # Log the transaction into orders
        db.execute("INSERT INTO stocks (user_id, symbol, shares, price) VALUES (?, ?, ?, ?)", user_id, symbol, -shares, price)
        return redirect("/")
    else:
        return render_template("sell.html", owns = owns.keys())

@app.route("/setting", methods=["GET", "POST"])
@login_required
def setting():
    """Get stock quote."""
    info = db.execute("SELECT * FROM users WHERE id = ?", session["user_id"])
    new=request.form.get("new")
    change=request.form.get("change")
    for i in info:
        username, hash, name, email= i["username"], i["hash"], i["firstname"], i["email"]

    if request.method == "POST":
        #look for emply slots
        if not request.form.get("change"):
            return render_template("setting.html", invalid=True, name=name, username=username)
        if not request.form.get("new"):
            return render_template("setting.html", invalids=True, name=name, username=username)

        #change username
        if change == "username":
                # Query database for username
            rows = db.execute("SELECT * FROM users WHERE id = ?", session["user_id"])
            rowz = db.execute("SELECT * FROM users WHERE username LIKE ?", request.form.get("new"))
            if len(rowz) != 0:
                return render_template("setting.html", invalids1=True, name=name, txt="user name", username=username)

            # Ensure username exists and password is correct
            if not check_password_hash(rows[0]["hash"], request.form.get("cp")):
                return render_template("setting.html", invalids2=True, name=name, username=username)

            #update new username
            else:
                db.execute("UPDATE users SET username = ? WHERE id = ?", new, session["user_id"])
                return render_template("setting.html", name=name, username=username, hash=hash, email=email)

        #change password
        if change == "password":
            # Query database for username
            rows = db.execute("SELECT * FROM users WHERE username LIKE ?", username)

            # Ensure username exists and password is correct
            if not check_password_hash(rows[0]["hash"], request.form.get("cp")):
                return render_template("setting.html", invalids2=True, name=name, username=username)
            else:
                db.execute("UPDATE users SET hash = ? WHERE id = ?", generate_password_hash(new), session["user_id"])
                return render_template("setting.html", name=name, username=username, hash=hash, email=email)


        #change email
        if change == "email":
                # Query database for username
            rows = db.execute("SELECT * FROM users WHERE id = ?", session["user_id"])
            rowz = db.execute("SELECT * FROM users WHERE email LIKE ?", request.form.get("new"))
            if len(rowz) != 0:
                return render_template("setting.html", invalids1=True, name=name, txt="e-mail", username=username)

            # Ensure username exists and password is correct
            if not check_password_hash(rows[0]["hash"], request.form.get("cp")):
                return render_template("setting.html", invalids2=True, name=name, username=username)

            #update new username
            else:
                db.execute("UPDATE users SET email = ? WHERE id = ?", new, session["user_id"])
                return render_template("setting.html", name=name, username=username, hash=hash, email=email)

    else:
        return render_template("setting.html", name=name, username=username, hash=hash, email=email)


def shares_owned():
    """Helper function: Which stocks the user owns, and numbers of shares owned. Return: dictionary {symbol: qty}"""
    user_id = session["user_id"]
    owns = {}
    query = db.execute("SELECT symbol, shares FROM stocks WHERE user_id = ? ORDER BY symbol", user_id)
    for i in query:
        symbol, shares = i["symbol"], i["shares"]
        owns[symbol] = owns.setdefault(symbol, 0) + shares

    # filter zero-share stocks
    owns = {j: k for j, k in owns.items() if k != 0}
    return owns


def leader_board():
    """Helper function: Which stocks the user owns, and numbers of shares owned. Return: dictionary {symbol: qty}"""
    leaders = {}
    c=1
    query = db.execute("SELECT id, username, firstname, total FROM users ORDER BY total DESC LIMIT 5")
    for i in query:
        id, username, firstname, total = i["id"], i["username"], i["firstname"], i["total"]
        leaders[c] = id, username, firstname, usd(total)
        c+=1
    return leaders

