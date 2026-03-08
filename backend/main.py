"""
Confinement Centre - FastAPI Backend
=====================================
Run with:  uvicorn main:app --reload
API docs:  http://localhost:8000/docs
"""

from fastapi import FastAPI, HTTPException, Depends, Header, Body
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional
import sqlite3
import hashlib
import secrets
from datetime import date

# ─────────────────────────────────────────────
# App Setup
# ─────────────────────────────────────────────
app = FastAPI(title="Confinement Centre API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DB_PATH = "confinement.db"
SESSIONS = {}   # token -> user_id  (in-memory session store)

TODAY = str(date.today())


# ─────────────────────────────────────────────
# Database Helpers
# ─────────────────────────────────────────────
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def hash_pw(pw: str) -> str:
    return hashlib.sha256(pw.encode()).hexdigest()


def init_db():
    conn = get_db()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            username     TEXT    UNIQUE NOT NULL,
            password_hash TEXT   NOT NULL,
            name         TEXT    NOT NULL,
            role         TEXT    NOT NULL CHECK(role IN ('mother','nurse','chef','cleaner','sales','admin')),
            mother_id    INTEGER REFERENCES mothers(id)
        );

        CREATE TABLE IF NOT EXISTS mothers (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            name       TEXT NOT NULL,
            baby_name  TEXT NOT NULL,
            room       TEXT NOT NULL,
            baby_dob   TEXT,
            check_in   TEXT,
            check_out  TEXT
        );

        CREATE TABLE IF NOT EXISTS meal_plans (
            id        INTEGER PRIMARY KEY AUTOINCREMENT,
            mother_id INTEGER REFERENCES mothers(id),
            week      TEXT NOT NULL,
            day       TEXT NOT NULL,
            day_index INTEGER NOT NULL,
            breakfast TEXT,
            lunch     TEXT,
            dinner    TEXT,
            snack     TEXT
        );

        CREATE TABLE IF NOT EXISTS feeding_records (
            id        INTEGER PRIMARY KEY AUTOINCREMENT,
            mother_id INTEGER REFERENCES mothers(id),
            date      TEXT NOT NULL,
            time      TEXT NOT NULL,
            type      TEXT NOT NULL,
            amount    TEXT NOT NULL,
            duration  TEXT,
            notes     TEXT
        );

        CREATE TABLE IF NOT EXISTS bowel_records (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            mother_id   INTEGER REFERENCES mothers(id),
            date        TEXT NOT NULL,
            time        TEXT NOT NULL,
            color       TEXT NOT NULL,
            consistency TEXT NOT NULL,
            notes       TEXT
        );

        CREATE TABLE IF NOT EXISTS jaundice_records (
            id        INTEGER PRIMARY KEY AUTOINCREMENT,
            mother_id INTEGER REFERENCES mothers(id),
            date      TEXT NOT NULL,
            level     REAL NOT NULL,
            notes     TEXT
        );

        CREATE TABLE IF NOT EXISTS vitals_records (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            mother_id   INTEGER REFERENCES mothers(id),
            date        TEXT NOT NULL,
            weight      TEXT,
            height      TEXT,
            head_circ   TEXT,
            shower_time TEXT,
            notes       TEXT
        );

        CREATE TABLE IF NOT EXISTS activities (
            id       INTEGER PRIMARY KEY AUTOINCREMENT,
            name     TEXT NOT NULL,
            icon     TEXT,
            time     TEXT,
            duration TEXT,
            days     TEXT
        );

        CREATE TABLE IF NOT EXISTS activity_bookings (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            mother_id   INTEGER REFERENCES mothers(id),
            activity_id INTEGER REFERENCES activities(id),
            date        TEXT NOT NULL,
            status      TEXT DEFAULT 'confirmed'
        );

        CREATE TABLE IF NOT EXISTS receipts (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            submitted_by INTEGER REFERENCES users(id),
            description  TEXT NOT NULL,
            amount       REAL NOT NULL,
            date         TEXT NOT NULL,
            status       TEXT DEFAULT 'pending'
        );

        CREATE TABLE IF NOT EXISTS inventory (
            id        INTEGER PRIMARY KEY AUTOINCREMENT,
            item      TEXT NOT NULL,
            quantity  REAL NOT NULL,
            unit      TEXT NOT NULL,
            low_alert REAL DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS notes (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            from_user_id INTEGER REFERENCES users(id),
            from_name    TEXT NOT NULL,
            to_mother_id INTEGER REFERENCES mothers(id),
            message      TEXT NOT NULL,
            date         TEXT NOT NULL,
            is_read      INTEGER DEFAULT 0
        );
    """)
    conn.commit()
    conn.close()


def seed_db():
    conn = get_db()
    if conn.execute("SELECT COUNT(*) FROM users").fetchone()[0] > 0:
        conn.close()
        return

    c = conn.cursor()

    # Mothers
    c.execute("INSERT INTO mothers (name,baby_name,room,baby_dob,check_in,check_out) VALUES (?,?,?,?,?,?)",
              ("Sarah Chen", "Baby Boy Chen", "101", "2026-02-28", "2026-03-01", "2026-03-28"))
    m1 = c.lastrowid
    c.execute("INSERT INTO mothers (name,baby_name,room,baby_dob,check_in,check_out) VALUES (?,?,?,?,?,?)",
              ("Lisa Wong", "Baby Girl Wong", "102", "2026-03-02", "2026-03-03", "2026-03-30"))
    m2 = c.lastrowid

    # Users
    for u in [
        ("mother1",  hash_pw("pass"),  "Sarah Chen",     "mother",  m1),
        ("mother2",  hash_pw("pass"),  "Lisa Wong",      "mother",  m2),
        ("nurse1",   hash_pw("pass"),  "Mary Lim",       "nurse",   None),
        ("chef1",    hash_pw("pass"),  "Ahmad Razif",    "chef",    None),
        ("cleaner1", hash_pw("pass"),  "Siti Rahimah",   "cleaner", None),
        ("sales1",   hash_pw("pass"),  "Jason Tan",      "sales",   None),
        ("admin",    hash_pw("admin"), "Administrator",  "admin",   None),
    ]:
        c.execute("INSERT INTO users (username,password_hash,name,role,mother_id) VALUES (?,?,?,?,?)", u)

    chef_id = c.execute("SELECT id FROM users WHERE username='chef1'").fetchone()[0]
    nurse_id = c.execute("SELECT id FROM users WHERE username='nurse1'").fetchone()[0]

    # Meal plans – Mother 1
    week = "4 – 10 Mar 2026"
    for i, (day, b, l, d, s) in enumerate([
        ("Mon","Millet porridge with red dates & longan","Sesame ginger chicken rice","Pork rib black bean soup","Longan red date tea"),
        ("Tue","Oatmeal with wolfberries & honey","Steamed sea bass with ginger","Pork trotter black vinegar","Sesame walnut soup"),
        ("Wed","Red bean glutinous rice ball soup","Ginger fried rice with egg","Double boiled herbal chicken soup","Papaya milk"),
        ("Thu","Sesame oil vermicelli with egg","Braised pork belly with tofu","Fish head tofu soup","Longan red date tea"),
        ("Fri","Oatmeal with red dates","Ginger spring onion steamed fish","Pork rib lotus root soup","Almond milk"),
        ("Sat","Congee with century egg & pork","Steamed chicken with mushroom","Black chicken herbal soup","Red bean dessert"),
        ("Sun","Millet porridge with wolfberries","Pan-fried fish with ginger soy","Pork bone carrot soup","Papaya milk"),
    ]):
        c.execute("INSERT INTO meal_plans (mother_id,week,day,day_index,breakfast,lunch,dinner,snack) VALUES (?,?,?,?,?,?,?,?)",
                  (m1, week, day, i, b, l, d, s))

    # Meal plans – Mother 2
    for i, (day, b, l, d, s) in enumerate([
        ("Mon","Red date oatmeal","Ginger chicken vermicelli","Lotus root pork rib soup","Longan tea"),
        ("Tue","Porridge with wolfberries","Braised pork rice","Fish tofu soup","Sesame soup"),
        ("Wed","Glutinous rice balls","Steamed fish rice","Herbal chicken soup","Papaya milk"),
        ("Thu","Millet porridge","Ginger fried rice","Black bean pork soup","Red date tea"),
        ("Fri","Oatmeal red dates","Sesame chicken rice","Double boiled chicken soup","Almond milk"),
        ("Sat","Congee with egg","Braised chicken mushroom","Pork trotter vinegar","Red bean dessert"),
        ("Sun","Sesame vermicelli soup","Pan-fried fish","Lotus root soup","Papaya milk"),
    ]):
        c.execute("INSERT INTO meal_plans (mother_id,week,day,day_index,breakfast,lunch,dinner,snack) VALUES (?,?,?,?,?,?,?,?)",
                  (m2, week, day, i, b, l, d, s))

    # Feeding records
    for r in [
        (m1,"2026-03-07","06:00","Breast milk","90","15",""),
        (m1,"2026-03-07","09:00","Formula","120","","Baby seemed hungry"),
        (m1,"2026-03-07","12:00","Breast milk","80","12",""),
        (m2,"2026-03-07","07:00","Formula","100","",""),
        (m2,"2026-03-07","10:00","Breast milk","85","10",""),
    ]:
        c.execute("INSERT INTO feeding_records (mother_id,date,time,type,amount,duration,notes) VALUES (?,?,?,?,?,?,?)", r)

    # Bowel records
    for r in [
        (m1,"2026-03-07","07:30","Yellow","Soft","Normal"),
        (m1,"2026-03-07","13:00","Green","Loose","Slightly loose"),
        (m2,"2026-03-07","08:00","Yellow","Soft","Normal"),
    ]:
        c.execute("INSERT INTO bowel_records (mother_id,date,time,color,consistency,notes) VALUES (?,?,?,?,?,?)", r)

    # Jaundice records
    for r in [
        (m1,"2026-03-01",12.5,"Within normal range"),
        (m1,"2026-03-02",14.2,"Slightly elevated"),
        (m1,"2026-03-03",13.8,"Improving"),
        (m1,"2026-03-04",12.1,"Decreasing"),
        (m1,"2026-03-05",10.5,"Good progress"),
        (m1,"2026-03-06",9.2,"Normal range"),
        (m1,"2026-03-07",8.8,"Excellent"),
        (m2,"2026-03-03",11.0,"Normal"),
        (m2,"2026-03-04",13.5,"Monitor closely"),
        (m2,"2026-03-05",12.8,"Stable"),
        (m2,"2026-03-06",11.2,"Improving"),
        (m2,"2026-03-07",10.1,"Good"),
    ]:
        c.execute("INSERT INTO jaundice_records (mother_id,date,level,notes) VALUES (?,?,?,?)", r)

    # Vitals
    for r in [
        (m1,"2026-03-01","3.20","50.0","34.0","09:00",""),
        (m1,"2026-03-04","3.35","50.5","34.2","09:30",""),
        (m1,"2026-03-07","3.50","51.0","34.5","09:15","Good weight gain"),
        (m2,"2026-03-03","2.90","48.0","33.0","10:00",""),
        (m2,"2026-03-07","3.10","48.5","33.2","10:30",""),
    ]:
        c.execute("INSERT INTO vitals_records (mother_id,date,weight,height,head_circ,shower_time,notes) VALUES (?,?,?,?,?,?,?)", r)

    # Activities
    for a in [
        ("Yoga for New Moms",       "🧘","10:00 AM","45 mins","Mon, Wed, Fri"),
        ("Baby Massage Class",       "👶","2:00 PM", "30 mins","Tue, Thu"),
        ("Postnatal Nutrition Talk", "🥗","4:00 PM", "60 mins","Wednesday"),
        ("Breastfeeding Workshop",   "🤱","11:00 AM","45 mins","Saturday"),
        ("Postnatal Exercise",       "💪","9:00 AM", "30 mins","Daily"),
    ]:
        c.execute("INSERT INTO activities (name,icon,time,duration,days) VALUES (?,?,?,?,?)", a)

    c.execute("INSERT INTO activity_bookings (mother_id,activity_id,date,status) VALUES (?,?,?,?)", (m1,1,"2026-03-09","confirmed"))
    c.execute("INSERT INTO activity_bookings (mother_id,activity_id,date,status) VALUES (?,?,?,?)", (m1,4,"2026-03-14","confirmed"))

    c.execute("INSERT INTO receipts (submitted_by,description,amount,date,status) VALUES (?,?,?,?,?)",
              (chef_id,"Ginger, herbs & spices for confinement meals",85.50,"2026-03-05","pending"))
    c.execute("INSERT INTO receipts (submitted_by,description,amount,date,status) VALUES (?,?,?,?,?)",
              (chef_id,"Fresh vegetables and protein ingredients",120.00,"2026-03-06","approved"))

    for i in [
        ("Ginger",2.0,"kg",0.5), ("Sesame Oil",3,"bottles",1), ("Red Dates",500,"g",200),
        ("Wolfberries",200,"g",100), ("Black Vinegar",2,"bottles",1),
        ("Pork Rib",5.0,"kg",2), ("Chicken",8.0,"kg",3), ("Pork Trotter",4,"units",2),
    ]:
        c.execute("INSERT INTO inventory (item,quantity,unit,low_alert) VALUES (?,?,?,?)", i)

    c.execute("INSERT INTO notes (from_user_id,from_name,to_mother_id,message,date,is_read) VALUES (?,?,?,?,?,?)",
              (nurse_id,"Mary Lim",m1,"Baby's jaundice is improving well. Keep up breastfeeding every 2–3 hours!","2026-03-06",0))
    c.execute("INSERT INTO notes (from_user_id,from_name,to_mother_id,message,date,is_read) VALUES (?,?,?,?,?,?)",
              (nurse_id,"Mary Lim",m1,"Please allow morning sunlight exposure for 15 minutes between 8–9am.","2026-03-07",0))

    conn.commit()
    conn.close()
    print("✅ Database seeded with sample data.")


# Run on startup
init_db()
seed_db()


# ─────────────────────────────────────────────
# Auth
# ─────────────────────────────────────────────
def get_current_user(authorization: Optional[str] = Header(None)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Not authenticated")
    token = authorization[7:]
    user_id = SESSIONS.get(token)
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    conn = get_db()
    user = conn.execute("SELECT id,username,name,role,mother_id FROM users WHERE id=?", (user_id,)).fetchone()
    conn.close()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return dict(user)


@app.post("/api/auth/login")
def login(data: dict = Body(...)):
    conn = get_db()
    user = conn.execute(
        "SELECT id,username,name,role,mother_id FROM users WHERE username=? AND password_hash=?",
        (data.get("username"), hash_pw(data.get("password", "")))
    ).fetchone()
    conn.close()
    if not user:
        raise HTTPException(status_code=401, detail="Invalid username or password")
    token = secrets.token_hex(32)
    SESSIONS[token] = dict(user)["id"]
    return {"token": token, "user": dict(user)}


@app.post("/api/auth/logout")
def logout(authorization: Optional[str] = Header(None)):
    if authorization and authorization.startswith("Bearer "):
        SESSIONS.pop(authorization[7:], None)
    return {"success": True}


# ─────────────────────────────────────────────
# Users  (Admin only)
# ─────────────────────────────────────────────
@app.get("/api/users")
def get_users(cu=Depends(get_current_user)):
    if cu["role"] != "admin":
        raise HTTPException(403, "Admin only")
    conn = get_db()
    rows = conn.execute("SELECT id,username,name,role,mother_id FROM users").fetchall()
    conn.close()
    return [dict(r) for r in rows]


@app.post("/api/users")
def create_user(data: dict = Body(...), cu=Depends(get_current_user)):
    if cu["role"] != "admin":
        raise HTTPException(403, "Admin only")
    conn = get_db()
    try:
        conn.execute(
            "INSERT INTO users (username,password_hash,name,role,mother_id) VALUES (?,?,?,?,?)",
            (data["username"], hash_pw(data["password"]), data["name"], data["role"], data.get("mother_id"))
        )
        conn.commit()
        uid = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
        user = conn.execute("SELECT id,username,name,role,mother_id FROM users WHERE id=?", (uid,)).fetchone()
        conn.close()
        return dict(user)
    except Exception as e:
        conn.close()
        raise HTTPException(400, str(e))


@app.patch("/api/users/{uid}/role")
def update_role(uid: int, data: dict = Body(...), cu=Depends(get_current_user)):
    if cu["role"] != "admin":
        raise HTTPException(403, "Admin only")
    conn = get_db()
    conn.execute("UPDATE users SET role=? WHERE id=?", (data["role"], uid))
    conn.commit()
    conn.close()
    return {"success": True}


# ─────────────────────────────────────────────
# Mothers
# ─────────────────────────────────────────────
@app.get("/api/mothers")
def get_mothers(cu=Depends(get_current_user)):
    conn = get_db()
    rows = conn.execute("SELECT * FROM mothers").fetchall()
    conn.close()
    return [dict(r) for r in rows]


@app.post("/api/mothers")
def create_mother(data: dict = Body(...), cu=Depends(get_current_user)):
    if cu["role"] != "admin":
        raise HTTPException(403, "Admin only")
    conn = get_db()
    conn.execute("INSERT INTO mothers (name,baby_name,room,baby_dob,check_in,check_out) VALUES (?,?,?,?,?,?)",
                 (data["name"], data["baby_name"], data["room"], data.get("baby_dob"), data.get("check_in"), data.get("check_out")))
    conn.commit()
    mid = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
    m = conn.execute("SELECT * FROM mothers WHERE id=?", (mid,)).fetchone()
    conn.close()
    return dict(m)


# ─────────────────────────────────────────────
# Meal Plans
# ─────────────────────────────────────────────
@app.get("/api/meal-plans/{mother_id}")
def get_meal_plan(mother_id: int, cu=Depends(get_current_user)):
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM meal_plans WHERE mother_id=? ORDER BY day_index", (mother_id,)
    ).fetchall()
    conn.close()
    if not rows:
        return None
    return {"mother_id": mother_id, "week": rows[0]["week"], "meals": [dict(r) for r in rows]}


@app.put("/api/meal-plans/{mother_id}/{day_index}")
def update_meal(mother_id: int, day_index: int, data: dict = Body(...), cu=Depends(get_current_user)):
    if cu["role"] not in ("chef", "admin"):
        raise HTTPException(403, "Chef or Admin only")
    conn = get_db()
    existing = conn.execute(
        "SELECT id FROM meal_plans WHERE mother_id=? AND day_index=?", (mother_id, day_index)
    ).fetchone()
    if existing:
        conn.execute(
            "UPDATE meal_plans SET breakfast=?,lunch=?,dinner=?,snack=? WHERE mother_id=? AND day_index=?",
            (data.get("breakfast"), data.get("lunch"), data.get("dinner"), data.get("snack"), mother_id, day_index)
        )
    else:
        conn.execute(
            "INSERT INTO meal_plans (mother_id,week,day,day_index,breakfast,lunch,dinner,snack) VALUES (?,?,?,?,?,?,?,?)",
            (mother_id, data.get("week",""), data.get("day",""), day_index,
             data.get("breakfast"), data.get("lunch"), data.get("dinner"), data.get("snack"))
        )
    conn.commit()
    conn.close()
    return {"success": True}


# ─────────────────────────────────────────────
# Feeding Records
# ─────────────────────────────────────────────
@app.get("/api/feeding")
def get_all_feeding(filter_date: Optional[str] = None, cu=Depends(get_current_user)):
    conn = get_db()
    if filter_date:
        rows = conn.execute("SELECT * FROM feeding_records WHERE date=? ORDER BY mother_id,time", (filter_date,)).fetchall()
    else:
        rows = conn.execute("SELECT * FROM feeding_records ORDER BY date DESC,time").fetchall()
    conn.close()
    return [dict(r) for r in rows]


@app.get("/api/feeding/{mother_id}")
def get_feeding(mother_id: int, filter_date: Optional[str] = None, cu=Depends(get_current_user)):
    conn = get_db()
    if filter_date:
        rows = conn.execute("SELECT * FROM feeding_records WHERE mother_id=? AND date=? ORDER BY time", (mother_id, filter_date)).fetchall()
    else:
        rows = conn.execute("SELECT * FROM feeding_records WHERE mother_id=? ORDER BY date DESC,time", (mother_id,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


@app.post("/api/feeding")
def add_feeding(data: dict = Body(...), cu=Depends(get_current_user)):
    conn = get_db()
    conn.execute(
        "INSERT INTO feeding_records (mother_id,date,time,type,amount,duration,notes) VALUES (?,?,?,?,?,?,?)",
        (data["mother_id"], data.get("date", TODAY), data["time"], data["type"],
         data["amount"], data.get("duration",""), data.get("notes",""))
    )
    conn.commit()
    rid = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
    r = conn.execute("SELECT * FROM feeding_records WHERE id=?", (rid,)).fetchone()
    conn.close()
    return dict(r)


# ─────────────────────────────────────────────
# Bowel Records
# ─────────────────────────────────────────────
@app.get("/api/bowel/{mother_id}")
def get_bowel(mother_id: int, filter_date: Optional[str] = None, cu=Depends(get_current_user)):
    conn = get_db()
    if filter_date:
        rows = conn.execute("SELECT * FROM bowel_records WHERE mother_id=? AND date=? ORDER BY time", (mother_id, filter_date)).fetchall()
    else:
        rows = conn.execute("SELECT * FROM bowel_records WHERE mother_id=? ORDER BY date DESC,time", (mother_id,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


@app.post("/api/bowel")
def add_bowel(data: dict = Body(...), cu=Depends(get_current_user)):
    conn = get_db()
    conn.execute(
        "INSERT INTO bowel_records (mother_id,date,time,color,consistency,notes) VALUES (?,?,?,?,?,?)",
        (data["mother_id"], data.get("date", TODAY), data["time"],
         data["color"], data["consistency"], data.get("notes",""))
    )
    conn.commit()
    rid = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
    r = conn.execute("SELECT * FROM bowel_records WHERE id=?", (rid,)).fetchone()
    conn.close()
    return dict(r)


# ─────────────────────────────────────────────
# Jaundice Records
# ─────────────────────────────────────────────
@app.get("/api/jaundice/{mother_id}")
def get_jaundice(mother_id: int, cu=Depends(get_current_user)):
    conn = get_db()
    rows = conn.execute("SELECT * FROM jaundice_records WHERE mother_id=? ORDER BY date", (mother_id,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


@app.post("/api/jaundice")
def add_jaundice(data: dict = Body(...), cu=Depends(get_current_user)):
    conn = get_db()
    conn.execute(
        "INSERT INTO jaundice_records (mother_id,date,level,notes) VALUES (?,?,?,?)",
        (data["mother_id"], data.get("date", TODAY), data["level"], data.get("notes",""))
    )
    conn.commit()
    rid = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
    r = conn.execute("SELECT * FROM jaundice_records WHERE id=?", (rid,)).fetchone()
    conn.close()
    return dict(r)


# ─────────────────────────────────────────────
# Vitals Records
# ─────────────────────────────────────────────
@app.get("/api/vitals/{mother_id}")
def get_vitals(mother_id: int, cu=Depends(get_current_user)):
    conn = get_db()
    rows = conn.execute("SELECT * FROM vitals_records WHERE mother_id=? ORDER BY date DESC", (mother_id,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


@app.post("/api/vitals")
def add_vitals(data: dict = Body(...), cu=Depends(get_current_user)):
    conn = get_db()
    conn.execute(
        "INSERT INTO vitals_records (mother_id,date,weight,height,head_circ,shower_time,notes) VALUES (?,?,?,?,?,?,?)",
        (data["mother_id"], data.get("date", TODAY), data.get("weight"), data.get("height"),
         data.get("head_circ"), data.get("shower_time"), data.get("notes",""))
    )
    conn.commit()
    rid = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
    r = conn.execute("SELECT * FROM vitals_records WHERE id=?", (rid,)).fetchone()
    conn.close()
    return dict(r)


# ─────────────────────────────────────────────
# Activities & Bookings
# ─────────────────────────────────────────────
@app.get("/api/activities")
def get_activities(cu=Depends(get_current_user)):
    conn = get_db()
    rows = conn.execute("SELECT * FROM activities").fetchall()
    conn.close()
    return [dict(r) for r in rows]


@app.get("/api/bookings/{mother_id}")
def get_bookings(mother_id: int, cu=Depends(get_current_user)):
    conn = get_db()
    rows = conn.execute("SELECT * FROM activity_bookings WHERE mother_id=? ORDER BY date", (mother_id,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


@app.post("/api/bookings")
def create_booking(data: dict = Body(...), cu=Depends(get_current_user)):
    conn = get_db()
    conn.execute(
        "INSERT INTO activity_bookings (mother_id,activity_id,date,status) VALUES (?,?,?,?)",
        (data["mother_id"], data["activity_id"], data["date"], "confirmed")
    )
    conn.commit()
    rid = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
    r = conn.execute("SELECT * FROM activity_bookings WHERE id=?", (rid,)).fetchone()
    conn.close()
    return dict(r)


# ─────────────────────────────────────────────
# Receipts
# ─────────────────────────────────────────────
@app.get("/api/receipts")
def get_receipts(cu=Depends(get_current_user)):
    conn = get_db()
    if cu["role"] == "admin":
        rows = conn.execute(
            "SELECT r.*,u.name AS submitter_name FROM receipts r LEFT JOIN users u ON r.submitted_by=u.id ORDER BY r.date DESC"
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT r.*,u.name AS submitter_name FROM receipts r LEFT JOIN users u ON r.submitted_by=u.id WHERE r.submitted_by=? ORDER BY r.date DESC",
            (cu["id"],)
        ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


@app.post("/api/receipts")
def create_receipt(data: dict = Body(...), cu=Depends(get_current_user)):
    conn = get_db()
    conn.execute(
        "INSERT INTO receipts (submitted_by,description,amount,date,status) VALUES (?,?,?,?,?)",
        (cu["id"], data["description"], data["amount"], data.get("date", TODAY), "pending")
    )
    conn.commit()
    rid = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
    r = conn.execute("SELECT * FROM receipts WHERE id=?", (rid,)).fetchone()
    conn.close()
    return dict(r)


@app.patch("/api/receipts/{rid}")
def update_receipt(rid: int, data: dict = Body(...), cu=Depends(get_current_user)):
    if cu["role"] != "admin":
        raise HTTPException(403, "Admin only")
    conn = get_db()
    conn.execute("UPDATE receipts SET status=? WHERE id=?", (data["status"], rid))
    conn.commit()
    conn.close()
    return {"success": True}


# ─────────────────────────────────────────────
# Inventory
# ─────────────────────────────────────────────
@app.get("/api/inventory")
def get_inventory(cu=Depends(get_current_user)):
    conn = get_db()
    rows = conn.execute("SELECT * FROM inventory ORDER BY item").fetchall()
    conn.close()
    return [dict(r) for r in rows]


@app.post("/api/inventory")
def add_inventory(data: dict = Body(...), cu=Depends(get_current_user)):
    conn = get_db()
    conn.execute(
        "INSERT INTO inventory (item,quantity,unit,low_alert) VALUES (?,?,?,?)",
        (data["item"], data["quantity"], data["unit"], data.get("low_alert", 0))
    )
    conn.commit()
    rid = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
    r = conn.execute("SELECT * FROM inventory WHERE id=?", (rid,)).fetchone()
    conn.close()
    return dict(r)


@app.patch("/api/inventory/{iid}")
def update_inventory(iid: int, data: dict = Body(...), cu=Depends(get_current_user)):
    conn = get_db()
    if "quantity" in data:
        conn.execute("UPDATE inventory SET quantity=? WHERE id=?", (data["quantity"], iid))
    conn.commit()
    conn.close()
    return {"success": True}


# ─────────────────────────────────────────────
# Notes
# ─────────────────────────────────────────────
@app.get("/api/notes/{mother_id}")
def get_notes(mother_id: int, cu=Depends(get_current_user)):
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM notes WHERE to_mother_id=? ORDER BY date DESC,id DESC", (mother_id,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


@app.get("/api/notes/sent/{user_id}")
def get_sent_notes(user_id: int, cu=Depends(get_current_user)):
    conn = get_db()
    rows = conn.execute(
        "SELECT n.*,m.name AS mother_name FROM notes n LEFT JOIN mothers m ON n.to_mother_id=m.id WHERE n.from_user_id=? ORDER BY n.date DESC",
        (user_id,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


@app.post("/api/notes")
def create_note(data: dict = Body(...), cu=Depends(get_current_user)):
    conn = get_db()
    conn.execute(
        "INSERT INTO notes (from_user_id,from_name,to_mother_id,message,date,is_read) VALUES (?,?,?,?,?,?)",
        (cu["id"], cu["name"], data["to_mother_id"], data["message"], data.get("date", TODAY), 0)
    )
    conn.commit()
    rid = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
    r = conn.execute("SELECT * FROM notes WHERE id=?", (rid,)).fetchone()
    conn.close()
    return dict(r)


@app.patch("/api/notes/{nid}/read")
def mark_read(nid: int, cu=Depends(get_current_user)):
    conn = get_db()
    conn.execute("UPDATE notes SET is_read=1 WHERE id=?", (nid,))
    conn.commit()
    conn.close()
    return {"success": True}


# ─────────────────────────────────────────────
# Entry point
# ─────────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn
    import os
    port = int(os.environ.get("PORT", 8000))
    print("🌸 Starting Confinement Centre API...")
    print(f"📖 API Docs: http://localhost:{port}/docs")
    uvicorn.run(app, host="0.0.0.0", port=port)
