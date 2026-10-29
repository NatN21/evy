const conversa = document.getElementById("conversa");
const formulario = document.getElementById("formulario");
const campo = document.getElementById("campo");

// A senha não é mais usada no navegador: quem autentica é o cookie do aparelho.
localStorage.removeItem("evy_senha");

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
    credentials: "same-origin",
    headers: { "Content-Type": "application/json" },
  });
  if (resposta.status === 401) {
    location.href = "/parear";
    throw new Error("Aparelho não pareado.");
  }
  const dados = await resposta.json();
  if (!resposta.ok) {
    throw new Error(dados.erro || "Erro desconhecido.");
  }
  return dados;
}

// ---------- Chat ----------
async function carregarHistorico() {
  try {
    const dados = await chamar("/api/historico");
    dados.mensagens.forEach((m) => mostrar(m.papel, m.texto));
  } catch (erro) {
    mostrarErro(erro.message);
  }
}

// Altura do campo: cresce com o texto até 152px (≈ 5 linhas); depois rola.
// (O CSS com field-sizing já faz isso nos navegadores novos; isto cobre os demais.)
const ALTURA_MAXIMA_CAMPO = 152;

function ajustarAlturaDoCampo() {
  campo.style.height = "auto";
  campo.style.height = Math.min(campo.scrollHeight, ALTURA_MAXIMA_CAMPO) + "px";
}

campo.addEventListener("input", ajustarAlturaDoCampo);

// Em computador (mouse/teclado): Enter envia, Shift+Enter quebra linha.
// No celular: Enter quebra linha e o botão envia.
const temTecladoFisico = window.matchMedia("(hover: hover) and (pointer: fine)");

campo.addEventListener("keydown", (evento) => {
  if (evento.key === "Enter" && !evento.shiftKey && !evento.isComposing && temTecladoFisico.matches) {
    evento.preventDefault();
    formulario.requestSubmit();
  }
});

