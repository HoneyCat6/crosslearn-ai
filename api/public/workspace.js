const app = document.querySelector('#app');
const escape = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
let language = localStorage.getItem('crosslearn-language') || 'en';
let offlinePack = null;
let pending = JSON.parse(sessionStorage.getItem('crosslearn-pending') || '[]');
let user = null, tab = 'class', classes = [], classId = '', classData = null, banks = [], profile = null;
let pupil = null, state = null, chosen = null, readAloud = false, transcript = false, audioPlayed = false, selectedWord = '', letters = {};
let deleteConfirm = false, notice = '', noticeError = false, busy = false;
const csrf = () => document.cookie.split('; ').find(v => v.startsWith('crosslearn_csrf='))?.split('=').slice(1).join('=') || '';

async function api(path, method = 'GET', body, pupilAuth = false) {
  const headers = {'Content-Type':'application/json'};
  if (method !== 'GET') headers['X-CSRF-Token'] = csrf();
  if (pupilAuth) headers.Authorization = `Bearer ${pupil.token}`;
  const response = await fetch(path, {method, headers, credentials:'same-origin', body: body === undefined ? undefined : JSON.stringify(body)});
  if (!response.ok) {
    let message = 'The request could not be completed.';
    try { const error = await response.json(); message = typeof error.detail === 'string' ? error.detail : 'Please check the form values.'; } catch {}
    throw new Error(message);
  }
  return response.json();
}

function notify(message, error = false) {
  notice = message; noticeError = error;
  const node = document.querySelector('#notice');
  if (node) { node.className = error ? 'error-box' : 'success-box'; node.textContent = message; }
}

const button = (label, action, cls = 'secondary', extra = '') => `<button type="button" class="${cls}" data-action="${action}" ${extra}>${label}</button>`;
const date = value => new Date(value).toLocaleString();
const writable = () => user && ['teacher','admin'].includes(user.role);
const badge = value => `<span class="pill">${escape(value.replaceAll('_',' '))}</span>`;

function shell(content) {
  app.innerHTML = `<div class="demo-banner">◇ Synthetic demo · local teacher accounts · no real pupil data</div>
    <header><a class="brand" href="/" aria-label="CrossLearn home"><span class="brand-icon">✣</span>CrossLearn<span class="ai">AI</span></a>
    <nav><span class="account-chip">${user ? `${escape(user.username)} · ${escape(user.role)}` : pupil ? 'Pupil discovery' : 'Teacher workspace'}</span>
    ${user ? button('Sign out','logout','subtle') : ''}</nav></header>
    <main class="workspace-layout"><div id="notice" role="status" class="${notice ? noticeError ? 'error-box' : 'success-box' : ''}">${escape(notice)}</div>${content}</main>
    <footer><span class="brand-mini">✣ CrossLearn AI</span><span>Curiosity is where learning begins.</span><span>M2 · Synthetic data only</span></footer>`;
}

function renderLogin() {
  shell(`<section class="card login-card"><span class="eyebrow">A LITTLE EVIDENCE. A BETTER NEXT STEP.</span><h1>Welcome back.</h1>
    <p>Sign in to review content, guide a discovery session and see what to try next.</p>
    <form id="login"><label class="field">Username<input name="username" required autocomplete="username" placeholder="teacher.a"></label>
    <label class="field">Password<input type="password" name="password" required autocomplete="current-password"></label>
    <button class="primary" type="submit">Open my workspace →</button></form>
    <p class="quiet" style="margin-top:24px">Your locally generated demo credentials are in <code>api/.demo-access.json</code>. Available roles: teacher.a, admin.a, researcher.a and teacher.b.</p>
    ${pupil ? button('Resume pupil session','resume','subtle') : ''}</section>`);
}

async function loadWorkspace() {
  classes = await api('/api/teacher/classes');
  banks = await api('/api/teacher/content');
  if (!classes.some(c => c.id === classId)) classId = classes[0]?.id || '';
  classData = classId ? await api(`/api/teacher/classes/${classId}`) : null;
}

function nav() {
  return `<div class="workspace-head"><span class="eyebrow">${escape(user.school)} · ${escape(user.role)} WORKSPACE</span><h1>Evidence for the next explanation.</h1><p>Small observations. Thoughtful teaching. Every suggestion stays open to review.</p></div>
    <div class="workspace-nav">${button('My class','class',`secondary ${tab==='class'?'active':''}`)}${button('Evaluation report','report','secondary')}${button('Content & approval','content',`secondary ${tab==='content'?'active':''}`)}${['researcher','admin'].includes(user.role)?button('Research export','export-tab',`secondary ${tab==='export'?'active':''}`):''}${user.role==='admin'?button('Audit history','audit',`secondary ${tab==='audit'?'active':''}`):''}</div>`;
}

