import assert from 'node:assert/strict';
import test from 'node:test';
import {runInNewContext} from 'node:vm';
import { promises as fs } from 'node:fs';
import path from 'node:path';
import { gamePage, validView, snapshot, CDP, runCommand, prepareTarget, finishPreparation } from '../fishing_core/brave_cdp.mjs';

const page='https://www.kongregate.com/en/games/Juppiomenz/bit-heroes';
const quad=[0,0,1920,0,1920,1080,0,1080];
const view={size:[1920,1080],dpr:1,visual:[0,0,1920,1080,1],scroll:[0,0],
  focused:true,visible:true,brave:true,activeTag:'BODY',canvases:[]};

function inputFixture(){
  const f=fixture(),call=f.client.call;f.inputs=[];
  f.client.call=async(method,params,session)=>{
    if(method.startsWith('Input.')){f.inputs.push({params,session});return {};}
    if(method==='DOM.resolveNode')return {object:{objectId:'owner'}};
    if(method==='Runtime.releaseObject')return {};
    if(method==='Runtime.evaluate'||method==='Runtime.callFunctionOn')return {result:{value:true}};
    if(method==='Page.captureScreenshot'){
      assert.equal(session,'root');assert.deepEqual(params.clip,{x:0,y:0,width:1920,height:1080,scale:1});
      const header=Buffer.alloc(24);Buffer.from([137,80,78,71,13,10,26,10]).copy(header);
      header.write('IHDR',12);header.writeUInt32BE(1920,16);header.writeUInt32BE(1080,20);
      return {data:header.toString('base64')};
    }
    return call(method,params,session);
  };
  return f;
}

test('CDP ratón: identidad, punto válido y eventos en la sesión raíz',async()=>{
  for(const op of ['move','click','wheel']){
    const f=inputFixture(),state={identity:null};
    await assert.rejects(runCommand(f.client,op,state,[10,20],2));
    await runCommand(f.client,'check',state);
    for(const xy of [[-1,0],[1920,0],[0,1080],[1.5,2],['1',2],[1,2,3]])
      await assert.rejects(runCommand(f.client,op,state,xy,2));
    assert.equal(f.inputs.length,0);
    await runCommand(f.client,op,state,[10,20],2);
    assert.deepEqual(f.inputs.map(i=>i.params.type),op==='click'?['mouseMoved','mousePressed','mouseReleased']:
      op==='move'?['mouseMoved']:['mouseMoved','mouseWheel','mouseWheel']);  // rueda: mover encima y un evento por paso
    assert.ok(f.inputs.every(i=>i.session==='root' && i.params.x===10 && i.params.y===20));
    if(op==='click')assert.ok(f.inputs.slice(1).every(i=>i.params.button==='left'));
    if(op==='wheel')assert.deepEqual(f.inputs.slice(1).map(i=>i.params.deltaY),[100,100]);  // calibrado en vivo
  }
});

test('CDP ratón: cambios de huella, overlays y pasos inválidos no envían eventos',async()=>{
  for(const op of ['move','click','wheel'])for(const kind of ['identity','overlay','steps']){
    const f=inputFixture(),state={identity:null};await runCommand(f.client,'check',state);
    if(kind==='identity')f.geometry.get('game').context++;
    if(kind==='overlay'){
      const call=f.client.call;f.client.call=(method,...args)=>method==='Runtime.callFunctionOn'?
        {result:{value:false}}:call(method,...args);
    }
    if(kind==='steps' && op!=='wheel')continue;
    await assert.rejects(runCommand(f.client,op,state,[10,20],kind==='steps'?1.5:1));
    assert.equal(f.inputs.length,0);
  }
});

test('CDP frame: identidad fija, archivo privado, sin sobrescritura ni salida del directorio',async()=>{
  const dir=await fs.mkdtemp(path.resolve('tests/.cdp-frame-'));
  try{
    const f=inputFixture(),state={identity:null,framesDir:dir};
    await assert.rejects(runCommand(f.client,'frame',state,undefined,undefined,'one.png'));
    await runCommand(f.client,'check',state);
    for(const name of ['../escape.png','/escape.png','nested/a.png'])
      await assert.rejects(runCommand(f.client,'frame',state,undefined,undefined,name));
    await runCommand(f.client,'frame',state,undefined,undefined,'one.png');
    assert.equal((await fs.stat(path.join(dir,'one.png'))).mode&0o777,0o600);
    assert.equal((await fs.readFile(path.join(dir,'one.png'))).readUInt32BE(16),1920);
    await assert.rejects(runCommand(f.client,'frame',state,undefined,undefined,'one.png'));
    f.geometry.get('root').dpr=2;
    await assert.rejects(runCommand(f.client,'frame',state,undefined,undefined,'two.png'));
    assert.deepEqual(await fs.readdir(dir),['one.png']);assert.equal(f.inputs.length,0);
  }finally{await fs.rm(dir,{recursive:true,force:true});}
});

