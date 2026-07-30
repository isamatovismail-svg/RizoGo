/* ==========================================================================
   RIZO GO - ENTERPRISE FRONTEND & API ENGINE WITH I18N & LIVE CHAT
   ========================================================================== */

const API_BASE = '/api';

// Multi-Language Dictionary
const translations = {
    uz: {
        role_client: "Mijoz",
        role_driver: "Haydovchi",
        role_admin: "Admin / Dispetcher",
        service_taxi: "Taksi",
        service_delivery: "Jo'natma",
        route_title: "Manzil va Marshrut",
        lbl_pickup: "Qayerdan (Olish nuqtasi)",
        lbl_dropoff: "Qayerga (Borish nuqtasi)",
        map_hint: "Maslahat: Xaritaning istalgan joyiga bosib nuqtani tanlashingiz mumkin.",
        delivery_info: "Jo'natma ma'lumotlari",
        package_size: "O'lchami",
        pre_order: "Oldindan rejalashtirilgan buyurtma",
        btn_calc: "Narxlarni hisoblash",
        select_tariff: "Tarifni tanlang",
        payment_method: "To'lov usuli",
        btn_order: "Buyurtma berish"
    },
    ru: {
        role_client: "Клиент",
        role_driver: "Водитель",
        role_admin: "Админ / Диспетчер",
        service_taxi: "Такси",
        service_delivery: "Доставка",
        route_title: "Маршрут и Адрес",
        lbl_pickup: "Откуда (Точка забора)",
        lbl_dropoff: "Куда (Точка назначения)",
        map_hint: "Совет: Нажмите в любом месте на карте, чтобы выбрать точку.",
        delivery_info: "Информация о посылке",
        package_size: "Размер",
        pre_order: "Предварительный заказ",
        btn_calc: "Рассчитать стоимость",
        select_tariff: "Выберите тариф",
        payment_method: "Способ оплаты",
        btn_order: "Заказать сейчас"
    },
    en: {
        role_client: "Client",
        role_driver: "Driver",
        role_admin: "Admin / Dispatcher",
        service_taxi: "Taxi",
        service_delivery: "Delivery",
        route_title: "Route & Locations",
        lbl_pickup: "Pickup Location",
        lbl_dropoff: "Destination",
        map_hint: "Tip: Click anywhere on the map to set location points.",
        delivery_info: "Package Details",
        package_size: "Size",
        pre_order: "Scheduled Order",
        btn_calc: "Calculate Price",
        select_tariff: "Select Tariff",
        payment_method: "Payment Method",
        btn_order: "Book Ride"
    }
};

let currentLang = 'uz';

// State Management
let currentRole = 'client';
let serviceType = 'taxi';
let packageSize = 'small';
let selectedTariffId = null;
let paymentMethod = 'cash';
let paymentProvider = 'none';

let currentPickup = { address: "Amir Temur shoh ko'chasi, Toshkent", lat: 41.311081, lng: 69.240562 };
let currentDropoff = { address: "Chilonzor metro bekati, Toshkent", lat: 41.282500, lng: 69.204500 };
let currentDistance = 7.4;
let activePromo = null;

let activeClientTrip = null;
let activeDriverTrip = null;
let driverIsOnline = true;

let simulationInterval = null;
let chatPollingInterval = null;
let activeRatingStar = 5;

// Initialization
document.addEventListener('DOMContentLoaded', () => {
    initCanvasMap();
    fetchTariffs();
    loadAvailableOrders();
    updateAdminDashboard();
    calculateRouteAndTariffs();
});

// --- I18N MULTI-LANGUAGE ENGINE ---
function changeLanguage(lang) {
    currentLang = lang;
    document.querySelectorAll('[data-i18n]').forEach(el => {
        const key = el.dataset.i18n;
        if (translations[lang] && translations[lang][key]) {
            el.innerText = translations[lang][key];
        }
    });
}

