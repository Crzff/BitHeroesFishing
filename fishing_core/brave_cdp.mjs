// Transporte local y geometría; nunca imprime respuestas CDP, títulos ni URLs.
// https://chromedevtools.github.io/devtools-protocol/tot/Page/
// https://chromedevtools.github.io/devtools-protocol/tot/Input/#method-dispatchKeyEvent
// WebSocket nativo: https://nodejs.org/api/globals.html#class-websocket
import { createInterface } from 'node:readline';
import { pathToFileURL } from 'node:url';
import { promises as fs } from 'node:fs';
import path from 'node:path';
import net from 'node:net';
import {frames,MAX_MESSAGE} from './cdp_broker.mjs';
// Calibrado en vivo (SETTINGS, KORTZZ): 1 evento de deltaY=100 = 1 paso de rueda XTest. Unity solo atiende la rueda
// si antes llega mouseMoved sobre el canvas.
export const WHEEL_DELTA_PER_STEP=100;
export function gamePage(value){
  try{
    const u=new URL(value);
    return u.protocol==='https:' && u.hostname==='www.kongregate.com' && !u.username && !u.password &&
      (!u.port || u.port==='443') && ['/en/games/Juppiomenz/bit-heroes','/games/Juppiomenz/bit-heroes',
        '/en/games/juppiomenz/bit-heroes'].includes(u.pathname);
  }catch{return false;}
}

const same=(a,b)=>Array.isArray(a) && a.length===b.length && a.every((n,i)=>n===b[i]);
const validTarget=value=>typeof value==='string' && /^[0-9a-f]{32}$/i.test(value);
const fullQuad=[0,0,1920,0,1920,1080,0,1080];
const refuse=()=>{throw Error('BRAVE_GUARD');};
export function validView(v){
  return !!v && same(v.size,[1920,1080]) && v.dpr===1 && same(v.visual,[0,0,1920,1080,1]) &&
    same(v.scroll,[0,0]) && v.focused===true && v.visible===true && Array.isArray(v.canvases);
}

export async function snapshot(c){
  const {targetInfos}=await c.call('Target.getTargets');
  const pages=targetInfos.filter(t=>t.type==='page' && gamePage(t.url));
  if(pages.length!==1 || pages[0].targetId!==c.target)refuse();
  const {windowId,bounds}=await c.call('Browser.getWindowForTarget',{targetId:c.target});
  if(!Number.isSafeInteger(windowId) || windowId<=0 || !bounds || bounds.windowState==='minimized' ||
    !same([bounds.left,bounds.top,bounds.width,bounds.height],[0,0,1920,1080]))refuse();
  await c.settle();
  const frames=new Map(),roots=new Map();let root;
  for(const session of c.sessions.keys()){
    const {frameTree}=await c.call('Page.getFrameTree',{},session);
    if(session===c.root)root=frameTree.frame.id;
    if(roots.has(frameTree.frame.id))refuse();roots.set(frameTree.frame.id,session);
    const visit=(tree,parent)=>{
      const f=tree.frame,old=frames.get(f.id);
      if(typeof f.id!=='string' || !f.id || f.id.length>128 || typeof f.loaderId!=='string' || !f.loaderId ||
        f.loaderId.length>128 || frames.size>128 || (old && old.loader!==f.loaderId))refuse();
      frames.set(f.id,{id:f.id,loader:f.loaderId,parent:f.parentId ?? parent ?? old?.parent,
        children:[...new Set([...(old?.children ?? []),...(tree.childFrames ?? []).map(t=>t.frame.id)])]});
      for(const child of tree.childFrames ?? [])visit(child,f.id);
    };
    visit(frameTree);
  }
  // Page.getFrameTree puede omitir OOPIF; su sesión aporta el parentId explícito.
  for(const frame of frames.values()){
    if(frame.parent && frames.has(frame.parent)){
      const parent=frames.get(frame.parent);
      if(!parent.children.includes(frame.id))parent.children.push(frame.id);
    }
  }
  for(const frame of frames.values()){
    let id=frame.id;const seen=new Set();
    while(!roots.has(id)){
      if(!frames.has(id) || seen.has(id))refuse();seen.add(id);id=frames.get(id).parent;
    }
    frame.session=roots.get(id);
  }
  const result={window:windowId,chain:[]};let id=root;const seen=new Set();
  // ponytail: máximo ocho niveles observables; ampliar solo con una cadena real calibrada.
  for(let depth=0;depth<8;depth++){
    const frame=frames.get(id);
    if(!frame || seen.has(id))refuse();seen.add(id);
    const v=await c.readFrame(frame);
    if(!validView(v) || (depth===0 && v.brave!==true) || !Number.isSafeInteger(v.context) || v.context<=0)refuse();
    result.chain.push([frame.id,frame.loader,frame.session,v.context]);
    const children=[];
    for(const child of frame.children){
      const next=frames.get(child);
      if(!next || next.parent!==id)refuse();
      const owner=await c.readOwner(frame,child);
      if(owner && owner.visible===true && same(owner.quad,fullQuad))children.push({id:child,owner:owner.id});
    }
    if(v.canvases.length){
      const canvas=v.canvases[0];
      if(v.canvases.length!==1 || children.length || !canvas || canvas.visible!==true ||
        !same(canvas.size,[1920,1080]) || !same(canvas.rect,[0,0,1920,1080]) ||
        !['BODY','CANVAS'].includes(v.activeTag))refuse();
      return result;
    }
    if(children.length!==1)refuse();
    result.chain[result.chain.length-1].push(children[0].owner);id=children[0].id;
  }
  refuse();
}

