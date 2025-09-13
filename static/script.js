// --- COMPLETE SCRIPT WITH ALL FIXES AND NEW FEATURES ---

// Sidebar toggle functionality
function toggleSidebar() {
    document.getElementById('sidebar').classList.toggle('active');
    document.getElementById('overlay').classList.toggle('active');
    document.querySelector('.hamburger').classList.toggle('active');
}

// Navigation functionality
document.querySelectorAll('.nav-link').forEach(link => {
    link.addEventListener('click', function (e) {
        e.preventDefault();
        navigateToPage(this.dataset.page);
        if (window.innerWidth <= 768) { toggleSidebar(); }
    });
});

function navigateToPage(pageId) {
    document.querySelectorAll('.nav-link').forEach(l => l.classList.remove('active'));
    const activeLink = document.querySelector(`[data-page="${pageId}"]`);
    if (activeLink) activeLink.classList.add('active');

    document.querySelectorAll('.page-content').forEach(page => page.classList.remove('active'));
    const activePage = document.getElementById(pageId);
    if (activePage) activePage.classList.add('active');

    const pageNames = { 'home': 'Dashboard', 'services': 'All Services', 'tickets': 'My Applications', 'certificates': 'Certificates', 'payments': 'Payments', 'profile': 'Profile' };
    document.getElementById('current-page').textContent = pageNames[pageId] || 'Dashboard';

    if (pageId === 'tickets') {
        fetchAndRenderApplications(); // Refresh data when navigating to the tickets page
    }
}

// --- NEW, UPDATED TICKET TAB LOGIC ---
function switchTab(tabElement, filter) {
    document.querySelectorAll('.ticket-tab').forEach(tab => tab.classList.remove('active'));
    tabElement.classList.add('active');

    document.querySelectorAll('.ticket-item').forEach(item => {
        const itemType = item.dataset.type;
        const itemStatus = item.dataset.status;

        if (filter === 'complaint') {
            // If "Complaints" tab, show only items of type 'complaint'
            if (itemType === 'complaint') {
                item.style.display = 'block';
            } else {
                item.style.display = 'none';
            }
        } else {
            // For other tabs (active, completed, rejected), show non-complaints that match the status
            if (itemType !== 'complaint' && itemStatus === filter) {
                item.style.display = 'block';
            } else {
                item.style.display = 'none';
            }
        }
    });
}

// Notification system
function showNotification(message, type = 'success') {
    const notification = document.getElementById('notification');
    notification.textContent = message;
    notification.className = `notification ${type}`;
    notification.classList.add('show');
    setTimeout(() => { notification.classList.remove('show'); }, 4000);
}

// --- NEW: DYNAMIC TICKET CREATION & FETCHING ---
function createTicketItemHTML(ticket) {
    let statusMap = {
        "In Review": { text: "In Review", status: "active", class: "status-progress" },
        "Payment Pending": { text: "Payment Pending", status: "active", class: "status-new" },
        "Approved": { text: "Approved", status: "completed", class: "status-resolved" },
        "Completed": { text: "Completed", status: "completed", class: "status-resolved" },
        "Rejected": { text: "Rejected", status: "rejected", class: "status-rejected" }
    };

    let statusInfo = statusMap[ticket.status_text] || { text: ticket.status_text, status: "active", class: "status-progress" };

    let downloadButton = '';
    if (ticket.type === 'certificate' && statusInfo.status === 'completed') {
        downloadButton = `<a href="/static/Income_certificate.jpg" download="Income_Certificate.jpg" class="ticket-download-btn" title="Download Certificate">⬇️</a>`;
    }

    return `
        <div class="ticket-item" data-status="${statusInfo.status}" data-type="${ticket.type}">
            <div class="ticket-header">
                <div>
                    <div class="ticket-title">${ticket.title}</div>
                    <div class="ticket-info">ID: ${ticket.id}<br>${ticket.details}</div>
                </div>
                <div class="ticket-actions-container">
                    ${downloadButton}
                    <div class="ticket-status ${statusInfo.class}">${statusInfo.text}</div>
                </div>
            </div>
        </div>
    `;
}