// --- ROLE SWITCHER ---
function switchRole(role) {
    currentRole = role;
    document.querySelectorAll('.role-btn').forEach(btn => {
        btn.classList.toggle('active', btn.dataset.role === role);
    });

    document.querySelectorAll('.module-section').forEach(sec => sec.classList.remove('active'));
    document.getElementById(`${role}-module`).classList.add('active');

    if (role === 'admin') {
        updateAdminDashboard();
    } else if (role === 'driver') {
        loadAvailableOrders();
        loadDriverWallet();
    }
}

// --- SERVICE & ROUTE SELECTION ---
function setServiceType(type) {
    serviceType = type;
    document.getElementById('btn-service-taxi').classList.toggle('active', type === 'taxi');
    document.getElementById('btn-service-delivery').classList.toggle('active', type === 'delivery');
    document.getElementById('delivery-fields').classList.toggle('hidden', type !== 'delivery');
}

function selectPackageSize(size) {
    packageSize = size;
    document.querySelectorAll('.size-btn').forEach(btn => {
        btn.classList.toggle('active', btn.dataset.size === size);
    });
}

function toggleScheduleInput(checkbox) {
    document.getElementById('input-schedule-time').classList.toggle('hidden', !checkbox.checked);
}

function setQuickRoute(pName, pLat, pLng, dName, dLat, dLng) {
    currentPickup = { address: pName, lat: pLat, lng: pLng };
    currentDropoff = { address: dName, lat: dLat, lng: dLng };
    
    document.getElementById('input-pickup').value = pName;
    document.getElementById('input-dropoff').value = dName;
    
    calculateRouteAndTariffs();
}

function selectPaymentMethod(method, provider, el) {
    paymentMethod = method;
    paymentProvider = provider;
    document.querySelectorAll('.pay-option').forEach(opt => opt.classList.remove('active'));
    el.classList.add('active');
}

// --- PROMO CODE SYSTEM ---
async function applyPromoCode() {
    const code = document.getElementById('input-promo-code').value.trim();
    const msgBox = document.getElementById('promo-status-msg');

    if (!code) return;

    try {
        const res = await fetch(`${API_BASE}/promos/validate/`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ code: code })
        });

        const data = await res.json();
        if (data.valid) {
            activePromo = data;
            msgBox.className = 'promo-status-msg text-success mt-1';
            msgBox.innerText = `✅ Promokod faollashtirildi! (${data.discount_amount > 0 ? data.discount_amount + ' so\'m' : data.discount_percent + '%'} chegirma)`;
            msgBox.classList.remove('hidden');
            calculateRouteAndTariffs();
        } else {
            msgBox.className = 'promo-status-msg text-danger mt-1';
            msgBox.innerText = `❌ ${data.error}`;
            msgBox.classList.remove('hidden');
        }
    } catch (e) {
        console.error("Promo error:", e);
    }
}

// --- TARIFFS & SURGE PRICING ESTIMATION ---
async function fetchTariffs() {
    try {
        const res = await fetch(`${API_BASE}/tariffs/`);
        const tariffs = await res.json();
        renderTariffCards(tariffs);
    } catch (e) {
        console.error("Tariflarni olishda xato:", e);
    }
}

async function calculateRouteAndTariffs() {
    const pickupVal = document.getElementById('input-pickup').value;
    const dropoffVal = document.getElementById('input-dropoff').value;

    currentPickup.address = pickupVal;
    currentDropoff.address = dropoffVal;

    try {
        const res = await fetch(`${API_BASE}/trips/estimate/`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                pickup_lat: currentPickup.lat,
                pickup_lng: currentPickup.lng,
                dropoff_lat: currentDropoff.lat,
                dropoff_lng: currentDropoff.lng
            })
        });

        const data = await res.json();
        currentDistance = data.distance_km;

        // Show Surge Badge if surge multiplier > 1.0
        const surgeBadge = document.getElementById('surge-badge');
        if (data.surge_multiplier > 1.0) {
            surgeBadge.innerText = `⚡ Peak Surge ${data.surge_multiplier}x`;
            surgeBadge.classList.remove('hidden');
        } else {
            surgeBadge.classList.add('hidden');
        }

        renderTariffCardsWithPrices(data.estimates);
        drawMapRoute();
    } catch (e) {
        console.error("Hisoblashda xato:", e);
    }
}

