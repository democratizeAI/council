
const m = document.getElementById('app');
const state = { msgs: [] };

function render() {
  m.innerHTML = `
  <div class="flex-grow overflow-auto p-4">${state.msgs.map(msg => `
    <div class="mb-2">
      <div class="font-bold">You:</div><div>${msg.q}</div>
      <div class="font-bold">Council:</div><div>${msg.a}</div>
      <div class="text-xs text-gray-500">${msg.ms} ms • $${msg.$}</div>
    </div>`).join('')}</div>
  <div class="border-t p-2 flex">
    <input id="inp" class="flex-grow border rounded p-2" placeholder="Ask anything…"/>
    <button id="send" class="ml-2 bg-blue-500 text-white px-3 rounded">Send</button>
  </div>`;
  document.getElementById('send').onclick = async () => {
    const text = document.getElementById('inp').value;
    if (!text) return;
    const t0 = performance.now();
    const res = await fetch('/vote', {
      method: 'POST',
      headers: {'Content-Type':'application/json'},
      body: JSON.stringify({prompt: text})
    });
    const j = await res.json();
    state.msgs.push({q: text, a: j.answer, ms: j.meta.latency_ms, $: j.meta.cost_usd});
    render();
  };
}
render();
