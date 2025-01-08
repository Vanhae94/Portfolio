function captureCCTV(cctvId) {
  const streamElement = document.getElementById("detection-stream");
  const link = document.createElement("a");
  link.href = streamElement.src;
  link.download = `CCTV_${cctvId}_capture.jpg`;
  link.click();
}
