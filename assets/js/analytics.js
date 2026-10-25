/* Optional GA4: no tag, queue or request until an explicit, unexpired Allow choice.
   Configure the measurement ID in data/site.json and disable Enhanced measurement
   in the GA4 data stream. Only a page_view is sent here; inputs are never read. */
(function () {
  'use strict';

  var win = window, doc = document;
  var config = doc.getElementById('analytics-script');
  var id = config && config.getAttribute('data-measurement-id');
  var panel = doc.getElementById('analytics-choice');
  var opener = doc.getElementById('analytics-open');
  var title = doc.getElementById('analytics-title');
  var state = doc.getElementById('analytics-state');
  var allow = doc.getElementById('analytics-allow');
  var decline = doc.getElementById('analytics-decline');
  var close = doc.getElementById('analytics-close');
  var privacyLink = doc.getElementById('analytics-privacy');
  if (!id || !/^G-[A-Z0-9]+$/.test(id) || !panel || !opener || !state || !allow || !decline || !close) { return; }

  // A configured tag never runs in a local preview or on a different host.
  try {
    var canonical = new URL(config.getAttribute('data-site-url'));
    if (!/^https?:$/.test(win.location.protocol) || canonical.origin !== win.location.origin) { return; }
  } catch (e) { return; }

  var key = 'sept-analytics-consent-v1:' + id;
  var lifetime = 180 * 24 * 60 * 60;
  var disable = 'ga-disable-' + id;
  var loaded = false;
  var declinedHere = false;
  win[disable] = true;

  function parseChoice(raw) {
    try {
      var saved = JSON.parse(raw);
      if (saved && (saved.choice === 'allowed' || saved.choice === 'denied') &&
          typeof saved.expires === 'number' && saved.expires > Date.now()) { return saved.choice; }
    } catch (e) { /* Invalid or expired records grant no consent. */ }
    return '';
  }

  function readStore(name) {
    try { return parseChoice(win[name].getItem(key)); } catch (e) { return ''; }
  }

  function readChoice() {
    var local = readStore('localStorage'), session = readStore('sessionStorage');
    // A fallback refusal must override a stale Allow in either store after reload.
    if (local === 'denied' || session === 'denied') { return 'denied'; }
    return local === 'allowed' || session === 'allowed' ? 'allowed' : '';
  }

  function saveChoice(choice) {
    var record = JSON.stringify({ choice: choice, expires: Date.now() + lifetime * 1000 });
    var localSaved = false;
    try {
      win.localStorage.setItem(key, record);
      localSaved = readStore('localStorage') === choice;
    } catch (e) { /* Try storage that survives a reload of this tab. */ }
    if (localSaved) {
      try { win.sessionStorage.removeItem(key); } catch (e) { /* Denial still takes precedence. */ }
    } else {
      try { win.sessionStorage.setItem(key, record); } catch (e) { /* Report a failed choice below. */ }
    }
    if (choice === 'denied') {
      ['localStorage', 'sessionStorage'].forEach(function (name) {
        if (readStore(name) === 'allowed') {
          try { win[name].removeItem(key); } catch (e) { /* Never reload into a surviving Allow. */ }
        }
      });
    }
    return readChoice() === choice;
  }

  function cleanURL(value) {
    try {
      var url = new URL(value);
      return /^https?:$/.test(url.protocol) ? url.origin + url.pathname : '';
    } catch (e) { return ''; }
  }

  function clearCookies() {
    var domains = ['', win.location.hostname, '.' + win.location.hostname];
    try {
      doc.cookie.split(';').forEach(function (cookie) {
        var name = cookie.split('=')[0].trim();
        if (!/^sept_ga(?:_|$)/.test(name)) { return; }
        domains.forEach(function (domain) {
          doc.cookie = name + '=; Max-Age=0; path=/' + (domain ? '; domain=' + domain : '') + '; SameSite=Lax';
        });
      });
    } catch (e) { /* Disabling analytics and reloading still work if cookies are unavailable. */ }
  }

  function load() {
    if (loaded) { win[disable] = false; return; }
    loaded = true;
    win[disable] = false;
    win.dataLayer = win.dataLayer || [];
    win.gtag = function () { win.dataLayer.push(arguments); };
    var gtag = win.gtag;
    var denied = { analytics_storage: 'denied', ad_storage: 'denied', ad_user_data: 'denied', ad_personalization: 'denied' };
    var location = cleanURL(win.location.href);
    var referrer = cleanURL(doc.referrer);
    gtag('consent', 'default', denied);
    gtag('consent', 'update', { analytics_storage: 'granted', ad_storage: 'denied', ad_user_data: 'denied', ad_personalization: 'denied' });
    gtag('set', { page_location: location, page_referrer: referrer,
      allow_google_signals: false, allow_ad_personalization_signals: false,
      ads_data_redaction: true, url_passthrough: false });
    gtag('js', new Date());
    gtag('config', id, {
      send_page_view: false,
      page_location: location, page_referrer: referrer, page_title: doc.title,
      allow_google_signals: false, allow_ad_personalization_signals: false,
      cookie_prefix: 'sept', cookie_domain: win.location.hostname, cookie_path: '/',
      cookie_expires: lifetime, cookie_update: false, cookie_flags: 'SameSite=Lax;Secure'
    });
    gtag('event', 'page_view', { send_to: id, page_location: location,
      page_referrer: referrer, page_title: doc.title });
    var tag = doc.createElement('script');
    tag.async = true;
    tag.referrerPolicy = 'origin';
    tag.src = 'https://www.googletagmanager.com/gtag/js?id=' + encodeURIComponent(id);
    doc.head.appendChild(tag);
  }

  function stop(canReload) {
    // Google's opt-out flag stops sends and cookie writes before the loaded tag is removed by reload.
    win[disable] = true;
    clearCookies();
    if (loaded && canReload) { win.location.reload(); }
  }

  function describe(choice) {
    if (choice && readStore('localStorage') !== choice && readStore('sessionStorage') === choice) {
      state.textContent = 'Analytics is ' + (choice === 'denied' ? 'declined' : 'allowed') +
        ' for this tab. Your browser could not save the choice across visits.';
      return;
    }
    state.textContent = choice === 'allowed' ? 'Analytics is allowed in this browser.' :
      choice === 'denied' ? 'Analytics is declined in this browser.' : 'Analytics is off until you allow it.';
  }

  function show(focus) {
    panel.hidden = false;
    opener.setAttribute('aria-expanded', 'true');
    if (focus && title) { title.focus(); }
  }

  function hide() {
    var inside = panel.contains(doc.activeElement);
    panel.hidden = true;
    opener.setAttribute('aria-expanded', 'false');
    if (inside) { opener.focus(); }
  }

  function withdraw() {
    declinedHere = true;
    // Stop first, before attempting storage or touching any UI.
    win[disable] = true;
    // Do not rewrite an already-saved denial in response to another tab's event.
    var saved = readChoice() === 'denied' || saveChoice('denied');
    describe('denied');
    if (saved && readStore('localStorage') === 'denied') {
      hide();
    } else if (saved) {
      show(false);
    } else {
      state.textContent = 'Analytics is off for this page. Your browser could not save the choice.';
      show(false);
    }
    // Only a read-back denial makes a reload safe. Otherwise keep Google's code disabled here.
    stop(saved);
  }

  opener.hidden = false;
  opener.addEventListener('click', function () { show(true); });
  close.addEventListener('click', hide);
  allow.addEventListener('click', function () {
    var saved = saveChoice('allowed');
    if (readChoice() === 'denied') {
      win[disable] = true;
      state.textContent = 'Analytics stays off. Your browser could not replace the saved Decline choice.';
      show(false);
      return;
    }
    declinedHere = false;
    describe('allowed');
    load();
    if (saved) { hide(); } else {
      state.textContent = 'Analytics is allowed for this page. Your browser could not save the choice.';
      show(false);
    }
  });
  decline.addEventListener('click', withdraw);
  panel.addEventListener('keydown', function (event) { if (event.key === 'Escape') { hide(); } });
  if (privacyLink) {
    privacyLink.addEventListener('click', function () {
      hide();
      var details = doc.getElementById('privacy');
      if (details) { details.open = true; }
    });
  }
  win.addEventListener('storage', function (event) {
    if (event.key !== key && event.key !== null) { return; }
    // A denial event is authoritative even if this tab still reads a stale Allow.
    if (parseChoice(event.newValue) === 'denied') { withdraw(); return; }
    if (declinedHere) { return; }
    var choice = readChoice();
    describe(choice);
    if (choice === 'allowed') { load(); } else { stop(choice === 'denied'); }
    if (!choice) { show(false); } else { hide(); }
  });

  var choice = readChoice();
  describe(choice);
  declinedHere = choice === 'denied';
  if (choice === 'allowed') { load(); } else if (choice === 'denied') {
    stop(false);
    if (readStore('localStorage') !== 'denied') { show(false); }
  } else { show(false); }
}());