test('CDP frame: PNG o tamaño inválido y directorio público no publican archivos',async()=>{
  const dir=await fs.mkdtemp(path.resolve('tests/.cdp-frame-'));
  try{
    for(const kind of ['format','size','permissions']){
      const f=inputFixture(),state={identity:null,framesDir:dir},call=f.client.call;
      await runCommand(f.client,'check',state);
      if(kind==='permissions')await fs.chmod(dir,0o755);
      else f.client.call=async(method,...args)=>{
        const result=await call(method,...args);
        if(method==='Page.captureScreenshot'){
          if(kind==='format')return {data:Buffer.from('not PNG').toString('base64')};
          const header=Buffer.from(result.data,'base64');header.writeUInt32BE(1024,20);
          return {data:header.toString('base64')};
        }
        return result;
      };
      await assert.rejects(runCommand(f.client,'frame',state,undefined,undefined,'bad.png'));
      assert.deepEqual(await fs.readdir(dir),[]);
    }
  }finally{await fs.chmod(dir,0o700);await fs.rm(dir,{recursive:true,force:true});}
});

test('solo la página oficial, sin confundir host, ruta o esquema',()=>{
  assert.ok(gamePage(page+'?ignored=PRIVATE_TEST_MARKER'));
  assert.ok(gamePage('https://www.kongregate.com/en/games/juppiomenz/bit-heroes'));
  for(const url of ['http://www.kongregate.com/en/games/Juppiomenz/bit-heroes',
    page+'.other',page.replace('www.kongregate.com','www.kongregate.com.evil'),'not a URL'])assert.equal(gamePage(url),false);
});

test('rechaza tamaño restaurado, zoom, escala, desplazamiento y falta de foco',()=>{
  assert.ok(validView(view));
  for(const [key,value] of [['size',[1920,1024]],['dpr',2],['visual',[0,0,1920,1080,1.1]],
    ['scroll',[0,1]],['focused',false],['visible',false]])assert.equal(validView({...view,[key]:value}),false);
});

function fixture(){
  const ids=['root','wrapper','game'];
  const trees=new Map(ids.map((id,i)=>[id,{frameTree:{frame:{id,loaderId:'load-'+id,...(i?{parentId:ids[i-1]}:{})},
    ...(i<2?{childFrames:[{frame:{id:ids[i+1],parentId:id,loaderId:'load-'+ids[i+1]}}]}:{})}}]));
  const geometry=new Map(ids.map(id=>[id,{...structuredClone(view),context:ids.indexOf(id)+1}]));
  geometry.get('game').canvases=[{size:[1920,1080],rect:[0,0,1920,1080],visible:true}];
  const client={target:'A'.repeat(32),root:'root',sessions:new Map(ids.map(id=>[id,true])),
    settle:async()=>{},call:async(method,params={},session)=>{
      if(method==='Target.getTargets')return {targetInfos:[{type:'page',targetId:client.target,url:page,title:'PRIVATE_TEST_MARKER'}]};
      if(method==='Browser.getWindowForTarget')return {windowId:4,bounds:{left:0,top:0,width:1920,height:1080,windowState:'normal'}};
      if(method==='Page.getFrameTree')return trees.get(session);
      throw Error('comando inesperado: '+method);
    },readFrame:async(frame)=>geometry.get(frame.id),readOwner:async()=>({id:10,quad,visible:true})};
  return {client,geometry,trees};
}

test('cadena de dos iframe en procesos distintos y canvas/buffer completo',async()=>{
  const {client}=fixture();const result=await snapshot(client);
  assert.equal(result.window,4);assert.equal(result.chain.length,3);
  assert.equal(JSON.stringify(result).includes('PRIVATE_TEST_MARKER'),false);
});

