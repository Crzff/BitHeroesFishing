// CLI: node cdp_broker.mjs runs/<directorio-nuevo>/cdp.sock navegador [args...]
// Windows: el DACL por defecto del named pipe da LECTURA a otros usuarios (verían eventos generales); en la fase Windows
// hay que crearlo con un DACL explícito solo para el usuario. Escritura (control) no se concede a otros.
import net from 'node:net';
import {spawn} from 'node:child_process';
import {promises as fs} from 'node:fs';
import path from 'node:path';
import {randomUUID} from 'node:crypto';
import {pathToFileURL} from 'node:url';
export const MAX_MESSAGE=16*1024*1024;
export function frames(stream,onMessage,onError){
  let buffer=Buffer.alloc(0);
  stream.on('data',chunk=>{
    buffer=Buffer.concat([buffer,chunk]);
    for(let end;(end=buffer.indexOf(0))!==-1;){
      if(end>MAX_MESSAGE){onError();return;}
      const raw=buffer.subarray(0,end);buffer=buffer.subarray(end+1);
      try{const m=JSON.parse(raw.toString());if(!m || typeof m!=='object' || Array.isArray(m))throw Error();onMessage(m);}catch{onError();return;}
    }
    if(buffer.length>MAX_MESSAGE)onError();
  });
}
export async function startBroker(socketPath,executable,args=[]){
  if(args.some(a=>/^--remote-debugging-(port|pipe)(=|$)/.test(a)))throw Error('BROKER_ARGS');
  let endpoint,dir;
  if(process.platform==='win32')endpoint=`\\\\.\\pipe\\bitheroes-${randomUUID()}`;
  else{
    endpoint=path.resolve(socketPath);dir=path.dirname(endpoint);
    const runs=path.resolve('runs');
    if(!dir.startsWith(runs+path.sep) || dir===runs)throw Error('BROKER_PATH');
    // Un directorio nuevo evita reutilizar enlaces o sockets de otra sesión.
    if(await fs.realpath(path.dirname(dir))!==path.dirname(dir))throw Error('BROKER_PATH');
    await fs.mkdir(dir,{mode:0o700});await fs.chmod(dir,0o700);
  }
  const clients=new Set(),pending=new Map(),owners=new Map();let next=0,closed=false,browser,closing;
  const server=net.createServer(client=>{
    if(clients.size>=8 || closed){client.destroy();return;}
    clients.add(client);client.on('error',()=>client.destroy());
    client.on('close',()=>{
      clients.delete(client);
      for(const [id,p] of pending)if(p.client===client)pending.delete(id);
      // Conservar sesiones huérfanas bloqueadas hasta su detach o cierre del navegador.
      for(const [id,owner] of owners)if(owner===client)owners.set(id,null);
    });
    frames(client,m=>{
      if(!Number.isSafeInteger(m.id) || m.id<0 || typeof m.method!=='string' ||
        (m.sessionId && owners.get(m.sessionId)!==client) ||
        (m.params?.sessionId && owners.get(m.params.sessionId)!==client) || pending.size>=4096){client.destroy();return;}
      const id=++next;pending.set(id,{client,id:m.id,method:m.method});
      browser.stdio[3].write(JSON.stringify({...m,id})+'\0');
    },()=>client.destroy());
  });
  const close=()=>{
    if(closing)return closing;closed=true;
    closing=(async()=>{
    for(const client of clients)client.destroy();pending.clear();owners.clear();
    server.close();if(browser && browser.exitCode===null){
      browser.kill();
      const timer=setTimeout(()=>{if(browser.exitCode===null)browser.kill('SIGKILL');},1000);
      timer.unref();browser.once('exit',()=>clearTimeout(timer));
    }
    if(endpoint && dir){await fs.unlink(endpoint).catch(()=>{});await fs.rmdir(dir).catch(()=>{});}
    })();return closing;
  };
  try{
    browser=spawn(executable,[...args,'--remote-debugging-pipe'],{stdio:['ignore','ignore','ignore','pipe','pipe']});
    browser.on('error',()=>{void close();});browser.on('exit',()=>{void close();});
    await new Promise((resolve,reject)=>{browser.once('spawn',resolve);browser.once('error',reject);});
    browser.stdio[3].on('error',()=>{void close();});browser.stdio[4].on('error',()=>{void close();});
    frames(browser.stdio[4],m=>{
      if(m.id!==undefined){
        const p=pending.get(m.id);if(!p)return;pending.delete(m.id);
        if(m.result?.sessionId)owners.set(m.result.sessionId,p.client);
        if(!p.client.destroyed)p.client.write(JSON.stringify({...m,id:p.id})+'\0');
      }else{
        const owner=m.sessionId?owners.get(m.sessionId):null;
        if(m.method==='Target.attachedToTarget' && m.params?.sessionId){
          if(!owner)return;owners.set(m.params.sessionId,owner);
        }
        const recipients=m.sessionId?(owner?[owner]:[]):clients;
        for(const client of recipients)if(!client.destroyed)client.write(JSON.stringify(m)+'\0');
        if(m.method==='Target.detachedFromTarget')owners.delete(m.params?.sessionId);
      }
    },()=>{void close();});
    const old=process.umask(0o077);
    try{await new Promise((resolve,reject)=>{server.once('error',reject);server.listen(endpoint,resolve);});}
    finally{process.umask(old);}
    if(dir)await fs.chmod(endpoint,0o600);
    if(closed)throw Error('BROKER_CLOSED');
    return {endpoint,pid:browser.pid,close,browser};
  }catch(e){await close();throw e;}
}
if(process.argv[1] && import.meta.url===pathToFileURL(process.argv[1]).href){
  try{
    const broker=await startBroker(process.argv[2],process.argv[3],process.argv.slice(4));
    for(const signal of ['SIGINT','SIGTERM'])process.once(signal,()=>{void broker.close();});
    process.stdout.write(JSON.stringify({ok:true,pid:broker.pid,endpoint:broker.endpoint})+'\n');
  }catch{process.exitCode=1;}
}