function renderTariffCards(tariffs) {
    const container = document.getElementById('tariff-cards-container');
    container.innerHTML = tariffs.map((t, idx) => `
        <div class="tariff-item ${idx === 0 ? 'active' : ''}" data-id="${t.id}" onclick="selectTariff(${t.id}, this)">
            <div class="tariff-left">
                <div class="tariff-icon-wrap">
                    <i class="fa-solid ${t.icon}"></i>
                </div>
                <div>
                    <div class="tariff-title">${t.name}</div>
                    <div class="tariff-sub">Boshlang'ich: ${parseInt(t.base_price).toLocaleString()} so'm</div>
                </div>
            </div>
            <div class="tariff-price" id="tariff-price-${t.id}">${parseInt(t.minimum_price).toLocaleString()} so'm</div>
        </div>
    `).join('');
    
    if (tariffs.length > 0) selectedTariffId = tariffs[0].id;
}

function renderTariffCardsWithPrices(estimates) {
    estimates.forEach(est => {
        let finalPrice = est.estimated_price;
        if (activePromo) {
            if (activePromo.discount_amount > 0) finalPrice = Math.max(0, finalPrice - activePromo.discount_amount);
            else if (activePromo.discount_percent > 0) finalPrice = Math.max(0, finalPrice * (1 - activePromo.discount_percent / 100));
        }

        const priceEl = document.getElementById(`tariff-price-${est.tariff_id}`);
        if (priceEl) {
            priceEl.innerText = `${parseInt(finalPrice).toLocaleString()} so'm`;
        }
    });
}

function selectTariff(id, el) {
    selectedTariffId = id;
    document.querySelectorAll('.tariff-item').forEach(item => item.classList.remove('active'));
    el.classList.add('active');
}

// --- CREATE TRIP ORDER ---
async function createTripOrder() {
    const isScheduled = document.getElementById('check-scheduled').checked;
    const scheduledTime = isScheduled ? document.getElementById('input-schedule-time').value : null;

    const payload = {
        client_phone: document.getElementById('user-phone-display').innerText,
        tariff_id: selectedTariffId,
        service_type: serviceType,
        pickup_address: currentPickup.address,
        pickup_lat: currentPickup.lat,
        pickup_lng: currentPickup.lng,
        dropoff_address: currentDropoff.address,
        dropoff_lat: currentDropoff.lat,
        dropoff_lng: currentDropoff.lng,
        payment_method: paymentMethod,
        payment_provider: paymentProvider,
        promo_code: activePromo ? activePromo.code : null,
        scheduled_at: scheduledTime,
        package_size: packageSize,
        receiver_name: document.getElementById('delivery-receiver-name').value,
        receiver_phone: document.getElementById('delivery-receiver-phone').value,
        description: document.getElementById('delivery-desc').value
    };

    try {
        const res = await fetch(`${API_BASE}/trips/`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });

        if (res.ok) {
            activeClientTrip = await res.json();
            showClientActiveTripCard(activeClientTrip);
            loadAvailableOrders();
            startTripSimulation(activeClientTrip.id);
        }
    } catch (e) {
        console.error("Buyurtma berishda xato:", e);
    }
}

function showClientActiveTripCard(trip) {
    document.getElementById('client-active-trip-card').classList.remove('hidden');
    document.getElementById('client-trip-id').innerText = `#${trip.id}`;
    document.getElementById('client-trip-status-badge').innerText = 'Haydovchi qidirilmoqda...';
    document.getElementById('btn-create-trip').disabled = true;
    document.getElementById('trip-progress-bar').style.width = '15%';
}

