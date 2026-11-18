import test from 'node:test';import assert from 'node:assert/strict';
import {getWithRetry} from '../src/client.mjs';
test('a 429 is retried until it succeeds',async()=>{let n=0;const res=await getWithRetry(async()=>(++n<3?{status:429}:{status:200}));assert.equal(res.status,200);assert.equal(n,3);});
test('four 429s give up with 429',async()=>{let n=0;const res=await getWithRetry(async()=>{n++;return {status:429};});assert.equal(res.status,429);assert.equal(n,4);});
