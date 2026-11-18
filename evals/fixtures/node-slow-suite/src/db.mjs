import {DatabaseSync} from 'node:sqlite';
import {readdirSync,readFileSync} from 'node:fs';
const dir=new URL('./migrations/',import.meta.url);
/** A fresh in-memory database with every migration applied. */
export function openDb(){
  const db=new DatabaseSync(':memory:');
  for(const f of readdirSync(dir).filter(x=>x.endsWith('.sql')).sort())db.exec(readFileSync(new URL(f,dir),'utf8'));
  return db;
}
export const addUser=(db,name)=>db.prepare('INSERT INTO t1(name,created_at) VALUES(?,?)').run(name,Date.now()).lastInsertRowid;
export const countUsers=db=>db.prepare('SELECT count(*) AS n FROM t1').get().n;
