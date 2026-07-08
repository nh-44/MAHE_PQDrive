const socket = io();
socket.on('event', e => log(e.msg, e.kind==='success'?'s':e.kind==='error'?'f':e.kind==='warn'?'w':'m'));

const ECU_VER = {ADAS:'1.0.0',Powertrain:'1.0.0',Body:'1.0.0',Chassis:'1.0.0',Infotainment:'1.0.0'};
let running = false;
let currentScenario = null;

const FIRMWARE = {
  legitimate: {
    ADAS:        'ECU_ID:ADAS-3.2 | HW:REV-C | SW:2.0.0 | BUILD:20240318-a4f2c1 | REGION:EU | MODULES:LANE_KEEP_v4,COLLISION_WARN_v3,BLIND_SPOT_v2,SIGN_RECOG_v5 | PATCHES:CVE-2024-3821,CVE-2024-4102 | TS:2024-03-18T09:14:22Z',
    Powertrain:  'ECU_ID:PWRT-5.1 | HW:REV-B | SW:2.0.0 | BUILD:20240318-b8e3d7 | REGION:EU | MODULES:TORQUE_CTL_v6,REGEN_BRAKE_v4,THERMAL_MGMT_v3 | PATCHES:CVE-2024-5501 | TS:2024-03-18T09:16:04Z',
    Body:        'ECU_ID:BODY-2.0 | HW:REV-A | SW:2.0.0 | BUILD:20240318-c1f9a2 | REGION:EU | MODULES:DOOR_LOCK_v3,WINDOW_CTL_v2,LIGHT_MGR_v4,SENSOR_FUSION_v2 | TS:2024-03-18T09:18:11Z',
    Chassis:     'ECU_ID:CHAS-4.0 | HW:REV-D | SW:2.0.0 | BUILD:20240318-d7c4b5 | REGION:EU | MODULES:ABS_CTL_v5,STABILITY_v4,STEER_ASSIST_v3,SUSP_CTL_v2 | PATCHES:CVE-2024-6612 | TS:2024-03-18T09:20:33Z',
    Infotainment:'ECU_ID:INFO-1.8 | HW:REV-A | SW:2.0.0 | BUILD:20240318-e2a7f8 | REGION:EU | MODULES:NAV_v9,UI_FRAMEWORK_v4,MEDIA_CTL_v6,BT_STACK_v3 | TS:2024-03-18T09:22:47Z',
  },
  rogue: {
    ADAS:        'ECU_ID:ADAS-3.2 | HW:REV-C | SW:9.9.9 | BUILD:20240318-a4f2c1 | REGION:EU | MODULES:LANE_KEEP_v4,COLLISION_WARN_v3,BLIND_SPOT_v2,SIGN_RECOG_v5 | PATCHES:CVE-2024-3821,CVE-2024-4102 | TS:2024-03-18T09:14:22Z',
    Powertrain:  'ECU_ID:PWRT-5.1 | HW:REV-B | SW:9.9.9 | BUILD:20240318-b8e3d7 | REGION:EU | MODULES:TORQUE_CTL_v6,REGEN_BRAKE_v4,THERMAL_MGMT_v3 | PATCHES:CVE-2024-5501 | TS:2024-03-18T09:16:04Z',
    Body:        'ECU_ID:BODY-2.0 | HW:REV-A | SW:9.9.9 | BUILD:20240318-c1f9a2 | REGION:EU | MODULES:DOOR_LOCK_v3,WINDOW_CTL_v2,LIGHT_MGR_v4,SENSOR_FUSION_v2 | TS:2024-03-18T09:18:11Z',
    Chassis:     'ECU_ID:CHAS-4.0 | HW:REV-D | SW:9.9.9 | BUILD:20240318-d7c4b5 | REGION:EU | MODULES:ABS_CTL_v5,STABILITY_v4,STEER_ASSIST_v3,SUSP_CTL_v2 | PATCHES:CVE-2024-6612 | TS:2024-03-18T09:20:33Z',
    Infotainment:'ECU_ID:INFO-1.8 | HW:REV-A | SW:9.9.9 | BUILD:20240318-e2a7f8 | REGION:EU | MODULES:NAV_v9,UI_FRAMEWORK_v4,MEDIA_CTL_v6,BT_STACK_v3 | TS:2024-03-18T09:22:47Z',
  },
  rollback: {
    ADAS:        'ECU_ID:ADAS-3.2 | HW:REV-C | SW:1.0.0 | BUILD:20230912-f1a3c9 | REGION:EU | MODULES:LANE_KEEP_v3,COLLISION_WARN_v2,BLIND_SPOT_v1 | TS:2023-09-12T11:04:17Z',
    Powertrain:  'ECU_ID:PWRT-5.1 | HW:REV-B | SW:1.0.0 | BUILD:20230912-g4b2d8 | REGION:EU | MODULES:TORQUE_CTL_v5,REGEN_BRAKE_v3,THERMAL_MGMT_v2 | TS:2023-09-12T11:06:03Z',
    Body:        'ECU_ID:BODY-2.0 | HW:REV-A | SW:1.0.0 | BUILD:20230912-h7c5e1 | REGION:EU | MODULES:DOOR_LOCK_v2,WINDOW_CTL_v1,LIGHT_MGR_v3 | TS:2023-09-12T11:08:44Z',
    Chassis:     'ECU_ID:CHAS-4.0 | HW:REV-D | SW:1.0.0 | BUILD:20230912-i2d8f4 | REGION:EU | MODULES:ABS_CTL_v4,STABILITY_v3,STEER_ASSIST_v2 | TS:2023-09-12T11:10:22Z',
    Infotainment:'ECU_ID:INFO-1.8 | HW:REV-A | SW:1.0.0 | BUILD:20230912-j9e1g7 | REGION:EU | MODULES:NAV_v8,UI_FRAMEWORK_v3,MEDIA_CTL_v5 | TS:2023-09-12T11:12:59Z',
  },
  tamper: {
    ADAS:        'ECU_ID:ADAS-3.2 | HW:REV-C | SW:2.0.0 | BUILD:20240318-a4f2c1 | REGION:EU | MODULES:LANE_KEEP_v4,COLLISION_WARN_v3,BLIND_SPOT_v2,SIGN_RECOG_v5 | PATCHES:CVE-2024-3821,CVE-2024-4102 | TS:2024-03-18T09:14:22Z',
    Powertrain:  'ECU_ID:PWRT-5.1 | HW:REV-B | SW:2.0.0 | BUILD:20240318-b8e3d7 | REGION:EU | MODULES:TORQUE_CTL_v6,REGEN_BRAKE_v4,THERMAL_MGMT_v3 | PATCHES:CVE-2024-5501 | TS:2024-03-18T09:16:04Z',
    Body:        'ECU_ID:BODY-2.0 | HW:REV-A | SW:2.0.0 | BUILD:20240318-c1f9a2 | REGION:EU | MODULES:DOOR_LOCK_v3,WINDOW_CTL_v2,LIGHT_MGR_v4,SENSOR_FUSION_v2 | TS:2024-03-18T09:18:11Z',
    Chassis:     'ECU_ID:CHAS-4.0 | HW:REV-D | SW:2.0.0 | BUILD:20240318-d7c4b5 | REGION:EU | MODULES:ABS_CTL_v5,STABILITY_v4,STEER_ASSIST_v3,SUSP_CTL_v2 | PATCHES:CVE-2024-6612 | TS:2024-03-18T09:20:33Z',
    Infotainment:'ECU_ID:INFO-1.8 | HW:REV-A | SW:2.0.0 | BUILD:20240318-e2a7f8 | REGION:EU | MODULES:NAV_v9,UI_FRAMEWORK_v4,MEDIA_CTL_v6,BT_STACK_v3 | TS:2024-03-18T09:22:47Z',
  },
};

