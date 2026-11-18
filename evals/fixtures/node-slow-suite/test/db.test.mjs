import test from 'node:test';import assert from 'node:assert/strict';
import {openDb,addUser,countUsers} from '../src/db.mjs';
for(let i=0;i<40;i++)test(`user ${i} is stored once`,()=>{const db=openDb();const before=countUsers(db);addUser(db,'u'+i);assert.equal(countUsers(db),before+1);});
