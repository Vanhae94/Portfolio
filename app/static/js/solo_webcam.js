async function startSoloWebcam(cctvId) {
    const devices = await navigator.mediaDevices.enumerateDevices();
    const videoDevices = devices.filter(device => device.kind === 'videoinput');
    const index = parseInt(cctvId.replace('CCTV', '')) - 1;

    if (videoDevices[index]) {
        const videoElement = document.getElementById('video');
        try {
            const stream = await navigator.mediaDevices.getUserMedia({
                video: { deviceId: videoDevices[index].deviceId },
            });
            videoElement.srcObject = stream;
        } catch (error) {
            console.error(`웹캠(${cctvId}) 접근 오류:`, error);
        }
    } else {
        console.error(`CCTV ID(${cctvId})에 해당하는 웹캠이 없습니다.`);
    }
}

// 페이지 로드 시 해당 CCTV 스트림 시작
window.onload = () => startSoloWebcam('{{ cctv.cctv_id }}');