async function cancelActiveTrip() {
    if (!activeClientTrip) return;
    try {
        await fetch(`${API_BASE}/trips/${activeClientTrip.id}/cancel/`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ by: 'client' })
        });
        
        clearInterval(simulationInterval);
        document.getElementById('client-active-trip-card').classList.add('hidden');
        document.getElementById('btn-create-trip').disabled = false;
        activeClientTrip = null;
        alert("Buyurtma bekor qilindi.");
        loadAvailableOrders();
    } catch (e) {
        console.error(e);
    }
}

// --- SOS SAFETY CENTER ---
function triggerSOSEmergency() {
    alert("🚨 SOS XAVFSISLUK SIGNAL YUBORILDI!\n\nDispetcher va yaqin atrofdagi patrullarga safar ma'lumotlari hamda koordinatalaringiz yuborildi. 102 bilan bog'lanilmoqda...");
}

// --- DRIVER MODULE ACTIONS & WALLET ---
function toggleDriverOnline() {
    driverIsOnline = !driverIsOnline;
    const btn = document.getElementById('driver-status-btn');
    const text = document.getElementById('driver-status-text');

    if (driverIsOnline) {
        btn.className = 'toggle-online-btn online';
        text.innerText = 'ONLAYN';
    } else {
        btn.className = 'toggle-online-btn offline';
        text.innerText = 'OFLAYN';
    }
}

async function loadAvailableOrders() {
    try {
        const res = await fetch(`${API_BASE}/driver/available-trips/`);
        const trips = await res.json();
        
        const container = document.getElementById('available-orders-list');
        if (trips.length === 0) {
            container.innerHTML = '<div class="text-center text-dim p-3">Hozircha faol buyurtmalar yo\'q</div>';
            return;
        }

        container.innerHTML = trips.map(t => `
            <div class="order-card-item">
                <div class="order-top-row">
                    <span>${t.service_type === 'delivery' ? '📦 Jo\'natma' : '🚕 Safar'} #${t.id}</span>
                    <span class="order-price">${parseInt(t.estimated_price).toLocaleString()} so'm</span>
                </div>
                <div class="order-address-text">
                    📍 <strong>Qayerdan:</strong> ${t.pickup_address}<br>
                    🏁 <strong>Qayerga:</strong> ${t.dropoff_address} (${t.distance_km} km)
                </div>
                <button class="btn btn-primary btn-full btn-sm mt-2" onclick="driverAcceptTrip(${t.id})">
                    <i class="fa-solid fa-circle-check"></i> Qabul qilish
                </button>
            </div>
        `).join('');
    } catch (e) {
        console.error("Orders load error:", e);
    }
}

async function driverAcceptTrip(tripId) {
    try {
        const res = await fetch(`${API_BASE}/driver/trips/${tripId}/accept/`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ driver_id: 1 })
        });

        if (res.ok) {
            activeDriverTrip = await res.json();
            showDriverActiveTripWidget(activeDriverTrip);
            loadAvailableOrders();
        } else {
            const err = await res.json();
            alert(`⚠️ ${err.error || 'Qabul qilishda xato'}`);
        }
    } catch (e) {
        console.error("Accept error:", e);
    }
}

function showDriverActiveTripWidget(trip) {
    document.getElementById('driver-active-trip-box').classList.remove('hidden');
    document.getElementById('d-trip-pickup').innerText = trip.pickup_address;
    document.getElementById('d-trip-dropoff').innerText = trip.dropoff_address;
    document.getElementById('d-trip-price').innerText = parseInt(trip.estimated_price).toLocaleString();
    document.getElementById('d-trip-client').innerText = trip.client ? trip.client.username : 'Mijoz';

    document.getElementById('btn-driver-arrived').classList.remove('hidden');
    document.getElementById('btn-driver-start').classList.add('hidden');
    document.getElementById('btn-driver-complete').classList.add('hidden');
}