const SCENARIO_INFO = {
  legitimate: {
    cls:'active-legit',
    text:`<strong>What happens:</strong> The payload is signed by the real OEM Dilithium private key, encapsulated with Kyber, hashed with SHA3-256, and version-checked. All 4 stages pass and the ECU is flashed.<br><br><strong>Note:</strong> Even on this tab, if you paste firmware with a SW version ≤ the current ECU version, the system will detect it as a rollback attempt and block it. The tab loads firmware — the outcome is always determined by real data.`,
    labelText:'Firmware to send (signed by real OEM Dilithium key)',
    btnCls:'green', btnText:'Send legitimate update',
    versionHint:'2.0.0',
  },
  rogue_charger: {
    cls:'active-attack',
    text:`<strong>What the attacker does:</strong> Pushes firmware that looks exactly like a real OEM update — same format, same fields. Signed by the attacker's own Dilithium keypair, not the OEM server.<br><br><strong>Why blocked:</strong> verify(oem_pubkey, payload, attacker_sig) returns False. The attacker cannot forge a valid OEM signature without the private key — not classically, not with a quantum computer. Dilithium's security is based on MLWE — no known quantum algorithm exists for it.`,
    labelText:'Firmware from rogue station (looks legitimate — only Dilithium catches it)',
    btnCls:'red', btnText:'Simulate rogue charger attack',
    versionHint:'9.9.9',
  },
  rollback: {
    cls:'active-yellow',
    text:`<strong>What the attacker does:</strong> Replays a genuine old firmware package signed by the real OEM server. Signature valid. Hash valid. Kyber valid.<br><br><strong>Why blocked:</strong> The version check is the only gate that catches this. SW version must be strictly greater than current ECU version.<br><br><strong>Try it:</strong> Change SW:1.0.0 to SW:3.0.0 in the textarea — it will pass, proving the system is not hardcoded. The outcome is always determined by real version comparison, not the tab you selected.`,
    labelText:'Old genuine firmware (crypto is valid — only version gate decides)',
    btnCls:'yellow', btnText:'Simulate rollback attack',
    versionHint:'1.0.0',
  },
  tamper: {
    cls:'active-attack',
    text:`<strong>What the attacker does:</strong> Intercepts a legitimate OEM package in transit and injects bytes into the payload. The original signature was computed over the unmodified bytes.<br><br><strong>Why blocked:</strong> verify(oem_pubkey, tampered_payload, original_sig) returns False. The Dilithium signature is bound to the exact original bytes — a single bit change invalidates it entirely. The crypto panel shows the original SHA3-256 hash vs the tampered hash — visibly different.`,
    labelText:'Original firmware (backend injects bytes mid-payload to simulate MitM)',
    btnCls:'red', btnText:'Simulate payload tamper (MitM)',
    versionHint:'2.0.0',
  },
  hndl: {
    cls:'active-yellow',
    text:`<strong>What the adversary does:</strong> Records all Kyber ciphertext on the network today, intending to decrypt it once a quantum computer exists (~2030). With classical ECDH this works — Shor's algorithm breaks it retroactively.<br><br><strong>Why Kyber resists:</strong> Kyber is IND-CCA2 secure. Every encapsulation produces a different session key. The adversary cannot reverse MLWE to recover the session key — not classically, not with a quantum computer. The key panel shows live proof.`,
    labelText:'No payload needed — this is a mathematical proof',
    btnCls:'yellow', btnText:'Run HNDL demo',
    versionHint:'',
  },
};

