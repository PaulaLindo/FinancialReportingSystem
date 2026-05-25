/**
 * Asset detail — useful life and impairment journal submission.
 */
(function () {
    const assetId = window.assetDetailId;
    if (!assetId) return;

    const API = `/api/asset-manager/assets/${encodeURIComponent(assetId)}`;

    function bindFormValidation(form) {
        if (!form) return;
        form.addEventListener('invalid', (e) => {
            e.preventDefault();
            const field = e.target;
            if (field && field.validationMessage) {
                VarydianUtils.showToast(field.validationMessage, 'warning');
                field.focus();
            }
        }, true);
    }

    function setSubmitting(form, submitting) {
        const btn = form?.querySelector('button[type="submit"]');
        if (!btn) return;
        btn.disabled = submitting;
        btn.dataset.originalLabel = btn.dataset.originalLabel || btn.textContent;
        btn.textContent = submitting ? 'Submitting…' : btn.dataset.originalLabel;
        btn.classList.toggle('btn--loading', submitting);
    }

    async function postJournal(path, body) {
        const res = await VarydianUtils.safeFetch(`${API}/${path}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(body),
        });
        if (!res.success) throw new Error(res.error || 'Submission failed');
        return res;
    }

    function init() {
        const usefulLifeForm = document.getElementById('usefulLifeJournalForm');
        const impairmentForm = document.getElementById('impairmentJournalForm');
        const disposalForm = document.getElementById('disposalJournalForm');

        bindFormValidation(usefulLifeForm);
        bindFormValidation(impairmentForm);
        bindFormValidation(disposalForm);
        VarydianUtils.bindCurrencyInputs(document);

        usefulLifeForm?.addEventListener('submit', async (e) => {
            e.preventDefault();
            if (!usefulLifeForm.reportValidity()) return;
            const fd = new FormData(usefulLifeForm);
            setSubmitting(usefulLifeForm, true);
            try {
                const res = await postJournal('useful-life-journal', {
                    new_useful_life: parseInt(fd.get('new_useful_life'), 10),
                    effective_date: fd.get('effective_date') || null,
                    reason: fd.get('reason'),
                });
                VarydianUtils.showSuccess(res.message || 'Useful life journal submitted');
                setTimeout(() => window.location.reload(), 800);
            } catch (err) {
                VarydianUtils.showError(err.message);
                setSubmitting(usefulLifeForm, false);
            }
        });

        impairmentForm?.addEventListener('submit', async (e) => {
            e.preventDefault();
            if (!impairmentForm.reportValidity()) return;
            const fd = new FormData(impairmentForm);
            const recoverable = fd.get('recoverable_amount');
            setSubmitting(impairmentForm, true);
            try {
                const res = await postJournal('impairment-journal', {
                    impairment_amount: VarydianUtils.parseMoneyInput(fd.get('impairment_amount')),
                    recoverable_amount: recoverable
                        ? VarydianUtils.parseMoneyInput(recoverable) : null,
                    reason: fd.get('reason'),
                });
                VarydianUtils.showSuccess(res.message || 'Impairment journal submitted');
                setTimeout(() => window.location.reload(), 800);
            } catch (err) {
                VarydianUtils.showError(err.message);
                setSubmitting(impairmentForm, false);
            }
        });

        disposalForm?.addEventListener('submit', async (e) => {
            e.preventDefault();
            if (!disposalForm.reportValidity()) return;
            const fd = new FormData(disposalForm);
            setSubmitting(disposalForm, true);
            try {
                const res = await postJournal('disposal-journal', {
                    disposal_proceeds: VarydianUtils.parseMoneyInput(fd.get('disposal_proceeds') || '0'),
                    disposal_date: fd.get('disposal_date') || null,
                    reason: fd.get('reason'),
                });
                VarydianUtils.showSuccess(res.message || 'Disposal journal submitted');
                setTimeout(() => window.location.reload(), 800);
            } catch (err) {
                VarydianUtils.showError(err.message);
                setSubmitting(disposalForm, false);
            }
        });
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();