function classView() {
  if (!classData) return '<section class="card empty"><h2>No classes assigned yet.</h2></section>';
  return `<div class="status-line"><h2>${escape(classData.name)}</h2><label>Class <select id="class-select">${classes.map(c=>`<option value="${c.id}" ${c.id===classId?'selected':''}>${escape(c.name)}</option>`).join('')}</select></label></div>
    <div class="workspace-grid"><section class="card"><div class="card-heading"><h2>Your explorers</h2>${badge(`${classData.learners.length} synthetic learners`)}</div>
    ${classData.learners.length ? classData.learners.map(l=>`<article class="learner-row"><div class="avatar">${l.pseudonym.slice(-1)}</div><div><h3>${escape(l.pseudonym)}</h3><p>${l.completed_sessions} completed session(s) · ${escape(l.consent_status.replaceAll('_',' '))}</p></div>${button('View evidence →','profile','secondary',`data-id="${l.id}"`)}</article>`).join('') : '<p>No learners remain in this demo class.</p>'}</section>
    <section class="card"><span class="eyebrow">THE NEXT DISCOVERY</span><h2>Assignments</h2><p>Only reviewed sample content can be assigned to a class.</p>
    ${classData.assignments.map(a=>`<p><strong>${escape(a.title)}</strong><br><span class="quiet">${escape(a.version)}</span></p>`).join('') || '<p class="quiet">No assignment yet. Review the content to get started.</p>'}
    ${writable()?`<form id="assign"><label class="field">Approved content<select name="bank_id" required><option value="">Choose a word set</option>${banks.filter(b=>b.status==='approved_demo').map(b=>`<option value="${b.id}">${escape(b.title)} · ${escape(b.version)}</option>`).join('')}</select></label><button class="primary" type="submit">Assign to this class →</button></form>${button('Review sample content','content','subtle')}`:''}</section></div>`;
}

function contentView() {
  return `${writable()?`<details class="card"><summary>Create a new content version</summary><p>Copy an existing content payload, edit its scripts or questions, and choose a new version. Existing sessions retain their original snapshot. Plant concept IDs and the current grid size are required.</p><form id="content-draft"><label class="field">Title<input name="title" required maxlength="100"></label><label class="field">Content JSON<textarea name="payload" rows="12" required>${escape(JSON.stringify(banks[0]?.payload||{},null,2))}</textarea></label><button class="primary" type="submit">Save draft for review</button></form></details>`:''}<section class="hero-small"><h2>Review before discovery.</h2><p>These are technical sample items. Approval here permits synthetic demo use; it does not certify curriculum fit, calibrated difficulty or research readiness.</p></section>${banks.map(b=>`<section class="card content-card"><div class="card-heading"><h2>${escape(b.title)}</h2>${badge(b.status)}</div><p class="quiet">Version: ${escape(b.version)}${b.reviewed_at ? ` · Reviewed ${date(b.reviewed_at)}`:''}</p>
    ${b.payload.concepts.map(c=>`<details><summary>${escape(c.word)} · clue, explanation & questions</summary><p><strong>Crossword clue:</strong> ${escape(c.clue)}</p><p><strong>Text / audio script:</strong> ${escape(c.text)}</p><p><strong>Diagram description:</strong> ${escape(c.alt)}</p>${['baseline','post'].map(phase=>`<h3>${phase==='baseline'?'Baseline':'Post-test'}</h3><ol>${b.payload[phase].filter(q=>q.concept===c.id).map(q=>`<li>${escape(q.stem)}<ul>${q.options.map((o,i)=>`<li>${escape(o)}${i===q.answer?' ✓ keyed answer':''}</li>`).join('')}</ul></li>`).join('')}</ol>`).join('')}</details>`).join('')}
    ${writable()&&b.status!=='approved_demo'?`<form class="approve-content" data-id="${b.id}"><label class="check-label"><input type="checkbox" required>I have reviewed these items for synthetic demonstration use.</label><button type="submit" class="primary">Approve demo version →</button></form>`:''}</section>`).join('')}`;
}

function metricTable(s) {
  if (!s.metrics.length) return '<p class="quiet">This session is in progress. No comprehension results are reported yet.</p>';
  return `<div class="table-wrap"><table><caption class="sr-only">Concept scores for this session</caption><thead><tr><th>Concept</th><th>Format</th><th>Before</th><th>After</th><th>Change</th></tr></thead><tbody>${s.metrics.map(r=>`<tr><th scope="row">${escape(r.word)}</th><td>${escape(r.modality)}</td><td>${r.baseline_correct}/${r.baseline_total}</td><td>${r.post_correct}/${r.post_total}</td><td>${r.gain_pp>0?'+':''}${r.gain_pp} pp</td></tr>`).join('')}</tbody></table></div>`;
}

