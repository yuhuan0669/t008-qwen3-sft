// Bounded CPU checks of two samples already read by the primary reviewer.
// No network, filesystem, process, model or GPU APIs are provided to sample code.
const fs = require('node:fs');
const vm = require('node:vm');
const assert = require('node:assert/strict');
const path = require('node:path');
const crypto = require('node:crypto');
const rows = fs.readFileSync(path.join(__dirname, 'mixin_all.jsonl'), 'utf8').trim().split('\n').map(JSON.parse);
const get = n => rows.find(r => r.source_line_one_based === n);
const results = [];
const square = get(299);
const implementations = [...square.final_answer.matchAll(/```javascript\n([\s\S]*?)```/g)]
  .map(m => m[1]).filter(code => code.startsWith('function createSquareObject'));
assert.equal(implementations.length, 2);
const cases = [[2, 3], [-1, 0, 5], [], [2, 2], [-2, 0.5, 10]];
implementations.forEach((code, implementation) => {
  cases.forEach(input => {
    const expected = Object.fromEntries(input.map(n => [String(n), n * n]));
    const actual = JSON.parse(vm.runInNewContext(
      code + '\nJSON.stringify(createSquareObject(' + JSON.stringify(input) + '))', {}, {timeout: 100}));
    assert.deepEqual(actual, expected);
    results.push({source_line_one_based: 299, implementation, input, actual, passed: true});
  });
});
const greeting = get(439);
const html = greeting.final_answer.match(/```html\n([\s\S]*?)```/)[1];
assert.match(html, /<div id="greeting"><\/div>/);
assert.match(html, /position:\s*fixed/);
assert.match(html, /top:\s*0/);
assert.match(html, /<\/html>/);
const script = html.match(/<script>([\s\S]*?)<\/script>/)[1];
const element = {};
const queries = [];
class FixedDate extends Date { constructor() { super('2026-10-19T12:00:00Z'); } }
vm.runInNewContext(script, {
  Date: FixedDate,
  document: {getElementById(id) { queries.push(id); assert.equal(id, 'greeting'); return element; }},
}, {timeout: 100});
assert.deepEqual(queries, ['greeting']);
assert.equal(element.textContent, 'Good morning, John Doe! Today is Monday, October 19, 2026.');
results.push({source_line_one_based: 439, check: 'HTML markers/CSS static assertions + script with DOM stub and fixed date',
              output: element.textContent, passed: true});
const report = {runtime: process.version, samples_checked: [299, 439], checks: results,
  input_sha256: crypto.createHash('sha256').update(fs.readFileSync(path.join(__dirname, 'mixin_all.jsonl'))).digest('hex'),
  limits: ['Only reviewed code blocks for sources 299 and 439 executed in bounded VM contexts.',
           'No real browser rendering, security certification, or exhaustive JavaScript type/edge-case proof.',
           'These checks do not validate other samples, all reasoning text, or training effects.'],
  training_started: false};
fs.writeFileSync(path.join(__dirname, 'reviewed_javascript_checks.json'), JSON.stringify(report, null, 2) + '\n');
console.log(JSON.stringify({samples_checked: report.samples_checked, checks_passed: results.length, runtime: report.runtime}));
