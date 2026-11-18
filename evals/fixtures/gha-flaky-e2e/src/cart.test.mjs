import test from 'node:test';import assert from 'node:assert/strict';
const total=(items,tax)=>Math.round(items.reduce((s,i)=>s+i,0)*(1+tax)*100)/100;
test('cart total with 8% tax',()=>assert.equal(total([10],0.08),10.8));
