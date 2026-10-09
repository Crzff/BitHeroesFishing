import test from 'node:test';
import assert from 'node:assert/strict';
import net from 'node:net';
import {promises as fs} from 'node:fs';
import path from 'node:path';
import {randomUUID} from 'node:crypto';
import {once} from 'node:events';
import {spawn} from 'node:child_process';
import {createInterface} from 'node:readline';
import {startBroker,frames,MAX_MESSAGE} from '../fishing_core/cdp_broker.mjs';
import {openCDP} from '../fishing_core/brave_cdp.mjs';
const target='A'.repeat(32),url='https://www.kongregate.com/en/games/Juppiomenz/bit-heroes';
const fake=`const fs=require('fs');const input=fs.createReadStream(null,{fd:3});const output=fs.createWriteStream(null,{fd:4});let b='';let n=0;
function send(m){output.write(JSON.stringify(m)+'\\0');}
input.on('data',chunk=>{b+=chunk;let end;while((end=b.indexOf('\\0'))>=0){const m=JSON.parse(b.slice(0,end));b=b.slice(end+1);
if(m.method==='die'){process.exit();return;}
let result=m.method==='Target.getTargets'?{targetInfos:[{type:'page',targetId:'${target}',url:'${url}'}]}:m.method==='Target.attachToTarget'?{sessionId:'s'+(++n)}:{echo:m.params,wire:m.id};
send({id:m.id,result});if(m.method==='event'){send({method:'test.event',sessionId:m.sessionId,params:{}});send({method:'test.global',params:{}});}
}});`;
async function fixture(t){
  const dir=path.resolve('runs','broker-test-'+randomUUID());
  const broker=await startBroker(path.join(dir,'cdp.sock'),process.execPath,['-e',fake,'--']);
  t.after(async()=>{await broker.close();});return broker;
}
async function connect(t,endpoint){
  const socket=net.connect(endpoint);await once(socket,'connect');t.after(()=>socket.destroy());
  const queue=[],waiters=[];frames(socket,m=>{if(waiters.length)waiters.shift()(m);else queue.push(m);},()=>socket.destroy());
  return {socket,send:m=>socket.write(JSON.stringify(m)+'\0'),read:()=>queue.length?Promise.resolve(queue.shift()):new Promise(r=>waiters.push(r)),queue};
}
test('pipe: ids iguales, sesiones aisladas y eventos globales',async t=>{
  const b=await fixture(t),a=await connect(t,b.endpoint),c=await connect(t,b.endpoint);
  for(const client of [a,c])client.send({id:1,method:'Target.attachToTarget'});
  const ar=await a.read(),cr=await c.read();assert.equal(ar.id,1);assert.equal(cr.id,1);assert.notEqual(ar.result.sessionId,cr.result.sessionId);
  a.send({id:2,method:'event',sessionId:ar.result.sessionId});assert.equal((await a.read()).id,2);
  assert.equal((await a.read()).sessionId,ar.result.sessionId);assert.equal((await a.read()).method,'test.global');assert.equal((await c.read()).method,'test.global');
  c.send({id:3,method:'event',sessionId:ar.result.sessionId});await once(c.socket,'close');
});
test('socket privado y cierre con borrado',async t=>{
  const b=await fixture(t);
  if(process.platform!=='win32'){
    assert.equal((await fs.stat(path.dirname(b.endpoint))).mode&0o777,0o700);
    assert.equal((await fs.stat(b.endpoint)).mode&0o777,0o600);
  }
  const a=await connect(t,b.endpoint),closed=once(a.socket,'close');await b.close();await closed;
  if(process.platform!=='win32')await assert.rejects(fs.stat(b.endpoint),{code:'ENOENT'});
});
test('máximo ocho clientes y mensaje de 16 MB',async t=>{
  const b=await fixture(t),clients=[];for(let i=0;i<8;i++)clients.push(await connect(t,b.endpoint));
  const ninth=net.connect(b.endpoint);const closed=once(ninth,'close');ninth.on('error',()=>{});await closed;
  const a=clients[0];a.send({id:1,method:'echo',params:{text:'x'.repeat(2*1024*1024)}});assert.equal((await a.read()).result.echo.text.length,2*1024*1024);
  const dropped=once(a.socket,'close');a.socket.on('error',()=>{});a.socket.write(Buffer.alloc(MAX_MESSAGE+1,120));await dropped;
});
test('muerte del navegador cierra clientes y retira socket',async t=>{
  const b=await fixture(t),a=await connect(t,b.endpoint),closed=once(a.socket,'close');a.send({id:1,method:'die'});await closed;
  await b.close();if(process.platform!=='win32')await assert.rejects(fs.stat(b.endpoint),{code:'ENOENT'});
});
test('CDP usa pipe, descubre target y conserva attach y llamadas',async t=>{
  const b=await fixture(t),c=await openCDP(b.endpoint,target);t.after(()=>c.close());
  assert.equal(c.target,target);assert.ok(c.sessions.has(c.root));assert.deepEqual((await c.call('echo',{safe:true},c.root)).echo,{safe:true});
  await assert.rejects(openCDP(b.endpoint,'B'.repeat(32)));
});
test('rechaza flags TCP y directorio existente',async()=>{
  await assert.rejects(startBroker('runs/unused/cdp.sock',process.execPath,['--remote-debugging-port=9222']));
  if(process.platform!=='win32')await assert.rejects(startBroker('runs/cdp.sock',process.execPath,[]));
});

test('encuadre: fragmentos, varios mensajes y JSON inválido',async()=>{
  const {PassThrough}=await import('node:stream');const stream=new PassThrough(),messages=[];let errors=0;
  frames(stream,m=>messages.push(m),()=>errors++);
  stream.write('{"id":');stream.write('1}\0{"id":2}\0');assert.deepEqual(messages,[{id:1},{id:2}]);
  stream.write('invalid\0');assert.equal(errors,1);stream.destroy();
});
test('encuadre: límite exacto y exceso sin terminador',async()=>{
  const {PassThrough}=await import('node:stream');const stream=new PassThrough();let messages=0,errors=0;
  frames(stream,()=>messages++,()=>errors++);
  const raw=JSON.stringify({text:'x'.repeat(MAX_MESSAGE-11)});assert.equal(Buffer.byteLength(raw),MAX_MESSAGE);
  stream.write(raw+'\0');assert.equal(messages,1);assert.equal(errors,0);
  stream.write(Buffer.alloc(MAX_MESSAGE+1,120));assert.equal(errors,1);stream.destroy();
});

for(const signal of ['SIGINT','SIGTERM'])test('CLI: readiness y limpieza con '+signal,async t=>{
  const dir=path.resolve('runs','broker-test-'+randomUUID());
  const child=spawn(process.execPath,['fishing_core/cdp_broker.mjs',path.join(dir,'cdp.sock'),process.execPath,'-e',fake,'--'],
    {stdio:['ignore','pipe','ignore']});
  t.after(()=>{if(child.exitCode===null)child.kill('SIGKILL');});
  const lines=createInterface({input:child.stdout});
  const ready=await Promise.race([once(lines,'line').then(([line])=>JSON.parse(line)),
    once(child,'exit').then(()=>{throw Error('BROKER_START_FAILED');})]);
  assert.equal(ready.ok,true);assert.ok(Number.isInteger(ready.pid));
  const exited=once(child,'exit');child.kill(signal);await exited;
  if(process.platform!=='win32')await assert.rejects(fs.stat(ready.endpoint),{code:'ENOENT'});
});
