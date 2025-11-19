// --- CONFIG ---
// Service info
const service = {
  name: "Women's French Braid (Adriana)",
  price: 240,
  duration: 2 // in hours
};

// Available times per date
const availableTimes = {
  '2025-11-04': ['9:00 AM', '11:15 AM', '1:15 PM'],
  '2025-11-05': ['10:00 AM', '12:30 PM'],
  '2025-11-06': ['9:00 AM', '11:15 AM', '1:15 PM'],
  '2025-11-07': ['8:30 AM', '2:00 PM']
};

// --- ELEMENTS ---
const monthTitle = document.getElementById('monthTitle');
const daysContainer = document.getElementById('daysContainer');
const timesContainer = document.getElementById('timesContainer');
const timeSummary = document.getElementById('timeSummary');
const summary = document.getElementById('summary');
const totalSection = document.getElementById('totalSection');
const continueBtn = document.getElementById('continueBtn');

let selectedDate = null;
let selectedTime = null;

// --- RENDER CALENDAR ---
function renderCalendar() {
  monthTitle.textContent = "November 2025";

  // Clear previous buttons
  daysContainer.innerHTML = '';

  Object.keys(availableTimes).forEach(date => {
    const d = new Date(date);
    const dayName = d.toLocaleDateString('en-US', { weekday: 'short' });
    const dayNum = d.getDate();

    // Create day button
    const btn = document.createElement('button');
    btn.textContent = `${dayName} ${dayNum}`;
    btn.className = "px-3 py-2 rounded-lg bg-gray-100 hover:bg-cyan-100 transition";

    // On click, select the day
    btn.onclick = () => selectDay(date, btn);

    daysContainer.appendChild(btn);
  });
}

// --- SELECT DAY ---
function selectDay(date, button) {
  selectedDate = date;
  selectedTime = null;

  // Hide summary and total until a time is selected
  summary.classList.add('hidden');
  totalSection.classList.add('hidden');
  continueBtn.disabled = true;

  // Reset day button styles
  [...daysContainer.children].forEach(b => {
    b.classList.remove('bg-cyan-600', 'text-white');
    b.classList.add('bg-gray-100');
  });
  button.classList.add('bg-cyan-600', 'text-white');

  // Render available times for that day
  renderTimes(date);
}

// --- RENDER TIMES ---
function renderTimes(date) {
  timesContainer.innerHTML = '';

  availableTimes[date].forEach(time => {
    const btn = document.createElement('button');
    btn.textContent = time;
    btn.className = "px-4 py-2 rounded-lg bg-gray-100 hover:bg-cyan-100 transition";

    // On click, select time
    btn.onclick = () => selectTime(time, btn);

    timesContainer.appendChild(btn);
  });
}

// --- SELECT TIME ---
function selectTime(time, button) {
  selectedTime = time;

  // Reset all time buttons
  [...timesContainer.children].forEach(b => {
    b.classList.remove('bg-cyan-600', 'text-white');
    b.classList.add('bg-gray-100');
  });
  button.classList.add('bg-cyan-600', 'text-white');

  // Show summary and total
  summary.classList.remove('hidden');
  totalSection.classList.remove('hidden');
  continueBtn.disabled = false;

  const endTime = calculateEndTime(time, service.duration);
  timeSummary.textContent = `${time} – ${endTime}`;
}

// --- CALCULATE END TIME ---
function calculateEndTime(start, hours) {
  const [t, modifier] = start.split(' ');
  let [h, m] = t.split(':').map(Number);

  if (modifier === 'PM' && h !== 12) h += 12;
  if (modifier === 'AM' && h === 12) h = 0;

  const date = new Date();
  date.setHours(h + hours, m);

  return date.toLocaleTimeString([], { hour: 'numeric', minute: '2-digit' });
}

// --- CONTINUE BUTTON ---
continueBtn.addEventListener('click', () => {
  alert(`Booking confirmed for ${selectedDate} at ${selectedTime}`);
  // Redirect to login page after booking
  window.location.href = 'login.html';
});

// --- INITIALIZE CALENDAR ---
renderCalendar();
