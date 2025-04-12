document.addEventListener('DOMContentLoaded', () => {
    const wheel = document.getElementById('wheel');
    const spinButton = document.getElementById('spinButton');
    const prizeDisplay = document.getElementById('prizeDisplay');
    const resultContainer = document.getElementById('result');
    const winSound = document.getElementById('winSound');
    const loseSound = document.getElementById('loseSound');

    const prizes = [
        { value: 0.001, probability: 40, label: "0.001 ETH", color: "#FF6384", sound: winSound },
        { value: 0.002, probability: 30, label: "0.002 ETH", color: "#36A2EB", sound: winSound },
        { value: 0.005, probability: 15, label: "0.005 ETH", color: "#FFCE56", sound: winSound },
        { value: 0.01,  probability: 10, label: "0.01 ETH",  color: "#4BC0C0", sound: winSound },
        { value: 0.02,  probability: 4,  label: "0.02 ETH",  color: "#9966FF", sound: winSound },
        { value: 0.05,  probability: 1,  label: "0.05 ETH",  color: "#FF9F40", sound: winSound },
        { value: 0.1,   probability: 1,  label: "0.1 ETH",   color: "#00FF7F", sound: winSound },
        { value: 0,     probability: 10, label: "HAI PERSO", color: "#cccccc", sound: loseSound }
    ];

    function createWheel() {
        wheel.innerHTML = '<div class="center-hole"></div>';
        const segmentAngle = 360 / prizes.length;

        prizes.forEach((prize, index) => {
            const segment = document.createElement('div');
            segment.className = 'wheel-segment';
            segment.style.transform = `rotate(${index * segmentAngle}deg)`;
            segment.style.backgroundColor = prize.color;
            segment.appendChild(Object.assign(document.createElement('span'), { className: 'segment-label', textContent: prize.label }));
            wheel.appendChild(segment);
        });
    }

    function pickPrize() {
        const weighted = prizes.flatMap((prize, index) => Array(prize.probability).fill(index));
        return weighted[Math.floor(Math.random() * weighted.length)];
    }

    spinButton.addEventListener('click', () => {
        spinButton.disabled = true;
        resultContainer.classList.remove('visible');
        prizeDisplay.classList.remove('prize-pop');

        const winnerIndex = pickPrize();
        const segmentAngle = 360 / prizes.length;
        const stopAngle = winnerIndex * segmentAngle + Math.random() * segmentAngle;
        wheel.style.setProperty('--stop-angle', `${stopAngle}deg`);
        wheel.style.animation = 'none';
        void wheel.offsetWidth;
        wheel.style.animation = 'spin 2.5s cubic-bezier(0.08, 0.82, 0.17, 1) forwards';

        setTimeout(() => {
            const prize = prizes[winnerIndex];
            prizeDisplay.textContent = prize.value > 0 ? `HAI VINTO ${prize.label}!` : prize.label;
            prizeDisplay.className = 'prize-display prize-pop';
            prizeDisplay.style.background = prize.value > 0 ? 'linear-gradient(135deg, #ffd700, #ff9900)' : 'linear-gradient(135deg, #cccccc, #999999)';
            prize.sound.currentTime = 0;
            prize.sound.play();
            resultContainer.classList.add('visible');
            spinButton.disabled = false;

            if (window.Telegram && window.Telegram.WebApp) {
                Telegram.WebApp.sendData(JSON.stringify({ action: "wheel_spin", prize, timestamp: new Date().toISOString() }));
            }
        }, 2500);
    });

    createWheel();
});
