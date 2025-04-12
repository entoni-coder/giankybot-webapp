document.addEventListener('DOMContentLoaded', () => {
    const wheel = document.getElementById('wheel');
    const spinButton = document.getElementById('spinButton');
    const prizeText = document.getElementById('prizeText');
    const resultContainer = document.getElementById('result');

    const prizes = [
        { value: 0.001, probability: 40, label: "0.001 ETH", color: "#FF6384" },
        { value: 0.002, probability: 30, label: "0.002 ETH", color: "#36A2EB" },
        { value: 0.005, probability: 15, label: "0.005 ETH", color: "#FFCE56" },
        { value: 0.01,  probability: 10, label: "0.01 ETH",  color: "#4BC0C0" },
        { value: 0.02,  probability: 4,  label: "0.02 ETH",  color: "#9966FF" },
        { value: 0.05,  probability: 1,  label: "0.05 ETH",  color: "#FF9F40" },
        { value: 0,     probability: 10, label: "YOU LOST", color: "#cccccc" } // Aggiunto spicchio perdita
    ];

    function createWheel() {
        wheel.innerHTML = '';
        const total = prizes.length;
        const segmentAngle = 360 / total;

        prizes.forEach((prize, index) => {
            const segment = document.createElement('div');
            segment.className = 'wheel-segment';
            segment.style.transform = `rotate(${index * segmentAngle}deg) skewY(-${90 - segmentAngle}deg)`;
            segment.style.backgroundColor = prize.color;

            const label = document.createElement('span');
            label.textContent = prize.label;
            label.className = 'segment-label';
            label.style.transform = `skewY(${90 - segmentAngle}deg) rotate(${segmentAngle / 2}deg)`;

            segment.appendChild(label);
            wheel.appendChild(segment);
        });
    }

    function pickPrize() {
        const weighted = [];
        prizes.forEach((prize, index) => {
            for (let i = 0; i < prize.probability; i++) {
                weighted.push(index);
            }
        });
        const randomIndex = Math.floor(Math.random() * weighted.length);
        return weighted[randomIndex];
    }

    spinButton.addEventListener('click', () => {
        spinButton.disabled = true;
        resultContainer.classList.add('hidden');

        const winnerIndex = pickPrize();
        const degreesPerSegment = 360 / prizes.length;
        const randomOffset = Math.floor(Math.random() * degreesPerSegment);
        const spinDegrees = 360 * 5 + (360 - (winnerIndex * degreesPerSegment)) - randomOffset;

        wheel.style.transition = 'transform 5s ease-out';
        wheel.style.transform = `rotate(${spinDegrees}deg)`;

        setTimeout(() => {
            const prize = prizes[winnerIndex];
            if (prize.value > 0) {
                prizeText.textContent = `🎉 HAI VINTO ${prize.label}!`;
            } else {
                prizeText.textContent = `😢 ${prize.label}`;
            }
            resultContainer.classList.remove('hidden');
            spinButton.disabled = false;

            if (window.Telegram && window.Telegram.WebApp) {
                Telegram.WebApp.sendData(JSON.stringify({
                    action: "wheel_spin",
                    prize: prize,
                    timestamp: new Date().toISOString()
                }));
            }
        }, 5000);
    });

    createWheel();
});