test('ningún canvas, duplicados, buffer distinto y iframe desplazado se rechazan',async()=>{
  for(const canvases of [[],[{size:[1280,720],rect:[0,0,1920,1080],visible:true}],
    [{size:[1920,1080],rect:[1,0,1920,1080],visible:true}],
    [{size:[1920,1080],rect:[0,0,1920,1080],visible:false}],
    Array(2).fill({size:[1920,1080],rect:[0,0,1920,1080],visible:true})]){
    const {client,geometry}=fixture();geometry.get('game').canvases=canvases;
    await assert.rejects(snapshot(client));
  }
  const {client}=fixture();client.readOwner=async()=>({id:10,quad:[1,0,1920,0,1920,1080,1,1080],visible:true});
  await assert.rejects(snapshot(client));
});

test('target cambiado y varias pestañas del juego no eligen otra cuenta',async()=>{
  for(const targetInfos of [[{type:'page',targetId:'B'.repeat(32),url:page}],
    ['A','B'].map(id=>({type:'page',targetId:id.repeat(32),url:page}))]){
    const {client}=fixture();const call=client.call;
    client.call=(method,...args)=>method==='Target.getTargets'?{targetInfos}:call(method,...args);
    await assert.rejects(snapshot(client));
  }
});

test('RPC y autoattach solo a iframe, sin pausar ni cerrar el navegador',async()=>{
  class Socket extends EventTarget{
    readyState=1;commands=[];
    send(raw){
      const command=JSON.parse(raw);this.commands.push(command);
      queueMicrotask(()=>this.dispatchEvent(new MessageEvent('message',{data:JSON.stringify({id:command.id,result:{}})})));
    }
    close(){this.readyState=3;this.dispatchEvent(new Event('close'));}
  }
  const socket=new Socket(),c=new CDP(socket,'A'.repeat(32));c.root='root';c.addSession('root',null);
  await c.settle();
  socket.dispatchEvent(new MessageEvent('message',{data:JSON.stringify({method:'Target.attachedToTarget',sessionId:'root',
    params:{sessionId:'child',targetInfo:{type:'iframe',title:'PRIVATE_TEST_MARKER',url:page}}})}));
  await c.settle();assert.equal(c.sessions.size,2);
  assert.ok(socket.commands.every(c=>c.method==='Target.setAutoAttach' && c.params.waitForDebuggerOnStart===false));
  c.close();await assert.rejects(c.call('Target.getTargets'));
  assert.equal(socket.commands.some(c=>c.method==='Browser.close'),false);
});

test('Escape fijado al target propio, sin nativeVirtualKeyCode ni fallback',async()=>{
  const {client}=fixture(),call=client.call,keys=[];const state={identity:null,pressed:false};
  client.call=async(method,params,session)=>{
    if(method==='Input.dispatchKeyEvent'){keys.push({params,session});return {};}
    return call(method,params,session);
  };
  await assert.rejects(runCommand(client,'escapeDown',state));assert.equal(keys.length,0);
  await runCommand(client,'check',state);await runCommand(client,'escapeDown',state);await runCommand(client,'escapeUp',state);
  assert.deepEqual(keys.map(k=>k.params.type),['rawKeyDown','keyUp']);
  assert.ok(keys.every(k=>k.session==='root' && k.params.key==='Escape' && k.params.windowsVirtualKeyCode===27 &&
    !Object.hasOwn(k.params,'nativeVirtualKeyCode')));
});

test('cambio de documento/contexto o de geometría bloquea Escape antes del input',async()=>{
  for(const kind of ['loader','context','geometry']){
    const {client,trees,geometry}=fixture(),call=client.call,keys=[];const state={identity:null,pressed:false};
    client.call=async(method,...args)=>{if(method==='Input.dispatchKeyEvent'){keys.push(method);return {};}
      return call(method,...args);};
    await runCommand(client,'check',state);
    if(kind==='loader')trees.get('game').frameTree.frame.loaderId='reloaded';
    if(kind==='context')geometry.get('game').context=999;
    if(kind==='geometry')geometry.get('wrapper').size=[1920,1024];
    await assert.rejects(runCommand(client,'escapeDown',state));await runCommand(client,'escapeUp',state);
    assert.equal(keys.length,0);
  }
});

test('una parada durante la comprobación impide un keyDown tardío',async()=>{
  const {client}=fixture(),call=client.call,keys=[];const state={identity:null,pressed:false,cancelled:false};
  client.call=async(method,...args)=>{if(method==='Input.dispatchKeyEvent'){keys.push(method);return {};}
    return call(method,...args);};
  await runCommand(client,'check',state);state.cancelled=true;
  await assert.rejects(runCommand(client,'escapeDown',state));await runCommand(client,'escapeUp',state);
  assert.equal(keys.length,0);
});

