/**
 * Asset Manager — register list and new asset registration.
 */
(function () {
    const API = '/api/asset-manager';

    function escapeHtml(text) {
        if (window.TransactionCardUI && TransactionCardUI.escapeHtml) {
            return TransactionCardUI.escapeHtml(text);
        }
        const div = document.createElement('div');
        div.textContent = text == null ? '' : String(text);
        return div.innerHTML;
    }

    function formatMoney(n) {
        const v = Number(n) || 0;
        return `R ${v.toLocaleString('en-ZA', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
    }

    function statusClass(status) {
        return `asset-status asset-status--${String(status || 'active').replace(/\s+/g, '_')}`;
    }

    class AssetRegisterPage {
        constructor() {
            if (!window.location.pathname.includes('/asset-manager/register')) return;
            this.listEl = document.getElementById('assetRegisterList');
            this.summaryEl = document.getElementById('assetRegisterSummary');
            this.modal = document.getElementById('registerAssetModal');
            this.form = document.getElementById('registerAssetForm');
            this.init();
        }

        init() {
            document.getElementById('btnOpenRegisterAsset')?.addEventListener('click', () => this.openModal());
            this.modal?.querySelectorAll('[data-action="close-register-asset"]').forEach((el) => {
                el.addEventListener('click', () => this.closeModal());
            });
            this.form?.addEventListener('invalid', (e) => {
                e.preventDefault();
                const field = e.target;
                if (field?.validationMessage) {
                    VarydianUtils.showToast(field.validationMessage, 'warning');
                    field.focus();
                }
            }, true);
            this.form?.addEventListener('submit', (e) => {
                e.preventDefault();
                if (!this.form.reportValidity()) return;
                this.submitAsset();
            });
            this.modal?.querySelector('.submission-details-overlay')?.addEventListener('click', () => this.closeModal());
            document.getElementById('btnRunDepreciation')?.addEventListener('click', () => this.runDepreciation());
            VarydianUtils.bindCurrencyInputs(this.form);
            this.loadAssets();
        }

        async runDepreciation() {
            const year = new Date().getFullYear();
            const message = `Run annual depreciation for fiscal year ${year}? This updates carrying values for all active assets.`;
            const ok = typeof window.showConfirm === 'function'
                ? await window.showConfirm('Annual depreciation', message, {
                    confirmText: 'Run',
                    cancelText: 'Cancel',
                })
                : window.confirm(message);
            if (!ok) return;
            try {
                const res = await VarydianUtils.safeFetch(`${API}/depreciation/run`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ fiscal_year: year }),
                });
                if (!res.success) throw new Error(res.error || 'Depreciation run failed');
                VarydianUtils.showSuccess(res.message || 'Depreciation applied');
                this.loadAssets();
            } catch (err) {
                VarydianUtils.showError(err.message);
            }
        }

        openModal() {
            if (this.modal) VarydianUtils.showElement(this.modal, 'flex');
            this.form?.querySelectorAll('[data-currency-input]').forEach((el) => {
                el.dispatchEvent(new Event('blur'));
            });
        }

        closeModal() {
            if (this.modal) VarydianUtils.hideElement(this.modal);
            this.form?.reset();
        }

        async loadAssets() {
            try {
                const res = await VarydianUtils.safeFetch(`${API}/assets`);
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
                <div class="stat-card"><div class="stat-number stat-number--currency">${formatMoney(cost)}</div><div class="stat-label">Total cost</div></div>
                <div class="stat-card"><div class="stat-number stat-number--currency">${formatMoney(carrying)}</div><div class="stat-label">Carrying value</div></div>`;
        }

        renderList(assets) {
            if (!this.listEl) return;
            if (!assets.length) {
                this.listEl.innerHTML = '<p class="text-muted">No assets registered. Use <strong>Register asset</strong> to add the first item.</p>';
                return;
            }
            this.listEl.innerHTML = assets.map((a) => {
                const cat = (a.category_details && a.category_details.name) || a.asset_category || '—';
                return `
                <article class="asset-register-card">
                    <div class="asset-register-card__icon" aria-hidden="true">🏗️</div>
                    <div class="asset-register-card__body">
                        <h3><a href="/asset-manager/assets/${encodeURIComponent(a.asset_id)}">${escapeHtml(a.asset_name)}</a></h3>
                        <p class="text-muted">${escapeHtml(cat)} · ${escapeHtml(a.asset_id)}</p>
                        <p>Carrying value: <strong>${formatMoney(a.carrying_value)}</strong> · ${a.remaining_useful_life} yrs remaining</p>
                    </div>
                    <div class="asset-register-card__actions">
                        <span class="${statusClass(a.status)}">${escapeHtml(a.status || 'active')}</span>
                        <a href="/asset-manager/assets/${encodeURIComponent(a.asset_id)}" class="btn btn-sm btn-primary">Lifecycle</a>
                    </div>
                </article>`;
            }).join('');
        }

        async submitAsset() {
            if (!this.form) return;
            const submitBtn = this.form.querySelector('button[type="submit"]');
            const originalLabel = submitBtn?.textContent;
            if (submitBtn) {
                submitBtn.disabled = true;
                submitBtn.textContent = 'Saving…';
            }
            const fd = new FormData(this.form);
            const payload = Object.fromEntries(fd.entries());
            payload.purchase_cost = VarydianUtils.parseMoneyInput(payload.purchase_cost);
            payload.residual_value = VarydianUtils.parseMoneyInput(payload.residual_value || '0');
            if (!Number.isFinite(payload.purchase_cost)) {
                VarydianUtils.showError('Enter a valid purchase cost.');
                return;
            }
            if (!Number.isFinite(payload.residual_value)) {
                payload.residual_value = 0;
            }
            payload.useful_life_years = parseInt(payload.useful_life_years, 10);
            try {
                const res = await VarydianUtils.safeFetch(`${API}/assets`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(payload),
                });
                if (!res.success) throw new Error(res.error || 'Registration failed');
                VarydianUtils.showSuccess(res.message || 'Asset registered');
                this.closeModal();
                this.loadAssets();
            } catch (err) {
                VarydianUtils.showError(err.message || 'Could not register asset');
            } finally {
                if (submitBtn) {
                    submitBtn.disabled = false;
                    submitBtn.textContent = originalLabel || 'Save to register';
                }
            }
        }
    }

    document.addEventListener('DOMContentLoaded', () => new AssetRegisterPage());
})();
