let ticketVerification = {
    stream: null,
    step: 'qr',
    currentOrderId: null,
    currentOrderCode: null,
    qrResult: null,
    faceResult: null,
};

function resetVerificationUI() {
    const qrStep = document.getElementById('verification-step-qr');
    const faceStep = document.getElementById('verification-step-face');
    const summary = document.getElementById('verification-summary');
    const result = document.getElementById('verification-result');
    const loading = document.getElementById('verification-loading');
    const btnScanQr = document.getElementById('btnScanQr');
    const btnScanFace = document.getElementById('btnScanFace');
    const btnConfirmVerify = document.getElementById('btnConfirmVerify');
    const btnResetVerification = document.getElementById('btnResetVerification');

    if (qrStep) qrStep.style.display = 'block';
    if (faceStep) faceStep.style.display = 'none';
    if (summary) summary.style.display = 'none';
    if (result) result.innerHTML = '';
    if (loading) loading.style.display = 'none';
    if (btnScanQr) btnScanQr.disabled = false;
    if (btnScanFace) btnScanFace.disabled = true;
    if (btnConfirmVerify) btnConfirmVerify.disabled = true;
    if (btnResetVerification) btnResetVerification.style.display = 'none';

    ticketVerification.step = 'qr';
    ticketVerification.currentOrderId = null;
    ticketVerification.currentOrderCode = null;
    ticketVerification.qrResult = null;
    ticketVerification.faceResult = null;
}

function stopVerificationStream() {
    if (ticketVerification.stream) {
        ticketVerification.stream.getTracks().forEach(track => track.stop());
        ticketVerification.stream = null;
    }
}

function openQrCamera() {
    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
        alert('Trình duyệt của bạn không hỗ trợ camera.');
        return;
    }

    if (window.location.protocol !== 'https:' && window.location.hostname !== 'localhost' && window.location.hostname !== '127.0.0.1') {
        alert('Camera chỉ hoạt động trên HTTPS hoặc localhost.');
        return;
    }

    navigator.mediaDevices.getUserMedia({ video: { facingMode: 'environment' } })
        .then(function (stream) {
            ticketVerification.stream = stream;
            const video = document.getElementById('verification-qr-video');
            if (!video) {
                return;
            }

            video.srcObject = stream;
            video.setAttribute('playsinline', 'true');
            video.setAttribute('muted', 'true');
            video.style.display = 'block';
            document.getElementById('verification-qr-capture').style.display = 'block';

            video.onloadedmetadata = function () {
                video.play().catch(function () {
                    document.getElementById('verification-result').innerHTML = '<div class="alert alert-warning">Camera đã sẵn sàng nhưng cần tương tác thêm để bắt đầu xem trực tiếp.</div>';
                });
            };
        })
        .catch(function (err) {
            alert('Không thể mở camera: ' + err.message);
        });
}

function captureQrImage() {
    const video = document.getElementById('verification-qr-video');
    const canvas = document.getElementById('verification-qr-canvas');
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    const ctx = canvas.getContext('2d');
    ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
    const dataUrl = canvas.toDataURL('image/jpeg');
    const base64 = dataUrl.split(',')[1];

    document.getElementById('verification-loading').style.display = 'block';
    document.getElementById('verification-result').innerHTML = '<div class="alert alert-info">Đang quét mã QR...</div>';

    fetch('/organizer/verify-ticket/qr', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ image: base64 })
    })
    .then(res => res.json())
    .then(function (data) {
        if (data.success) {
            ticketVerification.currentOrderId = data.order_id;
            ticketVerification.currentOrderCode = data.authentication_code;
            ticketVerification.qrResult = data;
            document.getElementById('verification-result').innerHTML = '<div class="alert alert-success">' + data.message + '</div>';
            document.getElementById('verification-summary').style.display = 'block';
            document.getElementById('verification-summary-content').innerHTML = data.summary;
            document.getElementById('verification-step-face').style.display = 'block';
            document.getElementById('btnScanFace').disabled = false;
            document.getElementById('btnConfirmVerify').disabled = false;
        } else {
            document.getElementById('verification-result').innerHTML = '<div class="alert alert-danger">' + data.message + '</div>';
        }
    })
    .catch(function (err) {
        document.getElementById('verification-result').innerHTML = '<div class="alert alert-danger">Đã xảy ra lỗi: ' + err.message + '</div>';
    })
    .finally(function () {
        document.getElementById('verification-loading').style.display = 'none';
        stopVerificationStream();
    });
}