export class CDP{
  constructor(socket,target){
    this.socket=socket;this.target=target;this.root=null;this.next=0;this.pending=new Map();
    this.sessions=new Map();this.setup=[];this.contexts=new Map();this.failed=false;
    const dead=()=>{this.failed=true;for(const p of this.pending.values()){clearTimeout(p.timer);p.reject(Error('CDP_TRANSPORT'));}this.pending.clear();};
    socket.addEventListener('close',dead);socket.addEventListener('error',dead);
    socket.addEventListener('message',event=>{
      try{
        if(typeof event.data!=='string' || Buffer.byteLength(event.data)>MAX_MESSAGE)throw Error();
        const m=JSON.parse(event.data);
        if(m.id){
          const p=this.pending.get(m.id);if(!p)return;
          this.pending.delete(m.id);clearTimeout(p.timer);
          if(m.error)p.reject(Error('CDP_REJECTED'));else p.resolve(m.result);
        }else if(m.method==='Target.attachedToTarget' && m.params.targetInfo.type==='iframe'){
          this.addSession(m.params.sessionId,m.sessionId);
        }else if(m.method==='Target.detachedFromTarget'){
          this.sessions.delete(m.params.sessionId);
          if(m.params.sessionId===this.root)dead();
        }
      }catch{dead();socket.close();}
    });
  }

  call(method,params={},sessionId){
    if(this.failed || this.socket.readyState!==1)return Promise.reject(Error('CDP_TRANSPORT'));
    const id=++this.next;
    return new Promise((resolve,reject)=>{
      const timer=setTimeout(()=>{this.pending.delete(id);reject(Error('CDP_TRANSPORT'));},8000);  // Unity bloquea el hilo del iframe al cargar una escena (medido >1,5 s en vivo)
      this.pending.set(id,{resolve,reject,timer});
      try{this.socket.send(JSON.stringify({id,method,params,...(sessionId?{sessionId}:{})}));}
      catch{clearTimeout(timer);this.pending.delete(id);reject(Error('CDP_TRANSPORT'));}
    });
  }

  addSession(id,parent){
    if(this.sessions.has(id))return;
    if(this.sessions.size>=64){this.failed=true;return;}
    this.sessions.set(id,parent);
    this.setup.push(this.call('Target.setAutoAttach',{autoAttach:true,waitForDebuggerOnStart:false,flatten:true,
      filter:[{type:'iframe',exclude:false},{exclude:true}]},id).catch(()=>{this.failed=true;}));
  }

  async settle(){
    while(this.setup.length)await Promise.all(this.setup.splice(0));
    if(this.failed)refuse();
  }

