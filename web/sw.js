self.addEventListener("install", () => self.skipWaiting());

self.addEventListener("activate", (evento) => {
  evento.waitUntil(self.clients.claim());
});

self.addEventListener("fetch", (evento) => {
  evento.respondWith(fetch(evento.request));
});

self.addEventListener("push", (evento) => {
  let dados = { titulo: "Evy", corpo: "" };
  try {
    dados = evento.data.json();
  } catch (erro) {
    // aviso sem conteúdo legível: usa o padrão
  }
  evento.waitUntil(
    self.registration.showNotification(dados.titulo || "Evy", {
      body: dados.corpo || "",
      icon: "/web/icone-192.png",
    })
  );
});

self.addEventListener("notificationclick", (evento) => {
  evento.notification.close();
  evento.waitUntil(
    self.clients
      .matchAll({ type: "window", includeUncontrolled: true })
      .then((janelas) => {
        for (const janela of janelas) {
          if ("focus" in janela) return janela.focus();
        }
        return self.clients.openWindow("/");
      })
  );
});
