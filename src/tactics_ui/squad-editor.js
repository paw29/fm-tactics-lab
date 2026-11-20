'use strict';
let squadPlayer=0;
function syncSquadFromMatch(t){
 if(!t.squad)return;
 const byId=new Map(t.squad.map(p=>[p.source_uid,p]));
 for(const p of t.players.slice(0,t.roster_size)){
  const target=byId.get(p.source_uid);if(!target)continue;
  for(const key of ['name','attributes','native_profile'])target[key]=clone(p[key]);
 }
}
function syncMatchFromSquad(t){
 if(!t.squad)return;
 const byId=new Map(t.squad.map(p=>[p.source_uid,p]));
 for(const p of t.players.slice(0,t.roster_size)){
  const source=byId.get(p.source_uid);if(!source)continue;
  for(const key of ['name','attributes','native_profile'])p[key]=clone(source[key]);
 }
}
const squadSavePrevious=save;
save=function(){state?.teams?.forEach(syncSquadFromMatch);return squadSavePrevious();};
function squadStatus(p,t=team()){
 const index=t.players.findIndex(q=>q.source_uid===p.source_uid);
 if(index<0||index>=t.roster_size)return '未入选比赛名单';
 const slot=t.lineup.indexOf(index);
 return slot<0?'替补':`首发 · 有球 ${desktopPositionNames[t.phases[0][slot].position]} ／ 无球 ${desktopPositionNames[t.phases[1][slot].position]}`;
}
const squadToolbarPrevious=toolbar;
toolbar=function(){let html=squadToolbarPrevious();if(team().squad)html=html.replace(`${team().players.length} 人名单`,`一线队 ${team().squad.length} 人 · 本场 ${team().roster_size} / 23 人`);return html;};
const squadTacticsPrevious=tacticsView;
tacticsView=function(){
 const html=squadTacticsPrevious(),t=team();if(!t.squad)return html;
 const starters=new Set(t.lineup),bench=t.players.map((p,i)=>({p,i})).filter(({i})=>i<t.roster_size&&!starters.has(i));
 const panel=`<section class="bench-panel" aria-label="本场替补名单"><div class="bench-panel-heading"><div><h3>本场替补 <span class="tag">${bench.length} / 12</span></h3><p class="tiny muted">本场 ${t.roster_size} / 23 人 · 一线队另有 ${t.squad.length-t.roster_size} 人未入选</p></div><button class="button small" id="board-match-squad">调整比赛名单</button></div><div class="bench-player-list">${bench.map(({p,i},j)=>`<button class="bench-player" data-bench-player="${i}" title="查看${esc(displayName(p))}的属性"><span class="tag">替补 · ${kitNumber(p,i)}</span><b>${esc(displayName(p))}</b><small>查看属性 ↗</small></button>`).join('')||'<p class="tiny muted bench-empty">尚未选择替补，可通过“调整比赛名单”添加。</p>'}</div></section>`;
 return html.replace('</div></section><section class="instruction-panel">','</div>'+panel+'</section><section class="instruction-panel">');
};
const squadPlayersPrevious=playersView;
playersView=function(){
 const t=team();if(!t.squad)return squadPlayersPrevious();
 syncSquadFromMatch(t);squadPlayer=Math.min(squadPlayer,Math.max(0,t.squad.length-1));
 const p=t.squad[squadPlayer];
 const fragment=document.createElement('div');fragment.innerHTML=squadPlayersPrevious();
 const bulk=fragment.querySelector('.team-bulk-controls')?.outerHTML||'';
 return `${toolbar()}<div class="player-layout"><aside class="card player-list"><div style="padding:12px"><b>完整一线队 · ${t.squad.length}人</b><p class="tiny muted">未入选球员保留在这里，不参与模拟。</p><button class="button small" id="squad-selection">排首发／选替补</button></div>${t.squad.map((p,i)=>`<button data-squad-player="${i}" class="player-item ${i===squadPlayer?'active':''}"><span class="number">${kitNumber(p,i)}</span><span>${esc(displayName(p))}<small>${esc(squadStatus(p,t))}</small></span></button>`).join('')}</aside><section class="card"><div class="card-body">${bulk}<h2>${esc(displayName(p))}</h2><p class="tiny muted">${esc(squadStatus(p,t))} · CA ${p.native_profile?.current_ability??'未知'} · 所有属性可编辑，未入选球员的修改不会进入本场模拟。</p><label>姓名 <input id="squad-name" maxlength="48" value="${esc(displayName(p))}"></label><label class="raw-toggle"><input id="raw" type="checkbox" ${raw?'checked':''}>内部原值</label><div class="squad-attributes">${catalog.attributes.map(a=>`<label>${esc(a.label)}<input type="number" data-squad-attribute="${a.id}" value="${a.id<15||raw?p.attributes[a.id]:p.attributes[a.id]/5}" min="0" max="${a.id<15||!raw?20:100}" step="${a.id<15||raw?1:0.2}"></label>`).join('')}</div><button class="button small" id="squad-attribute-reset">恢复该球员导入属性</button></div></section></div>`;
};