  async readFrame(frame){
    const key=JSON.stringify([frame.session,frame.id,frame.loader]);
    if(!this.contexts.has(key)){
      const {executionContextId}=await this.call('Page.createIsolatedWorld',
        {frameId:frame.id,worldName:'bitheroes-geometry'},frame.session);
      this.contexts.set(key,executionContextId);
    }
    const context=this.contexts.get(key);
    const result=await this.call('Runtime.evaluate',{contextId:context,returnByValue:true,awaitPromise:true,
      timeout:6000,allowUnsafeEvalBlockedByCSP:false,expression:`(async()=>{
        const visible=e=>{const s=getComputedStyle(e);return s.display!=='none' && s.visibility==='visible' && Number(s.opacity)===1 && s.pointerEvents!=='none';};
        const v=visualViewport,cs=[...document.querySelectorAll('canvas')];
        return {size:[innerWidth,innerHeight],dpr:devicePixelRatio,
          visual:v?[v.offsetLeft,v.offsetTop,v.width,v.height,v.scale]:null,scroll:[scrollX,scrollY],
          focused:document.hasFocus(),visible:document.visibilityState==='visible',
          brave:!!(navigator.brave && await navigator.brave.isBrave()),activeTag:document.activeElement?.tagName,
          canvases:cs.slice(0,2).map(c=>{const r=c.getBoundingClientRect();return {size:[c.width,c.height],
            rect:[r.x,r.y,r.width,r.height],visible:visible(c)};})};
      })()`},frame.session);
    if(result.exceptionDetails || !result.result?.value)refuse();
    return {...result.result.value,context};
  }

  async readOwner(frame,child){
    let object;
    try{
      const {backendNodeId}=await this.call('DOM.getFrameOwner',{frameId:child},frame.session);
      const {model}=await this.call('DOM.getBoxModel',{backendNodeId},frame.session);
      object=(await this.call('DOM.resolveNode',{backendNodeId},frame.session)).object.objectId;
      const result=await this.call('Runtime.callFunctionOn',{objectId:object,returnByValue:true,
        functionDeclaration:"function(){const s=getComputedStyle(this);return s.display!=='none' && s.visibility==='visible' && Number(s.opacity)===1 && s.pointerEvents!=='none';}"},frame.session);
      if(result.exceptionDetails)refuse();
      return {id:backendNodeId,quad:model.content,visible:result.result?.value===true};
    }catch(e){if(e.message==='CDP_REJECTED')return null;throw e;}
    finally{if(object)await this.call('Runtime.releaseObject',{objectId:object},frame.session);}
  }

  close(){this.socket.close();}
}

export async function openBrowser(port){
  if(typeof port==='string' && !/^\d+$/.test(port)){
    const stream=net.connect(port),listeners=new Map();
    const socket={readyState:0,addEventListener:(name,fn)=>{
      if(!listeners.has(name))listeners.set(name,[]);listeners.get(name).push(fn);
    },send:data=>{if(Buffer.byteLength(data)>MAX_MESSAGE)throw Error();stream.write(data+'\0');},close:()=>stream.destroy()};
    const emit=(name,event)=>{for(const fn of listeners.get(name) ?? [])fn(event);};
    stream.on('error',()=>emit('error'));stream.on('close',()=>{socket.readyState=3;emit('close');});
    frames(stream,m=>emit('message',{data:JSON.stringify(m)}),()=>stream.destroy());
    try{
      await new Promise((resolve,reject)=>{
        const timer=setTimeout(()=>{stream.destroy();reject(Error('CDP_TRANSPORT'));},1500);
        stream.once('connect',()=>{clearTimeout(timer);socket.readyState=1;resolve();});
        stream.once('error',()=>{clearTimeout(timer);reject(Error('CDP_TRANSPORT'));});
      });
      return new CDP(socket,null);
    }catch{stream.destroy();throw Error('CDP_TRANSPORT');}
  }
  if(typeof port==='string')port=Number(port);
  if(!Number.isInteger(port) || port<1 || port>65535)refuse();
  const response=await fetch(`http://127.0.0.1:${port}/json/version`,{redirect:'error',signal:AbortSignal.timeout(1500)});
  if(!response.ok)refuse();
  let size=0;const parts=[];
  for await(const chunk of response.body){size+=chunk.length;if(size>16384)refuse();parts.push(chunk);}
  const u=new URL(JSON.parse(Buffer.concat(parts).toString()).webSocketDebuggerUrl);
  if(u.protocol!=='ws:' || u.hostname!=='127.0.0.1' || u.port!==String(port) || u.username || u.password || u.search || u.hash ||
    !/^\/devtools\/browser\/[a-f0-9-]{16,64}$/i.test(u.pathname))refuse();
  const socket=new WebSocket(u.href);let client;
  try{
    await new Promise((resolve,reject)=>{
      const timer=setTimeout(()=>reject(Error('CDP_TRANSPORT')),1500);
      socket.addEventListener('open',()=>{clearTimeout(timer);resolve();},{once:true});
      socket.addEventListener('error',()=>{clearTimeout(timer);reject(Error('CDP_TRANSPORT'));},{once:true});
    });
    client=new CDP(socket,null);return client;
  }catch{socket.close();throw Error('CDP_TRANSPORT');}
}