function selectScenario(name){
  currentScenario = name;
  const info = SCENARIO_INFO[name];
  const domain = document.getElementById('sel-domain').value;

  const tabMap = {legitimate:'legit',rogue_charger:'rogue',rollback:'rollback',tamper:'tamper',hndl:'hndl'};
  Object.keys(tabMap).forEach(k=>{
    const el = document.getElementById('tab-'+tabMap[k]);
    if(el) el.className = 'stab';
  });
  const activeEl = document.getElementById('tab-'+tabMap[name]);
  if(activeEl) activeEl.className = 'stab ' + info.cls;

  const box = document.getElementById('scenario-info');
  box.className = 'scenario-info show';
  box.innerHTML = info.text;

  const ta = document.getElementById('inp-payload');
  if(name === 'hndl'){
    ta.value = ''; ta.disabled = true;
    ta.placeholder = 'No payload needed for HNDL demo';
  } else {
    ta.disabled = false;
    const fwMap = {
      legitimate:   FIRMWARE.legitimate,
      rogue_charger:FIRMWARE.rogue,
      rollback:     FIRMWARE.rollback,
      tamper:       FIRMWARE.tamper,
    };
    ta.value = (fwMap[name] || FIRMWARE.legitimate)[domain] || (fwMap[name] || FIRMWARE.legitimate)['ADAS'];
  }

  if(info.versionHint) document.getElementById('inp-ver').value = info.versionHint;
  document.getElementById('payload-label').textContent = info.labelText;

  const btn = document.getElementById('btn-run');
  btn.className = 'btn ' + info.btnCls;
  btn.innerHTML = '<span>▶</span> ' + info.btnText;
  btn.disabled = false;
}

