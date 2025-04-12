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

function drawArrow(angle) {
  const arrowHeight = 20;
  const arrowWidth = 30;
  const centerX = canvas.width / 2;
  const centerY = canvas.height / 2 - canvas.width / 2 - 10; // Posizione della freccia sopra la ruota

  const arrowAngle = angle; // Allinea la freccia alla posizione vincente

  ctx.beginPath();
  ctx.moveTo(centerX - arrowWidth / 2, centerY); // Punto di partenza
  ctx.lineTo(centerX + arrowWidth / 2, centerY); // Punta della freccia
  ctx.lineTo(centerX, centerY - arrowHeight); // Punto finale (freccia verso l'alto)
  ctx.closePath();
  ctx.fillStyle = "black"; // Colore della freccia
  ctx.fill();
}

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

  // Disegna la freccia sotto la ruota
  drawArrow(currentAngle); // Passa l'angolo corrente per allineare la freccia
}

function spinWheel() {
  spinBtn.disabled = true;
  result.textContent = "";
  spinSound.play();

  const selectedIndex = getWeightedRandomIndex();

