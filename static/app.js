const state = {
    currentTab: 'vung-tau',
    tabData: null,
    searchQuery: '',
};

const DOM = {
    tabNav: () => document.getElementById('tab-nav'),
    tabContent: () => document.getElementById('tab-content'),
    searchInput: () => document.getElementById('search-input'),
    refreshBtn: () => document.getElementById('refresh-btn'),
    settingsModal: () => document.getElementById('settings-modal'),
    cookieInput: () => document.getElementById('cookie-input'),
    saveCookieBtn: () => document.getElementById('save-cookie-btn'),
    deleteCookieBtn: () => document.getElementById('delete-cookie-btn'),
    cookieStatusHint: () => document.getElementById('cookie-status-hint'),
    loadingOverlay: () => document.getElementById('loading-overlay'),
    cookieBanner: () => document.getElementById('cookie-banner'),
    lastUpdatedTime: () => document.getElementById('last-updated-time'),
    statusText: () => document.querySelector('.status-text')
};

document.addEventListener('DOMContentLoaded', () => {
    setupListeners();
    checkLocalCookie();
});

function setupListeners() {
    DOM.tabNav().addEventListener('click', (e) => {
        const btn = e.target.closest('.tab-btn');
        if (btn) {
            document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('tab-btn--active'));
            btn.classList.add('tab-btn--active');
            state.currentTab = btn.dataset.tab;
            state.tabData = null; // Reset dữ liệu cũ
            renderContent();
        }
    });

    DOM.refreshBtn().addEventListener('click', () => {
        const localCookie = localStorage.getItem('shopee_cookie');
        if (!localCookie) {
            showToast('Vui lòng cài đặt và lưu Cookie trước khi chạy quét!', 'error');
            DOM.settingsModal().style.display = 'flex';
            return;
        }
        fetchDataForTab(state.currentTab, localCookie);
    });

    document.getElementById('settings-btn').addEventListener('click', () => {
        DOM.settingsModal().style.display = 'flex';
        checkLocalCookie(); // Cập nhật hiển thị form khi mở modal
    });
    
    document.getElementById('modal-close').addEventListener('click', () => DOM.settingsModal().style.display = 'none');
    document.getElementById('cookie-banner-btn').addEventListener('click', () => DOM.settingsModal().style.display = 'flex');
    
    DOM.saveCookieBtn().addEventListener('click', saveCookie);
    DOM.deleteCookieBtn().addEventListener('click', deleteCookie);

    DOM.searchInput().addEventListener('input', (e) => {
        state.searchQuery = e.target.value.toLowerCase();
        renderContent();
    });
}

// Kiểm tra sự tồn tại của Cookie tại bộ nhớ Trình duyệt (localStorage)
function checkLocalCookie() {
    const localCookie = localStorage.getItem('shopee_cookie');
    if (localCookie) {
        DOM.cookieBanner().style.display = 'none';
        DOM.cookieInput().value = localCookie;
        DOM.cookieStatusHint().textContent = `Trạng thái: 🟢 Đã lưu Cookie (${localCookie.length} ký tự)`;
        DOM.cookieStatusHint().style.color = 'var(--accent-success)';
    } else {
        DOM.cookieBanner().style.display = 'flex';
        DOM.cookieInput().value = '';
        DOM.cookieStatusHint().textContent = 'Trạng thái: 🔴 Chưa cấu hình cookie trên máy';
        DOM.cookieStatusHint().style.color = 'var(--accent-danger)';
    }
}

// Xử lý Lưu Cookie
async function saveCookie() {
    const cookie = DOM.cookieInput().value.trim();
    if (!cookie) return showToast('Vui lòng điền cookie!', 'error');
    
    DOM.saveCookieBtn().textContent = 'Đang kiểm tra...';
    try {
        const res = await fetch('/api/cookie', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ cookie })
        });
        const json = await res.json();
        
        if (json.valid) {
            // LƯU TRỰC TIẾP VÀO TRÌNH DUYỆT USER
            localStorage.setItem('shopee_cookie', cookie);
            showToast('Lưu Cookie vào trình duyệt thành công!', 'success');
            DOM.settingsModal().style.display = 'none';
            checkLocalCookie();
            fetchDataForTab(state.currentTab, cookie);
        } else {
            showToast('Cookie không hợp lệ hoặc đã hết hạn!', 'error');
        }
    } catch (err) {
        showToast('Lỗi kết nối server!', 'error');
    } finally {
        DOM.saveCookieBtn().textContent = 'Xác thực & Lưu Trình Duyệt';
    }
}

