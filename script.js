const canvas = document.getElementById("wheelCanvas");
const ctx = canvas.getContext("2d");
const spinBtn = document.getElementById("spinBtn");
const result = document.getElementById("result");

const spinSound = document.getElementById("spinSound");
const winSound = document.getElementById("winSound");
const loseSound = document.getElementById("loseSound");

// Configurazione con probabilità aggiornata per Giankybotes
const wheelSections = [
  { text: "500", value: 500, color: "#FFCE56", weight: 1 },
  { text: "1000", value: 1000, color: "#4BC0C0", weight: 1 },
  { text: "200", value: 200, color: "#8AC24A", weight: 1 },
  { text: "You Lost", value: 0, color: "#F44336", weight: 0.5 },
  { text: "You Lost", value: 0, color: "#F44336", weight: 1.0 },
  { text: "You Lost", value: 0, color: "#F44336", weight: 0.5 }
];

let currentAngle = 0;
let isSpinning = false;

function drawWheel() {
  const radius = canvas.width / 2;
  const centerX = canvas.width / 2;
  const centerY = canvas.height / 2;
  const numSections = wheelSections.length;
  const arc = 2 * Math.PI / numSections;

  ctx.clearRect(0, 0, canvas.width, canvas.height);

  // Disegna gli spicchi
  for (let i = 0; i < numSections; i++) {
    const startAngle = i * arc + currentAngle;
    const endAngle = startAngle + arc;

    ctx.beginPath();
    ctx.moveTo(centerX, centerY);
    ctx.arc(centerX, centerY, radius, startAngle, endAngle);
    ctx.fillStyle = wheelSections[i].color;
    ctx.fill();
    ctx.strokeStyle = "#333";
    ctx.lineWidth = 2;
    ctx.stroke();

    // Testo
    ctx.save();
    ctx.translate(centerX, centerY);
    ctx.rotate(startAngle + arc / 2);
    ctx.textAlign = "right";
    ctx.fillStyle = "white";
    ctx.font = "bold 18px Arial";
    ctx.fillText(wheelSections[i].text, radius - 20, 10);
    ctx.restore();
  }

  // Centro della ruota
  ctx.beginPath();
  ctx.arc(centerX, centerY, 10, 0, 2 * Math.PI);
  ctx.fillStyle = "#333";
  ctx.fill();
}

function spinWheel() {
  if (isSpinning) return;
  
  isSpinning = true;
  spinBtn.disabled = true;
  result.textContent = "";
  spinSound.play();

  const selectedIndex = getWeightedRandomIndex();
  const numSections = wheelSections.length;
  const arc = 2 * Math.PI / numSections;

  // Ruota per almeno 5 giri + si ferma sul settore selezionato
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
      isSpinning = false;
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
  return wheelSections.length - 1;
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

// Inizializzazione
window.addEventListener('load', () => {
  drawWheel();
  spinBtn.addEventListener('click', spinWheel);
});