function profileView() {
  const completed = profile.sessions.filter(s=>s.stage==='results');
  return `${button('← Back to class','class','subtle')}<div class="status-line"><div><h2>${escape(profile.pseudonym)}</h2><p class="quiet">${completed.length} completed synthetic session(s)</p></div>${badge(profile.consent_status)}</div>
    <div class="workspace-grid"><section class="card"><span class="eyebrow">START A NEW OBSERVATION</span><h2>Ready for a discovery?</h2><p>Each new session rotates explanation formats. Repeated sample questions are practice; they are not fresh independent evidence.</p>
    ${writable()?`<form id="start-session"><label class="field">Class assignment<select name="assignment_id" required><option value="">Choose an assignment</option>${classData.assignments.map(a=>`<option value="${a.id}">${escape(a.title)}</option>`).join('')}</select></label><button class="primary" type="submit" ${profile.consent_status!=='synthetic_demo'?'disabled':''}>Start pupil session →</button><p class="quiet">Starting signs you out of the teacher account before opening the pupil view on this device.</p></form>`:''}</section>
    <section class="card"><span class="eyebrow">INTERPRET WITH CARE</span><h2>Insufficient evidence</h2><p>Two items per concept give coarse scores. Uncalibrated content and repeated sessions cannot establish a fixed learning style.</p><p class="quiet">Full baseline marks leave no room for measured gain. Use new calibrated items or later retention checks.</p>${writable()?button('Draft teacher recommendation','analyze','primary',completed.length&&profile.consent_status==='synthetic_demo'?'':'disabled'):''}</section></div>
    <div class="session-list">${profile.sessions.slice().reverse().map(s=>`<section class="card"><div class="card-heading"><h2>Session ${escape(s.id.slice(0,8))}</h2>${badge(s.stage)}</div><p class="timeline-label">${date(s.created_at)} · rotation ${s.rotation+1} · ${escape(s.version)}</p>${metricTable(s)}${writable()&&s.completed_at&&Date.now()-new Date(s.completed_at).getTime()>=7*86400000?button('Open delayed retention','open-retention','secondary',`data-id="${s.id}"`):''}<p class="quiet">Delayed retention: ${s.retention?.answered===6?`${s.retention.correct}/6 correct`:'not completed (due seven days after session)'}</p><details><summary>Exposure & accessibility evidence</summary><p class="quiet">${s.attempts} crossword check(s) · ${s.hints} letter reveal(s) · ${s.read_aloud_count} read-aloud question(s). Crossword spelling does not contribute to comprehension scores.</p>${s.exposures.map(e=>`<p class="quiet">${e.order}. ${escape(e.concept.toUpperCase())} · ${escape(e.modality)} · ${e.seconds}s elapsed · audio requested: ${e.audio_played?'yes':'no'} · transcript: ${e.transcript?'yes':'no'}</p>`).join('')}<p class="quiet">Elapsed time includes interruptions. Playback requests do not prove listening.</p></details></section>`).join('') || '<section class="card empty"><h2>No evidence yet.</h2><p>Complete the first discovery session to build this timeline.</p></section>'}</div>
    ${profile.recommendations.map(recommendationView).join('')}
    ${writable()?`<details class="card"><summary>Demo participation & deletion</summary><p>Withdrawing participation blocks pupil access and future analysis. Deleting removes linked assessments, responses, recommendations and reviews.</p><div class="button-group">${button(profile.consent_status==='withdrawn'?'Restore synthetic participation':'Withdraw participation','consent')}${button('Delete this synthetic learner','confirm-delete','secondary danger')}</div>${deleteConfirm?`<div class="confirm-box"><p>Delete ${escape(profile.pseudonym)} and all linked records? This cannot be undone.</p>${button('Delete learner and linked data','delete','secondary danger')}${button('Cancel','cancel-delete','subtle')}</div>`:''}</details>`:''}`;
}

function recommendationView(r) {
  const last = r.reviews.at(-1);
  return `<section class="card review-card"><div class="card-heading"><span class="eyebrow">${r.run.source==='model'?'BOUNDED MODEL SELECTION':'RULE-BASED FALLBACK'} · ${escape(r.run.model)}</span>${badge(r.status)}</div><h2>A suggestion for your review</h2><p>${escape(r.output.evidence_summary)}</p><p>${escape(r.output.teacher_action)}</p><p><strong>Next assessment:</strong> ${escape(r.output.next_assessment)}</p><ul>${r.output.limitations.map(t=>`<li>${escape(t)}</li>`).join('')}</ul>${r.run.error?'<p class="quiet">The model was unavailable or its output failed validation. A safe rule-based suggestion was used.</p>':''}
    ${writable()?`<form class="review" data-id="${r.id}"><label class="field">Teacher action<textarea name="teacher_action" required maxlength="2000">${escape(last?.teacher_action||r.output.teacher_action)}</textarea></label><label class="field">Feedback / observed result<textarea name="feedback" maxlength="2000" placeholder="Record your instructional decision or follow-up observation."></textarea></label><div class="button-group"><button type="submit" class="primary" name="decision" value="approved">Approve</button><button type="submit" class="secondary" name="decision" value="edited">Save edited action</button><button type="submit" class="secondary" name="decision" value="rejected">Reject draft</button></div></form>`:''}
    <details><summary>Decision history & agent trace</summary><p class="quiet">${r.run.trace.map(escape).join(' → ')}</p>${r.reviews.map(v=>`<p><strong>${escape(v.decision)}</strong> · ${date(v.created_at)}<br>${escape(v.teacher_action)}<br><span class="quiet">${escape(v.feedback)}</span></p>`).join('')||'<p class="quiet">Awaiting teacher review. No action is automatically assigned or published.</p>'}</details></section>`;
}