function openFaceCamera() {
    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
        alert('Trình duyệt của bạn không hỗ trợ camera.');
        return;
    }

    navigator.mediaDevices.getUserMedia({ video: { facingMode: 'user' } })
        .then(function (stream) {
            ticketVerification.stream = stream;
            const video = document.getElementById('verification-face-video');
            if (!video) {
                return;
            }

            video.srcObject = stream;
            video.setAttribute('playsinline', 'true');
            video.setAttribute('muted', 'true');
            video.style.display = 'block';
            document.getElementById('verification-face-capture').style.display = 'block';

            video.onloadedmetadata = function () {
                video.play().catch(function () {
                    document.getElementById('verification-result').innerHTML = '<div class="alert alert-warning">Camera khuôn mặt đã sẵn sàng nhưng cần tương tác thêm để bắt đầu xem trực tiếp.</div>';
                });
            };
        })
        .catch(function (err) {
            alert('Không thể mở camera: ' + err.message);
        });
}

function captureFaceImage() {
    const video = document.getElementById('verification-face-video');
    const canvas = document.getElementById('verification-face-canvas');
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    const ctx = canvas.getContext('2d');
    ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
    const dataUrl = canvas.toDataURL('image/jpeg');
    const base64 = dataUrl.split(',')[1];

    document.getElementById('verification-loading').style.display = 'block';
    document.getElementById('verification-result').innerHTML = '<div class="alert alert-info">Đang xác thực khuôn mặt...</div>';

    fetch('/organizer/verify-ticket/face', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ image: base64, order_id: ticketVerification.currentOrderId })
    })
    .then(res => res.json())
    .then(function (data) {
        if (data.success) {
            ticketVerification.faceResult = data;
            document.getElementById('verification-result').innerHTML = '<div class="alert alert-success">' + data.message + '</div>';
            document.getElementById('btnConfirmVerify').disabled = false;
        } else {
            document.getElementById('verification-result').innerHTML = '<div class="alert alert-danger">' + data.message + '</div>';
        }
    })
    .catch(function (err) {
        document.getElementById('verification-result').innerHTML = '<div class="alert alert-danger">Đã xảy ra lỗi: ' + err.message + '</div>';
    })
    .finally(function () {
        document.getElementById('verification-loading').style.display = 'none';
        stopVerificationStream();
    });
}

function confirmVerification() {
    document.getElementById('verification-loading').style.display = 'block';
    document.getElementById('verification-result').innerHTML = '<div class="alert alert-info">Đang cập nhật trạng thái vé...</div>';

    fetch('/organizer/verify-ticket/confirm', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ order_id: ticketVerification.currentOrderId })
    })
    .then(res => res.json())
    .then(function (data) {
        if (data.success) {
            document.getElementById('verification-result').innerHTML = '<div class="alert alert-success">' + data.message + '</div>';
            document.getElementById('btnConfirmVerify').disabled = true;
            document.getElementById('btnResetVerification').style.display = 'inline-block';
        } else {
            document.getElementById('verification-result').innerHTML = '<div class="alert alert-danger">' + data.message + '</div>';
        }
    })
    .catch(function (err) {
        document.getElementById('verification-result').innerHTML = '<div class="alert alert-danger">Đã xảy ra lỗi: ' + err.message + '</div>';
    })
    .finally(function () {
        document.getElementById('verification-loading').style.display = 'none';
    });
}

document.addEventListener('DOMContentLoaded', function () {
    resetVerificationUI();

    const btnResetVerification = document.getElementById('btnResetVerification');
    const btnScanQr = document.getElementById('btnScanQr');
    const btnCaptureQr = document.getElementById('btnCaptureQr');
    const btnScanFace = document.getElementById('btnScanFace');
    const btnCaptureFace = document.getElementById('btnCaptureFace');
    const btnConfirmVerify = document.getElementById('btnConfirmVerify');

    if (btnResetVerification) btnResetVerification.addEventListener('click', function () {
        stopVerificationStream();
        resetVerificationUI();
    });
    if (btnScanQr) btnScanQr.addEventListener('click', openQrCamera);
    if (btnCaptureQr) btnCaptureQr.addEventListener('click', captureQrImage);
    if (btnScanFace) btnScanFace.addEventListener('click', openFaceCamera);
    if (btnCaptureFace) btnCaptureFace.addEventListener('click', captureFaceImage);
    if (btnConfirmVerify) btnConfirmVerify.addEventListener('click', confirmVerification);
});