test('los procesos iframe se resuelven aunque las sesiones lleguen en otro orden',async()=>{
  const {client}=fixture();client.sessions=new Map([['game',true],['root',true],['wrapper',true]]);
  const result=await snapshot(client);
  assert.deepEqual(result.chain.map(f=>f[2]),['root','wrapper','game']);
});

test('CDP puede omitir el iframe remoto del árbol padre sin perder su parentId explícito',async()=>{
  const {client,trees}=fixture();trees.get('wrapper').frameTree.childFrames=[{frame:{id:'hidden',parentId:'wrapper',loaderId:'hidden-loader'}}];
  client.readOwner=async(parent,child)=>child==='hidden'?{id:11,quad:[],visible:false}:{id:10,quad,visible:true};
  const result=await snapshot(client);assert.deepEqual(result.chain.map(f=>f[2]),['root','wrapper','game']);
  trees.get('game').frameTree.frame.parentId='foreign';await assert.rejects(snapshot(client));
});

test('un overlay DOM bloquea el clic aunque el canvas mantenga tamaño y foco',async()=>{
  for(const blocked of [null,'root','wrapper','game']){
    const {client}=fixture(),call=client.call;const state={identity:null,pressed:false};
    client.call=async(method,params,session)=>{
      if(method==='DOM.resolveNode')return {object:{objectId:'iframe-owner'}};
      if(method==='Runtime.releaseObject')return {};
      if(method==='Runtime.callFunctionOn' || method==='Runtime.evaluate')return {result:{value:session!==blocked}};
      return call(method,params,session);
    };
    await runCommand(client,'check',state);
    if(blocked===null)await runCommand(client,'point',state,[10,20]);
    else await assert.rejects(runCommand(client,'point',state,[10,20]));
    for(const xy of [[1920,0],[-1,0],[10.5,20],['10',20]])await assert.rejects(runCommand(client,'point',state,xy));
  }
});

function startupFixture(options={}){
  const fresh='A'.repeat(32),old='B'.repeat(32),other='C'.repeat(32),commands=[];
  const restored={type:'page',targetId:old,url:page+'?private=PRIVATE_TEST_MARKER',title:'PRIVATE_TEST_MARKER'};
  let pages=options.empty?[]:[restored];const closing=new Set();
  const c={target:null,root:null,sessions:new Map(),addSession:()=>{},settle:async()=>{},
    readFrame:async()=>({...structuredClone(view),context:1,...options.geometry}),
    call:async(method,params={},session)=>{
      commands.push({method,params,session});
      if(method==='Target.getTargets'){
        const result={targetInfos:structuredClone(pages)};
        if(closing.size&&!options.neverCloses){pages=pages.filter(t=>!closing.has(t.targetId));closing.clear();}
        return result;
      }
      if(method==='Target.createTarget'){
        pages.push({type:'page',targetId:fresh,url:'about:blank'});
        if(options.delayedRestore)pages.push(restored);
        if(options.restoredBlank)pages.push({type:'page',targetId:other,url:'about:blank'});
        if(options.unexpected)pages.push({type:'page',targetId:'D'.repeat(32),url:'https://example.invalid/?private=PRIVATE_TEST_MARKER'});
        return {targetId:fresh};
      }
      if(method==='Target.closeTarget'){
        assert.ok(params.targetId===old || (options.restoredBlank && params.targetId===other));
        if(options.closeFails)return {success:false};
        closing.add(params.targetId);return {success:true};
      }
      if(method==='Target.attachToTarget'){
        if(options.restoredBlank && params.targetId===other)return {sessionId:'empty'};
        assert.equal(params.targetId,fresh);return {sessionId:'own'};
      }
      if(method==='Target.detachFromTarget'){assert.equal(params.sessionId,'empty');return {};}
      if(method==='Target.activateTarget'||method==='Browser.setWindowBounds')return {};
      if(method==='Browser.getWindowForTarget')return {windowId:7,bounds:{left:0,top:0,width:1920,height:1080,...options.bounds}};
      if(method==='Runtime.evaluate'){
        if(session==='empty')return {result:{value:!options.restoredBlankContent}};
        assert.equal(session,'own');assert.equal(pages.length,1);assert.equal(pages[0].url,'about:blank');
        return options.fullscreenFails?{exceptionDetails:{text:'PRIVATE_TEST_MARKER'}}:{result:{value:true}};
      }
      if(method==='Page.getFrameTree')return {frameTree:{frame:{id:'blank',loaderId:'blank-loader',url:'about:blank'}}};
      if(method==='Page.navigate'){
        assert.equal(pages.filter(t=>gamePage(t.url)).length,0,'nunca navegar mientras el juego restaurado sigue vivo');
        assert.equal(params.url,page);assert.equal(session,'own');pages[0].url=page;return {frameId:'blank'};
      }
      throw Error('PRIVATE_TEST_MARKER');
    }};
  return {c,commands,fresh,old,pages:()=>pages};
}