async function renderWorkspace() {
  let content = '';
  if (tab === 'report') {
    const report=await api(`/api/research/report/${classId}`);
    content=`<section class="card"><h2>Technical pilot evaluation</h2><p>${report.completed_sessions} completed synthetic sessions ? mean gain ${report.mean_gain_pp??'?'} pp</p><p>Rotation balance: ${report.balanced?'balanced':'incomplete'}. Difficulty: ${report.calibration}.</p><div class="table-wrap"><table><thead><tr><th>Rotation</th><th>Sessions</th></tr></thead><tbody>${Object.entries(report.rotations).map(([r,n])=>`<tr><td>${r}</td><td>${n}</td></tr>`).join('')}</tbody></table></div><ul>${report.limitations.map(v=>`<li>${escape(v)}</li>`).join('')}</ul></section>`;
  }
  if (tab === 'class') content = classView();
  if (tab === 'content') content = contentView();
  if (tab === 'profile') content = profileView();
  if (tab === 'export') content = `<section class="card"><h2>De-identified research export</h2><p>Download completed synthetic sessions from the selected class. Withdrawn learners are excluded. Exports contain random learner/session IDs, versions, formats, raw counts, percentage-point differences and accommodations.</p><label class="field">Class<select id="class-select">${classes.map(c=>`<option value="${c.id}" ${c.id===classId?'selected':''}>${escape(c.name)}</option>`).join('')}</select></label>${button('Download CSV','download','primary')}<p class="quiet">This sample bank is not calibrated. Exporting records does not make them research-ready.</p></section>`;
  if (tab === 'audit') {
    const events = await api('/api/admin/audit');
    content = `<section class="card"><h2>School audit history</h2><p class="quiet">Latest 200 events. Learner identifiers and educational payloads are excluded from this log.</p><div class="table-wrap"><table><thead><tr><th>When</th><th>Action</th><th>Actor ID</th></tr></thead><tbody>${events.map(e=>`<tr><td>${date(e.created_at)}</td><td>${escape(e.action.replaceAll('_',' '))}</td><td>${escape(e.actor_id.slice(0,8))}</td></tr>`).join('')}</tbody></table></div></section>`;
  }
  shell(nav()+content);
}

function diagram(c) {
  const moss = c.id==='moss', roots = c.id==='root';
  return `<svg class="plant" viewBox="0 0 440 340" role="img" aria-label="${escape(c.alt)}"><rect width="440" height="340" rx="25" fill="#edf4e8"/>
    ${moss?`<path d="M60 260Q110 150 220 190Q310 145 380 260Z" fill="#8b9a99"/>${Array.from({length:14},(_,i)=>`<path d="M${100+i*17} 215q-12-45 3-48q18 20 8 48" fill="${i%2?'#328252':'#579d66'}"/>`).join('')}<text x="220" y="80" text-anchor="middle">Damp + shady</text><path d="M220 100v50m-7-8 7 8 7-8" stroke="#2563eb" stroke-width="3" fill="none"/><text x="220" y="300" text-anchor="middle">Moss on a moist rock</text>`:`<path d="M40 245H400V310H40Z" fill="#d9c19a"/><path d="M220 245V90" stroke="${roots?'#43805b':'#dbab3d'}" stroke-width="12" stroke-linecap="round"/><path d="M217 163Q130 165 135 103Q209 99 217 163M225 140Q308 132 307 74Q231 78 225 140M225 204Q290 208 310 159Q250 149 225 204" fill="#519c68"/><path d="m220 242-25 42m25-42 25 42m-32-24-40 15m58-10 32 10m-44-22v46" stroke="#8f6235" stroke-width="5" fill="none"/><text x="${roots?70:352}" y="${roots?279:192}" text-anchor="middle">${roots?'Roots':'Stem'}</text><path d="${roots?'M100 275h65':'M320 190h-70'}" stroke="#2563eb" stroke-width="3"/><text x="220" y="331" text-anchor="middle" style="font-size:14px">Water travels from roots to leaves ↑</text>`}</svg>`;
}

const cellKeys = c => Array.from({length:c.length},(_,i)=>`${c.row+(c.direction==='down'?i:0)}-${c.col+(c.direction==='across'?i:0)}`);
function crosswordView() {
  const grid = {};
  for (const c of state.puzzle) cellKeys(c).forEach((key,i)=>{grid[key]??={words:[]};grid[key].words.push(c.id);if(!i)grid[key].number=c.number;});
  selectedWord ||= state.puzzle[0].id;
  return `<div class="page-top"><div><span class="eyebrow">THE LIVING WORLD</span><h1>Let’s connect the words.</h1><p>Three hidden words. No timer. Take your time.</p></div>${badge(`rotation ${state.rotation+1}`)}</div><div class="game-layout"><section class="card"><div class="crossword" aria-label="Four-row intersecting crossword">${Array.from({length:20},(_,i)=>{const k=`${Math.floor(i/5)}-${i%5}`,c=grid[k];return c?`<div class="cell ${c.words.includes(selectedWord)?'selected':''}">${c.number?`<span>${c.number}</span>`:''}<input data-cell="${k}" aria-label="Row ${Math.floor(i/5)+1}, column ${i%5+1}" value="${escape(letters[k]||'')}" maxlength="1" autocomplete="off" autocapitalize="characters"></div>`:'<div class="blocked"></div>';}).join('')}</div><p class="quiet keyboard-help">Tap and type. Use arrow keys to move; click a clue to choose a word.</p><div class="button-group">${button('Clear letters','clear','subtle')}${button('Reveal one letter','hint','subtle')}</div></section><section class="clue-panel"><div class="clues">${state.puzzle.map(c=>button(`<strong>${c.number} ${c.direction==='down'?'↓':'→'}</strong> ${escape(c.clue)}`,'clue',`pupil-clue ${selectedWord===c.id?'active':''}`,`data-id="${c.id}"`)).join('')}</div><p class="quiet">Spelling discovery and understanding are scored separately.</p>${button('Check crossword →','check','primary')}</section></div>`;
}

