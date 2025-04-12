document.addEventListener('DOMContentLoaded', () => {
    const wheel = document.getElementById('wheel');
    const spinButton = document.getElementById('spinButton');
    const prizeText = document.getElementById('prizeText');
    const resultContainer = document.getElementById('result');
    
    const prizes = [
        { value: 0.001, probability: 40, label: "0.001 ETH", color: "#FF6384" },
        { value: 0.002, probability: 30, label: "0.002 ETH", color: "#36A2EB" },
        { value: 0.005, probability: 15, label: "0.005 ETH", color: "#FFCE56" },
        { value: 0.01, probability: 10, label: "0.01 ETH", color: "#4BC0C0" },
        { value: 0.02, probability: 4, label: "0.02 ETH", color: "#9966FF" },
        { value: 0.05, probability: 1, label: "0.05 ETH", color: "#FF9F40" }
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
            label.textContent = prize.label;
            label.style.transform = `rotate(${segmentAngle/2}deg)`;
            
            segment.appendChild(label);
            wheel.appendChild(segment);
        });
    }
    
    spinButton.addEventListener('click', () => {
        spinButton.disabled = true;
        resultContainer.classList.add('hidden');
        
        const winnerIndex = Math.floor(Math.random() * prizes.length);
        const spinDegrees = 360 * 5 + (360 - (winnerIndex * (360 / prizes.length)));
        
        wheel.style.transform = `rotate(${spinDegrees}deg)`;
        
        setTimeout(() => {
            const prize = prizes[winnerIndex];
            prizeText.textContent = `HAI VINTO ${prize.label}!`;
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