async function driverUpdateStatus(newStatus) {
    if (!activeDriverTrip) return;
    try {
        const res = await fetch(`${API_BASE}/driver/trips/${activeDriverTrip.id}/status/`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ status: newStatus })
        });

        if (res.ok) {
            activeDriverTrip = await res.json();
            
            if (newStatus === 'arrived') {
                document.getElementById('btn-driver-arrived').classList.add('hidden');
                document.getElementById('btn-driver-start').classList.remove('hidden');
            } else if (newStatus === 'in_progress') {
                document.getElementById('btn-driver-start').classList.add('hidden');
                document.getElementById('btn-driver-complete').classList.remove('hidden');
            } else if (newStatus === 'completed') {
                document.getElementById('driver-active-trip-box').classList.add('hidden');
                activeDriverTrip = null;
                alert("Safar muvaffaqiyatli yakunlandi! 15% platforma komissiyasi balansdan yechildi.");
                loadAvailableOrders();
                loadDriverWallet();
                updateAdminDashboard();
            }
        }
    } catch (e) {
        console.error("Status update error:", e);
    }
}

// Driver Wallet API
async function loadDriverWallet() {
    try {
        const res = await fetch(`${API_BASE}/driver/wallet/?driver_id=1`);
        const data = await res.json();
        
        document.getElementById('driver-balance-display').innerText = parseInt(data.balance).toLocaleString();
        document.getElementById('modal-wallet-balance').innerText = `${parseInt(data.balance).toLocaleString()} so'm`;

        const list = document.getElementById('wallet-transactions-list');
        list.innerHTML = data.transactions.map(t => `
            <div class="glass-card mb-2 p-2" style="font-size:12px;">
                <div class="order-top-row">
                    <span>${t.description}</span>
                    <strong class="${t.amount >= 0 ? 'text-success' : 'text-danger'}">${t.amount >= 0 ? '+' : ''}${parseInt(t.amount).toLocaleString()} so'm</strong>
                </div>
                <div class="text-dim mt-1">${new Date(t.created_at).toLocaleString()}</div>
            </div>
        `).join('');
    } catch (e) {
        console.error(e);
    }
}

function openDriverWalletModal() {
    loadDriverWallet();
    document.getElementById('wallet-modal').classList.remove('hidden');
}

function closeDriverWalletModal() {
    document.getElementById('wallet-modal').classList.add('hidden');
}

async function depositDriverBalance(provider) {
    const amount = document.getElementById('deposit-amount-input').value;
    try {
        const res = await fetch(`${API_BASE}/driver/wallet/`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ driver_id: 1, amount: amount })
        });
        if (res.ok) {
            alert(`${provider.toUpperCase()} orqali ${parseInt(amount).toLocaleString()} so'm hisobga tushdi!`);
            loadDriverWallet();
        }
    } catch (e) {
        console.error(e);
    }
}

// --- LIVE IN-APP CHAT ---
function openChatModal() {
    const trip = activeClientTrip || activeDriverTrip;
    if (!trip) {
        alert("Chatdan foydalanish uchun faol safar bo'lishi kerak.");
        return;
    }
    document.getElementById('chat-modal').classList.remove('hidden');
    loadChatMessages(trip.id);
}

function closeChatModal() {
    document.getElementById('chat-modal').classList.add('hidden');
}

async function loadChatMessages(tripId) {
    try {
        const res = await fetch(`${API_BASE}/chat/${tripId}/messages/`);
        const messages = await res.json();
        
        const container = document.getElementById('chat-messages-container');
        container.innerHTML = messages.map(m => `
            <div class="chat-bubble ${m.sender_name === 'Anvar Karimov' ? 'received' : 'sent'}">
                <strong>${m.sender_name}:</strong> ${m.message}
            </div>
        `).join('');
        container.scrollTop = container.scrollHeight;
    } catch (e) {
        console.error(e);
    }
}