test('arranque: cierra la restauración antes de navegar y devuelve solo el target nuevo',async()=>{
  for(const options of [{},{empty:true},{empty:true,delayedRestore:true}]){
    const f=startupFixture(options);assert.equal(await prepareTarget(f.c),f.fresh);
    assert.equal(f.pages().length,1);assert.equal(f.pages()[0].targetId,f.fresh);
    assert.equal(f.commands.filter(c=>c.method==='Page.navigate').length,1);
    assert.ok(f.commands.filter(c=>c.method==='Target.closeTarget').every(c=>c.params.targetId===f.old));
    assert.equal(f.commands.some(c=>c.method==='Browser.close'||c.method.startsWith('Input.')),false);
  }
});

test('arranque: páginas ajenas, duplicadas o aparecidas durante la creación no se cierran ni se navegan',async()=>{
  for(const options of [{unexpected:true},{empty:true,delayedRestore:true,unexpected:true}]){
    const f=startupFixture(options);
    await assert.rejects(prepareTarget(f.c),error=>error.message==='BRAVE_GUARD');
    assert.equal(f.commands.some(c=>['Target.closeTarget','Runtime.evaluate','Page.navigate'].includes(c.method)),false);
  }
  for(const targetInfos of [[{type:'page',targetId:'D'.repeat(32),url:'https://example.invalid/'}],
    ['B','C'].map(id=>({type:'page',targetId:id.repeat(32),url:page}))]){
    const f=startupFixture(),call=f.c.call;
    f.c.call=(method,...args)=>method==='Target.getTargets'?{targetInfos}:call(method,...args);
    await assert.rejects(prepareTarget(f.c));assert.equal(f.commands.length,0);
  }
});

test('arranque: confirmación de cierre ausente impide la nueva carga',async()=>{
  for(const options of [{closeFails:true},{neverCloses:true}]){
    const f=startupFixture(options);await assert.rejects(prepareTarget(f.c,0));
    assert.equal(f.commands.some(c=>c.method==='Page.navigate'||c.method==='Runtime.evaluate'),false);
  }
});

test('arranque: ventana X equivalente no sustituye a verificar el viewport vacío real',async()=>{
  for(const options of [{geometry:{size:[1920,1024]}},{geometry:{size:[1910,1070]}},
    {geometry:{dpr:2}},{geometry:{scroll:[0,1]}},{geometry:{focused:false}},
    {geometry:{brave:false}},{geometry:{canvases:[{}]}},{bounds:{left:1}},{fullscreenFails:true}]){
    const f=startupFixture(options);await assert.rejects(prepareTarget(f.c,0));
    assert.equal(f.commands.some(c=>c.method==='Page.navigate'),false);
  }
});

test('arranque: una guarda ya fijada no puede sustituir su propia identidad',async()=>{
  const f=startupFixture();f.c.target=f.old;f.c.root='existing';
  await assert.rejects(prepareTarget(f.c));assert.equal(f.commands.length,0);
});

test('arranque: Fullscreen resuelto puede anteceder a la actualización del viewport; esperar sin navegar antes',async()=>{
  const f=startupFixture(),read=f.c.readFrame;let reads=0;
  f.c.readFrame=async frame=>{
    const v=await read(frame);return reads++===0?{...v,size:[1910,1070],visual:[0,0,1910,1070,1]}:v;
  };
  assert.equal(await prepareTarget(f.c),f.fresh);assert.equal(reads,2);
});

test('arranque: restauración tardía incluye una vacía del kiosco; cerrarla solo tras verificar DOM vacío',async()=>{
  const f=startupFixture({empty:true,delayedRestore:true,restoredBlank:true});
  assert.equal(await prepareTarget(f.c),f.fresh);assert.equal(f.pages().length,1);
  assert.ok(f.commands.some(c=>c.method==='Runtime.evaluate' && c.session==='empty' && !c.params.userGesture));
  assert.equal(f.commands.filter(c=>c.method==='Target.closeTarget').length,2);
  const g=startupFixture({empty:true,delayedRestore:true,restoredBlank:true,restoredBlankContent:true});
  await assert.rejects(prepareTarget(g.c));
  assert.equal(g.commands.some(c=>['Target.closeTarget','Page.navigate'].includes(c.method)),false);
});

