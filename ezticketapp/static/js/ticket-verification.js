let ticketVerification = {
    stream: null,
    currentStream: null,
    currentOrderId: null,
    currentOrderCode: null,
    qrResult: null,
    faceResult: null,
    qrVerified: false,
    faceVerified: false,
    qrImage: null,
    faceImage: null,
};

function resetVerificationUI() {
    const qrStart = document.getElementById('verification-qr-start');
    const qrCapture = document.getElementById('verification-qr-capture');
    const qrPreview = document.getElementById('verification-qr-preview');
    const qrResult = document.getElementById('verification-qr-result');
    const qrError = document.getElementById('verification-qr-error');
    
    const faceStart = document.getElementById('verification-face-start');
    const faceCapture = document.getElementById('verification-face-capture');
    const facePreview = document.getElementById('verification-face-preview');
    const faceResult = document.getElementById('verification-face-result');
    const faceError = document.getElementById('verification-face-error');
    
    const summary = document.getElementById('verification-summary');
    const finalResult = document.getElementById('verification-final-result');
    const loading = document.getElementById('verification-loading');
    const btnScanQr = document.getElementById('btnScanQr');
    const btnScanFace = document.getElementById('btnScanFace');
    const btnConfirmVerify = document.getElementById('btnConfirmVerify');
    const btnResetVerification = document.getElementById('btnResetVerification');

    if (qrStart) qrStart.style.display = 'block';
    if (qrCapture) qrCapture.style.display = 'none';
    if (qrPreview) qrPreview.style.display = 'none';
    if (qrResult) qrResult.style.display = 'none';
    if (qrError) qrError.style.display = 'none';
    
    if (faceStart) faceStart.style.display = 'none';
    if (faceCapture) faceCapture.style.display = 'none';
    if (facePreview) facePreview.style.display = 'none';
    if (faceResult) faceResult.style.display = 'none';
    if (faceError) faceError.style.display = 'none';
    
    if (summary) summary.style.display = 'none';
    if (finalResult) finalResult.style.display = 'none';
    if (loading) loading.style.display = 'none';
    if (btnScanQr) btnScanQr.disabled = false;
    if (btnScanFace) btnScanFace.disabled = true;
    if (btnConfirmVerify) btnConfirmVerify.disabled = true;
    if (btnResetVerification) btnResetVerification.style.display = 'none';

    const qrSummaryContent = document.getElementById('verification-summary-content');
    const qrResultContent = document.getElementById('verification-qr-result-content');
    const qrErrorContent = document.getElementById('verification-qr-error-content');
    const faceResultContent = document.getElementById('verification-face-result-content');
    const faceErrorContent = document.getElementById('verification-face-error-content');
    const finalResultContent = document.getElementById('verification-final-result-content');

    if (qrSummaryContent) qrSummaryContent.innerHTML = '';
    if (qrResultContent) qrResultContent.innerHTML = 'Chưa có kết quả';
    if (qrErrorContent) qrErrorContent.innerHTML = 'Chưa có kết quả';
    if (faceResultContent) faceResultContent.innerHTML = 'Chưa có kết quả';
    if (faceErrorContent) faceErrorContent.innerHTML = 'Chưa có kết quả';
    if (finalResultContent) finalResultContent.innerHTML = '';

    ticketVerification.currentOrderId = null;
    ticketVerification.currentOrderCode = null;
    ticketVerification.qrResult = null;
    ticketVerification.faceResult = null;
    ticketVerification.qrVerified = false;
    ticketVerification.faceVerified = false;
    ticketVerification.qrImage = null;
    ticketVerification.faceImage = null;
}

function restartVerificationFlow() {
    stopVerificationStream();
    resetVerificationUI();
    setTimeout(function () {
        openQrCamera();
    }, 50);
}

function triggerFreshScan() {
    window.location.reload();
}

function showSingleResetButton() {
    const btnResetVerification = document.getElementById('btnResetVerification');
    const btnScanQrNew = document.getElementById('btnScanQrNew');
    const btnScanFaceNew = document.getElementById('btnScanFaceNew');

    if (btnResetVerification) btnResetVerification.style.display = 'inline-block';
    if (btnScanQrNew) btnScanQrNew.style.display = 'none';
    if (btnScanFaceNew) btnScanFaceNew.style.display = 'none';
}

function stopVerificationStream() {
    if (ticketVerification.currentStream) {
        ticketVerification.currentStream.getTracks().forEach(track => track.stop());
        ticketVerification.currentStream = null;
    }
}