async function sendChatMessage() {
    const trip = activeClientTrip || activeDriverTrip;
    const textInput = document.getElementById('chat-input-text');
    const msg = textInput.value.trim();
    if (!msg || !trip) return;

    try {
        await fetch(`${API_BASE}/chat/${trip.id}/messages/`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ sender_id: 1, message: msg })
        });
        textInput.value = '';
        loadChatMessages(trip.id);
    } catch (e) {
        console.error(e);
    }
}

// --- REAL-TIME TRIP SIMULATION & MAP ANIMATION ---
function startTripSimulation(tripId) {
    let step = 0;
    
    simulationInterval = setInterval(async () => {
        step++;
        
        if (step === 2) {
            await driverAcceptTrip(tripId);
            document.getElementById('client-trip-status-badge').innerText = 'Haydovchi qabul qildi (Yo\'lda)';
            document.getElementById('client-driver-name').innerText = 'Anvar Karimov';
            document.getElementById('client-driver-car').innerText = 'Chevrolet Cobalt • 01 A 777 AA';
            document.getElementById('trip-progress-bar').style.width = '40%';
        } else if (step === 4) {
            document.getElementById('client-trip-status-badge').innerText = 'Haydovchi yetib keldi';
            document.getElementById('trip-progress-bar').style.width = '65%';
        } else if (step === 6) {
            document.getElementById('client-trip-status-badge').innerText = 'Yo\'lda (Safar boshlandi)';
            document.getElementById('trip-progress-bar').style.width = '85%';
        } else if (step === 9) {
            clearInterval(simulationInterval);
            document.getElementById('trip-progress-bar').style.width = '100%';
            document.getElementById('client-active-trip-card').classList.add('hidden');
            document.getElementById('btn-create-trip').disabled = false;
            openRatingModal(tripId);
        }
        
        moveDriverOnMap(step / 9);
    }, 3000);
}

// --- ADMIN DASHBOARD & LIVE TARIFF EDITOR ---
async function updateAdminDashboard() {
    try {
        const res = await fetch(`${API_BASE}/admin/dashboard/`);
        const stats = await res.json();

        document.getElementById('kpi-total-trips').innerText = stats.total_trips;
        document.getElementById('kpi-online-drivers').innerText = stats.online_drivers;
        document.getElementById('kpi-total-revenue').innerText = `${parseInt(stats.total_revenue).toLocaleString()} so'm`;
        document.getElementById('kpi-platform-commission').innerText = `${parseInt(stats.platform_commission).toLocaleString()} so'm`;

        const tripsRes = await fetch(`${API_BASE}/trips/`);
        const trips = await tripsRes.json();
        const tbody = document.getElementById('admin-trips-table-body');
        tbody.innerHTML = trips.slice(0, 5).map(t => `
            <tr>
                <td>#${t.id}</td>
                <td>${t.client ? t.client.username : 'Mijoz'}</td>
                <td>${t.driver ? t.driver.car_model : 'Qidirilmoqda'}</td>
                <td>${t.tariff ? t.tariff.name : 'Standart'}</td>
                <td><strong>${parseInt(t.estimated_price).toLocaleString()} so'm</strong></td>
                <td><span class="status-badge">${t.status}</span></td>
            </tr>
        `).join('');
    } catch (e) {
        console.error("Admin dashboard load error:", e);
    }
}

async function loadTariffDetailsToEditor(tariffId) {
    try {
        const res = await fetch(`${API_BASE}/tariffs/`);
        const tariffs = await res.json();
        const t = tariffs.find(x => x.id == tariffId);
        if (t) {
            document.getElementById('edit-tariff-base').value = parseInt(t.base_price);
            document.getElementById('edit-tariff-km').value = parseInt(t.price_per_km);
        }
    } catch (e) {
        console.error(e);
    }
}

