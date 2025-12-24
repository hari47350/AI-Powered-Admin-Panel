from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from fastapi.responses import FileResponse
from database import get_connection, create_tables
import csv

# ===============================
# CREATE APP FIRST
# ===============================
app = FastAPI()

# ===============================
# CORS (REQUIRED FOR FRONTEND)
# ===============================
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ===============================
# INIT DATABASE
# ===============================
create_tables()

# ===============================
# MODELS
# ===============================
class AIQuery(BaseModel):
    question: str

# ===============================
# BASIC ROUTES
# ===============================
@app.get("/")
def home():
    return {"status": "Backend is running"}

@app.get("/users")
def get_users():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id, name, email, last_login, role FROM users")
    users = cur.fetchall()
    conn.close()
    return users

@app.get("/stats")
def get_stats():
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("SELECT COUNT(*) FROM users")
    total = cur.fetchone()[0]

    cur.execute("""
        SELECT COUNT(*) FROM users
        WHERE last_login < date('now','-30 day')
    """)
    inactive = cur.fetchone()[0]

    conn.close()
    return {
        "total_users": total,
        "inactive_users": inactive
    }

# ===============================
# LOGIN
# ===============================
@app.post("/login")
def login(data: dict):
    username = data.get("username")
    password = data.get("password")

    if username == "admin" and password == "admin123":
        return {"role": "admin"}

    if username == "viewer" and password == "viewer123":
        return {"role": "viewer"}

    raise HTTPException(status_code=401, detail="Invalid credentials")

# ===============================
# EXPORT USERS CSV
# ===============================
@app.get("/export-users")
def export_users():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id, name, email, last_login, role FROM users")
    rows = cur.fetchall()
    conn.close()

    filename = "users.csv"
    with open(filename, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["ID", "Name", "Email", "Last Login", "Role"])
        writer.writerows(rows)

    return FileResponse(filename, media_type="text/csv", filename=filename)

# ===============================
# AI-STYLE INTENT INFERENCE
# ===============================
def infer_intent(question: str):
    q = question.lower()

    # All users
    if any(k in q for k in [
        "all users", "show users", "list users", "user list"
    ]):
        return "get_all_users"

    # Inactive users
    if any(k in q for k in [
        "inactive", "not logged", "not active", "dormant", "no recent activity"
    ]):
        return "get_inactive_users"

    # Active users
    if any(k in q for k in [
        "active users", "recent users", "recently active", "logged in recently"
    ]):
        return "get_active_users"

    # Counts
    if any(k in q for k in [
        "count", "how many", "total number", "number of"
    ]):
        if "admin" in q:
            return "get_admin_users"
        return "get_user_count"

    # Admin users
    if any(k in q for k in [
        "admin users", "administrators", "admin accounts"
    ]):
        return "get_admin_users"

    # Summary / overview
    if any(k in q for k in [
        "summary", "statistics", "overview", "dashboard", "status"
    ]):
        return "get_user_summary"

    return None

# ===============================
# AI QUERY ENDPOINT
# ===============================
@app.post("/ai-query")
def ai_query(data: AIQuery):
    intent = infer_intent(data.question)

    if not intent:
        return {"inference": "Could not understand the question", "result": []}

    conn = get_connection()
    cur = conn.cursor()

    if intent == "get_all_users":
        cur.execute("SELECT id, name, email, last_login, role FROM users")
        result = cur.fetchall()
        inference = "All users"

    elif intent == "get_inactive_users":
        cur.execute("""
            SELECT id, name, email, last_login, role
            FROM users
            WHERE last_login < date('now','-30 day')
        """)
        result = cur.fetchall()
        inference = "Inactive users (last 30 days)"

    elif intent == "get_active_users":
        cur.execute("""
            SELECT id, name, email, last_login, role
            FROM users
            WHERE last_login >= date('now','-30 day')
        """)
        result = cur.fetchall()
        inference = "Recently active users"

    elif intent == "get_user_count":
        cur.execute("SELECT COUNT(*) FROM users")
        result = cur.fetchone()[0]
        conn.close()
        return {"inference": "Total users", "result": result}

    elif intent == "get_admin_users":
        cur.execute("""
            SELECT id, name, email, role
            FROM users
            WHERE role = 'admin'
        """)
        result = cur.fetchall()
        inference = "Admin users"

    elif intent == "get_user_summary":
        cur.execute("SELECT COUNT(*) FROM users")
        total = cur.fetchone()[0]

        cur.execute("""
            SELECT COUNT(*) FROM users
            WHERE last_login < date('now','-30 day')
        """)
        inactive = cur.fetchone()[0]

        conn.close()
        return {
            "inference": "User summary",
            "result": {
                "total_users": total,
                "inactive_users": inactive
            }
        }

    conn.close()
    return {"inference": inference, "result": result}
