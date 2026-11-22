"use strict";
const $ = id => document.getElementById(id);
const screen = $("screen"), dialog = $("confirm");
const brand = window.TABLET_BRAND;
document.title = brand;
$("brand").textContent = brand;
const artPaths = [
  '<rect x="10" y="15" width="58" height="44" rx="10" fill="#86b6d4"/><rect x="16" y="20" width="46" height="32" rx="6" fill="#bfe1f2"/><path d="m69 29 21-11v39L69 45z" fill="#6396ba"/><circle cx="38" cy="32" r="6" fill="#f7e2ad"/><path d="M25 47q13-17 26 0" fill="#7198a9"/>',
  '<g transform="rotate(-12 44 39)"><rect x="12" y="12" width="59" height="46" rx="4" fill="#8aaf87"/></g><g transform="rotate(7 52 42)"><rect x="24" y="17" width="62" height="48" rx="4" fill="#fff4da"/><rect x="30" y="23" width="50" height="32" rx="1" fill="#bddcc7"/><circle cx="67" cy="32" r="4" fill="#edc16e"/><path d="m30 54 16-18 12 13 7-7 14 13z" fill="#81a27e"/></g>',
  '<g transform="rotate(-5 47 40)"><rect x="16" y="15" width="61" height="50" rx="5" fill="#fff4d8"/><path d="M16 31h61V20q0-5-5-5H21q-5 0-5 5z" fill="#dfa65f"/><path d="M30 9v12m32-12v12M28 42h8m7 0h7m-22 9h7"/><circle cx="72" cy="54" r="15" fill="#dcad68"/><path d="m65 54 5 5 9-11"/></g>',
  '<path d="m22 26 49-20" fill="none"/><rect x="10" y="25" width="77" height="40" rx="8" fill="#b69dc7"/><circle cx="32" cy="45" r="13" fill="#d6c5e3"/><circle cx="32" cy="45" r="7" fill="#9989ac"/><rect x="52" y="32" width="26" height="8" rx="2" fill="#fff0ca"/><path d="M53 48h23m-23 7h17"/></svg>',
  '<path d="M25 20q22-15 48 0v35q-22 16-48 0z" fill="#c7d9c4"/><circle cx="40" cy="38" r="3" fill="#294d39"/><circle cx="59" cy="38" r="3" fill="#294d39"/><path d="M40 48q10 8 20 0M50 11v7" fill="none"/>'
];
function art(i){return '<svg class="art" aria-hidden="true" viewBox="0 0 100 76"><g stroke="#293f38" stroke-width="3.3" stroke-linejoin="round" stroke-linecap="round">'+artPaths[i].replace('</svg>','')+'</g></svg>'}
const landscape='<svg class="landscape" aria-hidden="true" viewBox="0 0 320 112"><defs><clipPath id="hill"><path d="M0 102Q34 80 68 86Q113 47 161 66Q202 30 246 58Q280 73 320 67V107H0Z"/></clipPath></defs><g fill="#e6b458" stroke="#66583b" stroke-width="1.8"><circle cx="210" cy="50" r="24"/><path d="m210 14 0-9m-33 30-8-4m15-9-6-8m66 21 8-4m-18-10 5-8"/></g><g clip-path="url(#hill)" stroke="#4f6958" stroke-width="2"><path fill="#c1d2af" d="M0 25h320v83H0z"/><path fill="#9bb697" d="M-10 107Q63 44 145 83T331 60v50H0Z"/><path fill="#799b7c" d="M43 112Q137 62 221 86T340 74v38Z"/><path fill="#e2d0a8" d="M130 108q32-13 61-15t-12-8q42 3 28 9t-38 14z"/></g></svg>';
const cards=[['Call Family','See a familiar face','blue'],['Family Photos','Look through your album','green'],['Daily Reminders','See your tasks for today','amber'],['Radio & Music','Listen to a favorite station','purple'],['Talk to Agey','Ask your local AI companion','sage']];
const contacts=[['Sarah','sarah'],['David','david'],['Dr. Ahmed','doctor']];
const photos=[['family','A family moment outdoors'],['garden','An afternoon in the garden'],['lake','A quiet day by the lake']];
const tasks=['Check my medication schedule','Have a glass of water','Take a gentle stretch'];
const stations=[['Classical','https://stream.wqxr.org/wqxr'],['News','https://stream.live.vc.bbcmedia.co.uk/bbc_world_service'],['Relaxing','assets/relaxing.wav']];
let page='home', photo=0, selected=0, contact=0, idle, sound, reminderDay='';
let chatMessages=[], chatBusy=false, chatError='';
const player=new Audio();player.volume=.5;
function dayKey(){return new Date().toLocaleDateString('en-CA')}
function clock(){
  const d=new Date();
  $("clock").textContent=d.toLocaleTimeString([], {hour:'numeric',minute:'2-digit',hour12:true});
  $("date").textContent=d.toLocaleDateString('en-US',{weekday:'long',month:'short',day:'numeric'});
  if(page==='reminders' && dayKey()!==reminderDay) show('reminders');
}
clock();setInterval(clock,1000);
function beep(){
  try{sound ||= new AudioContext();sound.resume().catch(()=>{});const o=sound.createOscillator(),g=sound.createGain(),now=sound.currentTime;
    o.frequency.value=540;g.gain.setValueAtTime(.035,now);g.gain.exponentialRampToValueAtTime(.001,now+.09);o.connect(g).connect(sound.destination);o.start();o.stop(now+.1);
  }catch{}
}
document.addEventListener('contextmenu',e=>e.preventDefault());
document.addEventListener('click',e=>{const b=e.target.closest('button');if(!b)return;beep();if(window.TABLET_READ_ALOUD && 'speechSynthesis' in window){speechSynthesis.cancel();speechSynthesis.speak(new SpeechSynthesisUtterance(b.ariaLabel || b.textContent))}},true);
async function lockTablet(){
  player.pause();
  if(window.DAYWELL_PUBLIC_DEMO){
    chatMessages=[];chatError='';
    if(dialog.open)dialog.close();
    show('home');
    return;
  }
  try{await fetch('/api/logout',{method:'POST',headers:{'Content-Type':'application/json','X-Daywell-Request':'1'},body:'{}'})}catch{}
  location.replace('/');
}
function stayAwake(){clearTimeout(idle);idle=setTimeout(()=>{if(dialog.open)dialog.close();lockTablet()},300000)}
['pointerdown','keydown'].forEach(event=>document.addEventListener(event,stayAwake));
const action=(label,act,cls='')=>'<button class="'+cls+'" data-act="'+act+'">'+label+'</button>';
function show(next){
  if(page==='radio'&&next!=='radio'){player.pause();player.removeAttribute('src');player.load()}
  page=next;stayAwake();screen.className=page==='home'?'':'sub';
  $('back').hidden=page==='home';$('clockbox').style.display=page==='home'?'':'none';
  const titles={home:'Home screen',family:'Call Family',photos:'Family Photos',reminders:'Daily Reminders',radio:'Radio & Music',agey:'Talk to Agey',help:'Help / SOS',call:'Demo call'};
  $('location').textContent=titles[page];
  if(page==='home'){
    screen.innerHTML='<section class="hero"><div><h1>My home</h1><p>What would you like to do?</p></div>'+landscape+'</section><div class="grid">'+cards.map(([title,desc,cls],i)=>action(art(i)+'<span class="arrow" aria-hidden="true">↗</span><strong>'+title+'</strong><small>'+desc+'</small>',['family','photos','reminders','radio','agey'][i],'tile '+cls)).join('')+'</div>';
  }else if(page==='family'){
    screen.innerHTML='<h1>Call Family</h1><p>Choose a contact for a demo call.</p><div class="contacts">'+contacts.map(([name,img],i)=>action('<img src="assets/'+img+'.jpg" alt=""><span>'+name+'</span><small>Tap to call</small>','person-'+i,'contact')).join('')+'</div>';
  }else if(page==='call'){
    screen.classList.add('center');screen.innerHTML='<img class="portrait" src="assets/'+contacts[contact][1]+'.jpg" alt=""><h1>'+contacts[contact][0]+'</h1><p>Demo video call · No one has been contacted.</p>'+action('End call','family','danger');
  }else if(page==='photos'){
    screen.innerHTML='<h1>Family Photos</h1><div class="album"><img id="albumimg" alt=""><p aria-live="polite" id="caption"></p></div><div class="controls">'+action('← Previous photo','prev')+action('Next photo →','next')+'</div>';updatePhoto();
  }else if(page==='reminders'){
    reminderDay=dayKey();screen.innerHTML='<h1>Daily Reminders</h1><p>Tap a task when you finish it.</p>'+tasks.map((t,i)=>action('<span class="check" aria-hidden="true"></span>'+t,'task-'+i,'task')).join('');tasks.forEach((_,i)=>updateTask(i));
  }else if(page==='radio'){
    screen.innerHTML='<h1>Radio &amp; Music</h1><div class="stations">'+stations.map(([n],i)=>action(n,'station-'+i)).join('')+'</div><p id="status" role="status"></p><div class="controls">'+action('Play','play','purple')+'</div><div class="volume">'+action('−','quieter')+'<b id="vol"></b>'+action('+','louder')+'</div>';radioControls();screen.querySelector('[data-act=quieter]').ariaLabel='Lower volume';screen.querySelector('[data-act=louder]').ariaLabel='Raise volume';
  }else if(page==='agey'){
    screen.innerHTML='<h1>Talk to Agey</h1><p class="agey-note">A local AI companion. Agey can make mistakes and cannot call for help.</p><div id="chat" class="chat" role="log" aria-label="Conversation with Agey" aria-live="polite"></div><form id="chat-form" class="chat-form"><label for="chat-input">Your message</label><div><input id="chat-input" maxlength="2000" required autocomplete="off" placeholder="Ask Agey anything"><button id="chat-send" type="submit">Send</button></div></form><p id="chat-status" role="status"></p>';
    renderChat();
  }else{
    screen.innerHTML='<h1>Help / SOS</h1><p>If you need urgent help, use a telephone to call your local emergency number.</p><p>This tablet has no emergency calling service.</p>'+action('Return home','home');
  }
  const heading=screen.querySelector('h1');heading.tabIndex=-1;heading.focus({preventScroll:true});
}
function renderChat(){
  const log=$('chat');if(!log)return;
  log.replaceChildren();
  if(!chatMessages.length){const welcome=document.createElement('p');welcome.className='chat-welcome';welcome.textContent='Hello, I’m Agey. What would you like to talk about?';log.append(welcome)}
  for(const message of chatMessages){const bubble=document.createElement('p');bubble.className='bubble '+message.role;bubble.textContent=message.content;log.append(bubble)}
  log.scrollTop=log.scrollHeight;
  $('chat-send').disabled=chatBusy;
  $('chat-status').textContent=chatBusy?'Agey is thinking…':chatError;
}
screen.addEventListener('submit',async event=>{
  if(event.target.id!=='chat-form')return;
  event.preventDefault();
  if(window.DAYWELL_PUBLIC_DEMO){
    $('chat-status').textContent='Agey needs the installed version with local Ollama. This public demo supports photos, reminders, music and simulated calls.';
    return;
  }
  if(chatBusy)return;
  const input=$('chat-input'),content=input.value.trim();if(!content)return;
  chatMessages.push({role:'user',content});chatMessages=chatMessages.slice(-11);input.value='';chatBusy=true;chatError='';renderChat();
  try{
    const response=await fetch('/api/chat',{method:'POST',headers:{'Content-Type':'application/json','X-Daywell-Request':'1'},body:JSON.stringify({messages:chatMessages})});
    if(response.status===401)return location.replace('/');
    const result=await response.json();if(!response.ok)throw new Error(result.error||'Agey is unavailable.');
    chatMessages.push({role:'assistant',content:result.reply});chatMessages=chatMessages.slice(-12);
  }catch(error){chatError=error.message}
  finally{chatBusy=false;if(page==='agey'){renderChat();$('chat-input').focus()}}
});
function updatePhoto(){const [src,caption]=photos[photo];$('albumimg').src='assets/'+src+'.jpg';$('albumimg').alt=caption;$('caption').textContent=(photo+1)+' of '+photos.length+' · '+caption}
const sessionChecks=new Map();
function taskKey(i){return 'daywell/'+reminderDay+'/'+i}
function checked(i){const k=taskKey(i);if(sessionChecks.has(k))return sessionChecks.get(k);try{return localStorage.getItem(k)==='1'}catch{return false}}
function updateTask(i){const b=screen.querySelector('[data-act=task-'+i+']');b.setAttribute('aria-pressed',String(checked(i)));b.firstChild.textContent=checked(i)?'✓':''}
function radioControls(message){if(page!=='radio')return;
  [...screen.querySelectorAll('.stations button')].forEach((b,i)=>b.setAttribute('aria-pressed',String(i===selected)));
  screen.querySelector('[data-act=play]').textContent=player.paused?'Play':'Stop';
  $('vol').textContent='Volume '+Math.round(player.volume*100)+'%';
  if(message!==undefined)$('status').textContent=message;else $('status').textContent=stations[selected][0]+(selected===2?' · Offline music':' · Internet radio');
}
player.addEventListener('playing',()=>radioControls('Playing '+stations[selected][0]));
player.addEventListener('error',()=>{if(player.hasAttribute('src'))radioControls('Station unavailable. Try Relaxing for offline music.')});
player.addEventListener('ended',()=>radioControls());
screen.addEventListener('click',async e=>{
  const a=e.target.closest('button')?.dataset.act;if(!a)return;
  if(a.startsWith('person-')){contact=Number(a.slice(7));$('question').textContent='Call '+contacts[contact][0]+' now?';dialog.showModal();$('no').focus()}
  else if(a.startsWith('task-')){const i=Number(a.slice(5)),k=taskKey(i),v=!checked(i);sessionChecks.set(k,v);try{localStorage.setItem(k,v?'1':'0')}catch{}updateTask(i)}
  else if(a==='next'||a==='prev'){photo=(photo+(a==='next'?1:-1)+photos.length)%photos.length;updatePhoto()}
  else if(a.startsWith('station-')){player.pause();player.removeAttribute('src');player.load();selected=Number(a.slice(8));radioControls()}
  else if(a==='quieter'||a==='louder'){player.volume=Math.max(0,Math.min(1,Math.round(player.volume*10+(a==='louder'?1:-1))/10));$('vol').textContent='Volume '+Math.round(player.volume*100)+'%'}
  else if(a==='play'){if(!player.paused){player.pause();radioControls('Playback stopped.')}else{player.src=stations[selected][1];player.loop=selected===2;radioControls('Opening '+stations[selected][0]+'…');try{await player.play()}catch(err){if(err.name!=='AbortError')radioControls('Unable to play. Try Relaxing for offline music.')}}}
  else show(a);
});
$('yes').onclick=()=>{dialog.close();show('call')};$('no').onclick=()=>dialog.close();
$('back').onclick=()=>show(page==='call'?'family':'home');$('help').onclick=()=>show('help');$('lock').onclick=lockTablet;show('home');
