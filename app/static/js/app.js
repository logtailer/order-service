'use strict';

let currentPage = 1;
let currentStatus = '';
let selectedOrderId = null;

// ---- API ----

async function apiFetch(path, opts = {}) {
  const res = await fetch(path, {
    headers: { 'Content-Type': 'application/json' },
    ...opts,
  });
  const data = await res.json();
  if (!res.ok) throw new Error(data.error || `HTTP ${res.status}`);
  return data;
}

function toast(msg, isError = true) {
  const el = document.createElement('div');
  el.className = 'toast' + (isError ? ' error' : '');
  el.textContent = msg;
  document.body.appendChild(el);
  setTimeout(() => el.remove(), 4000);
}

// ---- Health ----

async function loadHealth() {
  try {
    const data = await apiFetch('/health');
    document.getElementById('db-dot').className = 'dot ' + data.db;
    document.getElementById('db-label').textContent = 'db ' + data.db;
  } catch {
    document.getElementById('db-dot').className = 'dot disconnected';
    document.getElementById('db-label').textContent = 'unreachable';
  }
}

// ---- Summary ----

async function loadSummary() {
  try {
    const data = await apiFetch('/orders/summary');
    document.getElementById('summary').innerHTML = Object.entries(data)
      .map(([status, count]) => `
        <div class="summary-card">
          <div class="count">${count}</div>
          <div class="label">${status}</div>
        </div>
      `).join('');
  } catch (e) {
    toast('Failed to load summary: ' + e.message);
  }
}

// ---- Orders list ----

function fmt(iso) {
  if (!iso) return '—';
  return new Date(iso).toLocaleString();
}

function badge(status) {
  return `<span class="badge badge-${status}">${status}</span>`;
}

async function loadOrders(page = 1, status = '') {
  currentPage = page;
  currentStatus = status;

  const params = new URLSearchParams({ page, per_page: 20 });
  if (status) params.set('status', status);

  try {
    const data = await apiFetch(`/orders?${params}`);
    const tbody = document.getElementById('orders-tbody');

    if (!data.orders.length) {
      tbody.innerHTML = '<tr><td colspan="5" class="empty">No orders found.</td></tr>';
    } else {
      tbody.innerHTML = data.orders.map(o => `
        <tr data-id="${o.id}"${o.id === selectedOrderId ? ' class="selected"' : ''}>
          <td>${o.id}</td>
          <td>${o.user_id}</td>
          <td>${badge(o.status)}</td>
          <td>$${(o.total_price || 0).toFixed(2)}</td>
          <td>${fmt(o.created_at)}</td>
        </tr>
      `).join('');
    }

    renderPagination(data.page, data.pages);
  } catch (e) {
    toast('Failed to load orders: ' + e.message);
  }
}

function renderPagination(page, pages) {
  const el = document.getElementById('pagination');
  if (pages <= 1) { el.innerHTML = ''; return; }

  const btns = [
    `<button ${page === 1 ? 'disabled' : ''} data-page="${page - 1}">&#8249;</button>`,
    ...Array.from({ length: pages }, (_, i) =>
      `<button data-page="${i + 1}"${i + 1 === page ? ' class="active"' : ''}>${i + 1}</button>`
    ),
    `<button ${page === pages ? 'disabled' : ''} data-page="${page + 1}">&#8250;</button>`,
    `<span class="page-info">page ${page} of ${pages}</span>`,
  ];
  el.innerHTML = btns.join('');
}

// ---- Detail ----

