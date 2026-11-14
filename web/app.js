'use strict';
const $ = id => document.getElementById(id);
const words = {
  enter:['Enter Existing Project','進入現有專案'], create:['Create New Project','建立新專案'],
  back:['← Projects','← 專案首頁'], code:['Project code','專案代碼'], format:['8–32 letters, digits or hyphens.','請輸入 8 至 32 個英文字母、數字或連字號。'],
  generate:['Generate a random code','隨機產生代碼'],sharing:['Anyone with this code can join and edit the plan.','知道代碼的人都能加入並編輯行程。'],
  next:['Continue','繼續'],welcome:['Join the trip','加入這趟旅程'], name:['Your display name','你的顯示名稱'],
  open:['Open workspace','開啟工作區'],copy:['Copy project code','複製專案代碼'],board:['Trip workspace','旅行工作區'],
  member:['Planning as','目前使用的名稱'],ideas:['Unscheduled','尚未排入行程'],empty:['Add the first idea for this trip.','為這趟旅程加入第一個點子。'],
  add:['Add a card','新增卡片'],title:['Title','標題'],note:['Notes (optional)','備註（選填）'],save:['Save card','儲存卡片'],
  codeFormat:['Use 8–32 letters, digits or hyphens.','請使用 8 至 32 個英文字母、數字或連字號。'],
  taken:['That code is taken. Try another or generate one.','這個代碼已被使用。請換一個或隨機產生。'], missing:['Project not found. Check the code and try again.','找不到專案。請確認代碼後再試一次。'],
  limited:['Too many attempts. Try again in one minute.','嘗試次數過多，請在一分鐘後重試。'],invalid:['Check the fields and try again.','請檢查欄位後再試一次。'],
  expired:['Session expired. Enter the project code again.','工作階段已過期，請重新輸入專案代碼。'],offline:['Connection interrupted. Try again.','連線中斷，請重試。'],
  saved:['Card saved.','卡片已儲存。'], copied:['Code copied.','已複製代碼。'],full:['This project has reached its 100-card limit.','此專案已達 100 張卡片上限。'],
  live:['Checking for changes every 2 seconds','每 2 秒檢查更新'],author:['Added by','新增者']
};
let zh = localStorage.language === 'zh-TW';
const t = key => (words[key] || words.offline)[Number(zh)];
let mode='join', code='', token='', name='', cards=[], generation=0, refreshId=0;
let draftId='';
const random = () => Array.from(crypto.getRandomValues(new Uint8Array(12)), n => 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789'[n%32]).join('');
function show(id){
  for(const item of ['landing','access','identity','workspace']) $(item).hidden=item!==id;
  $('status').textContent='';
  const first=$(id).querySelector('h1,h2');
  if(first){first.tabIndex=-1;first.focus();}
}
function translate(){
  document.documentElement.lang=zh?'zh-Hant':'en';
  $('lang').textContent=zh?'English':'繁體中文';
  document.querySelectorAll('[data-t]').forEach(el=>el.textContent=t(el.dataset.t));
  $('flow').textContent=t(mode==='join'?'enter':'create');
  if(!$('workspace').hidden) render();
}
$('lang').onclick=()=>{zh=!zh;localStorage.language=zh?'zh-TW':'en';translate();};
async function api(action,body={},auth=token){
  const res=await fetch('/api/'+action,{method:'POST',headers:{'Content-Type':'application/json','Authorization':'Bearer '+auth},body:JSON.stringify(body)});
  const data=await res.json();
  if(!res.ok) throw new Error(data.error);
  return data;
}
function access(modeToUse){
  mode=modeToUse;$('code').value='';$('generate').hidden=mode==='join';translate();show('access');$('code').focus();
}
$('enter').onclick=()=>access('join');
$('create').onclick=()=>access('create');
$('generate').onclick=()=>{$('code').value=random();$('code').focus();};
$('back').onclick=()=>show('landing');
$('leave').onclick=()=>{generation++;token='';sessionStorage.removeItem('openCode');show('landing');};
function render(){
  $('member').textContent=t('member')+' · '+name;
  $('empty').hidden=cards.length>0;
  $('cards').replaceChildren(...cards.map(card=>{
    const li=document.createElement('li');
    for(const [tag,value] of [['h3',card.title],['p',card.note],['small',t('author')+' · '+card.author]]){
      if(value){const el=document.createElement(tag);el.textContent=value;li.append(el);}
    }
    return li;
  }));
}
async function refresh(){
  const current=generation, seq=++refreshId;
  try{
    const data=await api('board');
    if(current!==generation || seq!==refreshId) return;
    name=data.name;cards=data.cards;render();$('sync').textContent=t('live');
  }catch(e){if(current===generation && seq===refreshId) $('sync').textContent=t(e.message);}
}
function board(data){
  name=data.name;cards=data.cards||[];
  if(!name){show('identity');$('name').value='';$('name').focus();return;}
  const draft=JSON.parse(localStorage.getItem('draft:'+token)||'{}');
  $('title').value=draft.title||'';$('note').value=draft.note||'';draftId=draft.request||random();
  show('workspace');render();$('sync').textContent=t('live');
}
function rememberDraft(){
  localStorage.setItem('draft:'+token,JSON.stringify({request:draftId,title:$('title').value,note:$('note').value}));
}
$('cardForm').oninput=rememberDraft;
function submit(id,action){
  $(id).onsubmit=async event=>{
    event.preventDefault();
    const submitter=$(id).querySelector('button:not([type=button])');
    if(submitter.disabled)return;
    submitter.disabled=true;$('status').textContent='';
    try{await action();}catch(e){$('status').textContent=t(e.message);}
    finally{submitter.disabled=false;}
  };
}
async function openProject(nextCode,create){
  code=nextCode;const key='guest:'+code;generation++;
  token=create?'':localStorage.getItem(key)||'';
  if(token){
    try{const data=await api('board');sessionStorage.openCode=code;board(data);return;}
    catch(e){if(e.message!=='expired')throw e;localStorage.removeItem(key);}
  }
  const session=await api(create?'create':'join',{code},'');
  token=session.token;localStorage.setItem(key,token);sessionStorage.openCode=code;board({name:null});
}
submit('codeForm',async()=>{
  const raw=$('code').value.trim();
  if(!/^[A-Za-z0-9-]{8,32}$/.test(raw))throw new Error('codeFormat');
  await openProject(raw.toUpperCase(),mode==='create');
});
submit('nameForm',async()=>{await api('name',{name:$('name').value});board(await api('board'));});
submit('cardForm',async()=>{
  rememberDraft();
  $('title').readOnly=$('note').readOnly=true;
  const owner=token;
  try{
    await api('card',{title:$('title').value,note:$('note').value,request:draftId});
    localStorage.removeItem('draft:'+owner);
    if(token!==owner)return;
    $('cardForm').reset();draftId=random();$('status').textContent=t('saved');await refresh();
  }finally{$('title').readOnly=$('note').readOnly=false;}
});
$('copy').onclick=async()=>{
  try{await navigator.clipboard.writeText(code);$('status').textContent=t('copied')+' '+t('sharing');}
  catch{window.prompt(t('code')+' · '+t('sharing'),code);}
};
translate();
if(sessionStorage.openCode)openProject(sessionStorage.openCode,false).catch(e=>{$('status').textContent=t(e.message);});
setInterval(()=>{if(!$('workspace').hidden && !document.hidden)refresh();},2000);
window.addEventListener('online',()=>{if(!$('workspace').hidden)refresh();});
