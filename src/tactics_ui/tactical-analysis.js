'use strict';
const tacticalLabNames={role:'角色实验室',team:'球队指令实验室',player:'个人指令实验室'};

function openTacticalLab(){
 const dialog=document.createElement('dialog');
 dialog.className='save-dialog tactical-lab-dialog';
 dialog.setAttribute('aria-labelledby','tactical-lab-title');
 const career=saveMode==='save',saveId=saveInfo?.id,clubId=saveClub;
 if(career&&(!saveLoaded||saveLoaded.save_id!==saveId||saveLoaded.club_uid!==clubId)){
  toast('请先将所选球队载入战术板');return;
 }
 const snapshot=clone(state),sides=editableTeamSides();
 let selected=career?saveOpponents.filter(row=>saveChosen.has(row.key)&&row.available):[];
 dialog.innerHTML=`<h2 id="tactical-lab-title">实验室</h2><div class="segmented tactical-lab-tabs">
 <button type="button" data-attribute-link>属性实验室</button>
 ${Object.entries(tacticalLabNames).map(([kind,label])=>`<button type="button" data-lab-kind="${kind}">${label}</button>`).join('')}</div>
 <form><div class="attribute-options">
 <label>分析球队 ${select(sides.map(id=>({id,label:snapshot.teams[id].name})),sides.includes(side)?side:sides[0],'data-lab-side')}</label>
 <label>阶段 ${select([{id:'0',label:'有球阶段'},{id:'1',label:'无球阶段'},{id:'both',label:'有球与无球'}],String(phase),'data-lab-phase')}</label>
 <label data-lab-slot-wrap>首发位置 <select data-lab-slot></select></label>
 <label data-lab-group-wrap>指令范围 <select data-lab-group></select></label>
 <label data-lab-mark-wrap>指定盯防位置 ${select([{id:0,label:'无需指定'},...catalog.positions.map(p=>({id:p.mask,label:desktopPositionNames[p.id]}))],0,'data-lab-mark')}</label>
 <label data-lab-player-wrap>指定盯防球员 <select data-lab-player></select></label>
 </div>
 ${career?`<button type="button" class="button" data-lab-pick>选择存档对手</button> <span data-lab-opponent-count></span>`:
  `<label>对手范围 ${select([{id:'current',label:'当前固定对手'},{id:'pool',label:'客队战术池全部战术'}],'current','data-lab-opponents')}</label>`}
 <div class="attribute-options">
 <label>探索种子数 <input type="number" data-lab-discovery min="4" max="100" value="8" required></label>
 <label>复测种子数 <input type="number" data-lab-verification min="2" max="200" value="32" required></label>
 </div>
 <div class="tactical-lab-toggles"><label><input type="checkbox" data-lab-both ${career?'checked':''}>主客场各测</label>
 <label><input type="checkbox" data-lab-all>复测全部候选</label></div>
 <p class="tiny muted">默认每组最多复测两个候选。原战术和候选使用同一组对手、主客场及种子。</p>
 <p data-lab-estimate role="status"></p>
 <div class="dialog-actions"><button type="button" class="button" data-lab-close>取消</button>
 <button type="submit" class="button primary" disabled>开始战术实验</button></div></form>`;
 const get=name=>dialog.querySelector('[data-lab-'+name+']'),form=dialog.querySelector('form');
 const submit=form.querySelector('[type=submit]');
 let kind='role',estimateTimer,requestNumber=0,starting=false;
 const phases=()=>get('phase').value==='both'?[0,1]:[Number(get('phase').value)];
 function payload(){
  const selectedSlot=get('slot').value;
  return {scenario:snapshot,kind,side:Number(get('side').value),phases:phases(),
   slots:kind==='team'?[0]:selectedSlot==='all'?Array.from({length:11},(_,i)=>i):[Number(selectedSlot)],
   groups:kind==='role'||get('group').value==='all'?[]:[Number(get('group').value)],mark_position:Number(get('mark').value),
   ...(!get('player-wrap').hidden&&get('player').value!==''?{mark_player:Number(get('player').value)}:{}),
   ...(career?{save_id:saveId,club_uid:clubId,opponents:selected.map(row=>row.key)}:{opponents:get('opponents').value}),
   seed_mode:$('#seed-mode').value,first_seed:Number($('#seed').value),workers:Number($('#workers').value),
   exploration_count:Number(get('discovery').value),validation_count:Number(get('verification').value),
   home_away:get('both').checked,validate_all:get('all').checked};
 }
 function estimate(){
  clearTimeout(estimateTimer);
  const current=++requestNumber;
  submit.disabled=true;
  if(!dialog.open||starting||!form.checkValidity())return;
  if(career&&!selected.length){get('estimate').textContent='请选择存档对手';return;}
  get('estimate').textContent='正在计算场次数';
  estimateTimer=setTimeout(async()=>{
   try{
    const result=await api('/api/tactical-screen/estimate',payload());
    if(current!==requestNumber||!dialog.open)return;
    get('estimate').textContent=`${result.candidates} 个候选 · 探索 ${result.exploration} 场 · 复测最多 ${result.validation} 场`;
    submit.disabled=false;
   }catch(error){
    if(current===requestNumber&&dialog.open)get('estimate').textContent=error.message;
   }
  },160);
 }
 function redraw(){
  const s=Number(get('side').value),team=snapshot.teams[s],p=phases()[0];
  const previous=get('slot').value||String(slot);
  get('slot').innerHTML=`<option value="all">全队 11 个位置</option>`+team.phases[p].map((cell,i)=>
   `<option value="${i}">${esc(desktopPositionNames[cell.position])} · ${esc(displayName(team.players[team.lineup[i]]))}</option>`).join('');
  get('slot').value=previous;
  get('slot-wrap').hidden=kind==='team';
  get('group-wrap').hidden=kind==='role';
  const group=get('group').value;
  const groups=kind==='team'?catalog.team_instructions:catalog.player_instructions;
  get('group').innerHTML='<option value="all">全部指令</option>'+groups.filter(g=>phases().includes(kind==='team'?g.possession_phase:g.phase))
   .map(g=>`<option value="${g.id}">${esc(g.label)}</option>`).join('');
  if([...get('group').options].some(o=>o.value===group))get('group').value=group;
  get('mark-wrap').hidden=kind!=='player'||!phases().includes(1);
  get('player-wrap').hidden=get('mark-wrap').hidden||career||get('opponents')?.value==='pool';
  const opponent=snapshot.teams[1-s],player=get('player').value;
  const order=opponent.lineup.concat(opponent.players.slice(0,opponent.roster_size).map((_,i)=>i).filter(i=>!opponent.lineup.includes(i)));
  get('player').innerHTML='<option value="">无需指定</option>'+order.map((index,i)=>`<option value="${i}">${esc(displayName(opponent.players[index]))}</option>`).join('');
  if([...get('player').options].some(o=>o.value===player))get('player').value=player;
  dialog.querySelectorAll('[data-lab-kind]').forEach(b=>b.classList.toggle('active',b.dataset.labKind===kind));
  estimate();
 }
 form.oninput=event=>{if([get('side'),get('phase'),get('opponents')].includes(event.target))redraw();else estimate();};
 dialog.querySelectorAll('[data-lab-kind]').forEach(b=>b.onclick=()=>{kind=b.dataset.labKind;redraw();});
 dialog.querySelector('[data-attribute-link]').onclick=()=>{dialog.close();openAttributeScreen();};
 if(career){
  const showCount=()=>get('opponent-count').textContent=`已选 ${selected.length} 队`;
  showCount();
  get('pick').onclick=async()=>{
   try{
    get('pick').disabled=true;
    let report;
    do{
     report=await api('/api/save/opponents',{id:saveId,club_uid:clubId});
     if(!dialog.open||saveInfo?.id!==saveId||saveClub!==clubId)return;
     if(report.status==='error')throw Error(report.stage);
     if(report.status==='reading'){
      get('estimate').textContent=report.stage||'正在读取存档对手';
      await new Promise(resolve=>setTimeout(resolve,1200));
     }
    }while(report.status==='reading');
    showSaveOpponents(report,{initial:new Set(selected.map(row=>row.key)),scope:'all',onAccept:keys=>{
     selected=report.opponents.filter(row=>row.available&&keys.has(row.key));showCount();estimate();
    }});
   }catch(error){get('estimate').textContent=error.message;}
   finally{get('pick').disabled=false;}
  };
 }
 form.onsubmit=async event=>{
  event.preventDefault();
  if(submit.disabled||career&&(saveInfo?.id!==saveId||saveClub!==clubId))return;
  starting=true;submit.disabled=true;
  try{
   const response=await api('/api/run-tactical-screen',payload());
   dialog.close();activeJob=response.id;polledJob=selectedJob=null;view='results';await poll();
  }catch(error){get('estimate').textContent=error.message;submit.disabled=false;starting=false;}
 };
 get('close').onclick=()=>dialog.close();
 dialog.onclose=()=>{clearTimeout(estimateTimer);dialog.remove();};
 document.body.append(dialog);dialog.showModal();redraw();
}