async function loadDetail(orderId) {
  selectedOrderId = orderId;
  document.querySelectorAll('#orders-tbody tr').forEach(r =>
    r.classList.toggle('selected', parseInt(r.dataset.id) === orderId)
  );

  try {
    const [order, history] = await Promise.all([
      apiFetch(`/orders/${orderId}`),
      apiFetch(`/orders/${orderId}/history`),
    ]);

    document.getElementById('detail-order-id').textContent = `#${orderId}`;
    document.getElementById('detail-section').classList.remove('hidden');

    const itemRows = (order.items || []).map(i => `
      <tr>
        <td>${i.product_id}</td>
        <td>${i.quantity}</td>
        <td>$${i.price.toFixed(2)}</td>
        <td>$${(i.price * i.quantity).toFixed(2)}</td>
      </tr>
    `).join('');

    const historyRows = history.map(h => `
      <tr>
        <td>${h.from_status ? badge(h.from_status) : '—'}</td>
        <td>${badge(h.to_status)}</td>
        <td>${fmt(h.changed_at)}</td>
        <td>${h.reason || '—'}</td>
      </tr>
    `).join('');

    document.getElementById('detail-content').innerHTML = `
      <div class="detail-meta">
        User ${order.user_id} &bull; ${badge(order.status)} &bull;
        Total <strong>$${(order.total_price || 0).toFixed(2)}</strong>
        ${order.notes ? `&bull; <em>${order.notes}</em>` : ''}
      </div>
      <div class="detail-grid">
        <div>
          <h3>Items</h3>
          ${itemRows ? `<table class="detail-table">
            <thead><tr><th>Product</th><th>Qty</th><th>Price</th><th>Subtotal</th></tr></thead>
            <tbody>${itemRows}</tbody>
          </table>` : '<p style="color:#999;font-size:13px">No items.</p>'}
        </div>
        <div>
          <h3>History</h3>
          ${historyRows ? `<table class="detail-table">
            <thead><tr><th>From</th><th>To</th><th>When</th><th>Reason</th></tr></thead>
            <tbody>${historyRows}</tbody>
          </table>` : '<p style="color:#999;font-size:13px">No history.</p>'}
        </div>
      </div>
    `;
  } catch (e) {
    toast('Failed to load order detail: ' + e.message);
  }
}

// ---- Create order ----

function addItemRow() {
  const row = document.createElement('div');
  row.className = 'item-row';
  row.innerHTML = `
    <input type="number" placeholder="Product ID" class="item-product" required min="1">
    <input type="number" placeholder="Qty" class="item-qty" required min="1">
    <input type="number" placeholder="Price" class="item-price" required min="0.01" step="0.01">
    <button type="button" class="remove-item" title="Remove">&#x2715;</button>
  `;
  row.querySelector('.remove-item').addEventListener('click', () => {
    if (document.querySelectorAll('.item-row').length > 1) row.remove();
  });
  document.getElementById('items-container').appendChild(row);
}

function openModal() {
  document.getElementById('items-container').innerHTML = '';
  document.getElementById('create-form').reset();
  addItemRow();
  document.getElementById('modal-overlay').classList.remove('hidden');
}

function closeModal() {
  document.getElementById('modal-overlay').classList.add('hidden');
}

async function handleCreate(e) {
  e.preventDefault();
  const form = e.target;
  const items = Array.from(document.querySelectorAll('.item-row')).map(row => ({
    product_id: parseInt(row.querySelector('.item-product').value),
    quantity:   parseInt(row.querySelector('.item-qty').value),
    price:      parseFloat(row.querySelector('.item-price').value),
  }));

  try {
    await apiFetch('/orders', {
      method: 'POST',
      body: JSON.stringify({
        user_id: parseInt(form.user_id.value),
        status:  form.status.value,
        notes:   form.notes.value || null,
        items,
      }),
    });
    closeModal();
    toast('Order created.', false);
    await Promise.all([loadSummary(), loadOrders(currentPage, currentStatus)]);
  } catch (e) {
    toast('Failed to create order: ' + e.message);
  }
}

// ---- Init ----

function init() {
  loadHealth();
  loadSummary();
  loadOrders();

  setInterval(loadHealth, 30000);

  document.getElementById('status-filter').addEventListener('change', e =>
    loadOrders(1, e.target.value)
  );
  document.getElementById('refresh-btn').addEventListener('click', () => {
    loadHealth(); loadSummary(); loadOrders(currentPage, currentStatus);
  });
  document.getElementById('new-order-btn').addEventListener('click', openModal);
  document.getElementById('close-modal').addEventListener('click', closeModal);
  document.getElementById('cancel-btn').addEventListener('click', closeModal);
  document.getElementById('modal-overlay').addEventListener('click', e => {
    if (e.target.id === 'modal-overlay') closeModal();
  });
  document.getElementById('add-item-btn').addEventListener('click', addItemRow);
  document.getElementById('create-form').addEventListener('submit', handleCreate);

  document.getElementById('orders-tbody').addEventListener('click', e => {
    const row = e.target.closest('tr[data-id]');
    if (row) loadDetail(parseInt(row.dataset.id));
  });
  document.getElementById('pagination').addEventListener('click', e => {
    const btn = e.target.closest('button[data-page]');
    if (btn) loadOrders(parseInt(btn.dataset.page), currentStatus);
  });
  document.getElementById('close-detail').addEventListener('click', () => {
    document.getElementById('detail-section').classList.add('hidden');
    selectedOrderId = null;
    document.querySelectorAll('#orders-tbody tr').forEach(r => r.classList.remove('selected'));
  });
}

document.addEventListener('DOMContentLoaded', init);