async function fetchAndRenderApplications() {
    try {
        const response = await fetch('/api/get-applications');
        const data = await response.json();
        if (!data.ok) {
            throw new Error('Failed to fetch applications');
        }

        const container = document.querySelector('#tickets .tickets-container');
        if (!container) return;

        // Add the tabs first if they don't exist
        if (!container.querySelector('.ticket-tabs')) {
            container.innerHTML = `
                <div class="ticket-tabs">
                    <button class="ticket-tab active" data-filter="complaint">Complaints</button>
                    <button class="ticket-tab" data-filter="active">Active</button>
                    <button class="ticket-tab" data-filter="completed">Completed</button>
                    <button class="ticket-tab" data-filter="rejected">Rejected</button>
                </div>
            `;
        }
        
        // Clear only the ticket items, not the tabs
        const existingItems = container.querySelectorAll('.ticket-item');
        existingItems.forEach(item => item.remove());

        data.applications.forEach(ticket => {
            container.innerHTML += createTicketItemHTML(ticket);
        });
        
        // Re-attach event listeners to the tabs
        container.querySelectorAll('.ticket-tab').forEach(tab => {
            tab.addEventListener('click', () => {
                switchTab(tab, tab.dataset.filter);
            });
        });

        // Make sure the initial tab filter is applied
        const initialActiveTab = container.querySelector('.ticket-tab.active');
        if (initialActiveTab) {
            switchTab(initialActiveTab, initialActiveTab.dataset.filter);
        }

    } catch (error) {
        console.error("Error fetching applications:", error);
        const container = document.querySelector('#tickets .tickets-container');
        if (container) container.innerHTML = '<p style="color: var(--warning-red);">Could not load applications.</p>';
    }
}


// --- EXISTING WORKING CODE (UNCHANGED) ---

// JAVASCRIPT FOR PAYMENT MODAL
const paymentModalOverlay = document.getElementById('paymentModalOverlay');
const paymentModalTitle = document.getElementById('paymentModalTitle');
const paymentModalBody = document.getElementById('paymentModalBody');

function openPaymentModal(paymentType) {
    let title = '';
    let bodyContent = '';
    switch (paymentType) {
        case 'property_tax':
            title = 'Property Tax Status';
            const transactionId = `TID${Math.floor(Math.random() * 900000) + 100000}`;
            bodyContent = `<p>Your property tax for the current year has already been paid.</p><p><strong>Amount Paid:</strong> ₹ 1,750</p><p><strong>Paid On:</strong> August 05, 2025</p><p><strong>Transaction ID:</strong> ${transactionId}</p>`;
            break;
        case 'water_bill':
            title = 'Water Bill Payment';
            bodyContent = `<p>Your monthly water bill is pending.</p><p><strong>Amount Due:</strong> ₹ 450</p><p><strong>Due Date:</strong> August 25, 2025</p><button class="pay-now-btn" onclick="handleWaterPayment(this)">Pay Now with UPI</button>`;
            break;
        case 'application_fees':
            title = 'Application Fees';
            bodyContent = '<p>You have no pending application fees.</p>';
            break;
        case 'penalties':
            title = 'Penalties & Fines';
            bodyContent = '<p>You have no pending penalties or fines.</p>';
            break;
    }
    paymentModalTitle.innerText = title;
    paymentModalBody.innerHTML = bodyContent;
    paymentModalOverlay.classList.add('show-modal');
}

function closePaymentModal() {
    paymentModalOverlay.classList.remove('show-modal');
}

function handleWaterPayment(button) {
    button.disabled = true;
    paymentModalBody.innerHTML = `<p style="font-size: 1.1rem; text-align: center; color: var(--success-green);">✅ Payment Request Sent!</p><p style="text-align: center;">A payment request for <strong>₹ 450</strong> has been sent to your registered UPI account.</p><p style="text-align: center;">Please complete the payment within 5 minutes.</p>`;
}

// JAVASCRIPT FOR CHATBOT
function displayBill(billData) {
    const chatHistory = document.getElementById('chat-history');
    const billContainer = document.createElement('div');
    billContainer.className = 'bill-container';
    let statusClass = billData.status === 'Paid' ? 'status-paid' : 'status-unpaid';
    let billHTML = `<h4>${billData.title}</h4><div class="bill-details"><p><strong>Bill ID:</strong> ${billData.bill_id}</p><p><strong>Name:</strong> ${billData.name}</p><p><strong>Amount:</strong> ${billData.amount}</p><p><strong>Status:</strong> <span class="bill-status ${statusClass}">${billData.status}</span></p>${billData.status === 'Paid' ? `<p><strong>Paid On:</strong> ${billData.paid_on}</p>` : `<p><strong>Due Date:</strong> ${billData.due_date}</p>`}</div>`;
    billContainer.innerHTML = billHTML;

    if (billData.status === 'Unpaid') {
        const payButton = document.createElement('button');
        payButton.className = 'pay-now-btn';
        payButton.textContent = 'Pay Now';
        payButton.onclick = () => {
            showNotification(`Payment request for ${billData.amount} sent to ${billData.phone}. Please pay within 5 minutes.`, 'success');
            payButton.disabled = true;
            payButton.textContent = 'Request Sent';
        };
        billContainer.appendChild(payButton);
    }
    chatHistory.appendChild(billContainer);
}

