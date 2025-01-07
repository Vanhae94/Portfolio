function startObjectDetection(cctvId) {
    const videoElement = document.getElementById(`video-${cctvId}`);
    videoElement.src = `/detect-people/${cctvId}`;
}