async function attachTarget(c,target){
  if(!validTarget(target) || c.root!==null)refuse();
  c.target=target;c.root=(await c.call('Target.attachToTarget',{targetId:target,flatten:true})).sessionId;
  if(typeof c.root!=='string' || !c.root)refuse();
  c.addSession(c.root,null);await c.settle();
}

export async function openCDP(port,target){
  if(!validTarget(target))refuse();
  const c=await openBrowser(port);
  try{
    if(typeof port==='string' && !/^\d+$/.test(port)){
      const pages=await startupPages(c);
      const games=pages.filter(t=>gamePage(t.url));
      if(games.length!==1 || games[0].targetId!==target)refuse();
    }
    await attachTarget(c,target);return c;
  }
  catch{c.close();throw Error('CDP_TRANSPORT');}
}

async function startupPages(c){
  const {targetInfos}=await c.call('Target.getTargets');
  if(!Array.isArray(targetInfos) || targetInfos.length>128)refuse();
  const pages=targetInfos.filter(t=>t.type==='page');
  if(pages.some(t=>!validTarget(t.targetId) || typeof t.url!=='string') ||
    new Set(pages.map(t=>t.targetId)).size!==pages.length)refuse();
  return pages;
}

async function closeEmptyRestore(c,target){
  if(!(c.startupBlanks instanceof Set) || c.startupBlanks.size || !validTarget(target) || target===c.target)refuse();
  const {sessionId}=await c.call('Target.attachToTarget',{targetId:target,flatten:true});
  if(typeof sessionId!=='string' || !sessionId)refuse();
  let empty;
  try{
    const r=await c.call('Runtime.evaluate',{returnByValue:true,timeout:1000,
      expression:"location.href==='about:blank' && document.body?.childNodes.length===0 && document.head?.childNodes.length===0"},sessionId);
    empty=!r.exceptionDetails && r.result?.value===true;
  }finally{await c.call('Target.detachFromTarget',{sessionId});}
  if(!empty || (await c.call('Target.closeTarget',{targetId:target})).success!==true)refuse();
  c.startupBlanks.add(target);
}