const savedPositionKeys=['gk','sw','dl','dc','dr','dm','ml','mc','mr','aml','amc','amr','stc','wbl','wbr'];
function squadPositionFit(person,position){
 const index=POS_ATTR[position];
 return person.attributes?.[index]??person.positions?.[savedPositionKeys[index]]??0;
}

function automaticMatchSquad(roster,formations){
 const positionsBySlot=formations[0].map((cell,i)=>[cell.position,formations[1][i].position]);
 const keeperSlot=positionsBySlot.findIndex(pair=>pair[0]==='GK');
 const keeperPriority=1000*(positionsBySlot.length+1);
 const candidates=roster.map(person=>{
  const ability=person.native_profile?.current_ability??person.ca??0;
  const fits=positionsBySlot.map(pair=>pair.map(position=>squadPositionFit(person,position)));
  const coverage=fits.map(pair=>Math.min(...pair)>=12);
  const scores=fits.map(([ip,oop])=>(3*Math.min(ip,oop)+Math.max(ip,oop))*10+ability);
  return {uid:person.uid,coverage,scores};
 });
 // The bitmask records occupied slots. Descending masks ensure a player is used
 // only once. Assign the whole XI together so specialists keep their best slots.
 const full=(1<<positionsBySlot.length)-1, best=Array(full+1).fill(null);
 best[0]={score:0};
 for(const person of candidates){
  for(let mask=full-1;mask>=0;mask--){
   const previous=best[mask];
   if(!previous)continue;
   for(let slot=0;slot<positionsBySlot.length;slot++){
    const next=mask|(1<<slot);
    if(next===mask)continue;
    const keeperBonus=slot===keeperSlot&&person.coverage[slot]?keeperPriority:0;
    const score=previous.score+person.scores[slot]+keeperBonus;
    if(!best[next]||score>best[next].score)best[next]={score,previous,slot,uid:person.uid};
   }
  }
 }
 const starters=Array(positionsBySlot.length);
 for(let chosen=best[full];chosen.previous;chosen=chosen.previous)starters[chosen.slot]=chosen.uid;

 const remaining=candidates.filter(person=>!starters.includes(person.uid));
 const substitutes=[],covered=new Set();
 function addReserve(person){
  substitutes.push(person.uid);
  person.coverage.forEach((fits,slot)=>{if(fits)covered.add(slot);});
  remaining.splice(remaining.indexOf(person),1);
 }
 function bestReserve(score){
  return remaining.reduce((best,person)=>!best||score(person)>score(best)?person:best,null);
 }
 const keeper=bestReserve(person=>person.coverage[keeperSlot]?person.scores[keeperSlot]:-1);
 if(keeper?.coverage[keeperSlot])addReserve(keeper);
 while(remaining.length&&substitutes.length<12){
  addReserve(bestReserve(person=>{
   const uncovered=person.coverage.filter((fits,slot)=>slot!==keeperSlot&&fits&&!covered.has(slot)).length;
   const bestFit=Math.max(...person.scores.filter((_,slot)=>slot!==keeperSlot));
   return uncovered*1000+bestFit;
  }));
 }
 return {starters,substitutes};
}