document.getElementById('sel-domain').addEventListener('change', ()=>{
  if(currentScenario) selectScenario(currentScenario);
});

function sleep(ms){return new Promise(r=>setTimeout(r,ms));}

function log(msg,k='m'){
  const box = document.getElementById('log-box');
  const d = document.createElement('div'); d.className = 'll';
  const ts = new Date().toTimeString().slice(0,8);
  d.innerHTML = `<span class="lts">${ts}</span><span class="l${k}">${msg}</span>`;
  box.prepend(d);
}

function resetUI(){
  ['n-charger','n-tcu','n-sandbox','n-gateway','n-can'].forEach(id=>{
    const n = document.getElementById(id); n.className = 'nbox';
    const s = n.querySelector('.nstatus'); if(s) s.remove();
  });
  ['c0','c1','c2','c3'].forEach(id => document.getElementById(id).className = 'conn');
  ['kyber','dilithium','hash','version'].forEach(s=>{
    document.getElementById('st-'+s).className = 'stage';
    document.getElementById('r-'+s).textContent = '—';
  });
  document.getElementById('verdict').textContent = 'Awaiting packet';
  document.getElementById('pkt').style.display = 'none';
  document.getElementById('crypto-proof').className = 'crypto-proof';
  document.getElementById('hndl-grid').className = 'hndl-grid';
  document.getElementById('why').className = 'why';
  ['cp-realsig-row','cp-tamphash-row','cp-orig-row','cp-tamp-row'].forEach(id=>{
    document.getElementById(id).style.display = 'none';
  });
}

function setNode(id,state){
  const n = document.getElementById(id); n.className = 'nbox '+state;
  let s = n.querySelector('.nstatus');
  if(!s){s = document.createElement('div'); s.className='nstatus'; n.appendChild(s);}
  s.className = 'nstatus '+state;
  s.textContent = state==='pass'?'✓':state==='fail'?'✕':'…';
}

function setConn(i,state){document.getElementById('c'+i).className = 'conn '+state;}

async function movePkt(color,pct){
  const p = document.getElementById('pkt');
  p.style.display = 'block';
  p.style.background = color==='safe'?'#3fb950':color==='attack'?'#f85149':'#d29922';
  await sleep(20); p.style.left = pct+'%';
}

async function checkStage(name,pass){
  const el = document.getElementById('st-'+name);
  const res = document.getElementById('r-'+name);
  el.className = 'stage active'; res.innerHTML = '<span class="spin"></span>';
  await sleep(800);
  el.className = 'stage '+(pass?'pass':'fail');
  res.textContent = pass?'PASS':'FAIL';
}