function renderPupil() {
  let content = `<div class="pupil-toolbar"><span class="eyebrow">YOUR DISCOVERY JOURNEY</span><div class="button-group">${button(language==='ms'?'English':'Bahasa Melayu','language','subtle')}${button('Larger text','large','subtle')}${button('High contrast','contrast','subtle')}</div></div>`;
  if (state.stage==='crossword') content += crosswordView();
  if (['baseline','post','retention'].includes(state.stage)) {
    const q = state.question;
    content += `<div class="page-top"><div><span class="eyebrow">${state.stage==='baseline'?'FIRST THOUGHTS':'TRY AGAIN'}</span><h1>${state.stage==='baseline'?'What do you think?':'Let’s put your ideas to work.'}</h1><p>Choose one answer. Feedback comes after the whole activity.</p></div></div><section class="card question-card"><div class="card-heading">${badge(`Question ${state.number} of ${state.total}`)}</div><h2 tabindex="-1">${escape(q.stem)}</h2>${button('♫ Read aloud','read','subtle read-aloud')}<div class="pupil-options">${q.options.map((o,i)=>button(`<span>${String.fromCharCode(65+i)}</span>${escape(o)}`,'answer',`option ${chosen===i?'chosen':''}`,`data-option="${i}" aria-pressed="${chosen===i}"`)).join('')}</div><p id="speech-status" class="quiet read-aloud-status" role="status"></p><div class="question-footer"><span class="quiet">Your thinking matters. Take your time.</span>${button(state.number===6?'Finish questions →':'Next question →','next-question','primary',chosen===null?'disabled':'')}</div></section>`;
  }
  if (state.stage==='learn') {
    const c=state.lesson;
    content+=`<div class="page-top"><div><span class="eyebrow">EXPLORE AN IDEA</span><h1>A new way to explore.</h1><p>One word, one explanation, your own pace.</p></div></div><section class="card lesson-card"><div class="card-heading"><span class="format ${c.modality}">${c.modality==='visual'?'Diagram':c.modality} explanation</span>${badge(`Word ${c.number} of 3`)}</div><h2>${escape(c.word)}</h2>${c.modality==='text'?`<div class="text-lesson"><p>${escape(c.text)}</p></div>`:c.modality==='visual'?`${diagram(c)}<p class="quiet lesson-note">${escape(c.alt)}</p>`:`<div class="audio-lesson"><div class="audio-orb">♫</div><h3>Listen a little closer.</h3><p>Hear an explanation about ${escape(c.word.toLowerCase())}.</p>${button(audioPlayed?'Replay audio':'Play explanation','audio')}<p id="speech-status" class="quiet read-aloud-status" role="status"></p>${button(transcript?'Hide accessible text':'Show accessible text','transcript','subtle')}${transcript?`<p class="transcript">${escape(c.text)}</p>`:''}</div>`}<div class="question-footer"><span class="quiet">There’s no hurry.</span>${button(c.number===3?'I’m ready for questions →':'Next word →','next-lesson','primary')}</div></section>`;
  }
  if (state.stage==='results') {
    const s=state.summary,before=s.metrics.reduce((n,r)=>n+r.baseline_correct,0),after=s.metrics.reduce((n,r)=>n+r.post_correct,0);
    content+=`<section class="card results-card"><div class="celebration">✦</div><span class="eyebrow">DISCOVERY COMPLETE</span><h1>Look how far you’ve grown!</h1><p>You explored three words. Try explaining one of them to someone you know.</p><div class="result-scores"><div><span>Before explanations</span><strong>${before}<small> / 6</small></strong></div><span>→</span><div><span>After explanations</span><strong>${after}<small> / 6</small></strong></div></div><p>Your progress is saved. Your teacher can review it in the workspace.</p>${button('Teacher sign-in →','teacher-login','primary')}</section><details class="card answer-review"><summary>Explore the answers</summary>${state.answers.map(q=>`<div><h3>${escape(q.stem)}</h3><p>${escape(q.correct_answer)}</p></div>`).join('')}</details>`;
  }
  shell(content);
  document.documentElement.lang=language;
  if(language==='ms') {
    const translations={'Larger text':'Teks lebih besar','High contrast':'Kontras tinggi','Let?s connect the words.':'Mari sambungkan perkataan.','What do you think?':'Apakah pendapat anda?','Choose one answer. Feedback comes after the whole activity.':'Pilih satu jawapan. Maklum balas selepas aktiviti selesai.','A new way to explore.':'Cara baharu untuk meneroka.','One word, one explanation, your own pace.':'Satu perkataan, satu penerangan, mengikut rentak anda.','Clear letters':'Padam huruf','Reveal one letter':'Dedahkan satu huruf','Check crossword ?':'Semak silang kata ?','Next question ?':'Soalan seterusnya ?','Finish questions ?':'Selesaikan soalan ?','Next word ?':'Perkataan seterusnya ?','Show accessible text':'Papar teks bantuan','Hide accessible text':'Sembunyikan teks bantuan','Play explanation':'Mainkan penerangan','Replay audio':'Main semula audio','There?s no hurry.':'Tidak perlu tergesa-gesa.','Your thinking matters. Take your time.':'Pemikiran anda penting. Ambil masa anda.','Delayed retention check':'Semakan ingatan tertunda'};
    const walker=document.createTreeWalker(app,NodeFilter.SHOW_TEXT);let node;
    while(node=walker.nextNode()){const value=node.nodeValue.trim();if(translations[value])node.nodeValue=node.nodeValue.replace(value,translations[value]);}
    notify('Navigasi Bahasa Melayu. Kandungan Sains dan soalan contoh kekal dalam Bahasa Inggeris.');
  }
}