// Xóa Cookie
function deleteCookie() {
    if (localStorage.getItem('shopee_cookie')) {
        localStorage.removeItem('shopee_cookie');
        showToast('Đã xóa Cookie khỏi trình duyệt của bạn!', 'info');
        checkLocalCookie();
        state.tabData = null;
        renderContent();
    } else {
        showToast('Trình duyệt không có cookie để xóa.', 'info');
    }
}

async function fetchDataForTab(tabKey, cookie) {
    DOM.loadingOverlay().style.display = 'flex';
    try {
        const res = await fetch(`/api/data/${tabKey}`, {
            headers: {
                'X-Shopee-Cookie': cookie // Gửi kèm cookie trong Header request
            }
        });
        if (!res.ok) throw new Error("Yêu cầu thất bại! Cookie của bạn có thể đã hết hạn.");
        const json = await res.json();
        
        state.tabData = json;
        DOM.lastUpdatedTime().textContent = json.last_updated;
        DOM.statusText().textContent = `Trạng Thái: 🟢 Sẵn Sàng`;
        
        animateValue(document.getElementById('val-hubs'), 0, json.hub_count, 500);
        animateValue(document.getElementById('val-warehouse'), 0, json.total_warehouse, 600);
        animateValue(document.getElementById('val-yard'), 0, json.total_yard, 600);
        
        renderContent();
        showToast(`Quét thành công khu vực ${json.label}!`, 'success');
    } catch (err) {
        showToast(err.message, 'error');
    } finally {
        DOM.loadingOverlay().style.display = 'none';
    }
}

function renderContent() {
    const container = DOM.tabContent();
    if (!state.tabData) {
        container.innerHTML = `
            <div class="empty-state" style="text-align:center; padding:50px;">
                <div class="empty-state-icon" style="font-size:3rem;">⚡</div>
                <p class="empty-state-text">Dữ liệu Tab này đang trống. Nhấp <b>[CHẠY QUÉT TAB NÀY]</b> ở góc trên bên phải để tải.</p>
            </div>`;
        return;
    }

    let hubs = [...state.tabData.hubs];
    hubs.sort((a, b) => b.warehouse - a.warehouse); // Giảm dần mặc định

    if (state.searchQuery) {
        hubs = hubs.filter(h => h.name.toLowerCase().includes(state.searchQuery));
    }

    let rowsHtml = '';
    hubs.forEach((hub, i) => {
        rowsHtml += `
            <tr>
                <td class="cell-index">${i + 1}</td>
                <td class="cell-name">${hub.name}</td>
                <td class="cell-number ${hub.warehouse > 100 ? 'value-high' : ''}">${hub.warehouse.toLocaleString('vi-VN')}</td>
                <td class="cell-number">${hub.yard.toLocaleString('vi-VN')}</td>
            </tr>`;
    });

    container.innerHTML = `
        <div class="table-wrapper">
            <table class="data-table">
                <thead>
                    <tr>
                        <th style="width:50px; text-align:center">#</th>
                        <th>Tên Hub Hệ Thống</th>
                        <th class="text-right sort-desc" style="color: var(--accent-primary);">Tổng Trong Kho (Kiện)</th>
                        <th class="text-right">Tổng Ngoài Bãi (Kiện)</th>
                    </tr>
                </thead>
                <tbody>
                    ${rowsHtml || '<tr><td colspan="4" style="text-align:center;">Không tìm thấy dữ liệu trạm phù hợp</td></tr>'}
                </tbody>
            </table>
        </div>`;
}

function animateValue(obj, start, end, duration) {
    let startTimestamp = null;
    const step = (timestamp) => {
        if (!startTimestamp) startTimestamp = timestamp;
        const progress = Math.min((timestamp - startTimestamp) / duration, 1);
        obj.innerHTML = Math.floor(progress * (end - start) + start).toLocaleString('vi-VN');
        if (progress < 1) window.requestAnimationFrame(step);
    };
    window.requestAnimationFrame(step);
}

function showToast(msg, type='info') {
    const container = document.getElementById('toast-container');
    const toast = document.createElement('div');
    toast.className = `toast toast--${type}`;
    toast.innerHTML = `<span class="toast-message">${msg}</span>`;
    container.appendChild(toast);
    setTimeout(() => toast.remove(), 3500);
}