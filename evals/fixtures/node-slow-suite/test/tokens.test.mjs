import test from 'node:test';import assert from 'node:assert/strict';
import {newSigner,sign,verify} from '../src/tokens.mjs';
for(let i=0;i<20;i++)test(`token ${i} verifies with its key`,()=>{const k=newSigner();const s=sign(k,'payload'+i);assert.equal(verify(k,'payload'+i,s),true);});
test('a token signed by another key is refused',()=>{const a=newSigner(),b=newSigner();assert.equal(verify(b,'x',sign(a,'x')),false);});
