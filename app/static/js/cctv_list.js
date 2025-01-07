async function checkWebcamStatus(cctvIds) {
    const devices = await navigator.mediaDevices.enumerateDevices();
    const videoDevices = devices.filter(device => device.kind === 'videoinput');
    
    cctvIds.forEach((cctvId, index) => {
        const statusElement = document.getElementById(`status-${cctvId}`);
        if (videoDevices[index]) {
            statusElement.textContent = "ON";
            statusElement.classList.add("online");
        } else {
            statusElement.textContent = "OFF";
            statusElement.classList.add("offline");
        }
    });
}

// CCTV 목록을 확인하여 상태 업데이트
window.onload = () => {
    const cctvIds = Array.from(document.querySelectorAll('[data-cctv-id]'))
        .map(element => element.dataset.cctvId);
    checkWebcamStatus(cctvIds);
};
