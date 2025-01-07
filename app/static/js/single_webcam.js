// 단일 웹캠 시작
async function startSingleWebcam() {
  const videoElement = document.getElementById('webcam-video');
  const cameraIndex = parseInt(window.location.pathname.split('/').pop()); // URL에서 인덱스 추출

  try {
    // 모든 미디어 장치 가져오기
    const devices = await navigator.mediaDevices.enumerateDevices();

    // 비디오 입력 장치 필터링
    const videoDevices = devices.filter(device => device.kind === 'videoinput');

    if (cameraIndex >= videoDevices.length || cameraIndex < 0) {
      alert("유효하지 않은 웹캠 번호입니다.");
      return;
    }

    // 선택된 웹캠의 스트림 시작
    const stream = await navigator.mediaDevices.getUserMedia({
      video: { deviceId: videoDevices[cameraIndex].deviceId },
    });
    videoElement.srcObject = stream;
  } catch (error) {
    console.error("웹캠 접근 오류: ", error);
    alert("웹캠을 불러오는 중 문제가 발생했습니다.");
  }
}

// 단일 웹캠 시작
window.onload = startSingleWebcam;