function openQrCamera() {
    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
        showAlert('error', 'Trình duyệt của bạn không hỗ trợ camera.');
        return;
    }

    if (window.location.protocol !== 'https:' && window.location.hostname !== 'localhost' && window.location.hostname !== '127.0.0.1') {
        showAlert('error', 'Camera chỉ hoạt động trên HTTPS hoặc localhost.');
        return;
    }

    stopVerificationStream();
    
    navigator.mediaDevices.getUserMedia({ video: { facingMode: 'environment' } })
        .then(function (stream) {
            ticketVerification.currentStream = stream;
            const video = document.getElementById('verification-qr-video');
            if (!video) {
                return;
            }

            document.getElementById('verification-qr-start').style.display = 'none';
            document.getElementById('verification-qr-capture').style.display = 'block';
            document.getElementById('verification-qr-error').style.display = 'none';
            document.getElementById('verification-qr-result').style.display = 'none';

            video.srcObject = stream;
            video.setAttribute('playsinline', 'true');
            video.setAttribute('muted', 'true');
            video.style.display = 'block';

            video.onloadedmetadata = function () {
                video.play().catch(function (err) {
                    console.log('Error playing video:', err);
                });
            };
        })
        .catch(function (err) {
            showAlert('error', 'Không thể mở camera: ' + err.message);
        });
}

function captureQrImage() {
    const video = document.getElementById('verification-qr-video');
    const canvas = document.getElementById('verification-qr-canvas');
    
    if (!video || !video.readyState === video.HAVE_ENOUGH_DATA) {
        showAlert('error', 'Camera chưa sẵn sàng. Vui lòng thử lại.');
        return;
    }

    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    const ctx = canvas.getContext('2d');
    ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
    const dataUrl = canvas.toDataURL('image/jpeg');
    const base64 = dataUrl.split(',')[1];

    ticketVerification.qrImage = dataUrl;

    document.getElementById('verification-loading').style.display = 'block';

    fetch('/organizer/verify-ticket/qr', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ image: base64 })
    })
    .then(res => res.json())
    .then(function (data) {
        stopVerificationStream();
        
        if (data.success) {
            ticketVerification.currentOrderId = data.order_id;
            ticketVerification.currentOrderCode = data.authentication_code;
            ticketVerification.qrResult = data;
            ticketVerification.qrVerified = true;

            // Show captured image and scan new button
            document.getElementById('verification-qr-start').style.display = 'none';
            document.getElementById('verification-qr-capture').style.display = 'none';
            document.getElementById('verification-qr-preview').style.display = 'block';
            document.getElementById('qr-preview-image').src = ticketVerification.qrImage;
            
            // Show result
            document.getElementById('verification-qr-error').style.display = 'none';
            document.getElementById('verification-qr-result').style.display = 'block';
            document.getElementById('verification-qr-result-content').innerHTML = 
                '<div class="verification-status success">✓ ' + data.message + '</div>';

            // Show summary
            document.getElementById('verification-summary').style.display = 'block';
            document.getElementById('verification-summary-content').innerHTML = data.summary;

            // Enable face verification
            document.getElementById('verification-face-start').style.display = 'block';
            document.getElementById('btnScanFace').disabled = false;

            updateConfirmButton();
        } else {
            document.getElementById('verification-qr-error').style.display = 'block';
            document.getElementById('verification-qr-error-content').innerHTML = 
                '<div class="verification-status error">✗ ' + data.message + '</div>';
            document.getElementById('verification-qr-result').style.display = 'none';
            setTimeout(function () { openQrCamera(); }, 1500);
        }
    })
    .catch(function (err) {
        stopVerificationStream();
        document.getElementById('verification-qr-error').style.display = 'block';
        document.getElementById('verification-qr-error-content').innerHTML = 
            '<div class="verification-status error">✗ Đã xảy ra lỗi: ' + err.message + '</div>';
        document.getElementById('verification-qr-result').style.display = 'none';
        setTimeout(function () { openQrCamera(); }, 1500);
    })
    .finally(function () {
        document.getElementById('verification-loading').style.display = 'none';
    });
}

function resetQrScan() {
    triggerFreshScan();
}

function openFaceCamera() {
    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
        showAlert('error', 'Trình duyệt của bạn không hỗ trợ camera.');
        return;
    }

    stopVerificationStream();

    navigator.mediaDevices.getUserMedia({ video: { facingMode: 'user' } })
        .then(function (stream) {
            ticketVerification.currentStream = stream;
            const video = document.getElementById('verification-face-video');
            if (!video) {
                return;
            }

            document.getElementById('verification-face-start').style.display = 'none';
            document.getElementById('verification-face-capture').style.display = 'block';
            document.getElementById('verification-face-error').style.display = 'none';
            document.getElementById('verification-face-result').style.display = 'none';

            video.srcObject = stream;
            video.setAttribute('playsinline', 'true');
            video.setAttribute('muted', 'true');
            video.style.display = 'block';

            video.onloadedmetadata = function () {
                video.play().catch(function (err) {
                    console.log('Error playing video:', err);
                });
            };
        })
        .catch(function (err) {
            showAlert('error', 'Không thể mở camera: ' + err.message);
        });
}

