const API_URL = 'http://localhost:5000';

const startBtn = document.getElementById('startBtn');
const downloadBtn = document.getElementById('downloadBtn');
const statusCard = document.getElementById('status-card');
const statusText = document.getElementById('statusText');
const progressBar = document.getElementById('progressBar');
const countValue = document.getElementById('countValue');
const errorMsg = document.getElementById('error-msg');
const queryInput = document.getElementById('query');
const locationInput = document.getElementById('location');

let pollInterval = null;

async function startScraping() {
    const query = queryInput.value.trim();
    const loc = locationInput.value.trim();

    if (!query || !loc) {
        showError("Please enter both query and location.");
        return;
    }

    startBtn.disabled = true;
    startBtn.querySelector('.btn-text').textContent = "Starting...";

    try {
        const response = await fetch(`${API_URL}/start-scraping`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ query: query, location: loc })
        });

        const data = await response.json();

        if (response.ok) {
            statusCard.classList.remove('hidden');
            startPolling();
        } else {
            showError(data.error || "Failed to start scraping");
            resetUI();
        }
    } catch (err) {
        showError("Cannot connect to backend. Is it running?");
        resetUI();
    }
}

function startPolling() {
    if (pollInterval) clearInterval(pollInterval);
    pollInterval = setInterval(checkProgress, 1000);
}

async function checkProgress() {
    try {
        const response = await fetch(`${API_URL}/progress`);
        const data = await response.json();

        updateUI(data);

        if (!data.is_active && data.target > 0 && data.download_ready) {
            // Finished
            clearInterval(pollInterval);
            startBtn.disabled = false;
            startBtn.querySelector('.btn-text').textContent = "Start New Scrape";
            downloadBtn.classList.remove('hidden');
        } else if (!data.is_active && !data.download_ready && data.status.includes('Error')) {
            clearInterval(pollInterval);
            showError(data.status);
            resetUI();
        }

    } catch (err) {
        console.error("Polling error", err);
    }
}

function updateUI(data) {
    statusText.textContent = data.status;
    countValue.textContent = data.count;

    // Convert to percentage
    const pct = Math.min((data.count / data.target) * 100, 100);
    progressBar.style.width = `${pct}%`;
}

function downloadFile() {
    window.location.href = `${API_URL}/download`;
}

function showError(msg) {
    errorMsg.textContent = msg;
    errorMsg.classList.remove('hidden');
    setTimeout(() => {
        errorMsg.classList.add('hidden');
    }, 5000);
}

function resetUI() {
    startBtn.disabled = false;
    startBtn.querySelector('.btn-text').textContent = "Start Scraping";
}

startBtn.addEventListener('click', startScraping);
downloadBtn.addEventListener('click', downloadFile);