test('arranque: tipos CDP inválidos y cambio de ventana durante Fullscreen se rechazan',async()=>{
  for(const kind of ['target-array','window-changed','frame-changed','navigation-error']){
    const f=startupFixture(),call=f.c.call;let windows=0;
    f.c.call=async(method,...args)=>{
      const result=await call(method,...args);
      if(kind==='target-array' && method==='Target.createTarget')return {targetId:[f.fresh]};
      if(kind==='window-changed' && method==='Browser.getWindowForTarget' && ++windows>1)result.windowId=99;
      if(kind==='frame-changed' && method==='Page.getFrameTree')result.frameTree.frame.url=page;
      if(kind==='navigation-error' && method==='Page.navigate')result.errorText='PRIVATE_TEST_MARKER';
      return result;
    };
    await assert.rejects(prepareTarget(f.c),error=>error.message==='BRAVE_GUARD');
    if(kind!=='navigation-error')assert.equal(f.commands.some(c=>c.method==='Page.navigate'),false);
  }
});

test('preparación completa: solo Play/Fullscreen del sitio y foco del canvas, sin teclas ni clics de juego',async()=>{
  const {client}=fixture(),call=client.call,actions=[];
  client.call=async(method,params,session)=>{
    if(method==='Runtime.evaluate'){
      if(params.expression.includes('scrollTo('))return {result:{value:false}};  // volver la página a 0: neutro
      assert.equal(params.userGesture,true);
      if(params.expression.includes('#gtm-play-now-button')){actions.push('play');return {result:{value:'clicked'}};}
      if(params.expression.includes('#fullscreen_button'))return {result:{value:[60,35]}};
      assert.equal(session,'game');actions.push('canvas-focus');return {result:{value:true}};
    }
    if(method==='Input.synthesizeTapGesture'){
      assert.equal(session,client.root);assert.deepEqual(params,{x:60,y:35,gestureSourceType:'mouse',tapCount:1});actions.push('fullscreen');return {};
    }
    assert.equal(method.startsWith('Input.'),false);return call(method,params,session);
  };
  await finishPreparation(client);assert.deepEqual(actions,['play','fullscreen','canvas-focus']);
});

test('preparación completa: no pulsar Play mientras el documento aún carga',async()=>{
  const {client}=fixture(),call=client.call;let plays=0,clicks=0;
  client.call=async(method,params,session)=>{
    if(method==='Input.synthesizeTapGesture'){clicks++;return {};}
    if(method!=='Runtime.evaluate')return call(method,params,session);
    if(!params.expression.includes('#'))return {result:{value:true}};
    const ready=params.expression.includes('#gtm-play-now-button') && plays++===0?'loading':'complete';
    const e={tagName:'BUTTON',disabled:false,getBoundingClientRect:()=>({x:10,y:10,width:100,height:50}),contains:()=>true,
      click:()=>{assert.equal(ready,'complete','No enviar una acción antes de que cargue el documento');clicks++;}};
    const value=runInNewContext(params.expression,{location:{href:page,protocol:'https:',hostname:'www.kongregate.com',pathname:'/en/games/Juppiomenz/bit-heroes'},
      document:{readyState:ready,querySelectorAll:()=>[e],hasFocus:()=>true,elementFromPoint:()=>e},innerWidth:1920,innerHeight:1080,
      getComputedStyle:()=>({display:'block',visibility:'visible',opacity:'1',pointerEvents:'auto'})});
    return {result:{value}};
  };
  await finishPreparation(client);assert.equal(clicks,2);assert.equal(plays,2);
});

test('Fullscreen requiere una pulsación nativa única sobre su botón, no HTMLElement.click',async()=>{
  const {client}=fixture(),call=client.call;let synthetic=0,native=0;
  const e={tagName:'BUTTON',disabled:false,getBoundingClientRect:()=>({x:10,y:10,width:100,height:50}),contains:()=>true,click:()=>{synthetic++;}};
  client.call=async(method,params,session)=>{
    if(method==='Input.synthesizeTapGesture'){
      assert.equal(session,client.root);assert.deepEqual(params,{x:60,y:35,gestureSourceType:'mouse',tapCount:1});native++;return {};
    }
    if(method==='Runtime.evaluate'){
      if(params.expression.includes('#gtm-play-now-button'))return {result:{value:'clicked'}};
      if(!params.expression.includes('#fullscreen_button'))return {result:{value:true}};
      const value=runInNewContext(params.expression,{location:{href:page,protocol:'https:',hostname:'www.kongregate.com',pathname:'/en/games/Juppiomenz/bit-heroes'},
        document:{readyState:'complete',querySelectorAll:()=>[e],hasFocus:()=>true,elementFromPoint:()=>e},innerWidth:1920,innerHeight:1080,
        getComputedStyle:()=>({display:'block',visibility:'visible',opacity:'1',pointerEvents:'auto'})});
      return {result:{value}};
    }
    return call(method,params,session);
  };
  await finishPreparation(client);assert.equal(synthetic,0);assert.equal(native,1);
});

