const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const vm=require('node:vm');
const ui=path.join(__dirname,'../src/tactics_ui');
function fragment(file,start,end){const text=fs.readFileSync(path.join(ui,file),'utf8');return text.slice(text.indexOf(start),end?text.indexOf(end,text.indexOf(start)):undefined);}
function context(values){return vm.createContext(values);}
test('automatic squad accounts for both shapes, current ability and reserve coverage',()=>{
 const c=context({});
 vm.runInContext(fragment('app.js','const POS_ATTR=','function autoLineup'),c);
 vm.runInContext(fragment('squad-editor.js','const savedPositionKeys=','showSaveLineup=function'),c);
 const positions=['GK','DL','DCL','DR','DCR','DMC','ML','MCL','MR','AMR','ST'];
 const phases=[positions,positions.map((p,i)=>i===1?'WBL':p)]
  .map(shape=>shape.map(position=>({position})));
 const roster=[
  {uid:1,ca:120,positions:{gk:20}},
  {uid:2,ca:85,positions:{gk:18}},
  {uid:3,ca:140,positions:{dl:20,wbl:20,dc:20}},
  {uid:4,ca:110,positions:{dl:18,wbl:18}},
  {uid:5,ca:200,positions:{dl:20,wbl:5}},
  {uid:6,ca:100,positions:{dr:20}},
  {uid:7,ca:125,positions:{dr:20}},
  ...['dc','dm','ml','mc','mr','amr','stc'].map((p,i)=>({uid:8+i,ca:100,positions:{[p]:20}})),
  ...Array.from({length:13},(_,i)=>({uid:30+i,ca:90,positions:{mc:13,dl:14,wbl:14}})),
 ];
 const picks=c.automaticMatchSquad(roster,phases);
 assert.deepEqual([picks.starters[0],picks.starters[1],picks.starters[3]],[1,4,7]);
 assert.deepEqual(new Set([picks.starters[2],picks.starters[4]]),new Set([3,8]));
 assert.equal(picks.substitutes[0],2);
 assert.equal(picks.substitutes.length,12);
 assert.equal(new Set([...picks.starters,...picks.substitutes]).size,23);
 const attributes=Array(15).fill(1);attributes[2]=20;
 assert.equal(c.squadPositionFit({attributes,positions:{dl:8}},'DL'),20);
 const onlyStarters=roster.filter(p=>picks.starters.includes(p.uid));
 assert.deepEqual(Array.from(c.automaticMatchSquad(onlyStarters,phases).substitutes),[]);
});
test('free and save matches share the preset, and only custom requires a valid number',async()=>{
 const controls={
  '#match-importance':{value:'13',disabled:false,checkValidity:()=>true},
  '#match-importance-custom':{value:'',checkValidity:()=>false},
  '#match-importance-custom-label':{},
  '#match-importance-availability':{},
  '#experiment-name':{value:''},
  '#execution-enabled':{checked:false},
 };
 const c=context({
  $:selector=>controls[selector],saveApiPrevious:async(url,data)=>({url,data}),
  saveMode:'free',saveLoaded:{club_uid:1,save_id:'save'},saveClub:1,saveInfo:{id:'save'},
  saveChosen:new Set(['other']),saveOpponents:[{key:'other'}],careerTwoRounds:false,careerRetest:100,
  updateMatchSettingsSummary(){},
 });
 vm.runInContext(fragment('save-mode.js','function updateMatchImportanceAvailability','function updateExecutionAvailability'),c);
 c.updateMatchImportanceAvailability(true);
 assert.equal(controls['#match-importance-custom-label'].hidden,true);
 vm.runInContext(fragment('save-mode.js','api=async function(url,data){','const saveResultsPrevious'),c);
 const input={scenario:{},reference:{}};
 const free=await c.api('/api/run',input);
 assert.equal(free.data.scenario.match_importance,13);
 assert.equal(free.data.reference.match_importance,13);
 assert.equal(input.scenario.match_importance,undefined);
 c.saveMode='save';
 controls['#match-importance'].value='19';
 const save=await c.api('/api/run',input);
 assert.equal(save.url,'/api/save/run');
 assert.equal(save.data.scenario.match_importance,19);
 controls['#match-importance'].value='custom';
 controls['#match-importance'].onchange();
 assert.equal(controls['#match-importance-custom-label'].hidden,false);
 await assert.rejects(c.api('/api/run',input),/1–20/);
 controls['#match-importance-custom'].value='7';
 controls['#match-importance-custom'].checkValidity=()=>true;
 const custom=await c.api('/api/run',input);
 assert.equal(custom.data.scenario.match_importance,7);
 assert.equal(custom.data.reference.match_importance,7);
 c.careerTwoRounds=true;
 const league=await c.api('/api/run',{...input,count:2,
  leagueRun:{two_rounds:false,retest_count:0,opponents:[{key:'different'}]}});
 assert.equal(league.data.count,2);
 assert.equal(league.data.two_rounds,false);
 assert.equal(league.data.opponents[0].key,'different');
 assert.equal(league.data.leagueRun,undefined);
 assert.ok(c.saveChosen.has('other'));
});
test('historical conditions and round labels use the completed experiment',()=>{
 const c=context({});
 vm.runInContext(fragment('save-mode.js','function historicalConditions','const saveResultsPrevious'),c);
 vm.runInContext(fragment('league-testing.js','function careerResultScope'),c);
 assert.equal(c.historicalConditions({match_conditions:{B:{importance:19,manual_execution:false}},runs:[]}),
  '比赛重要性 19 / 20 · 执行力自动');
 assert.equal(c.historicalConditions({runs:[{match_importance:13}]}),'比赛重要性 13 / 20 · 执行力自动');
 const job={test_rounds:[{},{}],round_results:{2:{completed:0}}};
 assert.equal(c.careerResultScope(job),'首轮');
 job.round_results[2].completed=1;
 assert.equal(c.careerResultScope(job),'复测');
 assert.equal(c.careerResultScope(job,true),'两轮合计');
});
test('save leaderboards rank goals and assists independently',()=>{
 const c=context({esc:String,resultPlayerName:p=>p.name});
 vm.runInContext(fragment('match-events.js','function saveLeaderboardTable','const eventDetailPrevious'),c);
 const players=[
  {name:'Forward',team:'Own',scope:'own',source_uid:1,goals:5,assists:1},
  {name:'Playmaker',team:'Own',scope:'own',source_uid:2,goals:2,assists:6},
 ];
 const scorers=c.saveLeaderboardTable(players,'goals',{});
 const assists=c.saveLeaderboardTable(players,'assists',{});
 assert.ok(scorers.indexOf('Forward')<scorers.indexOf('Playmaker'));
 assert.ok(assists.indexOf('Playmaker')<assists.indexOf('Forward'));
});
test('opposition button opens the save opponent picker on a DOM click',async()=>{
 const button={};let opened=0;
 const c=context({view:'opposition',$:s=>s==='[data-oi-choose]'?button:null,$$:()=>[],saveOpponentRequest:0,saveInfo:{id:'save'},saveClub:1,saveMode:'save',api:async()=>({status:'complete',opponents:[]}),showSaveOpponents:()=>opened++,toast:assert.fail});
 vm.runInContext(fragment('save-mode.js','async function discoverSaveOpponents','function showSaveOpponents'),c);
 vm.runInContext(fragment('advanced.js','function bindOpposition','function setPiecesView'),c);
 c.bindOpposition();await button.onclick({type:'click'});assert.equal(opened,1);
});
function team(ids,id='save',club=1){return {name:'Club',players:ids.map(source_uid=>({source_uid,name:String(source_uid)})),lineup:ids.map((_,i)=>i),roster_size:ids.length,roster_source:{id,club_uid:club},opposition:{players:ids.map(()=>({press:0,mark:0,tackle:0,foot:0,personal:false})),positions:{GK:{press:2}}},phases:[[{instructions:{14:34},target_player:0}]]};}
async function loadRoster(ids,id='save',automatic=false){
 const old=team([1,2]),other=team([9,10]);other.opposition.players[0]={press:2,mark:1,tackle:0,foot:0,personal:true};
 const loaded=team(ids,id,2),button={dataset:{loadRoster:'1'}};
 const c=context({state:{teams:[other,old]},saveMode:'free',saveClub:null,saveInfo:null,$$:s=>s==='[data-load-roster]'?[button]:[],$:()=>({value:'2'}),refreshPlayerLabels:async()=>{},save(){},saveModeDraft(){},render(){},toast:assert.fail,showActionError:(_,e)=>assert.fail(e),localStorage:{getItem:()=>null,setItem(){}},api:async url=>url.endsWith('board-clubs')?{id,own:null,opponent:2,clubs:[{uid:2,name:'Club'}]}:loaded});
 vm.runInContext(fragment('desktop-workspace.js','let boardRosterSource'),c);
 vm.runInContext("boardRosterSource={id:'save',clubs:[{uid:2}]};",c);
 if(automatic)await c.initializeBoardRoster();else{c.bindBoardRosterControls();await button.onclick();}
 return {other,loaded};
}
test('replacing a club clears player-specific instructions and missing marking targets',async()=>{
 const {other}=await loadRoster([3,4]);assert.equal(other.opposition.players[0].personal,false);assert.equal(other.opposition.players[0].press,0);assert.equal(other.phases[0][0].target_player,255);assert.equal(other.phases[0][0].instructions[14],0);assert.equal(other.opposition.positions.GK.press,2);
});
test('same-save roster reorder follows player identities and match roster order',async()=>{
 const {other}=await loadRoster([2,1]);assert.equal(other.opposition.players[1].personal,true);assert.equal(other.opposition.players[1].press,2);assert.equal(other.phases[0][0].target_player,1);
});
test('automatic save rebinding clears old-save personal targets even with reused UIDs',async()=>{
 const {other}=await loadRoster([1,2],'another-save',true);assert.equal(other.opposition.players[0].personal,false);assert.equal(other.phases[0][0].target_player,255);
});
function paired(second){
 const c=context({isComparison:()=>true,esc:String,fmt:n=>n.toFixed(2)});
 vm.runInContext(fragment('desktop.js','function pairedMatchTable','const desktopResultsPrevious'),c);
 const job={test_rounds:[{number:1,name:'First round',seeds:[1]},{number:2,name:'Retest',seeds:[2]}],runs:[{variant:'A',seed:1,result:{score:[0,0]}},{variant:'B',seed:1,result:{score:[10,0]}}]};
 if(second)job.runs.push({variant:'A',seed:2,result:{score:[2,0]}},{variant:'B',seed:2,result:{score:[0,0]}});
 return c.pairedMatchTable(job);
}
test('paired result uses independent retest scores once retest starts',()=>{const html=paired(true);assert.match(html,/Retest/);assert.match(html,/<td>2.00<\/td><td>0.00<\/td><td>-2.00<\/td><td>1<\/td>/);});
test('paired result keeps first round before retest starts',()=>{const html=paired(false);assert.match(html,/First round/);assert.match(html,/<td>0.00<\/td><td>10.00<\/td><td>\+10.00<\/td><td>1<\/td>/);});