export async function prepareTarget(c,viewportTimeout=2000){
  // Solo arranque explícito sobre un proceso/perfil previamente verificado por el dueño.
  // No se usa para reparar una guarda activa, restaurar UNKNOWN ni iniciar motores.
  try{
    c.startupStage='blank';
    if(c.target!==null || c.root!==null || !Number.isInteger(viewportTimeout) || viewportTimeout<0 || viewportTimeout>5000)refuse();
    const initial=await startupPages(c);
    if(initial.length>1 || initial.some(t=>!gamePage(t.url)))refuse();
    const {targetId}=await c.call('Target.createTarget',{url:'about:blank',newWindow:true,
      windowState:'fullscreen',left:0,top:0,width:1920,height:1080});
    if(!validTarget(targetId) || initial.some(t=>t.targetId===targetId))refuse();
    c.target=targetId;c.startupBlanks=new Set();
    const pages=await startupPages(c),own=pages.find(t=>t.targetId===targetId),restored=pages.filter(t=>t.targetId!==targetId);
    const games=restored.filter(t=>gamePage(t.url)),blanks=restored.filter(t=>t.url==='about:blank');
    if(own?.url!=='about:blank' || games.length>1 || blanks.length>1 || restored.length!==games.length+blanks.length ||
      games.some(t=>initial.length && t.targetId!==initial[0].targetId))refuse();
    if(blanks.length)await closeEmptyRestore(c,blanks[0].targetId);
    for(const t of games){
      if((await c.call('Target.closeTarget',{targetId:t.targetId})).success!==true)refuse();
    }
    const soleBlank=async()=>{
      const remaining=await startupPages(c);
      if(remaining.find(t=>t.targetId===targetId)?.url!=='about:blank' || remaining.some(t=>t.targetId!==targetId &&
        !restored.some(old=>old.targetId===t.targetId && (gamePage(t.url) || (t.url==='about:blank' && c.startupBlanks.has(t.targetId))))))refuse();
      return remaining.length===1;
    };
    // ponytail: closeTarget no prueba la retirada; 20 comprobaciones, ampliar solo con evidencia real.
    let closed=await soleBlank();
    for(let i=0;!closed && i<20;i++){
      await new Promise(resolve=>setTimeout(resolve,50));closed=await soleBlank();
    }
    if(!closed)refuse();
    await attachTarget(c,targetId);await c.call('Target.activateTarget',{targetId});
    const {windowId}=await c.call('Browser.getWindowForTarget',{targetId});
    if(!Number.isSafeInteger(windowId) || windowId<=0)refuse();
    await c.call('Browser.setWindowBounds',{windowId,bounds:{windowState:'normal'}});
    await c.call('Browser.setWindowBounds',{windowId,bounds:{left:0,top:0,width:1920,height:1080}});
    await c.call('Browser.setWindowBounds',{windowId,bounds:{windowState:'fullscreen'}});
    if(!await soleBlank())refuse();
    const result=await c.call('Runtime.evaluate',{returnByValue:true,userGesture:true,awaitPromise:true,
      expression:"location.href==='about:blank' && document.documentElement.requestFullscreen().then(()=>true,()=>false)"},c.root);
    if(result.exceptionDetails || result.result?.value!==true)refuse();
    const end=Date.now()+viewportTimeout;let f,identity;
    do{
      if(!await soleBlank())refuse();
      const {frameTree}=await c.call('Page.getFrameTree',{},c.root);f=frameTree.frame;
      if(f.url!=='about:blank' || typeof f.id!=='string' || !f.id || typeof f.loaderId!=='string' || !f.loaderId)refuse();
      const currentIdentity=JSON.stringify([f.id,f.loaderId]);
      if(identity && identity!==currentIdentity)refuse();identity=currentIdentity;
      const v=await c.readFrame({id:f.id,loader:f.loaderId,session:c.root});
      const current=await c.call('Browser.getWindowForTarget',{targetId}),bounds=current.bounds;
      if(current.windowId!==windowId || !bounds || bounds.windowState==='minimized')refuse();
      if(validView(v) && v.brave===true && !v.canvases.length && same([bounds.left,bounds.top,bounds.width,bounds.height],[0,0,1920,1080]))break;
      if(Date.now()>=end)refuse();
      await new Promise(resolve=>setTimeout(resolve,50));
    }while(true);
    if(!await soleBlank())refuse();
    const navigation=await c.call('Page.navigate',{url:'https://www.kongregate.com/en/games/Juppiomenz/bit-heroes'},c.root);
    if(navigation.errorText || navigation.isDownload || navigation.frameId!==f.id)refuse();
    c.startupNavigating=true;
    return targetId;  // Aún faltan Play/Fullscreen, guardas del juego y contraste de personaje.
  }catch{refuse();}  // Nunca propagar respuestas web, URLs, títulos ni errores CDP con datos privados.
}

async function soleOfficial(c){
  let pages=await startupPages(c);
  if(pages.length!==1){
    const own=pages.find(t=>t.targetId===c.target),extra=pages.filter(t=>t.targetId!==c.target);
    if(!own || (!gamePage(own.url) && own.url!=='about:blank') || extra.length!==1 || extra[0].url!=='about:blank' ||
      !(c.startupBlanks instanceof Set))refuse();
    const id=extra[0].targetId;
    if(!c.startupBlanks.has(id))await closeEmptyRestore(c,id);
    for(let i=0;i<20;i++){
      pages=await startupPages(c);
      if(pages.length===1)break;
      if(pages.length!==2 || !pages.some(t=>t.targetId===c.target) ||
        pages.some(t=>t.targetId!==c.target && (t.targetId!==id || t.url!=='about:blank')))refuse();
      await new Promise(resolve=>setTimeout(resolve,50));
    }
  }
  if(pages.length!==1 || pages[0].targetId!==c.target)refuse();
  if(gamePage(pages[0].url)){c.startupNavigating=false;return true;}
  if(pages[0].url==='' && c.startupNavigating===true)return false;  // Chromium aún no publicó la navegación propia.
  if(pages[0].url==='about:blank')return false;  // Solo la navegación inicial aún pendiente.
  refuse();
}

