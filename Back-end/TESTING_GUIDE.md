# Testing Guide - Service Selection Feature

## Quick Start

### 1. Start the Server

Navigate to the Back-end directory and start the FastAPI server:

```bash
cd Back-end
uvicorn main:app --reload
```

The server will start on `http://localhost:8000` (or `http://127.0.0.1:8000`)

### 2. Open the Bookings Page

In your browser, navigate to:
```
http://localhost:8000/bookings
```

## Testing Checklist

### ✅ Test 1: Service Selection UI
- [ ] You should see **three service buttons** at the top:
  - Women's French Braid (Adriana)
  - Coloring
  - Straightening
- [ ] Click each service button - it should highlight in cyan
- [ ] Only one service should be selected at a time

### ✅ Test 2: Calendar Display
- [ ] After selecting a service, the calendar should appear
- [ ] You should see available dates (December 2025)
- [ ] Click a date - it should highlight in cyan

### ✅ Test 3: Time Selection
- [ ] After selecting a date, available times should appear
- [ ] Click a time slot - it should highlight in cyan
- [ ] The booking summary should appear showing:
  - Service name
  - Price ($240.00)
  - Time range (start - end time)
  - Total ($240.00 (2 hours))

### ✅ Test 4: Booking Submission
- [ ] With a service, date, and time selected, click "Continue"
- [ ] The form should submit to the backend
- [ ] You should see a success alert
- [ ] You should be redirected to `/login`

### ✅ Test 5: Database Verification
After submitting a booking, verify it was saved:

**Option A: Using SQLite command line**
```bash
cd Back-end
sqlite3 hair_salon.db
```

Then run:
```sql
-- Check services were created
SELECT * FROM Services;

-- Check bookings were created
SELECT b.booking_id, s.name as service_name, b.booking_date, b.booking_time, b.status 
FROM Bookings b 
JOIN Services s ON b.service_id = s.service_id 
ORDER BY b.booking_id DESC 
LIMIT 5;
```

**Option B: Check the server console**
- Look for print statements showing:
  - "Received booking_type: [Service Name]"
  - "Booking successfully inserted!"

### ✅ Test 6: Test All Three Services
Repeat the process for each service:
1. **Women's French Braid (Adriana)** - should work
2. **Coloring** - should work
3. **Straightening** - should work

All should:
- Display correctly
- Submit successfully
- Create entries in the database

## Troubleshooting

### Server won't start
- Make sure you're in a virtual environment: `source venv/bin/activate` (Linux/Mac) or `venv\Scripts\activate` (Windows)
- Install dependencies: `pip install -r requirements.txt`
- Check if port 8000 is already in use

### Service buttons don't appear
- Open browser developer console (F12) and check for JavaScript errors
- Verify `bookings.html` has the `servicesContainer` div

### Booking submission fails
- Check browser console (F12) for errors
- Check server console for error messages
- Verify the form is submitting to `/api/bookings`

### Database issues
- The database file `hair_salon.db` should be in the `Back-end` directory
- If it doesn't exist, the server will create it on startup
- Check file permissions if you get database errors

## Expected Behavior

1. **Service Selection**: User must select a service before dates/times appear
2. **Date Selection**: User must select a date before times appear
3. **Time Selection**: User must select a time before the summary appears
4. **Form Validation**: "Continue" button is disabled until all selections are made
5. **Price Display**: All services show $240.00 (2 hours)
6. **Database**: Each booking creates:
   - A service entry (if it doesn't exist)
   - A booking entry linked to the service

## Quick Test Script

You can also test the API directly using curl:

```bash
# Test booking creation
curl -X POST "http://localhost:8000/api/bookings" \
  -F "booking_type=Coloring" \
  -F "appointment_datetime=2025-12-04 9:00 AM"
```

This should return a redirect response if successful.