test('Fullscreen espera al canvas del juego: el botón visible no acredita que el iframe esté listo',async()=>{
  const {client}=fixture(),call=client.call,read=client.readFrame;let gameReads=0,taps=0;
  client.readFrame=async(frame)=>{
    const v=await read(frame);
    return frame.id==='game' && gameReads++===0?{...v,canvases:[]}:v;
  };
  client.call=async(method,params,session)=>{
    if(method==='Runtime.evaluate')return {result:{value:params.expression.includes('#fullscreen_button')?[60,35]:params.expression.includes('#')?'clicked':true}};
    if(method==='Input.synthesizeTapGesture'){assert.ok(gameReads>=2,'No pulsar antes de crear el canvas');taps++;return {};}
    return call(method,params,session);
  };
  await finishPreparation(client,1000);assert.equal(taps,1);
});

test('Fullscreen: puntos malformados bloquean y un transporte incierto nunca repite la pulsación',async()=>{
  for(const value of [[-1,35],[1920,35],[60,1080],[60,null],[60,35,1],{x:60,y:35},'clicked',[60,35]]){
    const {client}=fixture(),call=client.call;let taps=0;
    client.call=async(method,params,session)=>{
      if(method==='Runtime.evaluate')return {result:{value:params.expression.includes('#gtm-play-now-button')?'clicked':value}};
      if(method==='Input.synthesizeTapGesture'){taps++;throw Error('CDP_TRANSPORT');}
      return call(method,params,session);
    };
    await assert.rejects(finishPreparation(client,0));
    assert.equal(taps,Array.isArray(value)&&value.length===2&&value[0]===60&&value[1]===35?1:0);
    assert.equal(client.startupStage,'fullscreen');
  }
});

test('arranque: URL vacía transitoria solo tras la navegación propia y antes del origen oficial',async()=>{
  const startup=startupFixture();await prepareTarget(startup.c);
  assert.equal(startup.c.startupNavigating,true);
  const {client}=fixture(),call=client.call,actions=[];client.startupNavigating=true;let reads=0;
  client.call=async(method,params,session)=>{
    if(method==='Target.getTargets' && reads++===0)return {targetInfos:[{type:'page',targetId:client.target,url:''}]};
    if(method==='Runtime.evaluate'){
      if(params.expression.includes('scrollTo('))return {result:{value:false}};  // volver la página a 0: neutro
      actions.push(params.expression.includes('#gtm-play-now-button')?'play':params.expression.includes('#fullscreen_button')?'fullscreen':'focus');
      return {result:{value:params.expression.includes('#fullscreen_button')?[60,35]:params.expression.includes('#')?'clicked':true}};
    }
    if(method==='Input.synthesizeTapGesture')return {};
    return call(method,params,session);
  };
  await finishPreparation(client,1000);
  assert.deepEqual(actions,['play','fullscreen','focus']);assert.equal(client.startupNavigating,false);
});

test('arranque: URL vacía sin navegación propia o tras Play sigue bloqueada sin repetir acciones',async()=>{
  for(const afterPlay of [false,true]){
    const {client}=fixture(),call=client.call,actions=[];
    if(afterPlay)client.startupNavigating=true;
    client.call=async(method,params,session)=>{
      if(method==='Target.getTargets' && (!afterPlay || actions.length))return {targetInfos:[{type:'page',targetId:client.target,url:''}]};
      if(method==='Runtime.evaluate'){actions.push('play');return {result:{value:'clicked'}};}
      return call(method,params,session);
    };
    await assert.rejects(finishPreparation(client,0));
    assert.deepEqual(actions,afterPlay?['play']:[]);
    await assert.rejects(snapshot(client));
  }
});