showSaveLineup=function(){
 const t=state.teams[0],loaded=!!saveLoaded&&saveLoaded.save_id===saveInfo?.id&&saveLoaded.club_uid===saveClub&&!!t.squad;
 if(!saveRoster)return;
 if(loaded)syncSquadFromMatch(t);
 const roster=loaded?t.squad.map(p=>({...p,uid:p.source_uid})):saveRoster.players;
 const people=new Map(roster.map(p=>[p.uid,p]));
 const picks=(loaded?t.lineup.map(i=>t.players[i].source_uid):saveRoster.picks).slice();
 const bench=(loaded?t.players.slice(0,t.roster_size).filter((_,i)=>!t.lineup.includes(i)).map(p=>p.source_uid):saveRoster.bench||[]).slice();
 const id=saveInfo?.id,club=saveClub;
 let active=picks.indexOf(null),pickingBench=false,stage=phase,edited=false,suggesting=false;
 let suggestion=null;
 if(active<0)active=0;
 let formations=loaded?t.phases:null;
 const dialog=document.createElement('dialog');dialog.className='save-dialog match-squad-dialog';
 dialog.innerHTML=`<div class="match-squad-head"><div><h2>比赛名单</h2><p data-squad-status aria-live="polite"></p></div>
 <div class="match-squad-actions"><button type="button" class="button" data-restore-squad>恢复存档名单</button>
 <button type="button" class="button" data-auto-squad title="按有球和无球的位置熟练度及当前能力选择首发和替补">自动挑选</button></div></div>
 <div class="match-squad-layout"><section>
 <div class="segmented" data-squad-phases hidden><button type="button" data-squad-phase="0">有球阶段</button><button type="button" data-squad-phase="1">无球阶段</button></div>
 <div data-squad-pitch></div>
 <div class="match-squad-bench"><button type="button" class="button small" data-pick-bench>编辑替补</button><span data-bench-count></span><div data-bench-players></div></div>
 </section><section><h3>一线队</h3><div class="match-squad-filters"><input type="search" placeholder="搜索球员" aria-label="搜索球员" data-squad-search>
 <label><input type="checkbox" data-squad-fit>只看熟悉该位置的球员</label></div>
 <p class="tiny muted" data-squad-context></p><div class="match-squad-players" data-squad-players></div>
 </section></div><div class="dialog-actions"><button type="button" class="button" data-close>取消</button><button type="button" class="button primary" data-apply>应用比赛名单</button></div>`;
 const get=name=>dialog.querySelector(`[data-${name}]`);
 const playerName=uid=>people.has(uid)?displayName(people.get(uid)):'请选择球员';
 const familiarity=p=>squadPositionFit(p,formations?.[stage][active]?.position);
 function drawPlayers(){
  const query=get('squad-search').value.trim().toLocaleLowerCase();
  get('squad-fit').disabled=!formations||pickingBench;
  const filtered=roster.filter(p=>!query||(p.name+' '+displayName(p)).toLocaleLowerCase().includes(query))
   .filter(p=>get('squad-fit').disabled||!get('squad-fit').checked||familiarity(p)>=12);
  if(formations&&!pickingBench)filtered.sort((a,b)=>familiarity(b)-familiarity(a));
  get('squad-players').innerHTML=filtered.map(p=>{
   const status=picks.includes(p.uid)?'首发':bench.includes(p.uid)?'替补':'';
   return `<button type="button" data-pick-player="${p.uid}" ${pickingBench&&picks.includes(p.uid)?'disabled':''}><span>${kitNumber(p)}</span><b translate="no">${esc(displayName(p))}</b><small>${status}${formations&&!pickingBench?` · ${familiarity(p)}/20`:''}</small></button>`;
  }).join('')||'<p class="muted">没有匹配的球员</p>';
 }
 function draw(){
  const count=picks.filter(uid=>people.has(uid)).length;
  const exactStarts=picks.every((uid,i)=>uid===saveRoster.savedPicks?.[i]);
  const exactBench=JSON.stringify(bench)===JSON.stringify(saveRoster.savedBench||[]);
  const source=count!==11?'名单有空位':suggestion==='auto'?'已自动挑选':exactStarts&&exactBench?'沿用存档名单':
   suggestion==='restore'?'已补齐空位':edited||saveRoster.manualSelection?'已编辑':'';
  get('squad-status').textContent=`${count}/11 首发 · ${bench.length}/12 替补${source?' · '+source:''}`;
  get('pick-bench').setAttribute('aria-pressed',String(pickingBench));
  get('apply').disabled=suggesting||count!==11||new Set(picks).size!==11;
  get('auto-squad').disabled=suggesting||people.size<11;
  get('restore-squad').disabled=suggesting;
  get('squad-phases').hidden=!formations;
  dialog.querySelectorAll('[data-squad-phase]').forEach(b=>b.classList.toggle('active',Number(b.dataset.squadPhase)===stage));
  const buttons=picks.map((uid,index)=>{
   const position=formations?.[stage][index].position,point=positions()[position];
   const label=position?desktopPositionNames[position]:`首发 ${index+1}`;
   return `<button type="button" data-pick-slot="${index}" class="${point?'pitch-slot':''} ${!pickingBench&&active===index?'selected':''}" ${point?`style="left:${point.x}%;top:${point.y}%"`:''}><small>${esc(label)}</small><b translate="no">${esc(playerName(uid))}</b></button>`;
  }).join('');
  get('squad-pitch').innerHTML=formations?`<div class="pitch match-squad-pitch"><div class="pitch-lines"><div class="halfway"></div><div class="centre-circle"></div><div class="box top"></div><div class="box bottom"></div></div>${buttons}</div>`:`<div class="match-squad-unplaced">${buttons}</div>`;
  get('bench-players').innerHTML=bench.map(uid=>`<button type="button" class="button small" data-bench-player="${uid}" translate="no">${esc(playerName(uid))}</button>`).join('');
  get('bench-count').textContent=`${bench.length}/12`;
  const position=formations?.[stage][active].position;
  get('squad-context').textContent=pickingBench?'点击球员加入或移出替补席':(position?desktopPositionNames[position]:`首发 ${active+1}`)+' · 选择球员';
  drawPlayers();
 }
 function choose(uid){
  if(pickingBench){
   const index=bench.indexOf(uid);
   if(index>=0)bench.splice(index,1);
   else if(picks.includes(uid))return;
   else if(bench.length<12)bench.push(uid);
   else{toast('最多选择12名替补');return;}
  }else{
   const other=picks.indexOf(uid),displaced=picks[active],reserve=bench.indexOf(uid);
   if(other===active)return;
   if(other>=0)picks[other]=displaced;
   if(reserve>=0)bench.splice(reserve,1,...(displaced==null?[]:[displaced]));
   picks[active]=uid;
   const empty=picks.indexOf(null);
   if(empty>=0)active=empty;
  }
  edited=true;suggestion=null;draw();
 }
 dialog.addEventListener('click',event=>{
  const b=event.target.closest('button');
  if(!b||suggesting)return;
  if(b.hasAttribute('data-pick-slot')){active=Number(b.dataset.pickSlot);pickingBench=false;draw();}
  else if(b.hasAttribute('data-squad-phase')){stage=Number(b.dataset.squadPhase);draw();}
  else if(b.hasAttribute('data-pick-player'))choose(Number(b.dataset.pickPlayer));
  else if(b.hasAttribute('data-pick-bench')){pickingBench=!pickingBench;draw();}
  else if(b.hasAttribute('data-bench-player')){pickingBench=true;choose(Number(b.dataset.benchPlayer));}
 });
 get('squad-search').oninput=drawPlayers;
 get('squad-fit').onchange=drawPlayers;
 async function suggestSelection(mode){
  if(suggesting)return;
  suggesting=true;draw();
  try{
   let original;
   if(mode==='restore'||!formations){
    const choice=loaded?saveLoaded.tactic_index:$('#career-tactic')?.value;
    if(choice==null||choice==='')throw Error('请先选择存档战术');
    const value=await api('/api/save/load',{id,club_uid:club,tactic_index:choice==='board'?'board':Number(choice),
     lineup:null,bench:null,scenario:state});
    if(!dialog.open||saveInfo?.id!==id||saveClub!==club)return;
    original=value.scenario.teams[0];
    formations??=original.phases;
   }
   const selection=mode==='auto'?automaticMatchSquad([...people.values()],formations):{
    starters:original.lineup.map(i=>original.players[i].source_uid),
    substitutes:original.players.slice(0,original.roster_size).filter((_,i)=>!original.lineup.includes(i)).map(p=>p.source_uid),
   };
   picks.splice(0,11,...selection.starters);
   bench.splice(0,bench.length,...selection.substitutes);
   edited=true;suggestion=mode;pickingBench=false;
  }catch(e){toast(e.message);}
  finally{suggesting=false;if(dialog.open)draw();}
 }
 get('auto-squad').onclick=()=>suggestSelection('auto');
 get('restore-squad').onclick=()=>suggestSelection('restore');
 get('close').onclick=()=>dialog.close();
 get('apply').onclick=async()=>{
  try{
   if(loaded){
    const result=await api('/api/save/selection',{scenario:state,lineup:picks,bench});
    if(!dialog.open||saveInfo?.id!==id||saveClub!==club)return;
    state=result.scenario;side=slot=player=0;save();render();
   }
   saveRoster.picks=picks.slice();saveRoster.bench=bench.slice();saveRoster.manualSelection=true;
   dialog.close();drawSaveMode();
  }catch(e){toast(e.message);}
 };
 dialog.onclose=()=>dialog.remove();document.body.append(dialog);draw();dialog.showModal();
};
const squadBindPrevious=bind;
bind=function(){squadBindPrevious();
 if($('#board-match-squad'))$('#board-match-squad').onclick=showSaveLineup;
 $$('[data-bench-player]').forEach(b=>b.onclick=()=>{const index=+b.dataset.benchPlayer;player=index;squadPlayer=team().squad.findIndex(p=>p.source_uid===team().players[index].source_uid);view='players';render();});
 $$('[data-squad-player]').forEach(b=>b.onclick=()=>{squadPlayer=+b.dataset.squadPlayer;render();});
 $$('[data-squad-attribute]').forEach(input=>input.onchange=()=>{const a=+input.dataset.squadAttribute,v=Number(input.value),value=a<15||raw?v:Math.round(v*5);if(!Number.isFinite(value)||!Number.isInteger(value)||value<0||value>(a<15?20:100)){toast('属性超出范围');render();return;}team().squad[squadPlayer].attributes[a]=value;syncMatchFromSquad(team());save();});
 if($('#squad-selection'))$('#squad-selection').onclick=showSaveLineup;
 if($('#squad-name'))$('#squad-name').onchange=e=>{team().squad[squadPlayer].name=e.target.value.slice(0,48);syncMatchFromSquad(team());save();render();};
 if($('#squad-attribute-reset'))$('#squad-attribute-reset').onclick=()=>{const p=team().squad[squadPlayer];p.attributes=clone(p.initial_attributes);syncMatchFromSquad(team());save();render();};
};
