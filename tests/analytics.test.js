'use strict';

// Exercise the real local script in an isolated browser-shaped VM. No network or packages.
var assert = require('node:assert/strict');
var fs = require('node:fs');
var path = require('node:path');
var vm = require('node:vm');
var source = fs.readFileSync(path.join(__dirname, '../assets/js/analytics.js'), 'utf8');
var id = 'G-TEST123456';
var key = 'sept-analytics-consent-v1:' + id;

function browser(options) {
  options = options || {};
  var elements = {}, scripts = [], cookies = [], events = {};
  var storage = Object.assign({}, options.localData || {});
  var session = Object.assign({}, options.sessionData || {});
  var reloads = 0;
  var doc = { title: 'Research · SEPT Lab at USC', referrer: options.referrer || 'https://ref.example/path?q=private#secret',
    head: { appendChild: function (tag) { scripts.push(tag); } },
    createElement: function () { return {}; },
    getElementById: function (name) { return elements[name] || null; }
  };
  Object.defineProperty(doc, 'cookie', { get: function () { if (options.blockCookies) { throw Error('blocked'); } return 'sept_ga=old; sept_ga_TEST123456=old; other_cookie=keep'; },
    set: function (value) { cookies.push(value); } });
  ['analytics-script', 'analytics-choice', 'analytics-open', 'analytics-title', 'analytics-state',
    'analytics-allow', 'analytics-decline', 'analytics-close', 'analytics-privacy', 'privacy'].forEach(function (name) {
    var listeners = {};
    elements[name] = { hidden: true, attributes: {}, textContent: '',
      getAttribute: function (attr) { return this.attributes[attr]; },
      setAttribute: function (attr, value) { this.attributes[attr] = value; },
      addEventListener: function (event, fn) { listeners[event] = fn; },
      fire: function (event, data) { if (listeners[event]) { listeners[event](data || {}); } },
      focus: function () { doc.activeElement = this; },
      contains: function (target) { return ['analytics-title', 'analytics-allow', 'analytics-decline', 'analytics-close', 'analytics-privacy'].some(function (child) { return elements[child] === target; }); }
    };
  });
  elements['analytics-script'].attributes = { 'data-measurement-id': options.id || id, 'data-site-url': 'https://septlab.com' };
  if (options.choice) { storage[key] = JSON.stringify({ choice: options.choice, expires: Date.now() + (options.expired ? -1 : 86400000) }); }
  if (options.sessionChoice) { session[key] = JSON.stringify({ choice: options.sessionChoice, expires: Date.now() + 86400000 }); }
  function store(name, values) {
    return {
      getItem: function (key) {
        if (options[name + 'GetFails'] || (name === 'local' && options.blockStorage)) { throw Error('get blocked'); }
        return values[key] || null;
      },
      setItem: function (key, value) {
        if (options[name + 'SetFails'] || (name === 'local' && options.blockStorage)) { throw Error('set blocked'); }
        values[key] = value;
      },
      removeItem: function (key) {
        if (options[name + 'RemoveFails'] || (name === 'local' && options.blockStorage)) { throw Error('remove blocked'); }
        delete values[key];
      }
    };
  }
  var url = new URL(options.url || 'https://septlab.com/research.html?q=private&utm_campaign=private#input');
  var win = { location: { href: url.href, origin: url.origin, pathname: url.pathname,
      protocol: url.protocol, hostname: url.hostname, reload: function () { reloads += 1; } },
    localStorage: store('local', storage), sessionStorage: store('session', session),
    addEventListener: function (event, fn) { events[event] = fn; }
  };
  vm.runInNewContext(source, { window: win, document: doc, URL: URL, Date: Date, console: console });
  return { win: win, doc: doc, elements: elements, scripts: scripts, cookies: cookies, storage: storage, session: session,
    reloads: function () { return reloads; },
    click: function (name) { elements[name].focus(); elements[name].fire('click'); },
    storageEvent: function (choice) {
      storage[key] = choice ? JSON.stringify({ choice: choice, expires: Date.now() + 86400000 }) : null;
      events.storage({ key: key, newValue: storage[key] });
    },
    emitStorage: function (choice) { events.storage({ key: key, newValue: JSON.stringify({ choice: choice, expires: Date.now() + 86400000 }) }); },
    commands: function () { return JSON.parse(JSON.stringify((win.dataLayer || []).map(function (args) { return Array.from(args); }))); }
  };
}