async function siteButton(c,selector,timeout){
  const end=Date.now()+timeout,tap=selector==='#fullscreen_button';
  do{
    if(await soleOfficial(c)){
      // Play usa DOM; Fullscreen necesita una pulsación real, no HTMLElement.click().
      // https://developer.mozilla.org/en-US/docs/Web/API/HTMLElement/click
      const r=await c.call('Runtime.evaluate',{returnByValue:true,userGesture:true,timeout:1000,expression:`(()=>{
        if(location.href==='about:blank')return 'missing';
        if(document.readyState!=='complete')return 'missing';
        if(location.protocol!=='https:' || location.hostname!=='www.kongregate.com' ||
          !['/en/games/Juppiomenz/bit-heroes','/en/games/juppiomenz/bit-heroes','/games/Juppiomenz/bit-heroes'].includes(location.pathname))return 'blocked';
        const es=document.querySelectorAll(${JSON.stringify(selector)});if(es.length===0)return 'missing';
        if(es.length!==1)return 'blocked';const e=es[0],r=e.getBoundingClientRect(),s=getComputedStyle(e);
        if(r.width<=0 || r.height<=0 || s.display==='none' || s.visibility!=='visible')return 'missing';
        // Kongregate 2026 (diseño "20 years"): los botones del juego quedan bajo el borde; traerlos a la vista y reintentar.
        if(r.bottom>innerHeight || r.top<0 || r.right>innerWidth || r.left<0){e.scrollIntoView({block:'center',inline:'center',behavior:'instant'});return 'missing';}  // instantáneo: con scroll suave el toque llegaba mientras el botón se movía
        const x=r.x+r.width/2,y=r.y+r.height/2,hit=document.elementFromPoint(x,y);
        if(e.tagName!=='BUTTON' || e.disabled || !document.hasFocus() || Number(s.opacity)!==1 ||
          s.pointerEvents==='none' || x<0 || y<0 || x>=innerWidth || y>=innerHeight || !hit || !e.contains(hit))return 'blocked';
        ${tap?'return [x,y];':"e.click();return 'clicked';"}})()`},c.root);
      const value=r.result?.value;
      if(r.exceptionDetails)refuse();
      if(tap && Array.isArray(value) && value.length===2 && value.every(Number.isFinite) &&
        value[0]>=0 && value[0]<1920 && value[1]>=0 && value[1]<1080){
        // CDP combina press/release; no quedan teclas retenidas ni se repite un efecto incierto.
        // https://chromedevtools.github.io/devtools-protocol/tot/Input/#method-synthesizeTapGesture
        await c.call('Input.synthesizeTapGesture',{x:value[0],y:value[1],gestureSourceType:'mouse',tapCount:1},c.root);return;
      }
      if(value==='clicked' && !tap)return;
      if(value!=='missing')refuse();
    }
    if(Date.now()>=end)refuse();
    await new Promise(resolve=>setTimeout(resolve,100));
  }while(true);
}

async function readyCanvas(c){
  await c.settle();const candidates=[];
  for(const session of c.sessions.keys()){
    const {frameTree}=await c.call('Page.getFrameTree',{},session),f=frameTree.frame;
    const v=await c.readFrame({id:f.id,loader:f.loaderId,session}),canvas=v.canvases?.[0];
    if(v.canvases?.length>1)refuse();
    if(v.visible===true && canvas?.visible===true && Array.isArray(canvas.size) && canvas.size.length===2 &&
      canvas.size.every(n=>Number.isSafeInteger(n)&&n>0) && Number.isSafeInteger(v.context) && v.context>0){
      candidates.push({session,context:v.context,view:v,canvas});
    }
  }
  if(candidates.length>1)refuse();return candidates[0];
}

