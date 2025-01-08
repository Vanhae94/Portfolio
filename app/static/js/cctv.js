function showCCTV(cctvId) {
  // CCTV 화면 전환
  const webcamFeeds = document.querySelectorAll(".webcam-feed");
  webcamFeeds.forEach((feed) => (feed.style.display = "none"));
  const selectedFeed = document.getElementById(`webcam-${cctvId}`);
  if (selectedFeed) selectedFeed.style.display = "block";

  // AJAX 요청으로 last_access 업데이트
  fetch(`/update-last-access/${cctvId}`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      timestamp: new Date().toISOString(),
    }),
  })
    .then((response) => {
      if (!response.ok) {
        console.error(`Failed to update last_access for CCTV ${cctvId}`);
      }
    })
    .catch((error) => console.error("Error:", error));
}

// 페이지 로드 시 첫 번째 CCTV 화면 표시
window.onload = () => {
  if (typeof cctvsData !== "undefined" && cctvsData.length > 0) {
    showCCTV(cctvsData[0].cctv_id);
  } else {
    console.error("No CCTV data available.");
  }
};

// 캡쳐 CCTV
async function captureCCTV(cctvId) {
  try {
    const response = await fetch(`/capture/${cctvId}`, {
      method: "POST",
    });

    if (response.ok) {
      const result = await response.json();
      alert(`캡쳐 성공: 파일명 ${result.file_path}`);
    } else {
      alert("캡쳐 실패!");
    }
  } catch (error) {
    console.error("캡쳐 요청 중 오류 발생:", error);
    alert("캡쳐 요청 중 문제가 발생했습니다.");
  }
}
