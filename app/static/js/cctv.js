function showCCTV(cctvId) {
  const webcamFeeds = document.querySelectorAll(".webcam-feed");
  webcamFeeds.forEach((feed) => (feed.style.display = "none"));
  const selectedFeed = document.getElementById(`webcam-${cctvId}`);
  if (selectedFeed) selectedFeed.style.display = "block";
}

// 페이지 로드 시 첫 번째 CCTV 화면 표시
window.onload = () => {
  if (typeof cctvsData !== "undefined" && cctvsData.length > 0) {
    showCCTV(cctvsData[0].cctv_id);
  } else {
    console.error("No CCTV data available.");
  }
};