export async function finishPreparation(c,timeout=30_000){
  try{
    if(!validTarget(c.target) || !c.root || !Number.isInteger(timeout) || timeout<0 || timeout>30_000)refuse();
    c.startupStage='play';
    await siteButton(c,'#gtm-play-now-button',timeout);
    c.startupStage='canvas';const readyEnd=Date.now()+timeout;
    while(true){
      if(!await soleOfficial(c))refuse();
      if(await readyCanvas(c))break;  // Sin aprobar geometría: primero debe existir el juego que recibe Fullscreen.
      if(Date.now()>=readyEnd)refuse();
      await new Promise(resolve=>setTimeout(resolve,100));
    }
    c.startupStage='fullscreen';
    await siteButton(c,'#fullscreen_button',timeout);
    const end=Date.now()+timeout;
    do{
      c.startupStage='canvas';
      if(!await soleOfficial(c))refuse();
      // El botón estaba bajo el borde (Kongregate 2026): con el juego ya en pantalla completa, volver la página a 0
      // para que la geometría estricta (scroll [0,0] en todos los frames) siga valiendo.
      await c.call('Runtime.evaluate',{returnByValue:true,timeout:1000,
        expression:"document.fullscreenElement && (scrollX||scrollY) && scrollTo({top:0,left:0,behavior:'instant'})"},c.root);
      const candidate=await readyCanvas(c);
      if(candidate && validView({...candidate.view,focused:true}) && same(candidate.canvas.size,[1920,1080]) &&
        same(candidate.canvas.rect,[0,0,1920,1080])){
        const {session,context}=candidate;
        const r=await c.call('Runtime.evaluate',{contextId:context,returnByValue:true,userGesture:true,
          expression:"(()=>{const c=document.querySelector('canvas');if(!c)return false;c.tabIndex=0;c.focus();return document.hasFocus() && document.activeElement===c;})()"},session);
        if(r.exceptionDetails || r.result?.value!==true)refuse();
        c.startupStage='snapshot';
        try{await snapshot(c);return;}catch(e){if(e.message!=='BRAVE_GUARD')throw e;}
      }
      if(Date.now()>=end)refuse();
      await new Promise(resolve=>setTimeout(resolve,100));
    }while(true);
  }catch{refuse();}
}

export async function runCommand(c,op,state,xy,steps,framePath){
  const point=['point','move','click','wheel'].includes(op);
  if(op==='check' || op==='escapeDown' || point || op==='frame'){
    if(op!=='check' && !state.identity)refuse();
    if(point && (!Array.isArray(xy) || xy.length!==2 || !xy.every(Number.isInteger) ||
      xy[0]<0 || xy[0]>=1920 || xy[1]<0 || xy[1]>=1080))refuse();
    if(op==='wheel' && (!Number.isSafeInteger(steps) || Math.abs(steps)>100))refuse();
    const geometry=await snapshot(c),current=JSON.stringify(geometry);
    if(state.identity && current!==state.identity)refuse();
    state.identity=current;
    if(op==='check')return;
    if(state.cancelled)refuse();
    if(point){
      for(const [, ,session,context,owner] of geometry.chain){
        let object,result;
        try{
          if(owner!==undefined){
            object=(await c.call('DOM.resolveNode',{backendNodeId:owner},session)).object.objectId;
            result=await c.call('Runtime.callFunctionOn',{objectId:object,returnByValue:true,
              arguments:xy.map(value=>({value})),
              functionDeclaration:'function(x,y){return this.ownerDocument.elementFromPoint(x,y)===this;}'},session);
          }else{
            result=await c.call('Runtime.evaluate',{contextId:context,returnByValue:true,timeout:6000,
              expression:`document.elementFromPoint(${xy[0]},${xy[1]})===document.querySelector('canvas') && !!document.querySelector('canvas')`},session);
          }
          if(result.exceptionDetails || result.result?.value!==true)refuse();
        }finally{if(object)await c.call('Runtime.releaseObject',{objectId:object},session);}
      }
      if(state.cancelled)refuse();
      const mouse=type=>c.call('Input.dispatchMouseEvent',{type,x:xy[0],y:xy[1],
        ...(type==='mousePressed'||type==='mouseReleased'?{button:'left',buttons:type==='mousePressed'?1:0,clickCount:1}:{}),
        ...(type==='mouseWheel'?{deltaX:0,deltaY:steps*WHEEL_DELTA_PER_STEP}:{})},c.root);
      if(op==='move'||op==='click')await mouse('mouseMoved');
      if(op==='click'){await mouse('mousePressed');await mouse('mouseReleased');}
      if(op==='wheel'){
        await mouse('mouseMoved');
        for(let i=0;i<Math.abs(steps);i++){
          if(state.cancelled)refuse();
          await c.call('Input.dispatchMouseEvent',{type:'mouseWheel',x:xy[0],y:xy[1],deltaX:0,deltaY:Math.sign(steps)*WHEEL_DELTA_PER_STEP},c.root);
          await new Promise(resolve=>setTimeout(resolve,40));
        }
      }
      return;
    }
    if(op==='frame'){
      if(typeof framePath!=='string' || !/^[a-zA-Z0-9_-]+\.png$/.test(framePath) || !state.framesDir)refuse();
      const dir=await fs.lstat(state.framesDir);
      if(!dir.isDirectory() || dir.isSymbolicLink() || (dir.mode&0o077))refuse();
      const destination=path.join(state.framesDir,framePath),temporary=destination+'.partial';
      // Nunca reemplazar un frame existente; el directorio es exclusivo del Bridge.
      try{await fs.lstat(destination);refuse();}catch(error){if(error.code!=='ENOENT')throw error;}
      const {data}=await c.call('Page.captureScreenshot',{format:'png',fromSurface:true,captureBeyondViewport:false,
        clip:{x:0,y:0,width:1920,height:1080,scale:1}},c.root);
      if(state.cancelled)refuse();
      const png=Buffer.from(data,'base64');
      if(png.length<24 || !png.subarray(0,8).equals(Buffer.from([137,80,78,71,13,10,26,10])) ||
        png.toString('ascii',12,16)!=='IHDR' || png.readUInt32BE(16)!==1920 || png.readUInt32BE(20)!==1080)refuse();
      const file=await fs.open(temporary,'wx',0o600);
      try{
        try{await file.writeFile(png);await file.sync();}finally{await file.close();}
        await fs.rename(temporary,destination);
      }finally{await fs.rm(temporary,{force:true});}
      return;
    }
    state.pressed=true;
    await c.call('Input.dispatchKeyEvent',{type:'rawKeyDown',key:'Escape',code:'Escape',windowsVirtualKeyCode:27},c.root);
  }else if(op==='escapeUp'){
    if(!state.pressed)return;
    try{await c.call('Input.dispatchKeyEvent',{type:'keyUp',key:'Escape',code:'Escape',windowsVirtualKeyCode:27},c.root);}
    finally{state.pressed=false;}
  }else refuse();
}