function tacticalReport(job){
 const format=(value,decimals=2)=>value==null?'—':value.toFixed(decimals);
 const percent=value=>value==null?'—':format(value*100,1)+'%';
 const delta=(value,scale=1)=>value==null?'—':(value>0?'+':'')+format(value*scale,scale===100?1:2);
 const rows=(job.tactical_report||[]).slice().sort((a,b)=>
  a.phase-b.phase||(a.slot??-1)-(b.slot??-1)||a.group.localeCompare(b.group)||
  (b.validation.pairs>0)-(a.validation.pairs>0)||
  (b.validation.win_rate??b.exploration.win_rate??-1)-(a.validation.win_rate??a.exploration.win_rate??-1));
 const cells=(row,sample)=>{
  const total=job.tactical_screen[sample+'_seeds'].length;
  const metric=row[sample];
  const uncertain=metric.win_error==null||Math.abs(metric.win_delta)<=metric.win_error;
  return `<td>${metric.pairs?percent(metric.win_rate):'—'}<small>${metric.pairs?metric.pairs+' 对 · '+metric.seeds+'/'+total+' 种子':''}</small></td>
  <td>${delta(metric.win_delta,100)}${metric.win_delta==null?'':' pp'}<small>${metric.pairs?'原方案 '+percent(metric.baseline_win_rate):''}</small><small>${metric.pairs&&uncertain?'差异未明':''}</small></td>
  <td>${format(metric.points)}</td><td>${delta(metric.xg_delta)}</td>`;
 };
 return `<section class="card match-statistics tactical-lab-results"><div class="card-head"><h3>${tacticalLabNames[job.tactical_screen.kind]}</h3></div>
 <div class="card-body"><p>${job.completed} / ${job.total} 场</p><div class="table-scroll"><table>
 <thead><tr><th rowspan="2">位置与选项</th><th colspan="4">探索</th><th colspan="4">独立复测</th></tr>
 <tr>${'<th>胜率</th><th>胜率变化</th><th>场均积分</th><th>净 xG 变化</th>'.repeat(2)}</tr></thead>
 <tbody>${rows.map(row=>`<tr><td><small>${row.phase?'无球':'有球'}${row.position?' · '+esc(desktopPositionNames[row.position]):''}
 ${row.player?` · <span translate="no">${esc(row.player)}</span>`:''}</small><b>${esc(row.slot===null||job.tactical_screen.kind==='player'?row.group+' · ':'')}${esc(row.option)}</b>
 ${row.baseline_option?`<small>原方案 · ${esc(row.baseline_option)}</small>`:''}
 ${row.adjustments.length?`<small>恢复角色预设 · ${row.adjustments.map(esc).join('、')}</small>`:''}</td>
 ${cells(row,'exploration')}${cells(row,'validation')}</tr>`).join('')}</tbody></table></div></div></section>`;
}

const tacticalResultsPrevious=resultsView;
resultsView=function(){
 const html=tacticalResultsPrevious();
 return selectedJob?.tactical_screen?tacticalReport(selectedJob)+html:html;
};
const tacticalBindPrevious=bind;
bind=function(){
 tacticalBindPrevious();
 const button=$('#run-attribute-screen');
 if(button){if(button.textContent!=='实验室')button.textContent='实验室';button.onclick=openTacticalLab;}
};