test('preparación completa: un overlay sobre Play o Fullscreen detiene sin repetir acciones',async()=>{
  for(const blocked of ['#gtm-play-now-button','#fullscreen_button']){
    const {client}=fixture(),call=client.call,actions=[];
    client.call=async(method,params,session)=>{
      if(method==='Runtime.evaluate'){
        actions.push(params.expression.includes('#gtm-play-now-button')?'play':'fullscreen');
        return {result:{value:params.expression.includes(blocked)?'blocked':'clicked'}};
      }
      return call(method,params,session);
    };
    await assert.rejects(finishPreparation(client,0));
    assert.deepEqual(actions,blocked==='#gtm-play-now-button'?['play']:['play','fullscreen']);
    assert.equal(client.startupStage,blocked==='#gtm-play-now-button'?'play':'fullscreen');
  }
});

test('preparación completa: ninguna acción del sitio si cambió el target o hay otra página',async()=>{
  for(const targetInfos of [[{type:'page',targetId:'B'.repeat(32),url:page}],
    [{type:'page',targetId:'A'.repeat(32),url:page},{type:'page',targetId:'B'.repeat(32),url:'about:blank'}]]){
    const {client}=fixture();let evaluated=false;
    client.call=async(method)=>{if(method==='Target.getTargets')return {targetInfos};evaluated=true;throw Error();};
    await assert.rejects(finishPreparation(client));assert.equal(evaluated,false);
  }
});

test('preparación completa: una vacía tardía solo se retira con autorización de arranque y prueba de DOM vacío',async()=>{
  for(const empty of [true,false]){
    const {client}=fixture(),call=client.call;client.startupBlanks=new Set();
    let blank=true,closed=false;const actions=[];
    client.call=async(method,params,session)=>{
      if(method==='Target.getTargets')return {targetInfos:[{type:'page',targetId:client.target,url:page},
        ...(blank?[{type:'page',targetId:'D'.repeat(32),url:'about:blank'}]:[])]};
      if(method==='Target.attachToTarget')return {sessionId:'empty'};
      if(method==='Target.detachFromTarget')return {};
      if(method==='Target.closeTarget'){assert.equal(params.targetId,'D'.repeat(32));blank=false;closed=true;return {success:true};}
      if(method==='Runtime.evaluate'){
        if(params.expression.includes('scrollTo('))return {result:{value:false}};  // volver la página a 0: neutro
        if(session==='empty'){assert.equal(params.userGesture,undefined);return {result:{value:empty}};}
        actions.push('site-or-focus');return {result:{value:params.expression.includes('#fullscreen_button')?[60,35]:params.expression.includes('#')?'clicked':true}};
      }
      if(method==='Input.synthesizeTapGesture')return {};
      return call(method,params,session);
    };
    if(empty){await finishPreparation(client);assert.equal(closed,true);assert.equal(actions.length,3);}
    else {await assert.rejects(finishPreparation(client));assert.equal(closed,false);assert.equal(actions.length,0);}
  }
});

test('preparación completa: no aceptar canvas ausente, ambiguo o geometría final incorrecta',async()=>{
  for(const kind of ['missing','duplicate','geometry']){
    const {client,geometry}=fixture(),call=client.call;
    if(kind==='missing')geometry.get('game').canvases=[];
    if(kind==='duplicate')geometry.get('wrapper').canvases=structuredClone(geometry.get('game').canvases);
    if(kind==='geometry')geometry.get('root').dpr=2;
    client.call=async(method,params,session)=>method==='Input.synthesizeTapGesture'?{}:method==='Runtime.evaluate'?{result:{value:
      params.expression.includes('#fullscreen_button')?[60,35]:params.expression.includes('#')?'clicked':true}}:call(method,params,session);
    await assert.rejects(finishPreparation(client,0));
    assert.equal(client.startupStage,kind==='geometry'?'snapshot':'canvas');
  }
});


test('CDP acepta respuestas PNG mayores de 1 MB y rechaza mensajes mayores de 16 MB',async()=>{
  const listeners=new Map(),socket={readyState:1,addEventListener:(name,fn)=>listeners.set(name,fn),
    send:()=>{},close:()=>{socket.readyState=3;listeners.get('close')();}};
  const c=new CDP(socket,null),pending=c.call('Page.captureScreenshot');
  listeners.get('message')({data:JSON.stringify({id:1,result:{data:'x'.repeat(2*1024*1024)}})});
  assert.equal((await pending).data.length,2*1024*1024);
  const rejected=c.call('Page.captureScreenshot');
  listeners.get('message')({data:'x'.repeat(16*1024*1024+1)});
  await assert.rejects(rejected,{message:'CDP_TRANSPORT'});assert.equal(c.failed,true);
});