async function main(){
  let c;const startup=process.argv[3]==='--prepare',state={identity:null,pressed:false,cancelled:false};
  process.stdin.on('end',()=>{state.cancelled=true;if(startup)c?.close();});
  process.stdout.on('error',()=>{state.cancelled=true;if(startup)c?.close();});  // El padre murió: limpiar, no abortar por EPIPE.
  const answer=(id,ok)=>process.stdout.write(JSON.stringify({id,ok})+'\n');
  try{
    if(process.argv.length!==4 && !(process.argv.length===5 && !startup))refuse();
    if(process.argv[4])state.framesDir=path.resolve(process.argv[4]);
    if(startup){
      process.stdin.resume();c=await openBrowser(process.argv[2]);
      if(state.cancelled)refuse();
      const target=await prepareTarget(c);
      await finishPreparation(c);
      if(state.cancelled)refuse();
      process.stdout.write(JSON.stringify({id:0,ok:true,target})+'\n');return;
    }
    c=await openCDP(process.argv[2],process.argv[3]);answer(0,true);
    const lines=createInterface({input:process.stdin,crlfDelay:Infinity});
    for await(const line of lines){
      let request;
      try{
        if(line.length>1024)refuse();request=JSON.parse(line);
        if(!Number.isSafeInteger(request.id) || request.id<=0 || request.id>=2**31 ||
          Object.keys(request).sort().join(',')!==(request.op==='frame'?'id,op,path':request.op==='wheel'?'id,op,steps,xy':
            ['point','move','click'].includes(request.op)?'id,op,xy':'id,op'))refuse();
        await runCommand(c,request.op,state,request.xy,request.steps,request.path);answer(request.id,true);
      }catch{answer(Number.isSafeInteger(request?.id)?request.id:null,false);}
    }
  }catch{
    if(startup){
      const stage=['blank','play','fullscreen','canvas','snapshot'].includes(c?.startupStage)?c.startupStage:'connection';
      process.stdout.write(JSON.stringify({id:0,ok:false,stage})+'\n');
    }else answer(0,false);
  }
  finally{
    if(c){
      try{await runCommand(c,'escapeUp',state);}catch{/* Solo soltar la tecla original; nunca reenviar a otro target. */}
      c.close();
    }
  }
}

if(process.argv[1] && import.meta.url===pathToFileURL(process.argv[1]).href)await main();
