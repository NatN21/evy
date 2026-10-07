const conversa = document.getElementById("conversa");
const formulario = document.getElementById("formulario");
const campo = document.getElementById("campo");

function pegarSenha() {
  let senha = localStorage.getItem("evy_senha");
  if (!senha) {
    senha = prompt("Senha da Evy:") || "";
    localStorage.setItem("evy_senha", senha);
  }
  return senha;
}

function rolarParaOFim() {
  conversa.scrollTop = conversa.scrollHeight;
}

function mostrar(papel, texto) {
  const balao = document.createElement("div");
  balao.className = "mensagem " + papel;
  balao.textContent = texto;
  conversa.appendChild(balao);
  rolarParaOFim();
  return balao;
}

function mostrarErro(texto) {
  const aviso = document.createElement("div");
  aviso.className = "erro";
  aviso.textContent = texto;
  conversa.appendChild(aviso);
  rolarParaOFim();
}

async function chamar(url, opcoes = {}) {
  const resposta = await fetch(url, {
    ...opcoes,
    headers: {
      "Content-Type": "application/json",
      "X-Evy-Senha": pegarSenha(),
    },
  });
  if (resposta.status === 401) {
    localStorage.removeItem("evy_senha");
    throw new Error("Senha incorreta. Recarregue a página e tente de novo.");
  }
  const dados = await resposta.json();
  if (!resposta.ok) {
    throw new Error(dados.erro || "Erro desconhecido.");
  }
  return dados;
}

async function carregarHistorico() {
  try {
    const dados = await chamar("/api/historico");
    dados.mensagens.forEach((m) => mostrar(m.papel, m.texto));
  } catch (erro) {
    mostrarErro(erro.message);
  }
}

formulario.addEventListener("submit", async (evento) => {
  evento.preventDefault();
  const texto = campo.value.trim();
  if (!texto) return;
  campo.value = "";
  mostrar("user", texto);
  const pensando = mostrar("model", "...");
  campo.disabled = true;
  try {
    const dados = await chamar("/api/mensagem", {
      method: "POST",
      body: JSON.stringify({ mensagem: texto }),
    });
    pensando.textContent = dados.resposta;
    rolarParaOFim();
  } catch (erro) {
    pensando.remove();
    mostrarErro(erro.message);
  } finally {
    campo.disabled = false;
    campo.focus();
  }
});

carregarHistorico();
