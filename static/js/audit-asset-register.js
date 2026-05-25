/** Read-only asset register for Auditor role. */
(function () {
    if (!window.location.pathname.includes('/audit/asset-register')) return;

    const API = '/api/asset-manager/assets';

    function formatMoney(n) {
        const num = Number(n);
        if (!Number.isFinite(num)) return '—';
        return num.toLocaleString('en-ZA', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
    }

    function escapeHtml(value) {
        return String(value ?? '')
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;');
    }

    function statusClass(status) {
        const s = (status || 'active').toLowerCase();
        if (s === 'disposed') return 'status-disposed';
        if (s === 'fully_depreciated') return 'status-muted';
        return 'status-active';
    }

    class AuditAssetRegisterPage {
        constructor() {
            this.summaryEl = document.getElementById('assetRegisterSummary');
            this.listEl = document.getElementById('assetRegisterList');
            this.loadAssets();
        }

        async loadAssets() {
            try {
                const res = await VarydianUtils.safeFetch(API);
                if (!res.success) throw new Error(res.error || 'Failed to load assets');
                this.renderSummary(res.assets || []);
                this.renderList(res.assets || []);
            } catch (err) {
                if (this.listEl) {
                    this.listEl.innerHTML = `<p class="text-danger">${escapeHtml(err.message || 'Load failed')}</p>`;
                }
            }
        }

        renderSummary(assets) {
            if (!this.summaryEl) return;
            let carrying = 0;
            let cost = 0;
            for (const a of assets) {
                carrying += Number(a.carrying_value) || 0;
                cost += Number(a.purchase_cost) || 0;
            }
            this.summaryEl.innerHTML = `
                <div class="stat-card"><div class="stat-number">${assets.length}</div><div class="stat-label">Assets</div></div>
                <div class="stat-card"><div class="stat-number stat-number--currency">R ${formatMoney(cost)}</div><div class="stat-label">Total cost</div></div>
                <div class="stat-card"><div class="stat-number stat-number--currency">R ${formatMoney(carrying)}</div><div class="stat-label">Carrying value</div></div>`;
        }

        renderList(assets) {
            if (!this.listEl) return;
            if (!assets.length) {
                this.listEl.innerHTML = '<p class="text-muted">No assets in the register.</p>';
                return;
            }
            this.listEl.innerHTML = assets.map((a) => {
                const cat = (a.category_details && a.category_details.name) || a.asset_category || '—';
                return `
                <article class="asset-register-card asset-register-card--readonly">
                    <div class="asset-register-card__icon" aria-hidden="true">🏗️</div>
                    <div class="asset-register-card__body">
                        <h3>${escapeHtml(a.asset_name)}</h3>
                        <p class="text-muted">${escapeHtml(cat)} · ${escapeHtml(a.asset_id)}</p>
                        <p>Carrying value: <strong>R ${formatMoney(a.carrying_value)}</strong> · ${a.remaining_useful_life} yrs remaining</p>
                    </div>
                    <div class="asset-register-card__actions">
                        <span class="${statusClass(a.status)}">${escapeHtml(a.status || 'active')}</span>
                    </div>
                </article>`;
            }).join('');
        }
    }

    document.addEventListener('DOMContentLoaded', () => new AuditAssetRegisterPage());
})();