function captureFaceImage() {
    const video = document.getElementById('verification-face-video');
    const canvas = document.getElementById('verification-face-canvas');
    
    if (!video || !video.readyState === video.HAVE_ENOUGH_DATA) {
        showAlert('error', 'Camera chưa sẵn sàng. Vui lòng thử lại.');
        return;
    }

    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    const ctx = canvas.getContext('2d');
    ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
    const dataUrl = canvas.toDataURL('image/jpeg');
    const base64 = dataUrl.split(',')[1];

    ticketVerification.faceImage = dataUrl;

    document.getElementById('verification-loading').style.display = 'block';

    fetch('/organizer/verify-ticket/face', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ image: base64, order_id: ticketVerification.currentOrderId })
    })
    .then(res => res.json())
    .then(function (data) {
        stopVerificationStream();
        
        if (data.success) {
            ticketVerification.faceResult = data;
            ticketVerification.faceVerified = true;

            // Show captured image and retake button
            document.getElementById('verification-face-start').style.display = 'none';
            document.getElementById('verification-face-capture').style.display = 'none';
            document.getElementById('verification-face-preview').style.display = 'block';
            document.getElementById('face-preview-image').src = ticketVerification.faceImage;
            
            // Show success result
            document.getElementById('verification-face-error').style.display = 'none';
            document.getElementById('verification-face-result').style.display = 'block';
            document.getElementById('verification-face-result-content').innerHTML = 
                '<div class="verification-status success">✓ ' + data.message + '</div>';

            updateConfirmButton();
        } else {
            document.getElementById('verification-face-error').style.display = 'block';
            document.getElementById('verification-face-error-content').innerHTML = 
                '<div class="verification-status error">✗ ' + data.message + '</div>';
            document.getElementById('verification-face-result').style.display = 'none';
            setTimeout(function () { openFaceCamera(); }, 1500);
        }
    })
    .catch(function (err) {
        stopVerificationStream();
        document.getElementById('verification-face-error').style.display = 'block';
        document.getElementById('verification-face-error-content').innerHTML = 
            '<div class="verification-status error">✗ Đã xảy ra lỗi: ' + err.message + '</div>';
        document.getElementById('verification-face-result').style.display = 'none';
        setTimeout(function () { openFaceCamera(); }, 1500);
    })
    .finally(function () {
        document.getElementById('verification-loading').style.display = 'none';
    });
}

function resetFaceScan() {
    triggerFreshScan();
}

function updateConfirmButton() {
    const btnConfirmVerify = document.getElementById('btnConfirmVerify');
    
    // Only enable if BOTH QR and face are verified
    if (ticketVerification.qrVerified && ticketVerification.faceVerified) {
        if (btnConfirmVerify) btnConfirmVerify.disabled = false;
    } else {
        if (btnConfirmVerify) btnConfirmVerify.disabled = true;
    }
}

function showAlert(type, message) {
    const alertDiv = document.createElement('div');
    alertDiv.className = `alert alert-${type === 'error' ? 'danger' : type === 'success' ? 'success' : 'info'}`;
    alertDiv.textContent = message;
    alertDiv.style.marginBottom = '20px';
    
    const container = document.querySelector('.card-body');
    if (container && container.firstChild) {
        container.insertBefore(alertDiv, container.firstChild);
    }
    
    // Auto-remove after 5 seconds
    setTimeout(() => {
        alertDiv.remove();
    }, 5000);
}

function confirmVerification() {
    if (!ticketVerification.qrVerified || !ticketVerification.faceVerified) {
        showAlert('error', 'Bạn phải hoàn thành cả hai bước xác thực mới có thể xác nhận.');
        return;
    }

    document.getElementById('verification-loading').style.display = 'block';

    fetch('/organizer/verify-ticket/confirm', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ order_id: ticketVerification.currentOrderId })
    })
    .then(res => res.json())
    .then(function (data) {
        if (data.success) {
            document.getElementById('verification-final-result').style.display = 'block';
            document.getElementById('verification-final-result-content').innerHTML = 
                '<div class="verification-status success"><strong>✓ Xác thực thành công!</strong><br>' + data.message + '</div>';
            
            document.getElementById('btnConfirmVerify').disabled = true;
            document.getElementById('btnResetVerification').style.display = 'inline-block';
        } else {
            showAlert('error', data.message || 'Không thể xác nhận vé.');
        }
    })
    .catch(function (err) {
        showAlert('error', 'Đã xảy ra lỗi: ' + err.message);
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
    const btnScanQrNew = document.getElementById('btnScanQrNew');
    
    const btnScanFace = document.getElementById('btnScanFace');
    const btnCaptureFace = document.getElementById('btnCaptureFace');
    const btnScanFaceNew = document.getElementById('btnScanFaceNew');
    
    const btnConfirmVerify = document.getElementById('btnConfirmVerify');

    if (btnResetVerification) {
        btnResetVerification.addEventListener('click', function () {
            triggerFreshScan();
        });
    }
    
    if (btnScanQr) btnScanQr.addEventListener('click', openQrCamera);
    if (btnCaptureQr) btnCaptureQr.addEventListener('click', captureQrImage);
    if (btnScanQrNew) btnScanQrNew.addEventListener('click', resetQrScan);
    
    if (btnScanFace) btnScanFace.addEventListener('click', openFaceCamera);
    if (btnCaptureFace) btnCaptureFace.addEventListener('click', captureFaceImage);
    if (btnScanFaceNew) btnScanFaceNew.addEventListener('click', resetFaceScan);
    
    if (btnConfirmVerify) btnConfirmVerify.addEventListener('click', confirmVerification);
});
