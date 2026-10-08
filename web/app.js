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

if ("serviceWorker" in navigator) {
  navigator.serviceWorker.register("/sw.js");
}


// ---------- Painel de memória ----------
const botaoMemoria = document.createElement("button");
botaoMemoria.id = "abrir-memoria";
botaoMemoria.type = "button";
botaoMemoria.textContent = "Memória";
(document.querySelector("header") || document.body).appendChild(botaoMemoria);

const painel = document.createElement("section");
painel.id = "painel-memoria";
painel.hidden = true;
painel.innerHTML = `
  <div class="cartao">
    <div class="topo">
      <strong>O que a Evy lembra</strong>
      <button id="fechar-memoria" type="button">Fechar</button>
    </div>
    <ul id="lista-memoria"></ul>
  </div>
`;
document.body.appendChild(painel);

const listaMemoria = document.getElementById("lista-memoria");

async function carregarMemoria() {
  listaMemoria.textContent = "";
  try {
    const dados = await chamar("/api/memoria");
    if (dados.fatos.length === 0) {
      const vazio = document.createElement("li");
      vazio.className = "vazio";
      vazio.textContent = "Nada guardado ainda.";
      listaMemoria.appendChild(vazio);
      return;
    }
    dados.fatos.forEach((fato) => {
      const item = document.createElement("li");
      const texto = document.createElement("span");
      texto.textContent = fato;
      const apagar = document.createElement("button");
      apagar.type = "button";
      apagar.textContent = "Apagar";
      apagar.addEventListener("click", () => apagarFato(fato));
      item.append(texto, apagar);
      listaMemoria.appendChild(item);
    });
  } catch (erro) {
    listaMemoria.textContent = erro.message;
  }
}

async function apagarFato(fato) {
  if (!confirm("Apagar esta lembrança?\n\n" + fato)) return;
  try {
    await chamar("/api/memoria/apagar", {
      method: "POST",
      body: JSON.stringify({ fato }),
    });
    await carregarMemoria();
  } catch (erro) {
    alert(erro.message);
  }
}

botaoMemoria.addEventListener("click", () => {
  painel.hidden = false;
  carregarMemoria();
});

document.getElementById("fechar-memoria").addEventListener("click", () => {
  painel.hidden = true;
});