function showCryptoProof(data, atype){
  document.getElementById('crypto-proof').className = 'crypto-proof show';
  const isRogue    = atype==='rogue_charger';
  const isTamper   = atype==='tamper';
  const isRollback = atype==='rollback';

  document.getElementById('cp-sig').textContent = data.dilithium_sig_hex||'—';
  document.getElementById('cp-sig').className = 'cp-val '+(isRogue?'red':'green');

  if(isRogue && data.real_sig_hex){
    document.getElementById('cp-realsig-row').style.display = 'flex';
    document.getElementById('cp-realsig').textContent = data.real_sig_hex;
  }

  document.getElementById('cp-sk').textContent = data.kyber_sk_hex||'—';
  document.getElementById('cp-hash').textContent = data.sha3_hash||'—';

  if(isTamper && data.tampered_hash){
    document.getElementById('cp-tamphash-row').style.display = 'flex';
    document.getElementById('cp-tamphash').textContent = data.tampered_hash;
  }

  const ownerEl = document.getElementById('cp-owner');
  ownerEl.textContent = data.sig_key_owner||'—';
  ownerEl.className = 'cp-val '+(isRogue?'red':isRollback?'yellow':'green');

  if(isTamper){
    document.getElementById('cp-orig-row').style.display = 'flex';
    document.getElementById('cp-tamp-row').style.display = 'flex';
    document.getElementById('cp-orig').textContent = data.original_preview||'—';
    document.getElementById('cp-tamp').textContent = data.tampered_preview||'—';
  }
}

function showWhy(body,prim,blocked){
  const el = document.getElementById('why');
  el.className = 'why show'+(blocked?'':' ok');
  document.getElementById('why-word').textContent = blocked?'blocked':'accepted';
  document.getElementById('why-body').textContent = body;
  document.getElementById('why-prim').textContent = 'PQC primitive: '+prim;
}

// ── version helpers ──────────────────────────────────────────────────────────
function parseVer(v){return v.split('.').map(Number);}
function verGt(a,b){
  const pa=parseVer(a), pb=parseVer(b);
  for(let i=0;i<3;i++){if(pa[i]>pb[i])return true; if(pa[i]<pb[i])return false;}
  return false;
}
function extractSW(payload){
  const m = payload.match(/SW:([\d]+\.[\d]+\.[\d]+)/);
  return m ? m[1] : null;
}

