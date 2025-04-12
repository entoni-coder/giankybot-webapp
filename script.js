const canvas = document.getElementById("wheelCanvas");
const ctx = canvas.getContext("2d");
const spinBtn = document.getElementById("spinBtn");
const result = document.getElementById("result");

const spinSound = document.getElementById("spinSound");
const winSound = document.getElementById("winSound");
const loseSound = document.getElementById("loseSound");

const wheelSections = [
  { text: "10", value: 10, color: "#FF6384", weight: 40 },
  { text: "20", value: 20, color: "#36A2EB", weight: 30 },
  { text: "50", value: 50, color: "#4BC0C0", weight: 15 },
  { text: "100", value: 100, color: "#9966FF", weight: 7 },
  { text: "150", value: 150, color: "#FF9F40", weight: 5 },
  { text: "200", value: 200, color: "#8AC24A", weight: 2 },
  { text: "500", value: 500, color: "#FFD700", weight: 1 },
  { text: "You Lost", value: 0, color: "#FF3B3B", weight: 10 }
];

let currentAngle = 0;

function drawWheel() {
  const radius = canvas.width / 2;
  const centerX = canvas.width / 2;
  const centerY = canvas.height / 2;
  const numSections = wheelSections.length;
  const arc = 2 * Math.PI / numSections;

  ctx.clearRect(0, 0, canvas.width, canvas.height);

  for (let i = 0; i < numSections; i++) {
    const startAngle = i * arc + currentAngle;
    const endAngle = startAngle + arc;

    const gradient = ctx.createLinearGradient(centerX, centerY, centerX + radius * Math.cos(startAngle), centerY + radius * Math.sin(startAngle));
    gradient.addColorStop(0, wheelSections[i].color);
    gradient.addColorStop(1, "#222");

    // Draw segment
    ctx.beginPath();
    ctx.moveTo(centerX, centerY);
    ctx.arc(centerX, centerY, radius, startAngle, endAngle);
    ctx.fillStyle = gradient;
    ctx.fill();
    ctx.strokeStyle = "#fff";
    ctx.lineWidth = 2;
    ctx.stroke();

    // Draw text
    ctx.save();
    ctx.translate(centerX, centerY);
    ctx.rotate(startAngle + arc / 2);
    ctx.textAlign = "right";
    ctx.fillStyle = "#fff";
    ctx.font = "bold 18px 'Segoe UI'";
    ctx.fillText(wheelSections[i].text, radius - 15, 8);
    ctx.restore();
  }

  // Draw center circle
  ctx.beginPath();
  ctx.arc(centerX, centerY, 20, 0, 2 * Math.PI);
  ctx.fillStyle = "#fff";
  ctx.fill();
  ctx.strokeStyle = "#000";
  ctx.stroke();
}

function spinWheel() {
  spinBtn.disabled = true;
  result.textContent = "";
  spinSound.play();

  const selectedIndex = getWeightedRandomIndex();
  const numSections = wheelSections.length;
  const arc = 2 * Math.PI / numSections;
  const targetAngle = (2 * Math.PI * 5) + (Math.PI / 2 - selectedIndex * arc - arc / 2);
  const spinTime = 4000;
  let start = null;

  function animate(timestamp) {
    if (!start) start = timestamp;
    const progress = timestamp - start;
    const easing = (t) => 1 - Math.pow(1 - t, 3); // easeOutCubic

    const angle = currentAngle + easing(progress / spinTime) * (targetAngle - currentAngle);
    currentAngle = angle % (2 * Math.PI);
    drawWheel();

    if (progress < spinTime) {
      requestAnimationFrame(animate);
    } else {
      currentAngle = targetAngle % (2 * Math.PI);
      drawWheel();
      showResult(selectedIndex);
      spinBtn.disabled = false;
    }
  }

  requestAnimationFrame(animate);
}

function getWeightedRandomIndex() {
  const totalWeight = wheelSections.reduce((sum, s) => sum + s.weight, 0);
  let rand = Math.random() * totalWeight;

  for (let i = 0; i < wheelSections.length; i++) {
    rand -= wheelSections[i].weight;
    if (rand <= 0) return i;
  }
  return wheelSections.length - 1;
}

function showResult(index) {
  const selected = wheelSections[index];
  result.textContent = selected.value > 0 ? `🎉 Hai vinto: ${selected.text}!` : `💀 ${selected.text}`;
  result.style.color = selected.value > 0 ? "#00e676" : "#ff5252";
  selected.value > 0 ? winSound.play() : loseSound.play();
}
