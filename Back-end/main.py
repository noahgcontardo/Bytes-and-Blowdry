import os
import sqlite3
from datetime import datetime, date, time
from typing import Optional

from fastapi import FastAPI, Form, Depends, HTTPException, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlmodel import SQLModel, Field, Session, create_engine, select
from sqlalchemy import text
from passlib.context import CryptContext
from pydantic import BaseModel 


from authlib.integrations.starlette_client import OAuth
from starlette.config import Config
from starlette.middleware.sessions import SessionMiddleware


# ============================================================
# DATABASE MODELS
# ============================================================

class Admin(SQLModel, table=True):
    admin_id: Optional[int] = Field(default=None, primary_key=True)
    username: str
    password_hash: str
    email: Optional[str] = None


class Client(SQLModel, table=True):
    __tablename__ = "Clients"
    client_id: Optional[int] = Field(default=None, primary_key=True)
    first_name: str
    last_name: str
    phone: Optional[str] = None
    email: Optional[str] = None
    google_id: Optional[str] = Field(default=None)


class Services(SQLModel, table=True):
    service_id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    description: Optional[str] = None
    duration_minutes: int


class Bookings(SQLModel, table=True):
    booking_id: Optional[int] = Field(default=None, primary_key=True)
    client_id: int = Field(foreign_key="Clients.client_id")
    service_id: int = Field(foreign_key="Services.service_id")
    booking_date: date
    booking_time: time
    status: Optional[str] = "Scheduled"
    booking_type: Optional[str] = None
    notes: Optional[str] = None


class BookingCreate(BaseModel):
    booking_type: str
    appointment_datetime: str


# ============================================================
# DATABASE CONNECTION
# ============================================================

base_dir = os.path.dirname(os.path.abspath(__file__))
db_path = os.path.join(base_dir, "hair_salon.db")
sqlite_url = f"sqlite:///{db_path}"
engine = create_engine(sqlite_url, echo=True, connect_args={"check_same_thread": False})


def create_db_and_tables():
    SQLModel.metadata.create_all(engine)
    print("Database tables created successfully!") 
    ensure_google_id_column()


def ensure_google_id_column():
    with engine.connect() as conn:
        result = conn.exec_driver_sql("PRAGMA table_info('Clients');")
        columns = [row[1] for row in result]
        if "google_id" not in columns:
            conn.exec_driver_sql("ALTER TABLE Clients ADD COLUMN google_id VARCHAR;")
            print("Added missing google_id column to Clients table.")


def get_session():
    with Session(engine) as session:
        yield session


# ============================================================
# PASSWORD HASHING
# ============================================================

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password, hashed_password) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


# ============================================================
# FASTAPI SETUP
# ============================================================

# Load .env configuration 
config = Config(".env")

app = FastAPI(title="Hair Salon Backend", version="1.0") 

# Session middleware for OAuth to handle stroing user data during call back
app.add_middleware(SessionMiddleware, secret_key=config("SESSION_SECERT", default="!fallback-sercert-key!"))

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")


@app.on_event("startup")
def on_startup():
    create_db_and_tables() 

# ============================================================
# OAUTH SETUP
# ============================================================

# Initialize OAuth
oauth = OAuth(config)

# Google OAuth client
oauth.register(
    name='google',
    client_id=config('GOOGLE_CLIENT_ID'),
    client_secret=config('GOOGLE_CLIENT_SECRET'),
    server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
    client_kwargs={'scope': 'openid email profile'},
)

# ============================================================
# FRONTEND ROUTES
# ============================================================

@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})


@app.get("/bookings", response_class=HTMLResponse)
def get_bookings(request: Request):
    return templates.TemplateResponse("bookings.html", {"request": request})


@app.get("/admin", response_class=HTMLResponse)
def get_admin(request: Request):
    return templates.TemplateResponse("admin.html", {"request": request})


@app.get("/dashboard", response_class=HTMLResponse)
def get_dashboard(request: Request):
    return templates.TemplateResponse("dashboard.html", {"request": request})


@app.get("/about", response_class=HTMLResponse)
def about(request: Request):
    return templates.TemplateResponse("about.html", {"request": request})


@app.get("/login", response_class=HTMLResponse)
def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})


