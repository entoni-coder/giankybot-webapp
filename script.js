document.addEventListener('DOMContentLoaded', function() {
    const wheel = document.getElementById('wheel');
    const spinBtn = document.getElementById('spinBtn');
    const result = document.getElementById('result');
    const resultContainer = document.getElementById('resultContainer');
    const wheelSound = document.getElementById('wheelSound');
    const winSound = document.getElementById('winSound');
    const loseSound = document.getElementById('loseSound');
    
    // Configurazione della ruota con probabilità maggiori per valori bassi 
const wheelSections = [
    { text: "10", value: 10, color: "#FF6384", weight: 40 },  // 40% probabilità
    { text: "20", value: 20, color: "#36A2EB", weight: 30 },  // 30% probabilità
    { text: "30", value: 30, color: "#FFCE56", weight: 15 },  // 15% probabilità
    { text: "50", value: 50, color: "#4BC0C0", weight: 7 },   // 7% probabilità
    { text: "100", value: 100, color: "#9966FF", weight: 5 },  // 5% probabilità
    { text: "150", value: 150, color: "#FF9F40", weight: 2 },  // 2% probabilità
    { text: "200", value: 200, color: "#8AC24A", weight: 1 },  // 1% probabilità
    { text: "You Lost", value: 0, color: "#F44336", weight: 10 } // 10% probabilità di perdere
];

    
    // Crea la ruota visivamente con spicchi ordinati
    function createWheel() {
        const totalWeight = wheelSections.reduce((sum, section) => sum + section.weight, 0);
        let cumulativeAngle = 0;
        
        // Ordina gli spicchi per valore crescente
        const sortedSections = [...wheelSections].sort((a, b) => a.value - b.value);
        
        sortedSections.forEach((section, index) => {
            const sectionAngle = (section.weight / totalWeight) * 360;
            const sectionElement = document.createElement('div');
            sectionElement.className = 'wheel-section';
            sectionElement.style.backgroundColor = section.color;
            sectionElement.style.transform = `rotate(${cumulativeAngle}deg)`;
            
            // Calcola la posizione del testo
            const textRotation = cumulativeAngle + sectionAngle / 2;
            sectionElement.innerHTML = `
                <span style="
                    transform: rotate(${textRotation}deg);
                    display: inline-block;
                    transform-origin: left center;
                    margin-left: 20px;
                    width: 80px;
                ">
                    ${section.text}
                </span>
            `;
            
            wheel.appendChild(sectionElement);
            cumulativeAngle += sectionAngle;
        });
    }
    
    // Gira la ruota
    function spinWheel() {
        spinBtn.disabled = true;
        resultContainer.style.display = 'none';
        
        // Calcola la sezione vincente in base alle probabilità
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
        // Prima calcoliamo l'angolo di inizio della sezione
        let sectionStartAngle = 0;
        for (let i = 0; i < selectedIndex; i++) {
            sectionStartAngle += (wheelSections[i].weight / totalWeight) * 360;
        }
        
        // Poi calcoliamo l'angolo centrale della sezione
        const sectionAngle = (wheelSections[selectedIndex].weight / totalWeight) * 360;
        const sectionCenterAngle = sectionStartAngle + sectionAngle / 2;
        
        // Rotazione completa (5 giri) + angolo per centrare la sezione
        const totalAngle = 360 * 5 + (360 - sectionCenterAngle);
        
        // Animazione della ruota
        wheel.style.transform = `rotate(${totalAngle}deg)`;
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
        alert(`Hai vinto ${amount}! L'importo è stato inviato al tuo wallet.`);
    }
    
    // Inizializza la ruota
    createWheel();
    
    // Aggiungi l'evento al pulsante
    spinBtn.addEventListener('click', spinWheel);
});