async function sendMessage() {
    const chatInput = document.querySelector('.chat-input');
    const chatHistory = document.getElementById('chat-history');
    const languageSelector = document.getElementById('languageSelector');
    const message = chatInput.value.trim();
    if (!message) {
        showNotification('Please enter a message first.', 'error');
        return;
    }
    const userMessageDiv = document.createElement('div');
    userMessageDiv.className = 'chat-message user-message';
    userMessageDiv.textContent = message;
    chatHistory.appendChild(userMessageDiv);
    chatInput.value = '';
    chatHistory.scrollTop = chatHistory.scrollHeight;

    try {
        const response = await fetch('/api/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ 
                message: message,
                target_language: languageSelector.value
            }),
        });
        if (!response.ok) throw new Error(`HTTP error! Status: ${response.status}`);
        const data = await response.json();
        if (data.response_type === 'bill_details') {
            displayBill(data.data);
        } else {
            const botMessageDiv = document.createElement('div');
            botMessageDiv.className = 'chat-message bot-message';
            botMessageDiv.textContent = data.bot_reply;
            chatHistory.appendChild(botMessageDiv);
        }
    } catch (error) {
        console.error('Error sending message:', error);
        const errorMessageDiv = document.createElement('div');
        errorMessageDiv.className = 'chat-message bot-message';
        errorMessageDiv.textContent = 'Sorry, there was an error connecting to the server.';
        errorMessageDiv.style.backgroundColor = 'var(--warning-red)';
        errorMessageDiv.style.color = 'var(--white)';
        chatHistory.appendChild(errorMessageDiv);
        showNotification('Failed to get a response.', 'error');
    } finally {
        chatHistory.scrollTop = chatHistory.scrollHeight;
    }
}

// JAVASCRIPT FOR VOICE INPUT (STT)
let mediaRecorder;
let audioChunks = [];

async function startVoiceInput() {
    const micButton = document.getElementById('micButton');
    const chatInput = document.querySelector('.chat-input');
    const languageSelector = document.getElementById('languageSelector');

    if (mediaRecorder && mediaRecorder.state === "recording") {
        mediaRecorder.stop();
        return;
    }

    try {
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        mediaRecorder = new MediaRecorder(stream);

        mediaRecorder.onstart = () => {
            micButton.classList.add('is-recording');
            micButton.innerText = '🛑';
            chatInput.value = 'Listening...';
            audioChunks = [];
        };

        mediaRecorder.onstop = async () => {
            micButton.classList.remove('is-recording');
            micButton.innerText = '🎤';
            chatInput.value = 'Processing voice... Please wait...';

            const audioBlob = new Blob(audioChunks, { type: 'audio/webm' });
            const formData = new FormData();
            formData.append('audio', audioBlob, 'recording.webm');
            formData.append('language', languageSelector.value); // Add the language hint

            try {
                const response = await fetch('/api/voice-to-text', {
                    method: 'POST',
                    body: formData
                });
                if (!response.ok) {
                    const errorData = await response.json();
                    throw new Error(errorData.error || `Server error: ${response.status}`);
                }
                const data = await response.json();
                if (data.ok) {
                    chatInput.value = data.text;
                } else {
                    throw new Error(data.error || 'Could not understand audio.');
                }
            } catch (err) {
                console.error('Error in voice-to-text fetch:', err);
                chatInput.value = '';
                showNotification(err.message, 'error');
            }
            stream.getTracks().forEach(track => track.stop());
        };
        mediaRecorder.start();
    } catch (err) {
        console.error("Error accessing microphone:", err);
        showNotification('Microphone access denied. Please allow permissions.', 'error');
    }
}

// Attach listeners on page load
window.addEventListener('load', () => {
    setTimeout(() => {
        showNotification('Welcome to the Sahayatha Digital Portal!', 'success');
    }, 1000);
    
    // Attach mic button listener
    const micButton = document.getElementById('micButton');
    if (micButton) {
        micButton.addEventListener('click', startVoiceInput);
    }

    // Attach listener for Enter key in chat
    const chatInput = document.querySelector('.chat-input');
    if (chatInput) {
        chatInput.addEventListener('keypress', function (event) {
            if (event.key === 'Enter' && !event.shiftKey) {
                event.preventDefault();
                sendMessage();
            }
        });
    }
});