var fresh = browser();
assert.equal(fresh.scripts.length, 0, 'No GA request before Allow');
assert.equal(fresh.win.dataLayer, undefined, 'No Google queue before Allow');
assert.equal(fresh.elements['analytics-choice'].hidden, false);
fresh.click('analytics-close');
assert.equal(fresh.scripts.length, 0, 'Dismissal is not consent');
fresh.click('analytics-open');
assert.equal(fresh.doc.activeElement, fresh.elements['analytics-title']);
fresh.click('analytics-decline');
assert.equal(fresh.scripts.length, 0, 'Decline never loads Google');
assert.equal(fresh.win['ga-disable-' + id], true);
assert.equal(fresh.reloads(), 0, 'Initial decline does not reload or interrupt reading');
assert.equal(JSON.parse(fresh.storage[key]).choice, 'denied');
assert.equal(browser({ choice: 'denied' }).scripts.length, 0, 'Saved denial stays off');

fresh.click('analytics-open');
fresh.click('analytics-allow');
assert.equal(fresh.scripts.length, 1);
assert.equal(fresh.scripts[0].src, 'https://www.googletagmanager.com/gtag/js?id=' + id);
assert.equal(fresh.scripts[0].referrerPolicy, 'origin');
var commands = fresh.commands();
assert.deepEqual(commands[0], ['consent', 'default', { analytics_storage: 'denied', ad_storage: 'denied', ad_user_data: 'denied', ad_personalization: 'denied' }]);
assert.deepEqual(commands[1], ['consent', 'update', { analytics_storage: 'granted', ad_storage: 'denied', ad_user_data: 'denied', ad_personalization: 'denied' }]);
var config = commands.find(function (command) { return command[0] === 'config'; });
assert.equal(config[1], id);
assert.equal(config[2].send_page_view, false);
assert.equal(config[2].allow_google_signals, false);
assert.equal(config[2].allow_ad_personalization_signals, false);
assert.equal(config[2].page_location, 'https://septlab.com/research.html');
assert.equal(config[2].page_referrer, 'https://ref.example/path');
assert.equal(config[2].user_id, undefined);
var pageviews = commands.filter(function (command) { return command[0] === 'event'; });
assert.deepEqual(pageviews, [['event', 'page_view', { send_to: id, page_location: 'https://septlab.com/research.html', page_referrer: 'https://ref.example/path', page_title: 'Research · SEPT Lab at USC' }]]);
assert.equal(JSON.stringify(commands).includes('private'), false, 'No query, fragment or input sentinel in any command');
fresh.click('analytics-open');
fresh.click('analytics-allow');
assert.equal(fresh.scripts.length, 1, 'Allow is idempotent');
assert.equal(fresh.commands().filter(function (command) { return command[0] === 'event'; }).length, 1);
fresh.click('analytics-open');
fresh.click('analytics-decline');
assert.equal(fresh.win['ga-disable-' + id], true, 'Withdraw before unloading');
assert.equal(fresh.reloads(), 1, 'Withdrawal unloads the already-consented Google code');
assert.ok(fresh.cookies.some(function (value) { return value.startsWith('sept_ga=; Max-Age=0'); }));
assert.equal(fresh.cookies.some(function (value) { return value.startsWith('other_cookie='); }), false);

