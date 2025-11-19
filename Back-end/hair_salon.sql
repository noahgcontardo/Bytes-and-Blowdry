-- Hair Salon Backend Database Setup
-- 

PRAGMA foreign_keys = ON;

-- Drop old tables if they exist (for safety)
DROP TABLE IF EXISTS Bookings;
DROP TABLE IF EXISTS Services;
DROP TABLE IF EXISTS Clients;
DROP TABLE IF EXISTS Admin;

-- Admin table (only 1 admin login, no staff)
CREATE TABLE Admin (
    admin_id INTEGER PRIMARY KEY AUTOINCREMENT,
  --PRIMARY KEY = unique id for each admin record 
  --AUTO INCREMENT  = automatically increases by for each new admin 
    username VARCHAR(50) NOT NULL UNIQUE, 
  --VARCHAR(50) = text up to 50 characters 
  --NOTNULL = must always have a value 
    password_hash VARCHAR(255) NOT NULL,
  --passwords are stored as secure hashes (not plain text) 
  -- 255 allows room for long hashed strings
    email VARCHAR(100)
  --opt admin contant email
);

-- Clients table (people who book appointments)
CREATE TABLE Clients (
    client_id INTEGER PRIMARY KEY AUTOINCREMENT,
    first_name VARCHAR(50) NOT NULL,
    last_name VARCHAR(50) NOT NULL,
    phone VARCHAR(20),
    email VARCHAR(100) UNIQUE,
    google_id VARCHAR(255) UNIQUE
);

-- Services table (list of hair services)
CREATE TABLE Services (
    service_id INTEGER PRIMARY KEY AUTOINCREMENT,
    name VARCHAR(100) NOT NULL,
    description TEXT,
    duration_minutes INTEGER NOT NULL
);

-- Bookings table (records appointments)
CREATE TABLE Bookings (
    booking_id INTEGER PRIMARY KEY AUTOINCREMENT,
    client_id INTEGER NOT NULL,
    service_id INTEGER NOT NULL,
    booking_date DATE NOT NULL,
    booking_time TIME NOT NULL,
    status VARCHAR(20) DEFAULT 'Scheduled',
    booking_type VARCHAR(100),
    notes TEXT,
    FOREIGN KEY (client_id) REFERENCES Clients(client_id),
    FOREIGN KEY (service_id) REFERENCES Services(service_id)
);

-- test database with fakeuser: insert one admin account (you can update password later)
INSERT INTO Admin (username, password_hash, email)
VALUES ('admin', 'changeme', 'admin@example.com');
