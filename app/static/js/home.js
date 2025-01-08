const MAX_CAMERAS = 21;

async function setupWebcams() {
  const devices = await navigator.mediaDevices.enumerateDevices();
  const videoDevices = devices.filter((device) => device.kind === "videoinput");

  const gridContainer = document.getElementById("grid-container");
  gridContainer.innerHTML = ""; // 초기화

  for (let i = 0; i < MAX_CAMERAS; i++) {
    const camDiv = document.createElement("div");
    camDiv.classList.add("webcam-grid-item");
    camDiv.setAttribute("data-index", i);
    camDiv.setAttribute("data-cctv-id", `CCTV${i + 1}`); // CCTV ID 설정

    const videoElement = document.createElement("video");
    videoElement.setAttribute("autoplay", true);
    videoElement.setAttribute("playsinline", true);
    videoElement.setAttribute("id", `video-${i}`);
    videoElement.classList.add("webcam-video");

    if (videoDevices[i]) {
      // 활성화된 웹캠 스트림 설정
      navigator.mediaDevices
        .getUserMedia({ video: { deviceId: videoDevices[i].deviceId } })
        .then((stream) => {
          videoElement.srcObject = stream;
        })
        .catch((error) => {
          console.error(`웹캠 ${i + 1} 오류:`, error);
        });
    } else {
      // 웹캠이 없는 경우 빈 화면 (검은색)
      videoElement.style.backgroundColor = "black";
    }

    camDiv.appendChild(videoElement);
    gridContainer.appendChild(camDiv);

    // 클릭 및 더블클릭 이벤트 추가
    camDiv.addEventListener("click", () => highlightWebcam(i));
    camDiv.addEventListener("dblclick", () => focusWebcam(i));
  }
}

function highlightWebcam(index) {
  const allItems = document.querySelectorAll(".webcam-grid-item");
  allItems.forEach((item) => item.classList.remove("highlight"));
  const selectedItem = document.querySelector(`[data-index="${index}"]`);
  selectedItem.classList.add("highlight");
}

function focusWebcam(index) {
  const selectedItem = document.querySelector(`[data-index="${index}"]`);
  const cctvId = selectedItem.getAttribute("data-cctv-id");

  if (cctvId) {
    // `last_access` 업데이트를 위한 API 호출
    fetch(`/update-last-access/${cctvId}`, { method: "POST" })
      .then((response) => response.json())
      .then((data) => {
        if (data.success) {
          console.log(`Last access updated for ${cctvId}:`, data.last_access);
          // 업데이트 성공 시 해당 CCTV 화면으로 이동
          window.location.href = `/focus-webcam/${cctvId}`;
        } else {
          console.error(
            `Error updating last_access for ${cctvId}:`,
            data.message
          );
          alert("CCTV 접근 기록 업데이트 중 문제가 발생했습니다.");
        }
      })
      .catch((error) => {
        console.error(`Error during last_access update for ${cctvId}:`, error);
        alert("CCTV 접근 중 문제가 발생했습니다.");
      });
  } else {
    console.error(`CCTV ID not found for index: ${index}`);
    alert("CCTV ID를 찾을 수 없습니다.");
  }
}

window.onload = setupWebcams;