function speech(text) {
  const node = document.querySelector('#speech-status');
  if (!('speechSynthesis' in window)) {node.textContent='Audio is unavailable on this device. Use the accessible text.';return;}
  window.speechSynthesis.cancel();
  const utterance = new SpeechSynthesisUtterance(text);utterance.lang='en-GB';utterance.rate=.85;
  utterance.onend=()=>{node.textContent='Finished. You can replay the audio.';};
  utterance.onerror=()=>{node.textContent='Audio could not play. Try again or use accessible text.';};
  node.textContent='Playing…';window.speechSynthesis.speak(utterance);
}

async function savePack() {
  try { offlinePack = await api(`/api/pupil/${pupil.id}/offline-pack`, 'GET', undefined, true); sessionStorage.setItem('crosslearn-pack', JSON.stringify(offlinePack)); } catch {}
}
async function syncPending() {
  while (pending.length) {
    const entry = pending[0];
    state = await api(`/api/pupil/${entry.session}/${entry.action}`, 'POST', entry.body, true);
    pending.shift(); sessionStorage.setItem('crosslearn-pending', JSON.stringify(pending));
  }
  await savePack(); renderPupil();
}
async function pupilRequest(action, body) {
  if (!navigator.onLine && action === 'responses') {
    if (!offlinePack || new Date(offlinePack.expires_at) <= new Date()) throw Error('Reconnect to renew the pupil session.');
    if (pending.some(e => e.body.item_id === body.item_id)) throw Error('This answer is already queued. Reconnect to sync.');
    pending.push({session:pupil.id, action, body}); sessionStorage.setItem('crosslearn-pending', JSON.stringify(pending));
    const remaining = offlinePack.questions.filter(q => !pending.some(e => e.body.item_id === q.id));
    if (remaining.length) {state.question=remaining[0];state.number++;chosen=null;readAloud=false;renderPupil();}
    notify(`${pending.length} answer(s) saved on this device. Reconnect before the next phase.`, false);
    return state;
  }
  if (pending.length) {await syncPending(); return state;}
  const result = await api(`/api/pupil/${pupil.id}/${action}`,'POST',body,true);
  if (result.stage) {
    const previous = `${state.stage}:${state.question?.id||state.lesson?.id||''}`;
    state=result;
    if(previous!==`${state.stage}:${state.question?.id||state.lesson?.id||''}`){chosen=null;readAloud=false;transcript=false;audioPlayed=false;window.speechSynthesis?.cancel();}
    renderPupil();
    const heading=document.querySelector('.question-card h2,h1');if(heading){heading.tabIndex=-1;heading.focus();}
  }
  await savePack();
  return result;
}

async function resumePupil() {
  if (navigator.onLine) {
    if (pending.length) await syncPending();
    state=await api(`/api/pupil/${pupil.id}/next`,'GET',undefined,true); await savePack();
  } else {
    offlinePack=JSON.parse(sessionStorage.getItem('crosslearn-pack')||'null');
    if (!offlinePack || new Date(offlinePack.expires_at)<=new Date()) throw Error('Reconnect to open this pupil session.');
    state=structuredClone(offlinePack.state);
    const remaining=offlinePack.questions.filter(q=>!pending.some(e=>e.body.item_id===q.id));
    if(remaining.length) {state.question=remaining[0];state.number=7-remaining.length;}
  }
  try {letters=JSON.parse(sessionStorage.getItem(`letters:${pupil.id}`)||'{}');}catch{letters={};}
  renderPupil();
}

async function refreshProfile() {profile=await api(`/api/teacher/learners/${profile.id}`);await renderWorkspace();}
async function perform(fn) {
  if(busy)return;busy=true;
  document.querySelectorAll('button[type="submit"]').forEach(b=>b.disabled=true);
  try { await fn(); } catch(error) { notify(error.message||'Connection failed. Your submitted progress remains on the server; retry when connected.',true); }
  finally {busy=false;document.querySelectorAll('button[type="submit"]').forEach(b=>b.disabled=false);}
}

