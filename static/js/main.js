/* IntraCore Portal — 메인 스크립트 */

document.addEventListener('DOMContentLoaded', function () {
    const modal = document.getElementById('flag-modal');
    const toggle = document.getElementById('flag-toggle');
    const closeBtn = document.getElementById('flag-close');
    const overlay = modal ? modal.querySelector('.modal-overlay') : null;
    const submitBtn = document.getElementById('flag-submit');
    const challengeSelect = document.getElementById('flag-challenge');
    const flagInput = document.getElementById('flag-input');
    const flagResult = document.getElementById('flag-result');

    if (!modal || !toggle) return;

    // 문제 목록 로드
    function loadChallenges() {
        fetch('/challenges-list')
            .then(function (r) { return r.json(); })
            .then(function (data) {
                challengeSelect.innerHTML = '';
                data.forEach(function (c) {
                    var opt = document.createElement('option');
                    opt.value = c.slug;
                    opt.textContent = c.title;
                    challengeSelect.appendChild(opt);
                });
            });
    }

    // 모달 열기/닫기
    toggle.addEventListener('click', function () {
        modal.style.display = 'flex';
        loadChallenges();
        flagInput.value = '';
        flagResult.className = 'flag-result';
        flagResult.textContent = '';
    });

    function closeModal() { modal.style.display = 'none'; }
    closeBtn.addEventListener('click', closeModal);
    overlay.addEventListener('click', closeModal);

    // 플래그 제출
    submitBtn.addEventListener('click', function () {
        var slug = challengeSelect.value;
        var flag = flagInput.value.trim();
        if (!flag) return;

        var body = new FormData();
        body.append('challenge_slug', slug);
        body.append('flag', flag);

        fetch('/submit-flag', { method: 'POST', body: body })
            .then(function (r) { return r.json(); })
            .then(function (data) {
                flagResult.textContent = data.message;
                flagResult.className = 'flag-result ' + (data.success ? 'success' : 'error');
                if (data.success) {
                    flagInput.value = '';
                }
            })
            .catch(function () {
                flagResult.textContent = '서버 오류가 발생했습니다.';
                flagResult.className = 'flag-result error';
            });
    });

    // Enter 키로 제출
    flagInput.addEventListener('keydown', function (e) {
        if (e.key === 'Enter') submitBtn.click();
    });
});
