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
        { value: 0,     probability: 10, label: "YOU LOST", color: "#cccccc" }
    ];

    function createWheel() {
        wheel.innerHTML = '';
        const total = prizes.length;
        const segmentAngle = 360 / total;

        prizes.forEach((prize, index) => {
            const segment = document.createElement('div');
            segment.className = 'wheel-segment';
            
            const rotateAngle = index * segmentAngle;
            segment.style.transform = `rotate(${rotateAngle}deg)`;
            segment.style.backgroundColor = prize.color;
            segment.style.borderRight = '1px solid rgba(0,0,0,0.3)';
            
            const label = document.createElement('span');
            label.textContent = prize.label;
            label.className = 'segment-label';
            
            // Impostiamo la variabile CSS per l'angolo del segmento
            label.style.setProperty('--segment-angle', `${segmentAngle}deg`);
            
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
        resultContainer.classList.remove('visible');
        resultContainer.classList.add('hidden');

        const winnerIndex = pickPrize();
        const degreesPerSegment = 360 / prizes.length;
        const randomOffset = Math.floor(Math.random() * degreesPerSegment);
        
        // Rotazione antioraria (valori negativi) più veloce (meno giri ma più rapida)
        const spinDegrees = -360 * 5 - (winnerIndex * degreesPerSegment) - randomOffset;
        
        // Reset della rotazione per permettere giri multipli
        wheel.style.transition = 'none';
        wheel.style.transform = 'rotate(0deg)';
        
        // Forza il reflow per far applicare il reset
        void wheel.offsetWidth;
        
        // Nuova animazione più veloce (2 secondi invece di 3)
        wheel.style.transition = 'transform 2s cubic-bezier(0.08, 0.82, 0.17, 1)';
        wheel.style.transform = `rotate(${spinDegrees}deg)`;

        setTimeout(() => {
            const prize = prizes[winnerIndex];
            prizeText.textContent = prize.value > 0 ? `🎉 HAI VINTO ${prize.label}!` : `😢 ${prize.label}`;
            resultContainer.classList.remove('hidden');
            resultContainer.classList.add('visible', 'winner-animation');
            spinButton.disabled = false;

            if (window.Telegram && window.Telegram.WebApp) {
                Telegram.WebApp.sendData(JSON.stringify({
                    action: "wheel_spin",
                    prize: prize,
                    timestamp: new Date().toISOString()
                }));
            }
        }, 2000); // Ridotto da 3000 a 2000ms per la durata più breve
    });

    createWheel();
});