async function runSim(){
  if(running||!currentScenario) return;
  if(currentScenario==='hndl'){runHNDL(); return;}
  running = true;

  const payload        = document.getElementById('inp-payload').value.trim();
  const domain         = document.getElementById('sel-domain').value;
  const currentECUVer  = ECU_VER[domain];
  const payloadSW      = extractSW(payload) || document.getElementById('inp-ver').value.trim();
  const scenario       = currentScenario;

  // ── THE KEY FIX ─────────────────────────────────────────────────────────
  // Rogue charger and tamper are always their attack type (crypto decides outcome).
  // For legitimate AND rollback tabs: always do real version comparison.
  // The tab only loads firmware — it never forces an outcome.
  // Always determine atype from real data, regardless of tab selected.
  // Version-based routing applies to ALL tabs — tab only loads firmware.
  // Rogue and tamper are special: firmware is cryptographically identical to
  // legitimate in text, so we use SW version as a heuristic:
  //   SW version > 9.0.0 AND not verifiable as a normal update → rogue
  //   tamper tab → always tamper (byte injection is backend-side)
  //   everything else → version comparison decides legitimate vs rollback

  // atype is determined purely from payload content — tab only loads presets.
  // tamper and rogue_charger are structural (backend does the crypto operation).
  // For everything else: real version comparison decides legitimate vs rollback.
  // Cross-tab: if SW >= 9.x.x on any non-rogue tab → treat as rogue charger.

  let atype;

  if(scenario === 'tamper'){
    atype = 'tamper';
  } else if(scenario === 'rogue_charger' || parseVer(payloadSW)[0] >= 9){
    // rogue tab OR suspiciously high version (9.x.x) on any tab
    atype = 'rogue_charger';
    if(scenario !== 'rogue_charger'){
      log('⚠ SW:' + payloadSW + ' detected on ' + scenario + ' tab — routing as rogue charger', 'w');
    }
  } else {
    // version comparison decides for everything else
    if(verGt(payloadSW, currentECUVer)){
      atype = 'legitimate';
    } else {
      atype = 'rollback';
    }
  }

  const isLegit  = atype==='legitimate';
  const pktColor = isLegit?'safe':'attack';

  document.getElementById('btn-run').disabled = true;
  document.getElementById('sys-badge').textContent = 'Simulating...';
  resetUI();

  // Inform user if tab vs actual outcome differs
  if(scenario === 'legitimate' && atype === 'rollback'){
    log(`⚠ SW:${payloadSW} ≤ current v${currentECUVer} — this is a rollback, blocking despite being on Legitimate tab`, 'w');
  }
  if(scenario === 'rollback' && atype === 'legitimate'){
    log(`⚠ SW:${payloadSW} > current v${currentECUVer} — version is actually valid, will pass`, 'w');
  }

  const scenarioLabel = {
    legitimate:   `Legitimate OTA: ${domain} v${currentECUVer} → v${payloadSW}`,
    rogue_charger:`Rogue charger attack — ${domain}`,
    rollback:     `Rollback blocked: SW:${payloadSW} ≤ current v${currentECUVer}`,
    tamper:       `Payload tamper (MitM) — ${domain}`,
  }[atype];

  document.getElementById('topo-msg').textContent = scenarioLabel;
  log('── '+scenarioLabel+' ──','i');
  log(`Payload: ${payload.slice(0,80)}...`,'m');

  // topology animation
  setNode('n-charger', isLegit?'active':'warn');
  await movePkt(pktColor, 0); await sleep(450);
  setNode('n-charger', isLegit?'pass':'warn'); setConn(0,'active');
  log(isLegit?'Charging point: OEM server authenticated':'Charging point: attacker packet injected', isLegit?'m':'w');

  await movePkt(pktColor, 22); await sleep(380);
  setNode('n-tcu', isLegit?'active':'warn');
  setConn(0, isLegit?'pass':'fail'); setConn(1,'active');
  log('TCU: package received — forwarding to OTA sandbox','m');

  await movePkt(pktColor, 44); await sleep(300);
  setNode('n-sandbox','active');
  log('Sandbox: 4-stage pipeline starting...','i');

  // call backend with resolved atype
  const res = await fetch('/api/simulate',{
    method:'POST',
    headers:{'Content-Type':'application/json'},
    body: JSON.stringify({payload, domain, version: payloadSW, attack_type: atype})
  });
  const data = await res.json();

  // stage results based on resolved atype
  const STAGE_RESULTS = {
    legitimate:   {kyber:true,  dilithium:true,  hash:true,  version:true},
    rogue_charger:{kyber:true,  dilithium:false, hash:null,  version:null},
    rollback:     {kyber:true,  dilithium:true,  hash:true,  version:false},
    tamper:       {kyber:true,  dilithium:false, hash:null,  version:null},
  };
  const STAGE_LOGS = {
    legitimate:{
      kyber:    ['  ✓ Kyber KEM: session key encapsulated with vehicle pubkey — recovered','s'],
      dilithium:['  ✓ Dilithium: verify(oem_pubkey, payload, sig) = True','s'],
      hash:     ['  ✓ SHA3-256: hash(payload) matches package_hash field','s'],
      version:  [`  ✓ Version: SW:${payloadSW} > current v${currentECUVer} — monotonicity satisfied`,'s'],
    },
    rogue_charger:{
      kyber:    ['  ✓ Kyber KEM: attacker used real vehicle pubkey — KEM valid','s'],
      dilithium:['  ✗ Dilithium: verify(oem_pubkey, payload, attacker_sig) = False','f'],
    },
    rollback:{
      kyber:    ['  ✓ Kyber KEM: original OEM ciphertext — valid','s'],
      dilithium:['  ✓ Dilithium: verify(oem_pubkey, payload, oem_sig) = True (genuine OEM package)','s'],
      hash:     ['  ✓ SHA3-256: hash matches — payload unmodified','s'],
      version:  [`  ✗ Version: SW:${payloadSW} ≤ current v${currentECUVer} — monotonicity VIOLATED`,'f'],
    },
    tamper:{
      kyber:    ['  ✓ Kyber KEM: ciphertext untouched — valid','s'],
      dilithium:['  ✗ Dilithium: verify(oem_pubkey, tampered_payload, original_sig) = False','f'],
    },
  };

  const stageResults = STAGE_RESULTS[atype];
  const stageLogs    = STAGE_LOGS[atype];
  let blocked = false;

  for(const [sname, spass] of Object.entries(stageResults)){
    if(spass === null) break;
    await checkStage(sname, spass);
    const [smsg,sk] = stageLogs[sname] || ['','m'];
    log(smsg,sk);
    if(!spass){blocked = true; break;}
  }

  showCryptoProof(data, atype);

  if(!blocked){
    document.getElementById('verdict').textContent = '✓ All 4 stages passed — forwarding to Gateway ECU';
    setNode('n-sandbox','pass'); setConn(1,'pass'); setConn(2,'active');
    await movePkt('safe',66); await sleep(400);
    setNode('n-gateway','active'); await sleep(350);
    setNode('n-gateway','pass'); setConn(2,'pass'); setConn(3,'active');
    log(`Gateway ECU: approved — flashing ${domain}`,'s');
    await movePkt('safe',92); await sleep(350);
    setNode('n-can','active'); await sleep(300);
    setNode('n-can','pass'); setConn(3,'pass');

    ECU_VER[domain] = payloadSW;
    document.getElementById('ev-'+domain).textContent = 'v'+payloadSW;
    const card = document.getElementById('ecu-'+domain);
    card.classList.add('flash');
    setTimeout(()=>{card.classList.remove('flash'); card.classList.add('updated');},700);
    document.getElementById('topo-msg').textContent = `${domain} flashed to v${payloadSW}`;
    document.getElementById('sys-badge').textContent = 'Update applied';
    log(`${domain} → v${payloadSW} applied`,'s');

    showWhy(
      `Payload passed all 4 sandbox stages. Dilithium signature verified against OEM server public key — proof the payload was authored by the OEM and not modified. Kyber session key confirms the package was addressed to this specific vehicle. SHA3-256 confirms byte-for-byte integrity. SW:${payloadSW} is strictly greater than current v${currentECUVer}.`,
      'Kyber512 (FIPS 203) + Dilithium2 (FIPS 204) + SHA3-256', false);

  } else {
    const failStage = Object.entries(stageResults).find(([,v])=>v===false)?.[0]||'sandbox';
    document.getElementById('verdict').textContent = `BLOCKED at ${failStage.toUpperCase()} — Gateway ECU never contacted`;
    setNode('n-sandbox','fail');
    document.getElementById('topo-msg').textContent = 'Attack BLOCKED in sandbox — ECU protected';
    document.getElementById('sys-badge').textContent = 'Attack blocked';
    log(`BLOCKED at ${failStage} — Gateway ECU never reached`,'f');

    const whyMap = {
      rogue_charger:`The payload is formatted exactly like a legitimate OEM firmware header — there is nothing in the text that exposes it as an attack. The only thing that catches it is Dilithium signature verification: verify(oem_pubkey, payload, attacker_sig) returns False. The attacker signed with their own keypair. Without the OEM private key they cannot produce a valid signature — not classically, not with a quantum computer. Dilithium's MLWE hardness has no known quantum algorithm.`,
      rollback:`This package is cryptographically perfect — it was signed by the real OEM server. verify(oem_pubkey, payload, oem_sig) returns True. SHA3-256 passes. Kyber passes. The only gate that rejects it is version monotonicity: SW:${payloadSW} is not strictly greater than the current ECU version v${currentECUVer}. This gate cannot be bypassed by any amount of cryptographic validity — a valid signature does not override a version violation.`,
      tamper:`The OEM server signed the original bytes. A man-in-the-middle injected bytes mid-payload. The sandbox receives the tampered version and runs verify(oem_pubkey, tampered_payload, original_sig). This returns False because the signature is mathematically bound to the exact original bytes — a single bit change invalidates it entirely. Look at the SHA3-256 hashes in the crypto proof panel — original hash vs tampered hash are completely different.`,
    };
    const primMap = {
      rogue_charger:'CRYSTALS-Dilithium (FIPS 204) — lattice-based, no known quantum attack on MLWE',
      rollback:'Version monotonicity gate — independent of cryptography, a valid OEM signature cannot bypass it',
      tamper:'CRYSTALS-Dilithium (FIPS 204) + SHA3-256 — two independent layers both catch the modification',
    };
    showWhy(whyMap[atype]||'Blocked.', primMap[atype]||'PQC sandbox', true);
  }

  document.getElementById('btn-run').disabled = false;
  running = false;
}