async function saveAdminTariffChanges() {
    const tariffId = document.getElementById('admin-tariff-select').value;
    const basePrice = document.getElementById('edit-tariff-base').value;
    const kmPrice = document.getElementById('edit-tariff-km').value;

    try {
        const res = await fetch(`${API_BASE}/admin/tariffs/${tariffId}/`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ base_price: basePrice, price_per_km: kmPrice })
        });
        if (res.ok) {
            alert("✅ Tarif narxlari real vaqtda yangilandi!");
            fetchTariffs();
        }
    } catch (e) {
        console.error(e);
    }
}

// --- MODALS ENGINE ---
function openAuthModal() { document.getElementById('auth-modal').classList.remove('hidden'); }
function closeAuthModal() { document.getElementById('auth-modal').classList.add('hidden'); }

function sendAuthOTP() {
    document.getElementById('auth-step-phone').classList.add('hidden');
    document.getElementById('auth-step-otp').classList.remove('hidden');
}

function verifyAuthOTP() {
    const phone = document.getElementById('auth-phone-input').value;
    document.getElementById('user-phone-display').innerText = phone;
    closeAuthModal();
}

function openRatingModal(tripId) {
    document.getElementById('rating-modal').classList.remove('hidden');
    document.getElementById('rating-modal').dataset.tripId = tripId;
}

function setStarRating(val) {
    activeRatingStar = val;
    const stars = document.querySelectorAll('#star-rating-box .star-btn');
    stars.forEach((s, idx) => {
        s.classList.toggle('active', idx < val);
    });
}

async function submitTripRating() {
    const tripId = document.getElementById('rating-modal').dataset.tripId;
    const comment = document.getElementById('rating-comment').value;

    try {
        await fetch(`${API_BASE}/trips/${tripId}/rate/`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ client_rating: activeRatingStar, comment: comment })
        });
        document.getElementById('rating-modal').classList.add('hidden');
        alert("Bahoyingiz saqlandi. Rahmat!");
    } catch (e) {
        console.error(e);
    }
}

async function toggleTripHistory() {
    const modal = document.getElementById('history-modal');
    modal.classList.remove('hidden');

    try {
        const res = await fetch(`${API_BASE}/trips/`);
        const trips = await res.json();
        const container = document.getElementById('history-list-container');
        
        container.innerHTML = trips.map(t => `
            <div class="glass-card mb-2">
                <div class="order-top-row">
                    <span>${t.service_type === 'delivery' ? '📦 Delivery' : '🚕 Trip'} #${t.id} - ${new Date(t.created_at).toLocaleString()}</span>
                    <span class="order-price">${parseInt(t.estimated_price).toLocaleString()} so'm</span>
                </div>
                <p class="mt-2">📍 ${t.pickup_address} ➔ 🏁 ${t.dropoff_address}</p>
                <div class="mt-2 text-dim font-sm">To'lov: ${t.payment ? t.payment.method : 'Naqd'} | Status: ${t.status}</div>
            </div>
        `).join('');
    } catch (e) {
        console.error(e);
    }
}

function closeTripHistory() {
    document.getElementById('history-modal').classList.add('hidden');
}

// --- CANVAS MAP ENGINE & INTERACTIVE PIN CLICK LISTENER ---
let canvas, ctx;
let driverProgressRatio = 0;

function initCanvasMap() {
    canvas = document.getElementById('cityMapCanvas');
    ctx = canvas.getContext('2d');

    function resizeCanvas() {
        canvas.width = canvas.parentElement.clientWidth;
        canvas.height = canvas.parentElement.clientHeight;
        renderMapFrame();
    }
    window.addEventListener('resize', resizeCanvas);
    resizeCanvas();

    // Map Click Listener: Set Pickup / Dropoff pin by clicking anywhere on the map!
    canvas.addEventListener('click', (e) => {
        const rect = canvas.getBoundingClientRect();
        const clickX = e.clientX - rect.left;
        const clickY = e.clientY - rect.top;

        // Alternate pickup / dropoff setting on click
        const placeName = `Xarita Nuqtasi [${Math.round(clickX)}, ${Math.round(clickY)}]`;
        currentDropoff = { address: placeName, lat: 41.3000 + (clickY / 10000), lng: 69.2500 + (clickX / 10000) };
        document.getElementById('input-dropoff').value = placeName;
        calculateRouteAndTariffs();
    });

    requestAnimationFrame(function loop() {
        renderMapFrame();
        requestAnimationFrame(loop);
    });
}