formulario.addEventListener("submit", async (evento) => {
  evento.preventDefault();
  const texto = campo.value.trim();
  if (!texto) return;
  campo.value = "";
  campo.style.height = "auto";
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

// ---------- Menu lateral ----------
const menu = document.getElementById("menu");
const fundoMenu = document.getElementById("fundo-menu");

function abrirMenu() {
  menu.classList.add("aberto");
  fundoMenu.hidden = false;
}

function fecharMenu() {
  menu.classList.remove("aberto");
  fundoMenu.hidden = true;
}

document.getElementById("abrir-menu").addEventListener("click", abrirMenu);
document.getElementById("fechar-menu").addEventListener("click", fecharMenu);
fundoMenu.addEventListener("click", fecharMenu);

// ---------- Painéis ----------
const painel = document.getElementById("painel-memoria");
const tituloPainel = document.getElementById("titulo-painel");
const listaMemoria = document.getElementById("lista-memoria");
const controlesAvisos = document.getElementById("controles-avisos");
const estadoAvisos = document.getElementById("estado-avisos");

function itemVazio(texto) {
  const vazio = document.createElement("li");
  vazio.className = "vazio";
  vazio.textContent = texto;
  return vazio;
}

function botaoApagar(rotulo, aoClicar) {
  const botao = document.createElement("button");
  botao.type = "button";
  botao.textContent = rotulo;
  botao.addEventListener("click", aoClicar);
  return botao;
}

// Memória
async function carregarMemoria() {
  listaMemoria.textContent = "";
  try {
    const dados = await chamar("/api/memoria");
    if (dados.fatos.length === 0) {
      listaMemoria.appendChild(itemVazio("Nada guardado ainda."));
      return;
    }
    dados.fatos.forEach((fato) => {
      const item = document.createElement("li");
      const texto = document.createElement("span");
      texto.textContent = fato;
      item.append(texto, botaoApagar("Apagar", () => apagarFato(fato)));
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

// Lembretes
async function carregarLembretes() {
  listaMemoria.textContent = "";
  try {
    const dados = await chamar("/api/lembretes");
    if (dados.lembretes.length === 0) {
      listaMemoria.appendChild(itemVazio("Nenhum lembrete pendente."));
      return;
    }
    dados.lembretes.forEach((lembrete) => {
      const item = document.createElement("li");
      const bloco = document.createElement("span");
      const quando = document.createElement("strong");
      quando.textContent =
        lembrete.descricao + (lembrete.vencido ? " (já passou)" : "");
      if (lembrete.vencido) quando.className = "vencido";
      const texto = document.createElement("div");
      texto.textContent = lembrete.texto;
      bloco.append(quando, texto);
      item.append(bloco, botaoApagar("Apagar", () => apagarLembrete(lembrete)));
      listaMemoria.appendChild(item);
    });
  } catch (erro) {
    listaMemoria.textContent = erro.message;
  }
}

async function apagarLembrete(lembrete) {
  if (!confirm("Apagar este lembrete?\n\n" + lembrete.texto)) return;
  try {
    await chamar("/api/lembretes/apagar", {
      method: "POST",
      body: JSON.stringify({ id: lembrete.id }),
    });
    await carregarLembretes();
  } catch (erro) {
    alert(erro.message);
  }
}

// Dispositivos
async function carregarDispositivos() {
  listaMemoria.textContent = "";
  try {
    const dados = await chamar("/api/dispositivos");
    dados.dispositivos.forEach((d) => {
      const item = document.createElement("li");
      const bloco = document.createElement("span");
      const nome = document.createElement("strong");
      nome.textContent = d.nome;
      const uso = document.createElement("div");
      uso.textContent =
        "Último uso: " +
        new Date(d.ultimo_uso * 1000).toLocaleString("pt-BR", {
          dateStyle: "short",
          timeStyle: "short",
        });
      bloco.append(nome, uso);
      item.append(bloco, botaoApagar("Revogar", () => revogarDispositivo(d)));
      listaMemoria.appendChild(item);
    });
    listaMemoria.appendChild(
      itemVazio("Para parear outro aparelho, rode  venv/bin/python parear.py  no YhwBook.")
    );
  } catch (erro) {
    listaMemoria.textContent = erro.message;
  }
}

async function revogarDispositivo(d) {
  const aviso =
    "Revogar este aparelho?\n\n" +
    d.nome +
    "\n\nSe for o aparelho que você está usando, será preciso parear de novo.";
  if (!confirm(aviso)) return;
  try {
    await chamar("/api/dispositivos/revogar", {
      method: "POST",
      body: JSON.stringify({ id: d.id }),
    });
    await carregarDispositivos();
  } catch (erro) {
    alert(erro.message);
  }
}

const paineis = {
  memoria: { titulo: "O que a Evy lembra", carregar: carregarMemoria, avisos: false },
  lembretes: { titulo: "Seus lembretes", carregar: carregarLembretes, avisos: true },
  dispositivos: { titulo: "Dispositivos pareados", carregar: carregarDispositivos, avisos: false },
};

function abrirPainel(nome) {
  const p = paineis[nome];
  tituloPainel.textContent = p.titulo;
  controlesAvisos.hidden = !p.avisos;
  painel.hidden = false;
  p.carregar();
  if (p.avisos) atualizarEstadoAvisos();
}

document.querySelectorAll(".item-menu").forEach((botao) => {
  botao.addEventListener("click", () => {
    fecharMenu();
    abrirPainel(botao.dataset.painel);
  });
});

document.getElementById("fechar-painel").addEventListener("click", () => {
  painel.hidden = true;
});

// ---------- Avisos (notificações push) ----------
function chaveParaBytes(chave) {
  const preenchimento = "=".repeat((4 - (chave.length % 4)) % 4);
  const base64 = (chave + preenchimento).replace(/-/g, "+").replace(/_/g, "/");
  const bruto = atob(base64);
  return Uint8Array.from(bruto, (c) => c.charCodeAt(0));
}

async function atualizarEstadoAvisos() {
  if (!("serviceWorker" in navigator) || !("PushManager" in window)) {
    estadoAvisos.textContent = "Este navegador não suporta avisos.";
    return;
  }
  if (Notification.permission === "denied") {
    estadoAvisos.textContent = "Avisos bloqueados nas configurações do aparelho.";
    return;
  }
  const registro = await navigator.serviceWorker.ready;
  const inscricao = await registro.pushManager.getSubscription();
  estadoAvisos.textContent = inscricao
    ? "Avisos ativados neste aparelho."
    : "Avisos desativados.";
}

async function ativarAvisos() {
  try {
    const permissao = await Notification.requestPermission();
    if (permissao !== "granted") {
      await atualizarEstadoAvisos();
      return;
    }
    const registro = await navigator.serviceWorker.ready;
    const { chave } = await chamar("/api/push/chave");
    const inscricao = await registro.pushManager.subscribe({
      userVisibleOnly: true,
      applicationServerKey: chaveParaBytes(chave),
    });
    await chamar("/api/push/inscrever", {
      method: "POST",
      body: JSON.stringify(inscricao.toJSON()),
    });
    await atualizarEstadoAvisos();
  } catch (erro) {
    estadoAvisos.textContent = "Não deu certo: " + erro.message;
  }
}

async function testarAviso() {
  try {
    await chamar("/api/push/testar", { method: "POST", body: "{}" });
    estadoAvisos.textContent = "Aviso de teste enviado.";
  } catch (erro) {
    estadoAvisos.textContent = "Falha no teste: " + erro.message;
  }
}

document.getElementById("ativar-avisos").addEventListener("click", ativarAvisos);
document.getElementById("testar-avisos").addEventListener("click", testarAviso);

// ---------- Tema (Sistema / Claro / Escuro) ----------
const botoesTema = document.querySelectorAll(".seletor-tema button");
const metaTema = document.querySelector('meta[name="theme-color"]');
const aparelhoEscuro = window.matchMedia("(prefers-color-scheme: dark)");

function aplicarTema(tema) {
  if (tema === "claro" || tema === "escuro") {
    document.documentElement.dataset.tema = tema;
  } else {
    tema = "sistema";
    document.documentElement.removeAttribute("data-tema");
  }
  localStorage.setItem("tema", tema);
  const escuro = tema === "escuro" || (tema === "sistema" && aparelhoEscuro.matches);
  metaTema.setAttribute("content", escuro ? "#201A17" : "#EDE0D4");
  botoesTema.forEach((b) =>
    b.setAttribute("aria-pressed", String(b.dataset.tema === tema))
  );
}

botoesTema.forEach((b) =>
  b.addEventListener("click", () => aplicarTema(b.dataset.tema))
);
aparelhoEscuro.addEventListener("change", () =>
  aplicarTema(localStorage.getItem("tema") || "sistema")
);
aplicarTema(localStorage.getItem("tema") || "sistema");

// ---------- Início ----------
carregarHistorico();

if ("serviceWorker" in navigator) {
  navigator.serviceWorker.register("/sw.js");
}
