  function showCCTV(cctvId) {
      const webcamFeeds = document.querySelectorAll('.webcam-feed');
      webcamFeeds.forEach(feed => feed.style.display = 'none');
      const selectedFeed = document.getElementById(`webcam-${cctvId}`);
      if (selectedFeed) selectedFeed.style.display = 'block';
  }

  // 페이지 로드 시 첫 번째 CCTV 화면 표시
  window.onload = () => {
      const cctvsData = {{ cctvs|tojson }};
      showCCTV(cctvsData[0].cctv_id);
  };