const canvas = document.getElementById("wheelCanvas");
const ctx = canvas.getContext("2d");
const spinBtn = document.getElementById("spinBtn");
const result = document.getElementById("result");

const spinSound = document.getElementById("spinSound");
const winSound = document.getElementById("winSound");
const loseSound = document.getElementById("loseSound");

// Configurazione con probabilità
const wheelSections = [
  { text: "10", value: 10, color: "#FF6384", weight: 40 },
  { text: "20", value: 20, color: "#36A2EB", weight: 30 },
  { text: "50", value: 50, color: "#4BC0C0", weight: 15 },
  { text: "100", value: 100, color: "#9966FF", weight: 7 },
  { text: "150", value: 150, color: "#FF9F40", weight: 5 },
  { text: "200", value: 200, color: "#8AC24A", weight: 2 },
  { text: "500", value: 500, color: "#FFCE56", weight: 1 },
  { text: "You Lost", value: 0, color: "#F44336", weight: 10 }
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

    // Spicchio
    ctx.beginPath();
    ctx.moveTo(centerX, centerY);
    ctx.arc(centerX, centerY, radius, startAngle, endAngle);
    ctx.fillStyle = wheelSections[i].color;
    ctx.fill();
    ctx.stroke();

    // Testo
    ctx.save();
    ctx.translate(centerX, centerY);
    ctx.rotate(startAngle + arc / 2);
    ctx.textAlign = "right";
    ctx.fillStyle = "white";
    ctx.font = "bold 16px Arial";
    ctx.fillText(wheelSections[i].text, radius - 10, 10);
    ctx.restore();
  }
}

function spinWheel() {
  spinBtn.disabled = true;
  result.textContent = "";
  spinSound.play();

  const selectedIndex = getWeightedRandomIndex();
  const numSections = wheelSections.length;
  const arc = 2 * Math.PI / numSections;

  // Ruota per almeno 5 giri + si ferma sul settore selezionato
  const targetAngle = (2 * Math.PI * 5) + (Math.PI / 2 - selectedIndex * arc - arc / 2);
  let spinTime = 4000;
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
  const totalWeight = wheelSections.reduce((acc, sec) => acc + sec.weight, 0);
  let random = Math.random() * totalWeight;

  for (let i = 0; i < wheelSections.length; i++) {
    random -= wheelSections[i].weight;
    if (random <= 0) return i;
  }
  return wheelSections.length - 1; // fallback
}

function showResult(index) {
  const selected = wheelSections[index];
  result.textContent = `Hai vinto: ${selected.text}`;
  if (selected.value > 0) {
    result.style.color = "#4CAF50";
    winSound.play();
  } else {
    result.style.color = "#F44336";
    loseSound.play();
  }
}

// Inizializza
drawWheel();
spinBtn.addEventListener("click", spinWheel);

