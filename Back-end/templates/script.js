// --- CONFIG ---
// Available services
const services = {
  "Women's French Braid (Adriana)": {
    name: "Women's French Braid (Adriana)",
    price: 240,
    duration: 2 // in hours
  },
  "Coloring": {
    name: "Coloring",
    price: 240,
    duration: 2 // in hours
  },
  "Straightening": {
    name: "Straightening",
    price: 240,
    duration: 2 // in hours
  }
};

// Available times per date
const availableTimes = {
  '2025-11-04': ['9:00 AM', '11:15 AM', '1:15 PM'],
  '2025-11-05': ['10:00 AM', '12:30 PM'],
  '2025-11-06': ['9:00 AM', '11:15 AM', '1:15 PM'],
  '2025-11-07': ['8:30 AM', '2:00 PM']
};

// --- ELEMENTS ---
const servicesContainer = document.getElementById('servicesContainer');
const monthTitle = document.getElementById('monthTitle');
const daysContainer = document.getElementById('daysContainer');
const timesContainer = document.getElementById('timesContainer');
const timeSummary = document.getElementById('timeSummary');
const summary = document.getElementById('summary');
const totalSection = document.getElementById('totalSection');
const totalPrice = document.getElementById('totalPrice');
const continueBtn = document.getElementById('continueBtn');
const serviceName = document.getElementById('serviceName');
const servicePrice = document.getElementById('servicePrice');
const bookingTypeInput = document.getElementById('bookingType');

let selectedService = null;
let selectedDate = null;
let selectedTime = null;

// --- RENDER SERVICES ---
function renderServices() {
  if (!servicesContainer) return;
  
  servicesContainer.innerHTML = '';
  Object.values(services).forEach(service => {
    const btn = document.createElement('button');
    btn.textContent = service.name;
    btn.className = "px-4 py-2 rounded-lg bg-gray-100 hover:bg-cyan-100 transition";
    btn.onclick = () => selectService(service, btn);
    servicesContainer.appendChild(btn);
  });
}

// --- SELECT SERVICE ---
function selectService(service, button) {
  selectedService = service;
  selectedDate = null;
  selectedTime = null;

  // Reset service button styles
  [...servicesContainer.children].forEach(b => {
    b.classList.remove('bg-cyan-600', 'text-white');
    b.classList.add('bg-gray-100');
  });
  button.classList.add('bg-cyan-600', 'text-white');

  // Clear calendar and times
  if (daysContainer) daysContainer.innerHTML = '';
  if (timesContainer) timesContainer.innerHTML = '';
  if (summary) summary.classList.add('hidden');
  if (totalSection) totalSection.classList.add('hidden');
  if (continueBtn) continueBtn.disabled = true;

  // Show calendar
  renderCalendar();
}

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
  if (!selectedService) return;
  
  selectedDate = date;
  selectedTime = null;

  // Hide summary and total until a time is selected
  if (summary) summary.classList.add('hidden');
  if (totalSection) totalSection.classList.add('hidden');
  if (continueBtn) continueBtn.disabled = true;

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
  if (!selectedService) return;
  
  selectedTime = time;

  // Reset all time buttons
  [...timesContainer.children].forEach(b => {
    b.classList.remove('bg-cyan-600', 'text-white');
    b.classList.add('bg-gray-100');
  });
  button.classList.add('bg-cyan-600', 'text-white');

  // Show summary and total
  if (summary) summary.classList.remove('hidden');
  if (totalSection) totalSection.classList.remove('hidden');
  if (continueBtn) continueBtn.disabled = false;

  // Update service display
  if (serviceName) serviceName.textContent = selectedService.name;
  if (servicePrice) servicePrice.textContent = `$${selectedService.price.toFixed(2)}`;
  if (bookingTypeInput) bookingTypeInput.value = selectedService.name;
  
  const endTime = calculateEndTime(time, selectedService.duration);
  if (timeSummary) timeSummary.textContent = `${time} – ${endTime}`;
  
  // Update total
  if (totalPrice) totalPrice.textContent = `$${selectedService.price.toFixed(2)} (${selectedService.duration} hours)`;
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
if (continueBtn) {
  continueBtn.addEventListener('click', () => {
    if (!selectedService || !selectedDate || !selectedTime) {
      alert('Please select a service, date, and time');
      return;
    }
    alert(`Booking confirmed for ${selectedService.name} on ${selectedDate} at ${selectedTime}`);
    // Redirect to login page after booking
    window.location.href = '/login';
  });
}

// --- INITIALIZE ---
if (servicesContainer) {
  renderServices();
} else {
  // If no service container, assume single service mode (backward compatibility)
  selectedService = services["Women's French Braid (Adriana)"];
  renderCalendar();
}