function moveDriverOnMap(ratio) {
    driverProgressRatio = Math.min(1, Math.max(0, ratio));
}

function resetMapCamera() {
    driverProgressRatio = 0;
}

function toggleMapTraffic() {
    alert("Tirbandlik rejimi yoqildi (Toshkent markazida yashil/sariq oqimlar ko'rsatilmoqda).");
}

function renderMapFrame() {
    if (!ctx) return;
    const w = canvas.width;
    const h = canvas.height;

    // Dark Map Base
    ctx.fillStyle = '#0d1117';
    ctx.fillRect(0, 0, w, h);

    // City Grid & Blocks
    ctx.strokeStyle = 'rgba(255, 255, 255, 0.04)';
    ctx.lineWidth = 1;
    const gridSize = 40;

    for (let x = 0; x < w; x += gridSize) {
        ctx.beginPath(); ctx.moveTo(x, 0); ctx.lineTo(x, h); ctx.stroke();
    }
    for (let y = 0; y < h; y += gridSize) {
        ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(w, y); ctx.stroke();
    }

    // Main Avenues
    ctx.strokeStyle = '#1e293b';
    ctx.lineWidth = 14;
    
    ctx.beginPath();
    ctx.moveTo(w * 0.1, h * 0.8);
    ctx.lineTo(w * 0.9, h * 0.2);
    ctx.stroke();

    ctx.beginPath();
    ctx.moveTo(w * 0.15, h * 0.25);
    ctx.lineTo(w * 0.85, h * 0.75);
    ctx.stroke();

    // Active Route
    const pX = w * 0.25;
    const pY = h * 0.65;
    const dX = w * 0.75;
    const dY = h * 0.35;

    ctx.shadowColor = '#10b981';
    ctx.shadowBlur = 12;
    ctx.strokeStyle = '#10b981';
    ctx.lineWidth = 5;
    ctx.setLineDash([8, 6]);
    ctx.beginPath();
    ctx.moveTo(pX, pY);
    ctx.lineTo(dX, dY);
    ctx.stroke();
    ctx.setLineDash([]);
    ctx.shadowBlur = 0;

    // Pickup Marker
    ctx.fillStyle = '#10b981';
    ctx.beginPath();
    ctx.arc(pX, pY, 10, 0, Math.PI * 2);
    ctx.fill();
    ctx.fillStyle = '#ffffff';
    ctx.font = 'bold 11px Outfit';
    ctx.fillText('A (Olish)', pX - 24, pY + 24);

    // Dropoff Marker
    ctx.fillStyle = '#ef4444';
    ctx.beginPath();
    ctx.arc(dX, dY, 10, 0, Math.PI * 2);
    ctx.fill();
    ctx.fillStyle = '#ffffff';
    ctx.fillText('B (Borish)', dX - 24, dY + 24);

    // Animated Driver Car Icon
    const currentCarX = pX + (dX - pX) * driverProgressRatio;
    const currentCarY = pY + (dY - pY) * driverProgressRatio;

    ctx.shadowColor = '#3b82f6';
    ctx.shadowBlur = 18;
    ctx.fillStyle = '#3b82f6';
    ctx.beginPath();
    ctx.arc(currentCarX, currentCarY, 12, 0, Math.PI * 2);
    ctx.fill();
    ctx.shadowBlur = 0;

    ctx.fillStyle = '#ffffff';
    ctx.font = 'bold 14px FontAwesome';
    ctx.fillText('🚕', currentCarX - 7, currentCarY + 5);
}
