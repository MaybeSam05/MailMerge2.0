let numParams = 0;

function generateParameters() {
  const container = document.getElementById('parametersContainer');
  container.innerHTML = '';

  numParams = document.getElementById('numParams').value;
  for (let i = 1; i <= numParams; i++) {
    const input = document.createElement('input');
    input.type = 'text';
    input.name = `replace${i}`;
    input.placeholder = `Replace ${i}`;
    input.className = 'dynamic-input';
    container.appendChild(input);
  }
}

function generateEmails() {
  const container = document.getElementById('emailsContainer');
  container.innerHTML = '';

  const numEmails = document.getElementById('numEmails').value;
  for (let i = 1; i <= numEmails; i++) {
    const emailSection = document.createElement('div');
    emailSection.className = 'section';
    
    const emailLabel = document.createElement('h3');
    emailLabel.innerText = `Email ${i}`;
    emailLabel.style.color = 'var(--primary-color)';
    emailSection.appendChild(emailLabel);

    const emailInput = document.createElement('input');
    emailInput.type = 'text';
    emailInput.name = `email${i}`;
    emailInput.placeholder = `Email ${i}`;
    emailInput.className = 'dynamic-input';
    emailSection.appendChild(emailInput);

    for (let j = 1; j <= numParams; j++) {
      const paramInput = document.createElement('input');
      paramInput.type = 'text';
      paramInput.name = `email${i}_param${j}`;
      paramInput.placeholder = `Parameter ${j}`;
      paramInput.className = 'dynamic-input';
      emailSection.appendChild(paramInput);
    }

    container.appendChild(emailSection);
  }
}