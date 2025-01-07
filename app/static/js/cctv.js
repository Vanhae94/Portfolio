async function startAllWebcams(cctvs) {
    const devices = await navigator.mediaDevices.enumerateDevices();
    const videoDevices = devices.filter(device => device.kind === 'videoinput');

    cctvs.forEach((cctv, index) => {
        const videoElement = document.getElementById(`video-${cctv.cctv_id}`);
        if (videoDevices[index]) {
            try {
                const stream = await navigator.mediaDevices.getUserMedia({
                    video: { deviceId: videoDevices[index].deviceId },
                });
                videoElement.srcObject = stream;
            } catch (error) {
                console.error(`웹캠(${cctv.cctv_id}) 접근 오류:`, error);
            }
        } else {
            console.error(`CCTV ID(${cctv.cctv_id})에 해당하는 웹캠이 없습니다.`);
        }
    });
}
