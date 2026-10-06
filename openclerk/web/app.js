'use strict';
const $ = id => document.getElementById(id);
const token = document.querySelector('meta[name="session-token"]').content;
let current = null;
let requesting = false;
async function api(path, data) {
  const response = await fetch('/api/' + path, {method: data === undefined ? 'GET' : 'POST',
    headers: {'Authorization': 'Bearer ' + token, 'Content-Type': 'application/json'},
    body: data === undefined ? undefined : JSON.stringify(data)});
  const body = await response.json();
  if (!response.ok) throw new Error(body.error || 'Operation failed');
  return body;
}
function render(state) {
  current = state;
  $('state').textContent = state.state;
  $('steps').textContent = `${state.steps} / ${state.max_steps} reviewed steps`;
  const active = !['idle','stopped','completed','handoff','uncertain'].includes(state.state);
  $('start').disabled = state.busy || requesting;
  $('observe').disabled = !active || state.busy || requesting;
  $('propose').disabled = !active || state.busy || !!state.pending || requesting || state.steps >= state.max_steps;
  $('approve').disabled = !state.pending || state.busy || requesting;
  $('reject').disabled = !state.pending || state.busy || requesting;
  $('error').hidden = !state.error;
  $('error').textContent = state.error;
  if (state.observation) {
    $('screenshot').src = state.observation.image; $('screenshot').hidden = false; $('empty').hidden = true;
    $('screen-meta').textContent = `${state.observation.width} × ${state.observation.height} · window ${state.observation.window_id}`;
  } else {
    $('screenshot').hidden = true; $('screenshot').removeAttribute('src'); $('empty').hidden = false;
    $('screen-meta').textContent = 'No capture yet';
  }
  $('proposal').hidden = !state.pending; $('no-proposal').hidden = !!state.pending; $('marker').hidden = true;
  if (state.pending) {
    const action = state.pending.action;
    $('action-kind').textContent = action.kind;
    const details = {...action}; delete details.kind; delete details.reason; delete details.expected;
    $('action-detail').textContent = JSON.stringify(details);
    $('reason').textContent = action.reason; $('expected').textContent = action.expected;
    $('completion-evidence').hidden = action.kind !== 'done';
    $('completion-evidence').textContent = action.evidence || '';
    $('approve').textContent = action.kind === 'done' ? 'Confirm visible result' : action.kind === 'handoff' ? 'Confirm handoff' : 'Approve this action';
    if (typeof action.x === 'number' && state.observation) {
      $('marker').hidden = false;
      $('marker').style.left = (action.x / state.observation.width * 100) + '%';
      $('marker').style.top = (action.y / state.observation.height * 100) + '%';
    }
  }
  const events = [...state.events].reverse().slice(0,12);
  $('events').replaceChildren();
  if (!events.length) {const li = document.createElement('li'); li.textContent = 'No run has started.'; $('events').append(li);}
  events.forEach(event => {const li = document.createElement('li'); const time = document.createElement('time');
    time.textContent = new Date(event.time * 1000).toLocaleTimeString(); li.append(time);
    li.append(document.createTextNode(event.event.replaceAll('_',' ') + (event.kind ? ' · ' + event.kind : ''))); $('events').append(li);});
}
async function act(path, data={}) {
  requesting = true; if(current) render(current);
  try { render(await api(path,data)); }
  catch(error) { try {render(await api('status'));} catch {} $('error').hidden=false; $('error').textContent=error.message; }
  finally {requesting=false; if(current) {const message=$('error').textContent; const shown=!$('error').hidden; render(current); if(shown){$('error').hidden=false;$('error').textContent=message;}}}
}
$('start').onclick = () => act('start',{task:$('task').value,bundle_id:$('target').value,model:$('model').value});
$('observe').onclick = () => act('observe');
$('propose').onclick = () => act('propose');
$('approve').onclick = () => act('approve',{proposal_id:current?.pending?.id});
$('reject').onclick = () => act('reject',{proposal_id:current?.pending?.id});
// Stop gets its own request so it can interrupt model planning without waiting for it.
$('stop').onclick = async () => {try{render(await api('stop',{}));}catch(error){$('error').hidden=false;$('error').textContent=error.message;}};
async function refresh() {
  try {const {models} = await api('models'); const selected=$('model').value;
    $('model').replaceChildren(); models.filter(m=>!m.endsWith('cloud')).forEach(model=>{const option=document.createElement('option');option.value=model;option.textContent=model;$('model').append(option);});
    if(models.includes(selected)) $('model').value=selected;
    if(!models.length) {const option=document.createElement('option');option.value='';option.textContent='No model installed';$('model').append(option);}
  } catch(error) {$('error').hidden=false;$('error').textContent=error.message;}
  try {const {apps}=await api('apps'); if(apps.length){$('target').replaceChildren(); apps.forEach(app=>{const option=document.createElement('option');option.value=app.bundle_id;option.textContent=app.name;$('target').append(option);});}} catch {}
}
$('refresh').onclick=refresh;
async function init(){
  render(await api('status'));
  try {const doctor=await api('doctor');$('capture-permission').textContent='Window capture access: '+(doctor.screen_recording?'available':'permission needed');$('input-permission').textContent='Native input access: '+(doctor.accessibility?'available':'permission needed');}
  catch(error){$('capture-permission').textContent=error.message;$('input-permission').textContent='Native bridge unavailable';}
  await refresh();
}
init().catch(error=>{$('error').hidden=false;$('error').textContent=error.message;});
setInterval(async()=>{if(!requesting){try{render(await api('status'));}catch{}}},2000);
