/* Accessible SVG charts. All visible labels are escaped; tables expose exact values. */
export function chartView({rows,series=[{key:'count',label:'Nombre'}],type='columns',esc,format=x=>new Intl.NumberFormat('fr-FR',{maximumFractionDigits:1}).format(x)}){
 const colors=['#246c63','#b37c23','#4b7192','#9b5877','#74834c'];
 const legend=`<div class="chart-legend">${series.map((s,i)=>`<span><i style="background:${colors[i%colors.length]}"></i>${esc(s.label)}</span>`).join('')}</div>`;
 const table=`<div class="table-wrap"><table><thead><tr><th>Libellé</th>${series.map(s=>`<th>${esc(s.label)}</th>`).join('')}</tr></thead><tbody>${rows.map(r=>`<tr><td>${esc(r.label)}</td>${series.map(s=>`<td>${r[s.key]==null?'':esc(format(Number(r[s.key])))}</td>`).join('')}</tr>`).join('')}</tbody></table></div>`;
 if(!rows.length)return '<p class="chart-empty">Aucune observation dans ce périmètre.</p>';
 if(type==='table')return table;
 const max=Math.max(1,...rows.flatMap(r=>series.map(s=>Number(r[s.key]||0))));
 let content='',height=300,width=760;
 if(type==='bars'){
  height=Math.max(220,rows.length*54+35);
  rows.forEach((r,i)=>{const y=i*54+30;content+=`<text x="0" y="${y-8}" class="chart-label">${esc(r.label)}</text>`;series.forEach((s,j)=>{const v=Number(r[s.key]||0),w=v/max*570;content+=`<rect x="0" y="${y+j*12}" width="${w}" height="9" rx="3" fill="${colors[j%colors.length]}"><title>${esc(r.label)} / ${esc(s.label)} : ${esc(format(v))}</title></rect><text x="${Math.min(w+8,690)}" y="${y+j*12+9}" class="chart-value">${esc(format(v))}</text>`;});});
 }else if(type==='donut'&&series.length===1){
  const total=rows.reduce((a,r)=>a+Number(r[series[0].key]||0),0);let acc=0;
  rows.forEach((r,i)=>{const v=Number(r[series[0].key]||0),pct=total?v/total*100:0;content+=`<circle cx="200" cy="140" r="90" fill="none" stroke="${colors[i%colors.length]}" stroke-width="35" pathLength="100" stroke-dasharray="${pct} ${100-pct}" stroke-dashoffset="${-acc}" transform="rotate(-90 200 140)"><title>${esc(r.label)} : ${esc(format(v))}</title></circle><rect x="355" y="${30+i*28}" width="10" height="10" fill="${colors[i%colors.length]}"/><text x="375" y="${40+i*28}" class="chart-label">${esc(r.label)} (${esc(format(v))})</text>`;acc+=pct;});
  content+=`<text x="200" y="145" text-anchor="middle" class="chart-total">${esc(format(total))}</text>`;height=Math.max(300,rows.length*28+55);
 }else{
  const bottom=235,left=65,span=650,step=span/Math.max(rows.length,1),plot=190;
  for(let i=0;i<=4;i++){const y=bottom-i*plot/4;content+=`<line x1="${left}" y1="${y}" x2="735" y2="${y}" stroke="#dfe8e5"/><text x="55" y="${y+4}" text-anchor="end" class="chart-tick">${esc(format(max*i/4))}</text>`;}
  rows.forEach((r,i)=>{const x=left+(i+.5)*step;if(rows.length<=12||i%Math.ceil(rows.length/10)===0||i===rows.length-1)content+=`<text x="${x}" y="260" text-anchor="middle" class="chart-tick">${esc(r.label.length>17?r.label.slice(0,15)+'…':r.label)}</text>`;});
  series.forEach((s,j)=>{
   if(type==='line'){
    const pts=rows.map((r,i)=>`${left+(i+.5)*step},${bottom-Number(r[s.key]||0)/max*plot}`).join(' ');
    content+=`<polyline points="${pts}" fill="none" stroke="${colors[j%colors.length]}" stroke-width="3" ${j?'stroke-dasharray="7 4"':''}/>`;
    rows.forEach((r,i)=>{const v=Number(r[s.key]||0);content+=`<circle cx="${left+(i+.5)*step}" cy="${bottom-v/max*plot}" r="4" fill="${colors[j%colors.length]}"><title>${esc(r.label)} / ${esc(s.label)} : ${esc(format(v))}</title></circle>`;});
   }else rows.forEach((r,i)=>{const v=Number(r[s.key]||0),h=v/max*plot,w=Math.max(2,Math.min(36,step*.7/series.length));content+=`<rect x="${left+(i+.5)*step+(j-series.length/2)*w}" y="${bottom-h}" width="${w-1}" height="${h}" rx="2" fill="${colors[j%colors.length]}"><title>${esc(r.label)} / ${esc(s.label)} : ${esc(format(v))}</title></rect>`;});
  });
 }
 return `${legend}<div class="chart-canvas"><svg viewBox="0 0 ${width} ${height}" role="img" aria-label="${esc(series.map(s=>s.label).join(', '))}. Valeurs exactes dans le tableau associé.">${content}</svg></div><details class="chart-data"><summary>Voir les valeurs exactes</summary>${table}</details>`;
}
