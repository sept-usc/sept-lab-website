/* SEPT Lab website: progressive enhancement only.
   Every page works without this file: the menu shows as a list of links and every publication is
   visible. It adds:
   - the Menu button below 769 px (the stylesheet folds the menu as soon as the inline script in the
     head has set the js class; this file opens and closes it);
   - opening a collapsed year on the Publications page when an address points into it;
   - the motion of the home page's vision image, with its Pause button;
   - the link in the vision image's corner, which loads the journey (assets/js/journey.js, the game in
     the home page's dialog) when the reader shows interest in it;
   - printing every folded list open: the Publications page's years and the Research page's lists of a
     direction's papers. */
(function () {
  'use strict';

  var doc = document;
  var media = function (query) {
    return window.matchMedia ? window.matchMedia(query) : { matches: false };
  };
  var onChange = function (mq, fn) {
    if (mq.addEventListener) { mq.addEventListener('change', fn); } else if (mq.addListener) { mq.addListener(fn); }
  };
  var toArray = function (nodes) { return Array.prototype.slice.call(nodes); };

  /* ---------- Menu ---------- */
  var nav = doc.querySelector('.site-nav');
  var toggle = nav && nav.querySelector('.menu-toggle');
  if (toggle) {
    var setOpen = function (open) {
      toggle.setAttribute('aria-expanded', open ? 'true' : 'false');
      nav.classList.toggle('is-open', open);
    };
    toggle.addEventListener('click', function () {
      setOpen(toggle.getAttribute('aria-expanded') !== 'true');
    });
    doc.addEventListener('keydown', function (event) {
      if (event.key === 'Escape' && nav.classList.contains('is-open')) {
        // Focus returns to the button only from inside the menu, which is about to disappear.
        var inside = nav.contains(doc.activeElement);
        setOpen(false);
        if (inside) { toggle.focus(); }
      }
    });
    var wide = media('(min-width: 769px)');
    onChange(wide, function () { if (wide.matches) { setOpen(false); } });
  }

  /* ---------- A link into a collapsed year opens it ---------- */
  var reveal = function () {
    var id = window.location.hash.slice(1);
    if (!id) { return; }
    var target = null;
    try { target = doc.getElementById(decodeURIComponent(id)); } catch (e) { target = null; }
    var details = target && target.closest ? target.closest('details') : null;
    if (details && !details.open) {
      details.open = true;
      target.scrollIntoView();
    }
  };
  window.addEventListener('hashchange', reveal);
  reveal();

  /* ---------- Print every folded list open ---------- */
  var folded = [];
  window.addEventListener('beforeprint', function () {
    folded = toArray(doc.querySelectorAll('details.year:not([open]), details.area__more:not([open])'));
    folded.forEach(function (details) { details.open = true; });
  });
  window.addEventListener('afterprint', function () {
    folded.forEach(function (details) { details.open = false; });
    folded = [];
  });

  /* ---------- Vision image: motion ---------- */
  // The home page's drawing has hooks for an 8-second loop whose keyframes are in style.css; they run
  // only while the figure has data-motion="running" and freeze with "paused". The loop pauses while
  // the figure is off-screen, the tab is hidden or the journey dialog is open, and when the reader
  // presses the button (WCAG 2.2.2); that choice is remembered on this device. Until the motion first
  // runs in a visit (a reader who paused it on an earlier visit, or a figure that starts off-screen,
  // in a hidden tab or behind the journey's dialog) the figure has no data-motion at all: an intro
  // frozen before it starts would keep the layers on their own compositing layers, drawn softer than
  // the still image. Pausing during the intro ends the intro at once, for the same reason. Under
  // prefers-reduced-motion: reduce the figure gets no data-motion and the button stays hidden, so the
  // drawing is still, as without JavaScript. A drawing without the hooks gets neither.
  var vision = doc.querySelector('.vision');
  var motionButton = vision && vision.querySelector('.vision__toggle');
  if (motionButton && vision.querySelector('.vision-sv-pu')) {
    var reduce = media('(prefers-reduced-motion: reduce)');
    var journey = doc.getElementById('journey');
    var MOTION_KEY = 'sept-vision-motion';
    var stopped = false;
    var started = false;
    // Until the observer's first report (a frame later), the figure counts as out of view, so the
    // intro plays when the reader first sees the figure.
    var inView = !window.IntersectionObserver;
    try { stopped = window.localStorage.getItem(MOTION_KEY) === 'paused'; } catch (e) { stopped = false; }
    var syncMotion = function () {
      if (reduce.matches) {
        vision.removeAttribute('data-motion');
        motionButton.hidden = true;
        started = false;
        return;
      }
      var run = !stopped && inView && !doc.hidden && !(journey && journey.open);
      if (run) { started = true; }
      if (started) { vision.setAttribute('data-motion', run ? 'running' : 'paused'); } else { vision.removeAttribute('data-motion'); }
      var label = stopped ? 'Play animation' : 'Pause animation';
      if (motionButton.textContent !== label) { motionButton.textContent = label; }
      motionButton.hidden = false;
    };
    var settleIntro = function () {
      if (!vision.getAnimations) { return; }
      vision.getAnimations({ subtree: true }).forEach(function (animation) {
        if (/^vision-lift/.test(animation.animationName || '')) {
          try { animation.finish(); } catch (e) { /* already over */ }
        }
      });
    };
    motionButton.addEventListener('click', function () {
      stopped = !stopped;
      try { window.localStorage.setItem(MOTION_KEY, stopped ? 'paused' : 'running'); } catch (e) { /* not kept */ }
      if (stopped) { settleIntro(); }
      syncMotion();
    });
    onChange(reduce, syncMotion);
    doc.addEventListener('visibilitychange', syncMotion);
    if (window.IntersectionObserver) {
      new IntersectionObserver(function (entries) {
        inView = entries[entries.length - 1].isIntersecting;
        syncMotion();
      }).observe(vision);
    }
    if (journey && window.MutationObserver) {
      new MutationObserver(syncMotion).observe(journey, { attributes: true, attributeFilter: ['open'] });
    }
    syncMotion();
  }

  /* ---------- The journey: loaded on demand ---------- */
  // The link in the vision image's corner opens the journey, the game in <dialog id="journey">. Its
  // stylesheet and script (the link's data-style-href and data-script-src) are loaded only once the
  // reader shows interest: the pointer comes over the link, the link gets focus or a touch, or the
  // address is index.html#journey. The stylesheet comes first, so the game never shows unstyled; the
  // script then takes the link over and opens the dialog for #journey. A click that comes before the
  // script opens the game as soon as it has loaded; a click with a modifier key opens a new tab at
  // #journey. If either file fails to load, the link hides again.
  var journeyLink = doc.getElementById('journey-open');
  var journeyBox = doc.getElementById('journey');
  if (journeyLink && journeyBox && typeof journeyBox.showModal === 'function' &&
      !!doc.createElement('canvas').getContext) {
    var journeyState = 0;  // 0 not requested, 1 loading, 2 loaded
    var journeyWaiting = false;
    var journeyFailed = function () { journeyState = 2; journeyLink.hidden = true; };
    var loadJourney = function () {
      if (journeyState) { return; }
      journeyState = 1;
      var sheet = doc.createElement('link');
      sheet.rel = 'stylesheet';
      sheet.href = journeyLink.getAttribute('data-style-href');
      sheet.onerror = journeyFailed;
      sheet.onload = function () {
        var script = doc.createElement('script');
        script.src = journeyLink.getAttribute('data-script-src');
        script.onerror = journeyFailed;
        script.onload = function () {
          journeyState = 2;
          // The script has added its own click handler, which opens the dialog.
          if (journeyWaiting && !journeyLink.hidden) { journeyWaiting = false; journeyLink.click(); }
        };
        doc.head.appendChild(script);
      };
      doc.head.appendChild(sheet);
    };
    journeyLink.addEventListener('pointerenter', loadJourney);
    journeyLink.addEventListener('focus', loadJourney);
    journeyLink.addEventListener('touchstart', loadJourney, { passive: true });
    journeyLink.addEventListener('click', function (event) {
      if (journeyState === 2 || event.button || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) { return; }
      event.preventDefault();
      journeyWaiting = true;
      loadJourney();
    });
    window.addEventListener('hashchange', function () {
      if (window.location.hash === '#journey') { loadJourney(); }
    });
    journeyLink.hidden = false;
    if (window.location.hash === '#journey') { loadJourney(); }
  }
}());