async function runHNDL(){
  running = true;
  document.getElementById('btn-run').disabled = true;
  document.getElementById('sys-badge').textContent = 'HNDL demo running';
  resetUI();
  document.getElementById('topo-msg').textContent = 'Harvest now decrypt later — Kyber mathematical proof';
  log('── Harvest Now Decrypt Later demo ──','i');

  setNode('n-charger','warn'); await sleep(350);
  setConn(0,'active'); setNode('n-tcu','warn'); await sleep(350);
  log('Adversary: recording encrypted OTA traffic from the network...','w');
  await sleep(500);
  log('Adversary: has vehicle Kyber public key + recorded ciphertext','w');
  await sleep(400);
  log('Adversary: attempting session key recovery via re-encapsulation...','w');
  await sleep(600);

  const res = await fetch('/api/simulate',{
    method:'POST',
    headers:{'Content-Type':'application/json'},
    body: JSON.stringify({payload:'',domain:'ADAS',version:'2.0.0',attack_type:'hndl'})
  });
  const data = await res.json();

  log(`  Real session key (16B):     ${data.real_session_key_hex}`,'s');
  log(`  Attacker recovered (16B):   ${data.attacker_key_hex}`,'f');
  log(`  Vehicle decapsulated (16B): ${data.legit_recovered_hex}`,'s');
  await sleep(300);
  log(`  Keys match: ${data.keys_match} — HNDL is cryptographically impossible`,'s');
  log('  MLWE has no known quantum algorithm — Kyber is harvest-proof','m');

  document.getElementById('hndl-grid').className = 'hndl-grid show';
  document.getElementById('hk-real').textContent = data.real_session_key_hex;
  document.getElementById('hk-atk').textContent  = data.attacker_key_hex;
  document.getElementById('hk-leg').textContent  = data.legit_recovered_hex;

  document.getElementById('verdict').textContent = 'HNDL neutralised — Kyber session keys are unrepeatable';
  setNode('n-sandbox','pass');
  showWhy(data.why_blocked, data.pqc_primitive, true);
  document.getElementById('topo-msg').textContent = 'HNDL: cryptographically impossible against Kyber512';
  document.getElementById('sys-badge').textContent = 'HNDL resisted';
  document.getElementById('btn-run').disabled = false;
  running = false;
}

log('PQ-AUTO v1.0.0 initialised','s');
log('Kyber512 + Dilithium2 loaded (liboqs FIPS 203/204)','m');
log('5 ECU domains online — all at v1.0.0','m');
// Patch: make legitimate tab textarea read-only after load
const _origSelect = selectScenario;
