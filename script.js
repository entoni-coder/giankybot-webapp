document.addEventListener('DOMContentLoaded', function() {
    const wheel = document.getElementById('wheel');
    const spinBtn = document.getElementById('spinBtn');
    const result = document.getElementById('result');
    const resultContainer = document.getElementById('resultContainer');
    const wheelSound = document.getElementById('wheelSound');
    const winSound = document.getElementById('winSound');
    const loseSound = document.getElementById('loseSound');
    
    // Configurazione della ruota
    const wheelSections = [
        { text: "10", value: 10, color: "#FF6384", weight: 20 },
        { text: "20", value: 20, color: "#36A2EB", weight: 15 },
        { text: "30", value: 30, color: "#FFCE56", weight: 12 },
        { text: "50", value: 50, color: "#4BC0C0", weight: 8 },
        { text: "100", value: 100, color: "#9966FF", weight: 5 },
        { text: "150", value: 150, color: "#FF9F40", weight: 3 },
        { text: "200", value: 200, color: "#8AC24A", weight: 2 },
        { text: "You Lost", value: 0, color: "#F44336", weight: 35 }
    ];
    
    // Crea la ruota visivamente
    function createWheel() {
        const totalWeight = wheelSections.reduce((sum, section) => sum + section.weight, 0);
        let cumulativeAngle = 0;
        
        wheelSections.forEach((section, index) => {
            const sectionAngle = (section.weight / totalWeight) * 360;
            const sectionElement = document.createElement('div');
            sectionElement.className = 'wheel-section';
            sectionElement.textContent = section.text;
            sectionElement.style.backgroundColor = section.color;
            sectionElement.style.transform = `rotate(${cumulativeAngle}deg)`;
            sectionElement.style.clipPath = `polygon(0 0, 100% 0, 100% 100%)`;
            
            // Aggiusta la posizione del testo
            const textRotation = cumulativeAngle + sectionAngle / 2;
            sectionElement.style.transform = `rotate(${cumulativeAngle}deg)`;
            sectionElement.innerHTML = `<span style="transform: rotate(${textRotation}deg); display: inline-block; transform-origin: left center; margin-left: 10px;">${section.text}</span>`;
            
            wheel.appendChild(sectionElement);
            cumulativeAngle += sectionAngle;
        });
    }
    
    // Gira la ruota
    function spinWheel() {
        spinBtn.disabled = true;
        resultContainer.style.display = 'none';
        
        // Calcola l'angolo di rotazione basato sulle probabilità
        const totalWeight = wheelSections.reduce((sum, section) => sum + section.weight, 0);
        const random = Math.random() * totalWeight;
        let cumulativeWeight = 0;
        let selectedIndex = 0;
        
        for (let i = 0; i < wheelSections.length; i++) {
            cumulativeWeight += wheelSections[i].weight;
            if (random <= cumulativeWeight) {
                selectedIndex = i;
                break;
            }
        }
        
        // Calcola l'angolo di rotazione per centrare la sezione selezionata
        const sectionAngle = (wheelSections[selectedIndex].weight / totalWeight) * 360;
        const totalAngle = 360 * 5; // 5 giri completi
        const targetAngle = totalAngle + (360 - (selectedIndex * (360 / wheelSections.length) + sectionAngle / 2));
        
        // Animazione della ruota
        wheel.style.transform = `rotate(${targetAngle}deg)`;
        wheelSound.currentTime = 0;
        wheelSound.play();
        
        // Mostra il risultato dopo l'animazione
        setTimeout(() => {
            const selectedSection = wheelSections[selectedIndex];
            result.textContent = selectedSection.text;
            resultContainer.style.display = 'block';
            
            if (selectedSection.value > 0) {
                result.style.color = "#4CAF50";
                result.style.backgroundColor = "#E8F5E9";
                winSound.play();
                
                // Invia la vincita al wallet (simulato)
                sendToWallet(selectedSection.value);
            } else {
                result.style.color = "#F44336";
                result.style.backgroundColor = "#FFEBEE";
                loseSound.play();
            }
            
            spinBtn.disabled = false;
        }, 4000);
    }
    
    // Funzione simulata per inviare le vincite al wallet
    function sendToWallet(amount) {
        console.log(`Invio di ${amount} al wallet...`);
        // Qui andrebbe il codice reale per connettersi al wallet e inviare l'importo
        // Per una demo reale, dovresti integrare con un servizio di wallet come MetaMask
    }
    
    // Inizializza la ruota
    createWheel();
    
    // Aggiungi l'evento al pulsante
    spinBtn.addEventListener('click', spinWheel);
});
