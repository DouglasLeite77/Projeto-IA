const claimField = document.getElementById("claim");
const resultSection = document.getElementById("result");
const errorBox = document.getElementById("error");
const resultUrlRow = document.getElementById("result-url-row");
const resultUrlLink = document.getElementById("result-url");
const resultGNewsScore = document.getElementById("result-gnews-score");
const analyzeButton = document.getElementById("analyze-button");

const setResult = (data) => {
  document.getElementById("result-claim").textContent = data.claim;
  document.getElementById("result-source").textContent = data.source;
  document.getElementById("result-verdict").textContent = data.verdict;
  document.getElementById("result-probability").textContent = `${(data.probability * 100).toFixed(1)}%`;
  document.getElementById("result-detail").textContent = data.detail;
  if (data.url) {
    resultUrlRow.hidden = false;
    resultUrlLink.href = data.url;
    resultUrlLink.textContent = data.url;
  } else {
    resultUrlRow.hidden = true;
    resultUrlLink.href = "#";
    resultUrlLink.textContent = "";
  }
  errorBox.textContent = "";
  resultSection.classList.remove("hidden");
  try { claimField.value = data.claim || claimField.value; } catch (e) {}
};

const setError = (message) => {
  errorBox.textContent = message;
  errorBox.classList.remove("hidden");
};

const clearResult = () => {
  document.getElementById("result-claim").textContent = "";
  document.getElementById("result-source").textContent = "";
  document.getElementById("result-verdict").textContent = "";
  document.getElementById("result-probability").textContent = "";
  document.getElementById("result-gnews-score").textContent = "";
  document.getElementById("result-detail").textContent = "";
  resultUrlRow.hidden = true;
  resultUrlLink.href = "#";
  resultUrlLink.textContent = "";
  resultSection.classList.add("hidden");
};

const preventFormSubmission = (event) => {
  if (event) {
    event.preventDefault();
    event.stopPropagation();
  }
};

async function sendClaim() {
  errorBox.classList.add("hidden");
  clearResult();
  const claim = claimField.value.trim();
  if (!claim) {
    setError("Digite uma afirmação para analisar.");
    return;
  }

  analyzeButton.disabled = true;
  analyzeButton.textContent = "Analisando...";

  try {
    console.log("Enviando sentença para análise:", claim);
    const response = await fetch("http://127.0.0.1:8000/analyze", {
      method: "POST",
      mode: "cors",
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify({ claim })
    });

    let data;
    const contentType = response.headers.get("content-type") || "";
    if (contentType.includes("application/json")) {
      data = await response.json();
    } else {
      const text = await response.text();
      throw new Error(`Resposta inválida do backend: ${text}`);
    }

    console.log("Resposta do backend:", response.status, data);
    if (!response.ok) {
      throw new Error(data?.detail || "Erro ao consultar o backend.");
    }

    setResult(data);
  } catch (error) {
    console.error(error);
    setError(error.message || "Erro desconhecido ao analisar a afirmação.");
  } finally {
    analyzeButton.disabled = false;
    analyzeButton.textContent = "Analisar";
  }
}

console.log("frontend app.js loaded");

document.addEventListener("submit", preventFormSubmission, true);

document.addEventListener("click", (event) => {
  const target = event.target;
  if (target && target.id === "analyze-button") {
    event.preventDefault();
    event.stopPropagation();
    console.log("analyze button clicked");
    sendClaim();
  }
});

if (analyzeButton) {
  analyzeButton.type = "button";
}