test('opening a legacy real-player draft preserves edits across repeated initialization',async()=>{
 const own=team([1,2]);delete own.roster_source;own.lineup=[1,0];own.players[0].attributes=[99];
 const initial=structuredClone(own),stored=new Map();let reads=0;
 const c=context({state:{teams:[own,team([8,9])]},saveMode:'free',saveClub:null,saveInfo:null,
  localStorage:{getItem:key=>stored.get(key)||null,setItem:(key,value)=>stored.set(key,value)},
  refreshPlayerLabels:async()=>{},save(){stored.set('draft',JSON.stringify(c.state));},showActionError:(_,e)=>assert.fail(e),
  api:async url=>{if(url.endsWith('board-clubs'))return {id:'save',own:1,opponent:null,clubs:[{uid:1,name:'Club'}]};reads++;return team([3,4]);}});
 vm.runInContext(fragment('desktop-workspace.js','let boardRosterSource'),c);
 await c.initializeBoardRoster();await c.initializeBoardRoster();
 assert.deepEqual(c.state.teams[0],initial);assert.equal(reads,0);assert.equal(stored.has('draft'),false);
});

test('loading a different save clears the loaded teams UID overrides',()=>{
 const own=team([1,2],'old-save'),other=team([9,10],'old-save');
 own.opposition.by_player_uid={'999':{press:2,mark:0,tackle:0,foot:0,personal:true}};
 const c=context({state:{teams:[own,other]}});
 vm.runInContext(fragment('desktop-workspace.js','let boardRosterSource'),c);
 const loaded=structuredClone(own);loaded.roster_source.id='new-save';
 c.replaceBoardRoster(c.state,0,loaded);
 assert.equal(c.state.teams[0].opposition.by_player_uid,undefined);
 assert.equal(c.state.teams[0].opposition.positions.GK.press,2);
});

test('same-save roster reload preserves explicit UID overrides',()=>{
 const own=team([1,2]),other=team([9,10]);
 own.opposition.by_player_uid={'999':{press:2,mark:0,tackle:0,foot:0,personal:true}};
 const c=context({state:{teams:[own,other]}});
 vm.runInContext(fragment('desktop-workspace.js','let boardRosterSource'),c);
 c.replaceBoardRoster(c.state,0,structuredClone(own));
 assert.equal(c.state.teams[0].opposition.by_player_uid['999'].press,2);
});