# ============================================================
# AUTHENTICATION ROUTES
# ============================================================

@app.post("/login")
def login(email: str = Form(...), password: str = Form(...)):
    return {"message": "OK", "email": email}



# --- OAuth Login/Callback Routes ---

@app.get("/auth/google")
async def login_google(request: Request):
    redirect_uri = str(request.url_for("auth_google_callback"))
    return await oauth.google.authorize_redirect(request, redirect_uri)

@app.get("/auth/google/callback")
async def auth_google_callback(request: Request, session: Session = Depends(get_session)):
    token = await oauth.google.authorize_access_token(request)
    user_info = await oauth.google.userinfo(token=token)

    if not user_info:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unable to retrieve user information from Google.")
    
    # 1. Look for user by email
    user_email = user_info.get('email')
    client = session.exec(select(Client).where(Client.email == user_email)).first()
    
    if not client:
        # 2. If client does not exist, create a new one
        client = Client(
            first_name=user_info.get('given_name', 'User'),
            last_name=user_info.get('family_name', 'Client'),
            email=user_email,
            google_id=user_info.get('sub') # 'sub' is Google's unique user ID
        )
        session.add(client)
        session.commit()
        session.refresh(client)

    # Store necessary info in the session
    request.session['user'] = {
        'client_id': client.client_id,
        'email': client.email,
        'name': f"{client.first_name} {client.last_name}"
    }

    return RedirectResponse(url="/bookings", status_code=status.HTTP_302_FOUND)

# ============================================================
# BOOKINGS API
# ============================================================
@app.get("/api/bookings")
def api_get_bookings():
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # Check if Bookings table exists
    cursor.execute("""
        SELECT name FROM sqlite_master 
        WHERE type='table' AND name='Bookings';
    """)
    exists = cursor.fetchone()

    if not exists:
        conn.close()
        return []  # return empty list so the server doesn't crash

    cursor.execute("SELECT booking_id, booking_type, booking_date, booking_time, status FROM Bookings")
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]




@app.post("/api/bookings")
def create_booking(
    booking_type: str = Form(...),
    appointment_datetime: str = Form(...)
):
    """
    Inserts a confirmed booking into the database from form data.
    """
    import sqlite3
    from datetime import datetime

    # Debug prints to see incoming data
    print("Received booking_type:", booking_type)
    print("Received appointment_datetime:", appointment_datetime)

    # Parse appointment_datetime string
    try:
        parsed_dt = datetime.strptime(appointment_datetime, "%Y-%m-%d %I:%M %p")
        booking_date = parsed_dt.date().isoformat()
        booking_time = parsed_dt.time().isoformat()
    except ValueError as e:
        print("Error parsing datetime:", e)
        raise HTTPException(status_code=400, detail=f"Invalid datetime format: {appointment_datetime}")

    # Connect to SQLite
    conn = sqlite3.connect("hair_salon.db")
    cursor = conn.cursor()

    try:
        # --- 1. Find or create default Client ID ---
        client_name = "Walk-in"
        cursor.execute("SELECT client_id FROM Clients WHERE first_name = ?", (client_name,))
        client_row = cursor.fetchone()
        if not client_row:
            cursor.execute("INSERT INTO Clients (first_name, last_name) VALUES (?, ?)", (client_name, "Client"))
            client_id = cursor.lastrowid
        else:
            client_id = client_row[0]

        # --- 2. Find or create Service ID ---
        cursor.execute("SELECT service_id FROM Services WHERE name = ?", (booking_type,))
        service_row = cursor.fetchone()
        if not service_row:
            # Default duration: 120 minutes
            cursor.execute("INSERT INTO Services (name, duration_minutes) VALUES (?, ?)", (booking_type, 120))
            service_id = cursor.lastrowid
        else:
            service_id = service_row[0]

        # --- 3. Insert into Bookings ---
        cursor.execute(
            "INSERT INTO Bookings (client_id, service_id, booking_date, booking_time, status, booking_type) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (client_id, service_id, booking_date, booking_time, "Scheduled", booking_type)
        )
        conn.commit()
        print("Booking successfully inserted!")

    except Exception as e:
        conn.rollback()
        print("Error inserting booking:", e)
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()

    # Redirect to bookings page
    return RedirectResponse(url="/login", status_code=303)