assert.equal(browser({ choice: 'allowed' }).scripts.length, 1, 'Unexpired Allow carries across pages');
assert.equal(browser({ choice: 'allowed', expired: true }).scripts.length, 0, 'Expired Allow does not load Google');
assert.equal(browser({ id: 'AW-123' }).scripts.length, 0, 'Only a GA4 measurement ID is accepted');
assert.equal(browser({ choice: 'denied', blockCookies: true }).scripts.length, 0, 'Cookie restrictions cannot break an opt-out');
assert.equal(browser({ url: 'http://localhost:8000/' }).scripts.length, 0, 'No tracking on local previews');
assert.equal(browser({ url: 'https://preview.example/' }).elements['analytics-open'].hidden, true);
var blocked = browser({ blockStorage: true });
assert.equal(blocked.scripts.length, 0);
blocked.click('analytics-allow');
assert.equal(blocked.scripts.length, 1, 'Storage failures do not fabricate consent or break an explicit choice');
var otherTab = browser({ choice: 'allowed' });
otherTab.storageEvent('denied');
assert.equal(otherTab.win['ga-disable-' + id], true);
assert.equal(otherTab.reloads(), 1, 'Withdrawal propagates to another open tab');

// A readable stale Allow must never revive GA after a failed write and reload.
var fallback = browser({ choice: 'allowed', localSetFails: true, localRemoveFails: true });
fallback.click('analytics-open');
fallback.click('analytics-decline');
assert.equal(JSON.parse(fallback.storage[key]).choice, 'allowed');
assert.equal(JSON.parse(fallback.session[key]).choice, 'denied');
assert.equal(fallback.win['ga-disable-' + id], true);
assert.equal(fallback.reloads(), 1, 'A read-back session denial permits a safe reload');
assert.match(fallback.elements['analytics-state'].textContent, /for this tab.*across visits/);
assert.equal(browser({ localData: fallback.storage, sessionData: fallback.session }).scripts.length, 0,
  'Session denial overrides the stale local Allow after reload');

var noSave = browser({ choice: 'allowed', localSetFails: true, localRemoveFails: true,
  sessionSetFails: true, sessionRemoveFails: true });
noSave.click('analytics-open');
noSave.click('analytics-decline');
assert.equal(noSave.win['ga-disable-' + id], true);
assert.equal(noSave.reloads(), 0, 'Do not reload into the old Allow when neither store can save a denial');
assert.equal(noSave.elements['analytics-choice'].hidden, false);
assert.match(noSave.elements['analytics-state'].textContent, /off for this page.*could not save/);
noSave.emitStorage('allowed');
assert.equal(noSave.win['ga-disable-' + id], true, 'A stale Allow event cannot reverse this page\'s refusal');

// A cross-tab denial is authoritative even if this tab's storage reads still return old data.
var crossTabFailure = browser({ choice: 'allowed', localSetFails: true, localRemoveFails: true,
  sessionSetFails: true, sessionRemoveFails: true });
crossTabFailure.emitStorage('denied');
assert.equal(crossTabFailure.win['ga-disable-' + id], true);
assert.equal(crossTabFailure.reloads(), 0, 'Cross-tab withdrawal with no saved denial stays on this page');
assert.match(crossTabFailure.elements['analytics-state'].textContent, /could not save/);
var crossTabFallback = browser({ choice: 'allowed', localSetFails: true, localRemoveFails: true });
crossTabFallback.emitStorage('denied');
assert.equal(crossTabFallback.reloads(), 1);
assert.equal(browser({ localData: crossTabFallback.storage, sessionData: crossTabFallback.session }).scripts.length, 0,
  'Cross-tab fallback denial remains off after reload');
var staleSession = browser({ choice: 'allowed', sessionChoice: 'allowed', sessionRemoveFails: true });
staleSession.storageEvent('denied');
assert.equal(staleSession.reloads(), 1);
assert.equal(browser({ localData: staleSession.storage, sessionData: staleSession.session }).scripts.length, 0,
  'Local denial overrides a session Allow that could not be removed');

var emptyReferrer = browser({ referrer: 'mailto:private@example.org' });
emptyReferrer.click('analytics-allow');
assert.equal(emptyReferrer.commands().find(function (command) { return command[0] === 'config'; })[2].page_referrer, '');
console.log('analytics: consent, withdrawal, privacy parameters and preview isolation pass');
