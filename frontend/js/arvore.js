// Visualizador: apenas DESENHA a árvore recebida do backend (nenhuma AVL é reimplementada aqui).
function desenharArvore(root,box,onSel){
  if(!root){box.innerHTML='<div class="empty">Árvore vazia ou dados indisponíveis (N/D).</div>';return}
  const W=110,V=90,pos=[];let i=0;
  (function walk(n,d){if(!n)return;walk(n.l,d+1);n.x=i++*W+60;n.y=d*V+40;n.d=d;pos.push(n);walk(n.r,d+1)})(root,0);
  const w=i*W+60,h=(Math.max(...pos.map(p=>p.d))+1)*V+50;let e='',nd='';
  pos.forEach(n=>{[n.l,n.r].forEach(c=>{if(c)e+=`<path class="edge" d="M${n.x} ${n.y+25}C${n.x} ${(n.y+c.y)/2+25},${c.x} ${(n.y+c.y)/2},${c.x} ${c.y-25}"/>`});
    const f=FB(n),cl=Math.abs(f)>1?'bad':Math.abs(f)===1?'warn':'';
    nd+=`<g class="nd ${cl}" data-i="${pos.indexOf(n)}"><rect x="${n.x-46}" y="${n.y-25}" width="92" height="56" rx="8"/><text class="t" x="${n.x}" y="${n.y-8}" text-anchor="middle">${esc(n.tag)}</text><text x="${n.x}" y="${n.y+7}" text-anchor="middle">H:${n.h??'N/D'} FB:${f}</text><text x="${n.x}" y="${n.y+22}" text-anchor="middle">Uso:${n.uso??'N/D'}</text></g>`});
  box.innerHTML=`<svg class="ic0" width="${w}" height="${h}" viewBox="0 0 ${w} ${h}" style="min-width:${w}px;transform-origin:top center">${e}${nd}</svg>`;
  const tip=document.getElementById('tip');
  box.querySelectorAll('.nd').forEach(g=>{const n=pos[+g.dataset.i];
    g.onmousemove=ev=>{tip.style.display='block';tip.style.left=ev.clientX+14+'px';tip.style.top=ev.clientY+14+'px';tip.innerHTML=`<b>${esc(n.tag)}</b><br>Altura: ${n.h??'N/D'}<br>FB: ${FB(n)}<br>Uso: ${n.uso??'N/D'}`};
    g.onmouseleave=()=>tip.style.display='none';
    g.onclick=()=>{box.querySelectorAll('.sel').forEach(x=>x.classList.remove('sel'));g.classList.add('sel');onSel(n)}});
  return pos}
