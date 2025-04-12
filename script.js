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
        { value: 0.1,   probability: 1,  label: "0.1 ETH",   color: "#00FF7F" },
        { value: 0,     probability: 10, label: "HAI PERSO", color: "#cccccc" }
    ];

    function createWheel() {
        wheel.innerHTML = '';
        const segmentAngle = 360 / prizes.length;

        prizes.forEach((prize, index) => {
            const segment = document.createElement('div');
            segment.className = 'wheel-segment';
            segment.style.transform = `rotate(${index * segmentAngle}deg)`;
            segment.style.backgroundColor = prize.color;
            
            const label = document.createElement('span');
            label.className = 'segment-label';
            label.textContent = prize.label;
            
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
        return weighted[Math.floor(Math.random() * weighted.length)];
    }

    spinButton.addEventListener('click', () => {
        spinButton.disabled = true;
        resultContainer.classList.remove('visible');
        
        const winnerIndex = pickPrize();
        const segmentAngle = 360 / prizes.length;
        const stopAngle = winnerIndex * segmentAngle + Math.random() * segmentAngle;
        
        // Imposta l'angolo di stop come variabile CSS
        wheel.style.setProperty('--stop-angle', `${stopAngle}deg`);
        
        // Applica l'animazione
        wheel.style.animation = 'none';
        void wheel.offsetWidth; // Trigger reflow
        wheel.style.animation = 'spin 3s cubic-bezier(0.17, 0.89, 0.32, 1) forwards';
        
        setTimeout(() => {
            const prize = prizes[winnerIndex];
            prizeText.textContent = prize.value > 0 ? `🎉 ${prize.label} 🎉` : `😢 ${prize.label}`;
            resultContainer.classList.add('visible');
            spinButton.disabled = false;
            
            if (window.Telegram && window.Telegram.WebApp) {
                Telegram.WebApp.sendData(JSON.stringify({
                    action: "wheel_spin",
                    prize: prize,
                    timestamp: new Date().toISOString()
                }));
            }
        }, 3000);
    });

    createWheel();
});
