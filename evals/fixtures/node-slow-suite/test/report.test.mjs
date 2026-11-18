import test from 'node:test';import assert from 'node:assert/strict';
import {eventsInWindow} from '../src/report.mjs';
const events=[{id:1,at:Date.parse('2026-10-01T12:00:00Z')},{id:2,at:Date.parse('2026-10-02T12:00:00Z')}];
test('the report counts the October events',()=>{assert.deepEqual(eventsInWindow(events).map(e=>e.id),[1,2]);});
