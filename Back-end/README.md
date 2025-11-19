#  Hair Salon Backend API

This project is a RESTful API built with **FastAPI** to manage the core data of: clients, services, bookings, and admin access. It uses **SQLite** for a lightweight, file-based database.

---

##  START HERE: Virtual Environment and Setup

**You MUST create and activate a virtual environment (`venv`) before proceeding.** This prevents package conflicts with your main Python setup.

1.  **Create and Activate Environment (if not done):**
    * **Linux/Mac:** `python3 -m venv venv` then `source venv/bin/activate`
    * **Windows:** `python -m venv venv` then `venv\Scripts\activate`

2.  **Install Dependencies from requirements.txt:**
    ```bash
    pip install -r requirements.txt
    ```

###  Note on SQLite3

The core Python library for interacting with the database, **`sqlite3`**, is usually installed with Python and doesn't need a separate installation step. The needed packages are listed in `requirements.txt`.

---

##  Running the API Server

Once your `(venv)` is active and dependencies are installed, run the main application file (`main.py`) using Uvicorn:

```bash
uvicorn main:app --reload