app.addEventListener('submit',e=>{e.preventDefault();const form=e.target;const data=Object.fromEntries(new FormData(form));perform(async()=>{
  notice='';
  if(form.id==='login'){await api('/api/auth/login','POST',data);user=await api('/api/auth/me');tab='class';await loadWorkspace();await renderWorkspace();}
  if(form.id==='content-draft'){let payload;try{payload=JSON.parse(data.payload);}catch{throw Error('Enter valid JSON.');}await api('/api/teacher/content','POST',{title:data.title,payload});await loadWorkspace();await renderWorkspace();notify('New immutable version saved. Review and approve before assigning.');}
  if(form.id==='assign'){await api('/api/teacher/assignments','POST',{class_id:classId,bank_id:data.bank_id});await loadWorkspace();await renderWorkspace();notify('Assignment created. Open a learner to start a session.');}
  if(form.classList.contains('approve-content')){await api(`/api/teacher/content/${form.dataset.id}/approve`,'POST',{confirm_synthetic_review:true});await loadWorkspace();await renderWorkspace();notify('Version approved for synthetic demo use.');}
  if(form.id==='start-session'){
    if(pending.length) throw Error('Synchronize the previous pupil?s queued answers before starting another session.');
    pupil=await api('/api/sessions','POST',{assignment_id:data.assignment_id,learner_id:profile.id});
    sessionStorage.setItem('crosslearn-pupil',JSON.stringify(pupil));
    await api('/api/auth/logout','POST',{});user=null;state=null;letters={};selectedWord='';await resumePupil();
  }
  if(form.classList.contains('review')){await api(`/api/teacher/recommendations/${form.dataset.id}/review`,'POST',{decision:e.submitter.value,teacher_action:data.teacher_action,feedback:data.feedback});await refreshProfile();notify('Teacher decision saved with its review history.');}
});});

app.addEventListener('click',e=>{const b=e.target.closest('[data-action]');if(!b)return;const action=b.dataset.action;
  if(action==='answer'){chosen=Number(b.dataset.option);renderPupil();document.querySelector(`[data-option="${chosen}"]`)?.focus();return;}
  if(action==='language'){language=language==='en'?'ms':'en';localStorage.setItem('crosslearn-language',language);renderPupil();return;}
  if(action==='large'){document.body.classList.toggle('larger');return;}
  if(action==='contrast'){document.body.classList.toggle('high-contrast');return;}
  if(action==='clue'){selectedWord=b.dataset.id;renderPupil();document.querySelector(`[data-cell="${cellKeys(state.puzzle.find(c=>c.id===selectedWord))[0]}"]`)?.focus();return;}
  if(action==='clear'){letters={};sessionStorage.removeItem(`letters:${pupil.id}`);renderPupil();return;}
  if(action==='read'){readAloud=true;speech(`${state.question.stem}. ${state.question.options.map((o,i)=>`${String.fromCharCode(65+i)}. ${o}`).join('. ')}`);return;}
  if(action==='audio'){audioPlayed=true;b.textContent='Replay audio';speech(state.lesson.text);return;}
  if(action==='transcript'){transcript=!transcript;window.speechSynthesis?.cancel();renderPupil();return;}
  perform(async()=>{
    notice='';
    if(action==='logout'){await api('/api/auth/logout','POST',{});user=null;renderLogin();}
    if(action==='report'||action==='class'||action==='content'||action==='export-tab'||action==='audit'){tab=action==='export-tab'?'export':action;await loadWorkspace();await renderWorkspace();}
    if(action==='profile'){profile=await api(`/api/teacher/learners/${b.dataset.id}`);tab='profile';deleteConfirm=false;await renderWorkspace();}
    if(action==='analyze'){notify('Checking evidence and preparing a reviewable suggestion…');await api(`/api/teacher/learners/${profile.id}/analyze`,'POST',{});notice='';await refreshProfile();}
    if(action==='consent'){await api(`/api/teacher/learners/${profile.id}/consent`,'POST',{status:profile.consent_status==='withdrawn'?'synthetic_demo':'withdrawn'});await refreshProfile();}
    if(action==='confirm-delete'||action==='cancel-delete'){deleteConfirm=action==='confirm-delete';await renderWorkspace();}
    if(action==='delete'){await api(`/api/teacher/learners/${profile.id}`,'DELETE');profile=null;tab='class';await loadWorkspace();await renderWorkspace();notify('Learner and linked educational records deleted.');}
    if(action==='download'){const response=await fetch(`/api/research/export/${classId}`);if(!response.ok)throw Error('Export is unavailable for this account.');const url=URL.createObjectURL(await response.blob());const a=document.createElement('a');a.href=url;a.download='crosslearn-research.csv';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);}
    if(action==='check'){const result=await pupilRequest('crossword',{letters});if(result.stage==='crossword')notify(result.message,true);}
    if(action==='hint'){const keys=cellKeys(state.puzzle.find(c=>c.id===selectedWord));const cell=keys.find(k=>!letters[k])||keys[0];const h=await pupilRequest('hint',{cell});letters[h.cell]=h.letter;sessionStorage.setItem(`letters:${pupil.id}`,JSON.stringify(letters));renderPupil();}
    if(action==='next-question'&&state.stage==='retention'){
      const r=await api(`/api/pupil/${pupil.id}/retention`,'POST',{item_id:state.question.id,chosen_option:chosen,idempotency_key:`${pupil.id}:${state.question.id}`,read_aloud:readAloud},true);
      if(r.complete){await resumePupil();notify(`Delayed retention: ${r.correct}/6 correct.`);}else{state={stage:'retention',question:r.question,number:r.number,total:6};chosen=null;readAloud=false;renderPupil();}return;
    }
    if(action==='next-question'){await pupilRequest('responses',{item_id:state.question.id,chosen_option:chosen,idempotency_key:`${pupil.id}:${state.question.id}`,read_aloud:readAloud});}
    if(action==='next-lesson'){await pupilRequest('exposure',{concept_id:state.lesson.id,transcript,audio_played:audioPlayed});}
    if(action==='teacher-login'){window.speechSynthesis?.cancel();state=null;renderLogin();}
    if(action==='open-retention'){
      if(pending.length) throw Error('Synchronize queued answers first.');
      pupil=await api(`/api/teacher/sessions/${b.dataset.id}/retention-access`,'POST',{});
      sessionStorage.setItem('crosslearn-pupil',JSON.stringify(pupil));
      await api('/api/auth/logout','POST',{});user=null;await resumePupil();
      const r=await api(`/api/pupil/${pupil.id}/retention`,'GET',undefined,true);
      if(r.question){state={stage:'retention',question:r.question,number:r.number,total:6};chosen=null;renderPupil();}else notify(`Retention already complete: ${r.correct}/6.`);
    }
    if(action==='retention'){
      const r=await api(`/api/pupil/${pupil.id}/retention`,'GET',undefined,true);
      if(!r.available) {notify(`Retention check opens ${date(r.due_at)}.`);return;}
      if(r.complete) {notify(`Delayed retention: ${r.correct}/6 correct.`);return;}
      state={stage:'retention',question:r.question,number:r.number,total:6};chosen=null;renderPupil();
    }
    if(action==='resume'){await resumePupil();}
  });
});

