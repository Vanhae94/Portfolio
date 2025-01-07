document.getElementById("object-detection-btn").addEventListener("click", () => {
    fetch('/start-detection', { method: 'POST' })
        .then(response => {
            if (response.ok) {
                alert("객체 탐지가 시작되었습니다.");
            } else {
                alert("객체 탐지 중 오류가 발생했습니다.");
            }
        })
        .catch(err => console.error("요청 중 오류 발생:", err));
});

function getAllCCTVIds() {
    const cctvElements = document.querySelectorAll('[id^="webcam-"]');
    return Array.from(cctvElements).map(el => el.id.replace('webcam-', ''));
}

function updateCanvasWithYoloResults(results) {
    results.forEach(result => {
        const canvas = document.getElementById(`canvas-${result.cctv_id}`);
        const ctx = canvas.getContext('2d');
        ctx.clearRect(0, 0, canvas.width, canvas.height);

        result.detections.forEach(detection => {
            ctx.strokeStyle = 'red';
            ctx.lineWidth = 2;
            ctx.strokeRect(detection.x1, detection.y1, detection.x2 - detection.x1, detection.y2 - detection.y1);
            ctx.fillText(`ID: ${detection.class_id}`, detection.x1, detection.y1 - 5);
        });
    });
}