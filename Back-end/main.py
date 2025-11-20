import json
import os
import shutil
import sqlite3
from datetime import date, datetime, time
from typing import List, Optional
from uuid import uuid4

from fastapi import (
    Body,
    Depends,
    FastAPI,
    File,
    Form,
    HTTPException,
    Request,
    UploadFile,
    status,
)
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from passlib.context import CryptContext
from pydantic import BaseModel
from sqlmodel import Field, Session, SQLModel, create_engine, delete, select


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
    price: Optional[float] = None
    image_path: Optional[str] = None


class ServiceAvailability(SQLModel, table=True):
    availability_id: Optional[int] = Field(default=None, primary_key=True)
    service_id: int = Field(foreign_key="services.service_id")
    available_date: date
    slots: Optional[int] = Field(default=1)


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


class ServicePayload(BaseModel):
    name: str
    description: Optional[str] = None
    duration_minutes: int
    price: Optional[float] = None
    availability_dates: Optional[List[date]] = None


class ServiceUpdatePayload(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    duration_minutes: Optional[int] = None
    price: Optional[float] = None


class AvailabilityPayload(BaseModel):
    dates: List[date]
    slots: Optional[int] = 1


class BookingUpdatePayload(BaseModel):
    booking_date: Optional[date] = None
    booking_time: Optional[str] = None
    status: Optional[str] = None


ADMIN_WHITELIST = {"dankalbourji@gmail.com", "noahcgithub@gmail.com"}


# ============================================================
# DATABASE CONNECTION
# ============================================================

base_dir = os.path.dirname(os.path.abspath(__file__))
static_dir = os.path.join(base_dir, "static")
service_upload_dir = os.path.join(static_dir, "uploads", "services")
os.makedirs(service_upload_dir, exist_ok=True)

db_path = os.path.join(base_dir, "hair_salon.db")
sqlite_url = f"sqlite:///{db_path}"
engine = create_engine(sqlite_url, echo=True, connect_args={"check_same_thread": False})


def create_db_and_tables():
    SQLModel.metadata.create_all(engine)
    print("Database tables created successfully!") 
    ensure_google_id_column()
    ensure_booking_type_column()
    ensure_service_price_column()
    ensure_service_image_column()
    ServiceAvailability.__table__.create(engine, checkfirst=True)


def ensure_service_price_column():
    with engine.connect() as conn:
        result = conn.exec_driver_sql("PRAGMA table_info('Services');")
        columns = [row[1] for row in result]
        if "price" not in columns:
            conn.exec_driver_sql("ALTER TABLE Services ADD COLUMN price REAL;")
            conn.commit()
            print("Added missing price column to Services table.")


def ensure_service_image_column():
    with engine.connect() as conn:
        result = conn.exec_driver_sql("PRAGMA table_info('Services');")
        columns = [row[1] for row in result]
        if "image_path" not in columns:
            conn.exec_driver_sql("ALTER TABLE Services ADD COLUMN image_path VARCHAR;")
            conn.commit()
            print("Added missing image_path column to Services table.")


def ensure_google_id_column():
    with engine.connect() as conn:
        result = conn.exec_driver_sql("PRAGMA table_info('Clients');")
        columns = [row[1] for row in result]
        if "google_id" not in columns:
            conn.exec_driver_sql("ALTER TABLE Clients ADD COLUMN google_id VARCHAR;")
            print("Added missing google_id column to Clients table.")


def ensure_booking_type_column():
    """Ensure the Bookings table has a booking_type column."""
    with engine.connect() as conn:
        result = conn.exec_driver_sql("PRAGMA table_info('Bookings');")
        columns = [row[1] for row in result]
        if "booking_type" not in columns:
            conn.exec_driver_sql("ALTER TABLE Bookings ADD COLUMN booking_type VARCHAR;")
            conn.commit()
            print("Added missing booking_type column to Bookings table.")


def get_session():
    with Session(engine) as session:
        yield session


def get_admin_user_from_session(request: Request):
    return request.session.get("user")


def require_admin_user(request: Request):
    user = get_admin_user_from_session(request)
    if not user or not user.get("is_admin"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required.")
    return user


def serialize_service(session: Session, service: Services):
    availability_stmt = select(ServiceAvailability).where(ServiceAvailability.service_id == service.service_id)
    availability = session.exec(availability_stmt).all()
    return {
        "service_id": service.service_id,
        "name": service.name,
        "description": service.description,
        "duration_minutes": service.duration_minutes,
        "price": service.price,
        "image_path": service.image_path,
        "availability": [
            {
                "availability_id": slot.availability_id,
                "date": slot.available_date.isoformat(),
                "slots": slot.slots,
            }
            for slot in availability
        ],
    }


def serialize_booking(booking: Bookings, client: Client, service: Services):
    return {
        "booking_id": booking.booking_id,
        "booking_date": booking.booking_date.isoformat() if booking.booking_date else None,
        "booking_time": booking.booking_time.isoformat() if booking.booking_time else None,
        "status": booking.status,
        "booking_type": booking.booking_type,
        "client": {
            "client_id": client.client_id,
            "first_name": client.first_name,
            "last_name": client.last_name,
            "email": client.email,
            "phone": client.phone,
        },
        "service": {
            "service_id": service.service_id,
            "name": service.name,
            "duration_minutes": service.duration_minutes,
            "price": service.price,
        },
    }


def save_service_image_upload(image: UploadFile) -> str:
    file_extension = os.path.splitext(image.filename)[1]
    filename = f"{uuid4().hex}{file_extension}"
    destination_path = os.path.join(service_upload_dir, filename)
    with open(destination_path, "wb") as buffer:
        shutil.copyfileobj(image.file, buffer)
    relative_path = os.path.relpath(destination_path, base_dir)
    return f"/{relative_path.replace(os.sep, '/')}"


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

app.mount("/static", StaticFiles(directory=static_dir), name="static")
templates = Jinja2Templates(directory=os.path.join(base_dir, "templates"))


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
    user = get_admin_user_from_session(request)
    if user and user.get("is_admin"):
        return RedirectResponse(url="/dashboard", status_code=status.HTTP_302_FOUND)
    return templates.TemplateResponse("admin.html", {"request": request})


@app.get("/dashboard", response_class=HTMLResponse)
def get_dashboard(request: Request):
    user = get_admin_user_from_session(request)
    if not user or not user.get("is_admin"):
        return RedirectResponse(url="/login", status_code=status.HTTP_302_FOUND)
    return templates.TemplateResponse("dashboard.html", {"request": request, "user": user})


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
    """
    OAuth login endpoint. 
    - If called from admin page with ?admin=true, allows admin access
    - If called from general login (no param), always redirects to bookings
    """
    # Check if this is an admin login attempt
    admin_mode = request.query_params.get("admin", "false").lower() == "true"
    
    # Store the source in session so callback knows where to redirect
    request.session['oauth_source'] = 'admin' if admin_mode else 'login'
    
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
    is_admin = user_email in ADMIN_WHITELIST

    request.session['user'] = {
        'client_id': client.client_id,
        'email': client.email,
        'name': f"{client.first_name} {client.last_name}",
        'is_admin': is_admin,
    }

    # Determine redirect based on OAuth source
    oauth_source = request.session.get('oauth_source', 'login')
    
    # Only allow admin access if:
    # 1. OAuth was initiated from admin page (oauth_source == 'admin')
    # 2. User is actually whitelisted (is_admin == True)
    if oauth_source == 'admin' and is_admin:
        redirect_target = "/admin"  # Will redirect to dashboard
    else:
        # All other cases (general login, non-admin from admin page, etc.) go to bookings
        redirect_target = "/bookings"
    
    # Clear the OAuth source from session
    if 'oauth_source' in request.session:
        del request.session['oauth_source']
    
    return RedirectResponse(url=redirect_target, status_code=status.HTTP_302_FOUND)


# ============================================================
# ADMIN API
# ============================================================


@app.get("/api/admin/session")
def admin_session(request: Request):
    user = get_admin_user_from_session(request)
    if not user or not user.get("is_admin"):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Admin session not found.")
    return {"email": user["email"], "name": user["name"]}


@app.post("/api/admin/logout")
def admin_logout(request: Request):
    request.session.clear()
    return {"message": "Logged out successfully"}


@app.get("/api/admin/services")
def list_services_for_admin(
    session: Session = Depends(get_session),
    _: dict = Depends(require_admin_user),
):
    services = session.exec(select(Services)).all()
    return [serialize_service(session, service) for service in services]


@app.post("/api/admin/services")
async def create_service_admin(
    name: str = Form(...),
    description: Optional[str] = Form(None),
    duration_minutes: int = Form(...),
    price: Optional[float] = Form(None),
    availability_dates: Optional[str] = Form(None),
    image: Optional[UploadFile] = File(None),
    session: Session = Depends(get_session),
    _: dict = Depends(require_admin_user),
):
    service = Services(
        name=name,
        description=description,
        duration_minutes=duration_minutes,
        price=price,
    )

    if image:
        service.image_path = save_service_image_upload(image)

    session.add(service)
    session.commit()
    session.refresh(service)

    if availability_dates:
        try:
            dates_payload = json.loads(availability_dates)
            if not isinstance(dates_payload, list):
                raise ValueError
        except ValueError:
            raise HTTPException(status_code=400, detail="availability_dates must be a JSON list of ISO dates.")

        for iso_date in dates_payload:
            try:
                parsed_date = date.fromisoformat(iso_date)
            except ValueError:
                continue
            session.add(
                ServiceAvailability(
                    service_id=service.service_id,
                    available_date=parsed_date,
                    slots=1,
                )
            )
        session.commit()

    return serialize_service(session, service)


@app.patch("/api/admin/services/{service_id}")
def update_service_admin(
    service_id: int,
    payload: ServiceUpdatePayload,
    session: Session = Depends(get_session),
    _: dict = Depends(require_admin_user),
):
    service = session.get(Services, service_id)
    if not service:
        raise HTTPException(status_code=404, detail="Service not found.")

    update_data = payload.dict(exclude_unset=True)
    for field_name, value in update_data.items():
        setattr(service, field_name, value)

    session.add(service)
    session.commit()
    session.refresh(service)
    return serialize_service(session, service)


@app.post("/api/admin/services/{service_id}/availability")
def set_service_availability(
    service_id: int,
    payload: AvailabilityPayload,
    session: Session = Depends(get_session),
    _: dict = Depends(require_admin_user),
):
    service = session.get(Services, service_id)
    if not service:
        raise HTTPException(status_code=404, detail="Service not found.")

    session.exec(delete(ServiceAvailability).where(ServiceAvailability.service_id == service_id))
    session.commit()

    for availability_date in payload.dates:
        session.add(
            ServiceAvailability(
                service_id=service_id,
                available_date=availability_date,
                slots=payload.slots or 1,
            )
        )

    session.commit()
    session.refresh(service)

    return serialize_service(session, service)


@app.post("/api/admin/services/{service_id}/image")
async def upload_service_image(
    service_id: int,
    image: UploadFile = File(...),
    session: Session = Depends(get_session),
    _: dict = Depends(require_admin_user),
):
    service = session.get(Services, service_id)
    if not service:
        raise HTTPException(status_code=404, detail="Service not found.")

    service.image_path = save_service_image_upload(image)
    session.add(service)
    session.commit()
    session.refresh(service)
    return serialize_service(session, service)


@app.delete("/api/admin/services/{service_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_service(
    service_id: int,
    session: Session = Depends(get_session),
    _: dict = Depends(require_admin_user),
):
    service = session.get(Services, service_id)
    if not service:
        raise HTTPException(status_code=404, detail="Service not found.")

    session.exec(delete(ServiceAvailability).where(ServiceAvailability.service_id == service_id))
    session.delete(service)
    session.commit()
    return


@app.get("/api/admin/bookings")
def list_bookings_for_admin(
    session: Session = Depends(get_session),
    _: dict = Depends(require_admin_user),
):
    statement = (
        select(Bookings, Client, Services)
        .join(Client, Client.client_id == Bookings.client_id)
        .join(Services, Services.service_id == Bookings.service_id)
    )
    rows = session.exec(statement).all()
    return [serialize_booking(booking, client, service) for booking, client, service in rows]


@app.patch("/api/admin/bookings/{booking_id}")
def update_booking_admin(
    booking_id: int,
    payload: BookingUpdatePayload,
    session: Session = Depends(get_session),
    _: dict = Depends(require_admin_user),
):
    booking = session.get(Bookings, booking_id)
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found.")

    if payload.booking_date:
        booking.booking_date = payload.booking_date

    if payload.booking_time:
        try:
            parsed_time = datetime.strptime(payload.booking_time, "%H:%M").time()
        except ValueError:
            raise HTTPException(status_code=400, detail="booking_time must be HH:MM")
        booking.booking_time = parsed_time

    if payload.status:
        booking.status = payload.status

    session.add(booking)
    session.commit()
    session.refresh(booking)

    service = session.get(Services, booking.service_id)
    client = session.get(Client, booking.client_id)
    return serialize_booking(booking, client, service)


# ============================================================
# PUBLIC SERVICES API (for bookings page)
# ============================================================
@app.get("/api/services")
def get_services_public(session: Session = Depends(get_session)):
    """Public endpoint to get all services with availability for the bookings page."""
    services = session.exec(select(Services)).all()
    
    # Collect all availability dates from all services into one map
    all_available_times = {}
    
    result = []
    for service in services:
        availability_stmt = select(ServiceAvailability).where(ServiceAvailability.service_id == service.service_id)
        availability = session.exec(availability_stmt).all()
        
        # Merge availability dates into the global map
        for slot in availability:
            date_str = slot.available_date.isoformat()
            # Default to some common time slots if not specified
            # You can customize this logic based on your needs
            if date_str not in all_available_times:
                all_available_times[date_str] = ['9:00 AM', '11:15 AM', '1:15 PM', '3:00 PM']
        
        result.append({
            "service_id": service.service_id,
            "name": service.name,
            "description": service.description,
            "duration_minutes": service.duration_minutes,
            "price": service.price,
            "image_path": service.image_path,
        })
    
    # Return services and a combined available_times map
    return {
        "services": result,
        "available_times": all_available_times
    }


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
    request: Request,
    booking_type: str = Form(...),
    appointment_datetime: str = Form(...),
    session: Session = Depends(get_session)
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
        # --- 1. Find or create Client ID (use logged-in user if available) ---
        user_session = request.session.get('user')
        if user_session and 'client_id' in user_session:
            client_id = user_session['client_id']
            print(f"Using logged-in user client_id: {client_id}")
        else:
            # Fall back to Walk-in client
            client_name = "Walk-in"
            cursor.execute("SELECT client_id FROM Clients WHERE first_name = ?", (client_name,))
            client_row = cursor.fetchone()
            if not client_row:
                cursor.execute("INSERT INTO Clients (first_name, last_name) VALUES (?, ?)", (client_name, "Client"))
                client_id = cursor.lastrowid
            else:
                client_id = client_row[0]
            print(f"Using Walk-in client_id: {client_id}")

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