app.addEventListener('change',e=>{if(e.target.id==='class-select')perform(async()=>{classId=e.target.value;await loadWorkspace();await renderWorkspace();});});
function focusCell(key) {document.querySelector(`[data-cell="${key}"]`)?.focus();}
app.addEventListener('focusin',e=>{const key=e.target.dataset.cell;if(!key)return;if(!cellKeys(state.puzzle.find(c=>c.id===selectedWord)).includes(key))selectedWord=state.puzzle.find(c=>cellKeys(c).includes(key)).id;
  document.querySelectorAll('[data-cell]').forEach(el=>el.parentElement.classList.toggle('selected',cellKeys(state.puzzle.find(c=>c.id===selectedWord)).includes(el.dataset.cell)));e.target.select();});
app.addEventListener('input',e=>{const key=e.target.dataset.cell;if(!key)return;const value=e.target.value.replace(/[^a-z]/gi,'').slice(-1).toUpperCase();letters[key]=value;e.target.value=value;sessionStorage.setItem(`letters:${pupil.id}`,JSON.stringify(letters));if(value){const keys=cellKeys(state.puzzle.find(c=>c.id===selectedWord));focusCell(keys[keys.indexOf(key)+1]);}});
app.addEventListener('keydown',e=>{const key=e.target.dataset.cell;if(!key)return;const keys=cellKeys(state.puzzle.find(c=>c.id===selectedWord));if(e.key==='Backspace'&&!e.target.value){e.preventDefault();focusCell(keys[keys.indexOf(key)-1]);}if(e.key.startsWith('Arrow')){e.preventDefault();const vertical=['ArrowDown','ArrowUp'].includes(e.key),word=state.puzzle.find(c=>cellKeys(c).includes(key)&&c.direction===(vertical?'down':'across'));if(word)selectedWord=word.id;const [r,c]=key.split('-').map(Number);focusCell(`${r+(e.key==='ArrowDown'?1:e.key==='ArrowUp'?-1:0)}-${c+(e.key==='ArrowRight'?1:e.key==='ArrowLeft'?-1:0)}`);}});

window.addEventListener('offline',()=>notify('You’re offline. Keep this tab open and retry when connected; only confirmed submissions are saved.',true));
window.addEventListener('online',()=>perform(async()=>{if(pupil&&pending.length){await syncPending();notify('Queued answers synchronized.');}else notify('Connection restored.');}));

try {pupil=JSON.parse(sessionStorage.getItem('crosslearn-pupil')||'null');}catch{}
try {user=await api('/api/auth/me');await loadWorkspace();await renderWorkspace();}
catch {if(pupil){try{await resumePupil();}catch(error){notify(error.message,true);renderLogin();}}else renderLogin();}

if ('serviceWorker' in navigator) navigator.serviceWorker.register('/sw.js').catch(()=>{});
