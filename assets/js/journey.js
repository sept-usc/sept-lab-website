/* SEPT Lab: "the journey", the home page's Easter egg (README, "The journey"). A quiet link in the corner
   of the vision image opens a modal dialog with a small pixel-map game: a
   figure walks a path past one stop per research direction to the SEPT tree, plays a short scene at each
   stop and earns its badge. With every badge it rests under the tree: the view closes in on the tree as
   the figure settles into the logo's pose, the tree's flowers light one per badge, and the ending card
   appears beside the tree or under the map. The canvas draws pictures only; every word is HTML, from
   #journey-themes, the dialog's data-* attributes and STORY. One ES5 function, no globals, ASCII only
   (other characters are \u escapes); journey.css styles the dialog. site.js shows the link and loads this
   file, after journey.css, once the reader points at the link, focuses or touches it, or opens
   index.html#journey. The game is built on the first open and runs only while the dialog is open. */
(function () {
  'use strict';

  var doc = document, win = window;
  var dialog = doc.getElementById('journey'), opener = doc.getElementById('journey-open');
  var mount = doc.getElementById('journey-game'), data = doc.getElementById('journey-themes'), themes;
  if (!opener) return;
  if (!dialog || !mount || !data || typeof dialog.showModal !== 'function' ||
      !doc.createElement('canvas').getContext) { opener.hidden = true; return; }
  try {
    themes = JSON.parse(data.textContent).filter(function (t) { return t && t.title; });
  } catch (e) { themes = []; }
  var N = themes.length;
  if (!N || N > 4) { opener.hidden = true; return; }

  /* ---- the dialog: the link opens it, and so does index.html#journey; Esc, the close button and a
     click on the backdrop close it. The page behind does not scroll, focus returns to the link, and the
     hash goes again: the history entry the link added is taken back, so Back closes the game first.
     Opened from the address, the page has not been seen yet: closing leaves it at the top, with the
     focus on the link but not scrolled to it. */
  var HASH = '#journey', game = null, pushed = false, held = null, downOut = false, byAddress = false;
  function hold(on) {
    var de = doc.documentElement, b = doc.body;
    if (on && !held) {
      held = [de.style.overflow, b.style.paddingRight];
      var bar = win.innerWidth - de.clientWidth;  // the scrollbar's room is kept, so nothing shifts
      de.style.overflow = 'hidden';
      if (bar > 0) b.style.paddingRight = bar + 'px';
    } else if (!on && held) {
      de.style.overflow = held[0]; b.style.paddingRight = held[1]; held = null;
    }
  }
  function open(byLink) {
    if (dialog.open) return;
    if (!game) {
      try { game = build(); } catch (e) { opener.hidden = true; if (win.console) win.console.error(e); return; }
    }
    hold(true);
    byAddress = !byLink;
    dialog.showModal();
    if (byLink && location.hash !== HASH) {
      try { history.pushState(null, '', HASH); pushed = true; } catch (e) { pushed = false; }
    }
    game.show();
  }
  dialog.addEventListener('close', function () {
    if (game) game.hide();
    hold(false);
    if (pushed) { pushed = false; history.back(); }
    else if (location.hash === HASH) {
      try { history.replaceState(history.state, '', location.pathname + location.search); } catch (e) { }
    }
    if (byAddress) opener.focus({ preventScroll: true }); else opener.focus();
  });
  function onHash() {
    if (location.hash === HASH) open(false);
    else if (dialog.open) { pushed = false; dialog.close(); }
  }
  win.addEventListener('popstate', onHash);
  win.addEventListener('hashchange', onHash);
  opener.addEventListener('click', function (e) {
    if (e.button || e.metaKey || e.ctrlKey || e.shiftKey || e.altKey) return;  // a new tab opens #journey
    e.preventDefault();
    open(true);
  });
  function outside(e) {
    var b = dialog.getBoundingClientRect();
    return e.target === dialog && (e.clientX < b.left || e.clientX >= b.right || e.clientY < b.top || e.clientY >= b.bottom);
  }
  dialog.addEventListener('pointerdown', function (e) { downOut = outside(e); });
  dialog.addEventListener('click', function (e) { if (downOut && outside(e)) dialog.close(); downOut = false; });
  Array.prototype.forEach.call(dialog.querySelectorAll('[data-journey-close]'), function (b) {
    b.addEventListener('click', function () { dialog.close(); });
  });
  opener.setAttribute('aria-haspopup', 'dialog');
  opener.hidden = false;
  if (location.hash === HASH) {
    open(false);
    // As the page finishes loading, the browser focuses the target of #journey, which is now the open
    // dialog itself; the focus goes back to the card's button (or the map).
    if (doc.readyState !== 'complete') {
      win.addEventListener('load', function () {
        if (game && dialog.open && (doc.activeElement === dialog || doc.activeElement === doc.body)) game.focus();
      });
    }
  }

  /* ---- the game, built on the first open */
  function build() {
    // a scene follows the id or title, else a pennant
    var ART = [/\btees?\b|confiden|enclave/i, /attack|vulnerab|side.?channel/i, /verif|proof/i, /\bagents?\b/i], used = [];
    // per scene: the action, what it shows (illustrating the direction's summary), what to click
    var STORY = [
      ['Lock the enclave', 'The data steps into the enclave and the door locks behind it. It keeps computing inside; the snooping host bounces off the wall.', 'the vault'],
      ['Catch the leaking bit', 'The magnifier sweeps the chip and catches a bit leaking out through a side channel. A report goes to the vendor.', 'the red bit'],
      ['Stamp the evidence', 'The model\u2019s answer is stamped with evidence of which model ran and how; an answer without that evidence gets an X.', 'the stamp'],
      ['Block the bad call', 'The agent\u2019s tools run inside the sandbox. When a call reaches for the agent\u2019s secrets outside, the monitor blocks it.', 'the gate'],
      ['Raise the flag', 'The flag goes up: this stop is on the map.', 'the flag']
    ];
    themes.forEach(function (t) {
      t.art = 4;
      for (var a = 0; a < ART.length; a++) {
        if (!used[a] && ART[a].test((t.id || '') + ' ' + t.title)) { t.art = a; used[a] = 1; break; }
      }
      t.href = t.href || 'research.html#' + (t.id || '');
      t.papers = (t.papers || []).filter(function (p) { return p && p.title && p.href; }).slice(0, 2);
    });
    function attr(n, d) { return dialog.getAttribute('data-' + n) || d; }
    var LAYERS = themes.map(function (t) { return t.layer || t.short || t.title; });
    var NUM = ['one', 'two', 'three', 'four'][N - 1];
    function cap(s) { return s.charAt(0).toUpperCase() + s.slice(1); }

    /* ---- palette: 17 colours from the logo */
    var PAL = {
      K: '#252e24', Y: '#f0c148', R: '#b22a28',  // logo ink, sun gold, red
      o: '#b08532', y: '#f4dd9b', W: '#fbf8f0',  // deep gold, pale gold (walked path), paper
      g: '#e9ecdc', h: '#d7dcc3', G: '#a9b994', D: '#6c8466', // meadow, meadow shade, leaves, leaf shadow
      p: '#f5efdd', q: '#d9cca6',  // path, path edge
      l: '#c8cbc2', m: '#8f968b', d: '#545c51',  // greys
      B: '#7493b2', b: '#c3d5df'  // glass and water
    };

    /* ---- drawing: everything goes to X at OX, OY */
    var X = null, OX = 0, OY = 0;
    var round = Math.round, abs = Math.abs, floor = Math.floor, max = Math.max, min = Math.min, rand = Math.random;
    function into(ctx, ox, oy, fn) {
      var s = [X, OX, OY];
      X = ctx; OX = ox; OY = oy; fn();
      X = s[0]; OX = s[1]; OY = s[2];
    }
    function r(a, b, w, h, c) { if (w > 0 && h > 0) { X.fillStyle = PAL[c]; X.fillRect(round(OX + a), round(OY + b), w, h); } }
    function d(c, xy) { for (var i = 0; i < xy.length; i += 2) r(xy[i], xy[i + 1], 1, 1, c); }
    function spr(s, a, b) { X.drawImage(s, round(OX + a), round(OY + b)); }
    function mk(w, h) { var c = doc.createElement('canvas'); c.width = w; c.height = h; return c; }
    function painted(w, h, fn) { var c = mk(w, h); into(c.getContext('2d'), 0, 0, fn); return c; }
    // an ellipse turned by ang; ring keeps a band that wide, chk every other pixel
    function oval(cx, cy, rx, ry, col, ang, ring, chk) {
      var c = Math.cos(ang || 0), s = Math.sin(ang || 0), R = max(rx, ry);
      for (var yy = floor(cy - R); yy <= cy + R; yy++) {
        for (var xx = floor(cx - R); xx <= cx + R; xx++) {
          var dx = xx + 0.5 - cx, dy = yy + 0.5 - cy, u = dx * c + dy * s, v = dy * c - dx * s;
          if (u * u / (rx * rx) + v * v / (ry * ry) > 1 || (chk && (xx + yy) % 2)) continue;
          if (ring && u * u / ((rx - ring) * (rx - ring)) + v * v / ((ry - ring) * (ry - ring)) <= 1) continue;
          r(xx, yy, 1, 1, col);
        }
      }
    }
    function disc(cx, cy, rad, col) { oval(cx, cy, rad, rad, col); }
    function stroke(pts, w, col) {  // a polyline drawn with a square brush
      for (var i = 0; i < pts.length - 1; i++) {
        var a = pts[i], b = pts[i + 1], n = max(abs(b[0] - a[0]), abs(b[1] - a[1]), 1);
        for (var s = 0; s <= n; s++) r(a[0] + (b[0] - a[0]) * s / n - w / 2, a[1] + (b[1] - a[1]) * s / n - w / 2, w, w, col);
      }
    }
    // an ASCII sprite, one palette letter a pixel; map recolours letters
    function sprite(rows, map) {
      var w = rows.reduce(function (m, row) { return max(m, row.length); }, 0);
      return painted(w, rows.length, function () {
        rows.forEach(function (row, y) {
          for (var x = 0; x < row.length; x++) { var k = map && map[row[x]] || row[x]; if (PAL[k]) r(x, y, 1, 1, k); }
        });
      });
    }
    function flipped(c) {
      var f = mk(c.width, c.height), x = f.getContext('2d');
      x.translate(c.width, 0); x.scale(-1, 1); x.drawImage(c, 0, 0);
      return f;
    }
    // time helpers (s): 0..1 over [a, b], eased; mix; a hop; a 1 px bob
    function f01(t, a, b) { return t <= a ? 0 : t >= b ? 1 : (t - a) / (b - a); }
    function sm(t, a, b) { var v = f01(t, a, b); return v * v * (3 - 2 * v); }
    function mix(a, b, v) { return a + (b - a) * v; }
    function hop(t, period, h) { return -round(abs(Math.sin(t * Math.PI / period)) * h); }
    function bob(g) { return floor(g / 0.55) % 2 ? -1 : 0; }

    /* ---- sprites */
    var HEAD = ['..KKK..', '.KKKKK.', '.KKKKK.', '.KKKKK.', '..KKK..', '...K...', '..KKK..'];
    // standing and seated with their rows, for the dissolve from one into the other (figure())
    var STAND_R = HEAD.concat(['.K.K.K.', 'K..K..K', '...K...', '..K.K..', '.K...K.', '.K...K.']);
    var SIT_R = ['.............KKK....', '...........KKKKKKK..', '...........KKKKKKK..', '..........KKKKKKKKK.',
      '..........KKKKKKKKK.', '..........KKKKKKKKK.', '...........KKKKKKK..', '...........KKKKKKK..', '.............KKK....',
      '...............KK...', '................KK..', '.....KK..........KK.', '....KKKKKK.....KKKK.', '....KK.KKKKKKKKKKKK.',
      '...KK..KK..KKK...KK.', '...KK...KK.......KK.', '...KK....KK.......KK', '..KK.....KK.......KK', '..KK......KK......KK',
      '..KK.......KK.....KK', '.KK.........KK....KK', '.KK.........KK....KK', 'KK...........KK...KK', 'KK............KKKKKK',
      'KK............KKKKKK'];
    var FIG = {
      stand: sprite(STAND_R),
      walk1: sprite(HEAD.concat(['.K.K.K.', '...K..K', '...K...', '..K.K..', '.K...K.', 'K.....K'])),
      walk2: sprite(['.......'].concat(HEAD, ['..KKK..', '...K...', '...K...', '..K.K..', '..K.K..'])),
      // arms up: acting, then holding up the badge
      get: sprite(['K..KKK..K', 'K.KKKKK.K', 'K.KKKKK.K', 'K.KKKKK.K', '.K.KKK.K.', '..K.K.K..', '...KKK...',
        '....K....', '....K....', '....K....', '...K.K...', '..K...K..', '..K...K..']),
      // seated, as in the logo: the back against the trunk, the knees up, an arm resting on them. Larger
      // than the walker, as the logo's figure is, with a 9 pixel head and limbs 2 pixels thick, and set
      // against the sun's gold with a pixel or two of it between the back and the trunk (SIT), so the
      // head, back, arm and legs each read on their own
      sit: sprite(SIT_R)
    };
    FIG.walk1f = flipped(FIG.walk1); FIG.walk2f = flipped(FIG.walk2);

    // the SEPT tree under the sun, with four star-shaped flowers (FLOWER), as in the logo; at the end they
    // light one per badge (LIT) and the sun glows (glow()). The seated figure goes at SIT, and the walker
    // stops under its seat, SEAT pixels in.
    var TREE_W = 62, TREE_H = 65, SIT = { x: 13, y: 40 }, SEAT = 16;
    var FLOWER = [[9, 13], [22, 5], [34, 3], [51, 8]];
    var STAR = sprite(['...K...', '..KKK..', 'KKKKKKK', '.KKKKK.', '..KKK..', '.KK.KK.', '.K...K.']);
    // a lit flower over its star, one pixel up and left: a gold heart, and a pale gold halo to set it off the sun
    var LIT = sprite(['....y....', '...yKy...', '.yyKYKyy.', 'yKKYWYKKy', '.yKYYYKy.', '..yKKKy..', '.yKKyKKy.', '.yKy.yKy.', '..y...y..']);
    function tree(shade) {  // shade: with its shadow on the ground, which the map's still layer has
      if (shade) oval(36, 63.5, 13, 1.6, 'h');
      disc(31, 34, 29.5, 'Y');
      for (var y = 36; y <= 64; y++) {  // the trunk leans a little and flares at the root
        var w = y > 61 ? 7 : y > 50 ? 5 : 4;
        r(round(34.5 + (y - 36) * 0.1 - w / 2), y, w, 1, 'K');
      }
      stroke([[33, 38], [27, 31], [20, 25]], 3, 'K'); stroke([[20, 25], [13, 17]], 2, 'K');
      stroke([[33, 37], [31, 27], [28, 19]], 3, 'K'); stroke([[28, 19], [26, 10]], 2, 'K');
      stroke([[31, 27], [37, 8]], 1, 'K');
      stroke([[34, 37], [40, 29], [47, 22]], 3, 'K'); stroke([[47, 22], [52, 13]], 2, 'K');
      stroke([[40, 30], [50, 32]], 2, 'K');
      oval(45, 13, 8.5, 3.6, 'K', -1.05); oval(54.5, 23, 8.5, 3.6, 'K', 0.45);
      oval(51, 35, 7.5, 3.2, 'K', 0.95); oval(39.5, 21.5, 6, 2.8, 'K', -2.3);
      FLOWER.forEach(function (c) { spr(STAR, c[0], c[1]); });
    }
    var TREE = painted(TREE_W, TREE_H, function () { tree(1); });
    // the tree with the sun's glow behind it, in two steps, 4 pixels larger all round; made when first needed.
    // It leaves out the tree's shadow, so the halo closes under the trunk and the seat; the map's own
    // shadow stays under it, where the walked path covers it
    var GLOWS = [];
    function glow(step) {
      return GLOWS[step] || (GLOWS[step] = painted(TREE_W + 8, TREE_H + 8, function () {
        into(X, 4, 4, function () {
          oval(31, 34, 32.5, 32.5, 'y', 0, 3, step < 2);
          if (step > 1) oval(31, 34, 34, 34, 'y', 0, 1.5, 1);
          tree(0);
        });
      }));
    }
    var PAD = sprite(['.qqqqq.', 'qpppppq', 'qpppppq', '.qqqqq.']);
    var PAD_ON = sprite(['.ooooo.', 'oYYYYYo', 'oYYYYYo', '.ooooo.']);
    var SIGN = sprite(['KKKKKKK', 'KoooooKK', 'KoooooK', 'KKKKKKK', '...K', '...K', '...K', '..hKh']);
    var BUSH = sprite(['..GGG', '.GGGGGG', 'GGGGGGGG', 'GGGGGGGD', '.DGGGDD', '..DDDD']);
    var HINT = sprite(['KKKKKKK', 'KYYYYYK', '.KYYYK.', '..KYK..', '...K...']);
    // the way on: a gold chevron along the path, right, left, up and down
    var GO_R = sprite(['KK...', 'KYK..', '.KYK.', '..KYK', '.KYK.', 'KYK..', 'KK...']);
    var GO_U = ['...K...', '..KYK..', '.KYKYK.', 'KYK.KYK', 'KK...KK'];
    var GO = [GO_R, flipped(GO_R), sprite(GO_U), sprite(GO_U.slice().reverse())];
    // the map's sky: a cloud and two birds (with their rows, to dissolve them; sky())
    var CLOUD_R = ['.....WWW', '..WWWWWWWW.WW', '.WWWWWWWWWWWWW', 'WWWWWWWWWWWWWWWW', '.llllllllllllll'], CLOUD = sprite(CLOUD_R);
    var BIRD_R = [['d...d', '.d.d.', '..d..'], ['.....', 'ddddd', '..d..']], BIRD = BIRD_R.map(function (b) { return sprite(b); });
    // the badges; in outline (caption) or faint (rail) until earned
    var BADGE_ROWS = [
      ['..KKKKK..', '.K.....K.', '.K.....K.', 'KKKKKKKKK', 'KYYYYYYYK', 'KYYYKYYYK', 'KYYYKYYYK', 'KYYYYYYYK', 'KKKKKKKKK'],
      ['.KKKK....', 'KbbbbK...', 'KbWbbK...', 'KbbRbK...', 'KbbbbK...', '.KKKKo...', '.....oo..', '......oo.', '.......o.'],
      ['..KKKKK..', '.KYYYYYK.', 'KYYYYYKYK', 'KYYYYKYYK', 'KYKYKYYYK', '.KYKYYYK.', '..KKKKK..', '..RK.KR..', '..R...R..'],
      ['KKKKKKKKK', 'KYYYYYYYK', 'KYYYKYYYK', 'KYYYKYYYK', 'KYKKKKKYK', '.KYYKYYK.', '.KYYKYYK.', '..KYYYK..', '...KKK...'],
      ['.K.......', '.KRRRRR..', '.KRRRRRR.', '.KRRRRR..', '.K.......', '.K.......', '.K.......', 'KKK......', '.........']
    ];
    var LINE = { Y: 'W', o: 'K', R: 'K', b: 'W', B: 'W' }, FAINT = { K: 'l', Y: 'W', o: 'l', R: 'l', b: 'W', B: 'W' };
    var BADGE = [], BADGE_LINE = [], BADGE_OFF = [];
    BADGE_ROWS.forEach(function (b) { BADGE.push(sprite(b)); BADGE_LINE.push(sprite(b, LINE)); BADGE_OFF.push(sprite(b, FAINT)); });

    /* ---- the scenes, in 64 by 52 plots: p phase, t its seconds, g ambient clock; dur: setup, action and
       aftermath times; hot: where a click plays it; hint: where the arrow points; hit: the moments that
       land ([phase, t, x, y, kind]), which shake the view a pixel and throw sparks */
    var IDLE = 0, SETUP = 1, READY = 2, ACT = 3, AFTER = 4, GET = 5, DONE = 6;
    var PHASES = ['idle', 'setup', 'ready', 'act', 'after', 'get', 'done'];
    var DATA = [sprite(['KKKK.', 'KWWKK', 'KWWWK', 'KWWWK', 'KKKKK', '.K.K.']), sprite(['KKKK.', 'KWWKK', 'KWWWK', 'KWWWK', 'KKKKK', 'K...K'])];
    var LOCK = sprite(['..KKK..', '.K...K.', '.K...K.', 'KKKKKKK', 'KYYYYYK', 'KYYKYYK', 'KYYKYYK', 'KKKKKKK']);
    var SNOOP = sprite(['..dddd..', '.dddddd.', '.ddddWWd', '.ddddWKd', '.dddddd.', '..dddd..', '.dmmmmd.', 'dmmmmmmd',
      'dmmmmmmd', '.dmmmmd.', '..d..d..', '..d..d..']), SNOOP_L = flipped(SNOOP);
    var BIT = sprite(['.KKK.', 'KRRRK', 'KRRRK', 'KRRRK', '.KKK.']);
    var REPORT = sprite(['KKKKK..', 'KWWWKK.', 'KWRRWKK', 'KWWWWWK', 'KWRRRWK', 'KWWWWWK', 'KWRRWWK', 'KKKKKKK']);
    var CARD_R = ['KKKKKKK', 'KWWWWWK', 'KWmmmWK', 'KWWWWWK', 'KWmmWWK', 'KWWWWWK', 'KKKKKKK'];
    var CARD = sprite(CARD_R), UCARD = sprite(CARD_R, { K: 'm', m: 'l' });
    var ASK = sprite(['.mmm.', 'm...m', '....m', '..mm.', '..m..', '.....', '..m..']);
    var SEAL = sprite(['.YYY.', 'YYYYK', 'YKYKY', 'YYKYY', '.YYY.']);
    var XMARK = sprite(['RR...RR', 'RRR.RRR', '.RRRRR.', '..RRR..', '.RRRRR.', 'RRR.RRR', 'RR...RR']);
    var CALL = [sprite(['..K..', '.KYK.', 'KYYYK', '.KYK.', '..K..']), sprite(['..K..', '.KRK.', 'KRRRK', '.KRK.', '..K..'])];
    var STAMP = sprite(['...ooo...', '..ooooo..', '...ooo...', '....K....', '....K....', '.KKKKKKK.', 'KKKKKKKKK', 'KYYYYYYYK']);
    var TREE2 = sprite(['...GGG...', '.GGGGGGG.', 'GGGGGGGGG', 'GGGGGGGGD', 'GGGGGGGDD', '.DGGGGDD.', '..DDDDD..', '....o....', '...hoh...']);
    var ROBOT = sprite(['....R....', '....K....', '.KKKKKKK.', '.KlllllK.', '.KlKlKlK.', '.KlllllK.', '.KKKKKKK.',
      '..KmmmK..', '..KmmmK..', '..KmmmK..', '..K...K..']);

    function sEnclave(p, t) {
      var i, x;
      // the cloud machine
      oval(32, 47.5, 30, 2, 'h');
      r(2, 39, 60, 8, 'K'); r(3, 40, 58, 5, 'l'); r(3, 45, 58, 1, 'm');
      d('m', [6, 42, 8, 42, 10, 42, 53, 42, 55, 42]); d('Y', [58, 42]);
      // the enclave: a vault with a doorway
      r(20, 12, 24, 27, 'K'); r(21, 13, 22, 3, 'o'); r(21, 13, 22, 1, 'Y'); r(21, 16, 22, 23, 'd'); r(21, 16, 1, 23, 'm');
      r(27, 22, 10, 17, 'K');
      if (p >= READY || (p === SETUP && t > 0.9)) { r(30, 31, 4, 4, 'o'); r(31, 32, 2, 2, 'Y'); }  // the workload inside
      var dh = round(17 * (p >= AFTER ? 1 : p === ACT ? sm(t, 0, 0.3) : 0));
      if (dh) { r(27, 22, 10, dh, 'o'); r(28, 22, 8, dh - 1, 'Y'); }
      var ly = p >= AFTER ? 26 : p === ACT && t > 0.3 ? round(mix(20, 26, sm(t, 0.3, 0.45))) : 0;
      if (ly) spr(LOCK, 29, ly);
      if ((p === ACT && t > 0.45) || (p === AFTER && t < 0.4)) d('Y', [39, 23, 40, 22, 41, 21, 40, 26, 41, 26, 42, 26]);
      // the data walks in through the doorway
      if (p <= SETUP) {
        X.save(); X.beginPath(); X.rect(OX - 2, OY, 30, 52); X.clip();
        for (i = 0; i < 3; i++) {
          var v = p === SETUP ? max(0, t - i * 0.3) : 0;
          x = 14 - i * 6 + 16 * v;
          if (x < 29) spr(DATA[v > 0 && floor(v * 7) % 2 ? 1 : 0], x, 33 + (v > 0 ? hop(v, 0.3, 1.5) : 0));
        }
        X.restore();
      }
      // the snooping host creeps up, bumps the wall and backs off
      var sx = 51, sy = 27, away = 0;
      if (p === READY) sx = mix(51, 46, sm(t, 0, 2));
      else if (p === ACT) sx = 46;
      else if (p === AFTER) {
        sx = t < 0.3 ? mix(46, 45, sm(t, 0, 0.3)) : mix(45, 54, sm(t, 0.3, 0.9));
        if (t > 0.3 && t < 0.9) sy += hop(t - 0.3, 0.6, 4);
        away = t > 1.1;
      } else if (p > AFTER) { sx = 54; away = 1; }
      oval(sx + 4, 38.5, 4, 0.8, 'm');
      spr(away ? SNOOP : SNOOP_L, sx, sy);
    }

    function lens(cx, cy, caught) {
      cx = round(cx) + 0.5; cy = round(cy) + 0.5;
      stroke([[cx + 4.5, cy + 4.5], [cx + 8, cy + 8]], 2, 'o');
      disc(cx, cy, 6.5, 'K'); disc(cx, cy, 5.5, 'b');
      if (caught) spr(BIT, cx - 2.5, cy - 2.5);
      d('W', [cx - 4, cy - 2, cx - 3, cy - 3, cx - 2, cy - 4]);
    }
    function sLeak(p, t, g) {
      var i;
      // the chip on its board
      oval(23, 47.5, 22, 2, 'h');
      r(2, 41, 42, 6, 'K'); r(3, 42, 40, 3, 'G'); r(3, 45, 40, 1, 'D'); d('Y', [6, 43, 40, 43]);
      for (i = 0; i < 5; i++) {
        r(12 + i * 4, 15, 1, 2, 'l'); r(12 + i * 4, 39, 1, 2, 'l'); r(8, 19 + i * 4, 2, 1, 'l'); r(32, 19 + i * 4, 2, 1, 'l');
      }
      r(10, 17, 22, 22, 'K'); r(11, 18, 20, 20, 'd'); r(15, 22, 12, 12, 'm'); r(15, 22, 12, 1, 'l'); r(15, 22, 1, 12, 'l');
      d('Y', [12, 19]);
      // the vendor's mailbox; the flag goes up with the report
      oval(57, 43.5, 4, 1, 'h');
      r(56, 31, 2, 12, 'o'); r(50, 22, 13, 10, 'K'); r(51, 23, 11, 8, 'B'); r(51, 23, 11, 1, 'b'); r(53, 26, 7, 1, 'K');
      if (p > AFTER || (p === AFTER && t > 1.35)) { r(63, 15, 1, 11, 'K'); r(64, 15, 4, 4, 'R'); }
      else { r(63, 27, 3, 1, 'K'); r(65, 28, 3, 3, 'R'); }
      // a red bit seeping out of the chip
      var bx = -1, by = 0;
      if (p === SETUP && t > 1.2) { var f = sm(t, 1.2, 2.4); bx = mix(32, 38, f); by = 26 - 6 * f + round(Math.sin(f * 6.28) * 1.2); }
      else if (p === READY || (p === ACT && t < 0.35)) { bx = 38; by = 20 + (p === READY ? bob(g) : 0); }
      if (bx >= 0) {
        d('m', [34, 26, 35, 27, 35, 28, 34, 29]);
        spr(BIT, bx, by);
      }
      // the magnifier sweeps the chip, then takes the bit
      var mx = 15, my = 24, caught = p >= AFTER;
      if (p === SETUP) { mx = mix(15, 24, sm(t, 0, 1.6)); my = mix(24, 30, sm(t, 0, 1.6)); }
      else if (p === READY) { mx = 24; my = 30; }
      else if (p === ACT) { mx = mix(24, 40, sm(t, 0, 0.35)); my = mix(30, 22, sm(t, 0, 0.35)); caught = t >= 0.35; }
      else if (p >= AFTER) { mx = 40; my = 22; }
      lens(mx, my, caught);
      // the report flies to the mailbox
      if (p === AFTER && t > 0.15 && t < 1.15) {
        var q = sm(t, 0.15, 1.15);
        spr(REPORT, mix(38, 53, q), mix(13, 19, q) - round(7 * Math.sin(Math.PI * q)));
      }
    }

    function model(x0, unknown) {  // the model, or a gray look-alike with no evidence of what it is
      var A = [[5, 16], [5, 23], [5, 30]], B = [[11, 19], [11, 27]], C = [16, 23], e = unknown ? 'm' : 'K';
      oval(x0 + 10, 42.5, 10, 1.4, 'h');
      r(x0 + 3, 38, 2, 4, e); r(x0 + 15, 38, 2, 4, e);
      r(x0, 11, 20, 27, e); r(x0 + 1, 12, 18, 25, 'W');
      if (unknown) { spr(ASK, x0 + 8, 21); return; }
      A.forEach(function (a) { B.forEach(function (b) { stroke([[x0 + a[0] + 1, a[1] + 1], [x0 + b[0] + 1, b[1] + 1]], 1, 'l'); }); });
      B.forEach(function (b) { stroke([[x0 + b[0] + 1, b[1] + 1], [x0 + C[0] + 1, C[1] + 1]], 1, 'm'); });
      A.concat(B, [C]).forEach(function (n) { r(x0 + n[0], n[1], 2, 2, 'B'); });
    }
    function sProof(p, t, g) {
      // the verifier's desk
      r(21, 34, 22, 3, 'K'); r(22, 34, 20, 1, 'q'); r(23, 37, 1, 5, 'K'); r(40, 37, 1, 5, 'K');
      // the answers slide out; the one without evidence gets an X and goes back
      var rc = p === IDLE ? 13 : p === SETUP ? mix(13, 23, sm(t, 0, 0.9)) : 23;
      var hc = p === IDLE ? 42 : p === SETUP ? mix(42, 34, sm(t, 0.5, 1.4)) : p === AFTER ? mix(34, 43, sm(t, 1.1, 1.8)) : p > AFTER ? 43 : 34;
      spr(CARD, rc, 27); spr(UCARD, hc, 27);
      model(2, 0); model(42, 1);
      if (p > ACT || (p === ACT && t >= 0.15)) spr(SEAL, rc + 1, 28);
      if (p > AFTER || (p === AFTER && t > 0.8)) { spr(UCARD, hc, 27); spr(XMARK, hc, 27); }
      // the stamp seals the model's answer, then finds nothing to stamp on the other one
      var sx = 27, sy = 7;
      if (p === SETUP) { sx = mix(27, 22, sm(t, 1.2, 2.0)); sy = mix(7, 11, sm(t, 1.2, 2.0)); }
      else if (p === READY) { sx = 22; sy = 11 + bob(g); }
      else if (p === ACT) { sx = 22; sy = t < 0.15 ? mix(11, 19, sm(t, 0, 0.15)) : t < 0.3 ? 19 : mix(19, 11, sm(t, 0.3, 0.6)); }
      else if (p === AFTER) {
        sx = t < 1.2 ? mix(22, 33, sm(t, 0, 0.5)) : mix(33, 27, sm(t, 1.2, 1.8));
        sy = t < 1.2 ? 11 + round(3 * Math.sin(Math.PI * f01(t, 0.5, 0.9))) : mix(11, 7, sm(t, 1.2, 1.8));
      }
      spr(STAMP, sx, sy);
    }

    function sAgent(p, t, g) {
      var i;
      // the sandbox, with a gap in its right wall
      oval(20, 46.5, 19, 1.6, 'h');
      r(2, 24, 36, 21, 'o'); r(4, 26, 32, 17, 'p'); r(36, 30, 2, 8, 'p'); r(2, 44, 36, 1, 'K');
      d('q', [8, 40, 15, 38, 27, 41, 32, 37, 12, 28, 30, 28]);
      // a tool: a terminal, lit once used
      var lit = p >= ACT || (p === SETUP && t > 0.8) || p === READY;
      r(5, 29, 10, 8, 'K'); r(6, 30, 8, 5, 'd'); d('Y', [7, 31]); r(9, 31, lit ? 4 : 1, 1, lit ? 'Y' : 'l'); r(8, 37, 4, 1, 'K');
      spr(ROBOT, 19, 30);
      var reachL = (p === SETUP && t > 0.1 && t < 1.7) || p > AFTER || (p === AFTER && t > 1.0);
      if (reachL) r(16, 38, 3, 1, 'K');
      // the agent's secrets, outside
      oval(56, 43.5, 7, 1, 'h');
      r(50, 33, 12, 10, 'K'); r(51, 34, 10, 8, 'o'); r(51, 37, 10, 1, 'K'); r(55, 36, 2, 3, 'Y');
      // a gold call to the tool and back, then a red one for the gate
      var gx = -1, bx = -1, by = 34;
      if (p === SETUP) {
        if (t > 0.2 && t < 0.8) gx = mix(17, 13, sm(t, 0.2, 0.8));
        else if (t > 1.0 && t < 1.6) gx = mix(13, 17, sm(t, 1.0, 1.6));
      }
      if (p === READY) { bx = mix(27, 31, sm(t, 0, 1.4)); by += bob(g); }
      else if (p === ACT) bx = 31;
      else if (p === AFTER && t < 0.55) {
        bx = t < 0.2 ? mix(31, 32, sm(t, 0, 0.2)) : mix(32, 28, sm(t, 0.2, 0.55));
        if (t > 0.2) by += hop(t - 0.2, 0.35, 2);
      }
      if (gx >= 0) spr(CALL[0], gx - 1, 31);
      if (bx >= 0) spr(CALL[1], bx - 1, by - 2);
      if (p === AFTER && t >= 0.55 && t < 0.95) {  // the blocked call crumbles
        var k = round(mix(2, 4, f01(t, 0.55, 0.95)));
        d('m', [29 - k, 34 - k, 29 + k, 34 - k, 29 - k, 34 + k, 29 + k, 34 + k]); d('R', [29 - k, 34, 29 + k, 34]);
      }
      // the gate's barrier drops at the block
      var bar = p === ACT ? sm(t, 0, 0.25) : p > ACT ? 1 : 0;
      for (i = 0; i < round(10 * bar); i++) r(35, 29 + i, 3, 1, i % 2 ? 'K' : 'Y');
      // the monitor: a camera, red on the bad call
      r(47, 12, 1, 29, 'K'); r(45, 41, 5, 1, 'K'); r(45, 11, 5, 1, 'K');
      r(41, 5, 12, 6, 'K'); r(42, 6, 10, 4, 'l'); r(42, 9, 10, 1, 'm'); r(38, 6, 3, 4, 'K'); r(39, 7, 1, 2, 'B');
      r(50, 7, 1, 1, p === READY || p === ACT ? 'R' : 'Y');
      if (bx >= 0 || gx >= 0) d('l', [36, 11, 35, 13, 34, 15, 33, 17, 32, 19]);
    }

    function sFlag(p, t) {
      var fy = p <= READY ? 30 : p === ACT ? mix(30, 9, sm(t, 0, 0.8)) : 9;
      r(20, 38, 24, 6, 'K'); r(21, 39, 22, 4, 'l'); r(31, 8, 1, 30, 'K'); r(32, fy, 9, 5, 'R');
    }

    var SCENES = [
      { draw: sEnclave, dur: [2.4, 0.7, 1.6], hot: [16, 6, 46, 44], hint: [29, 3], hit: [[ACT, 0.45, 32, 29, 'gold']] },
      { draw: sLeak, dur: [2.4, 0.6, 2.0], hot: [6, 10, 56, 38], hint: [37, 13],
        hit: [[ACT, 0.35, 40, 22, 'catch'], [AFTER, 1.35, 65, 16, 'soft']] },
      { draw: sProof, dur: [2.1, 0.6, 2.0], hot: [0, 2, 64, 42], hint: [23, 1],
        hit: [[ACT, 0.15, 26, 30, 'gold'], [AFTER, 0.8, 37, 30, 'red']] },
      { draw: sAgent, dur: [2.2, 0.5, 1.8], hot: [22, 18, 22, 30], hint: [29, 25],
        hit: [[ACT, 0.25, 36, 32, 'gold'], [AFTER, 0.55, 29, 34, 'red']] },
      { draw: sFlag, dur: [0.5, 0.8, 0.3], hot: [16, 4, 32, 42], hint: [29, 0], hit: [[ACT, 0.8, 36, 11, 'soft']] }
    ];
    // timing (s) and speed (map px a second): a stride, the walk, the arrival hop, the badge held up, its
    // flight to the rail, the wait before the way on is shown, the rest of a setup acted on early, the
    // ambient life
    var STRIDE = 0.16, SPEED = 100, HOP = 0.22, GET_T = 0.6, FLY = 0.7, GO_WAIT = 1.4, HURRY = 0.15;
    var AMB_OPEN = 5, AMB_INPUT = 12;
    // the ending, from the moment the figure arrives at the tree with every badge: the badge rail fades
    // (HUD_OUT, over HUD_T), the view eases into the close-up of the tree (at ZOOM_AT, for ZOOM_IN; ZOOM_OUT
    // back), the flowers light one per badge (from BLOOM_AT, BLOOM_GAP apart, the last at BLOOM_END), the
    // sun glows in two steps (GLOW_GAP after the last flower, and again), and the card follows (CARD_GAP
    // after the last flower, at CARD_AT, once the view is in the close-up)
    var HUD_OUT = 0.15, HUD_T = 0.3, ZOOM_AT = 0.45, ZOOM_IN = 1, ZOOM_OUT = 0.6, BLOOM_AT = 1.6, BLOOM_GAP = 0.25;
    var GLOW_GAP = 0.2, CARD_GAP = 0.6, BLOOM_END = BLOOM_AT + (N - 1) * BLOOM_GAP, CARD_AT = BLOOM_END + CARD_GAP;

    /* ---- the map: 248 by 156 pixels with scenery around; the path runs right past the lower stops,
       turns, and runs back past the upper ones to the tree */
    var CW = 248, CH = 156, MX = 48, MY = 32, Y1 = 141, Y2 = 71, TX = 0, TY = 6;
    var SLOT = [[20, 82], [118, 82], [140, 12], [66, 12]];
    var stops = [{ x: 14, y: Y1 }], segs = [], sc = [];
    themes.forEach(function (t, i) {
      stops.push({ x: SLOT[i][0] + 32, y: i < 2 ? Y1 : Y2, i: i });
      sc.push({ th: t, art: t.art, s: SCENES[t.art], x: SLOT[i][0], y: SLOT[i][1], p: IDLE, t: 0, won: 0, shown: 0, pop: 0, hurry: 0 });
    });
    stops.push({ x: TX + SIT.x + SEAT, y: Y2, goal: 1 });
    var GOAL = N + 1;

    function cubic(a, b, c, e) {
      for (var out = [], i = 0; i <= 24; i++) {
        var t = i / 24, u = 1 - t, k0 = u * u * u, k1 = 3 * u * u * t, k2 = 3 * u * t * t, k3 = t * t * t;
        out.push([k0 * a[0] + k1 * b[0] + k2 * c[0] + k3 * e[0], k0 * a[1] + k1 * b[1] + k2 * c[1] + k3 * e[1]]);
      }
      return out;
    }
    function measure(pts) {
      for (var len = [0], i = 1; i < pts.length; i++)
        len.push(len[i - 1] + Math.sqrt(Math.pow(pts[i][0] - pts[i - 1][0], 2) + Math.pow(pts[i][1] - pts[i - 1][1], 2)));
      return { pts: pts, len: len, total: len[len.length - 1] || 1 };
    }
    function along(seg, f) {  // a fraction f along a segment, by length
      var dd = f * seg.total, len = seg.len, i = 1;
      while (i < len.length - 1 && len[i] < dd) i++;
      var a = seg.pts[i - 1], b = seg.pts[i], t = (dd - len[i - 1]) / ((len[i] - len[i - 1]) || 1);
      return [a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t];
    }
    function wiggle(a, b, s) { var dx = b[0] - a[0]; return cubic(a, [a[0] + dx / 3, a[1] - 2 * s], [a[0] + dx * 2 / 3, a[1] + 2 * s], b); }
    (function () {
      for (var j = 0; j < stops.length - 1; j++) {
        var a = [stops[j].x, stops[j].y], b = [stops[j + 1].x, stops[j + 1].y], s = j % 2 ? 1 : -1, pts;
        if (a[1] === b[1]) pts = wiggle(a, b, s);
        else {  // along the row, a half circle up, and back
          var R = (a[1] - b[1]) / 2, cx = 204, cy = b[1] + R;
          pts = wiggle(a, [cx, a[1]], s).slice(0, -1);
          for (var k = 0; k <= 24; k++) { var th = Math.PI / 2 - Math.PI * k / 24; pts.push([cx + R * Math.cos(th), cy + R * Math.sin(th)]); }
          pts = pts.slice(0, -1).concat(wiggle([cx, b[1]], b, -s));
        }
        segs.push(measure(pts));
      }
    })();
    function posXY(pos) {
      var i = min(floor(pos), segs.length - 1);
      return pos === i ? [stops[i].x, stops[i].y] : along(segs[i], pos - i);
    }

    // the still parts, and each path segment once walked
    var BW = CW + 2 * MX, BH = CH + 2 * MY, bg = mk(BW, BH), lit = [];
    function taken(x, y) {  // on a court, the tree, the pond, the rail or the path?
      return sc.map(function (s) { return [s.x, s.y + 4, 64, 54]; }).concat([[TX, TY, 64, 68], [CW - 18, 0, 18, 58], [86, 102, 30, 22]])
        .some(function (k) { return x > k[0] - 3 && x < k[0] + k[2] && y > k[1] - 2 && y < k[1] + k[3]; }) ||
        segs.some(function (sg) { return sg.pts.some(function (q) { return abs(q[0] - x - 1) < 8 && abs(q[1] - y) < 8; }); });
    }
    function paintPath(seg, fill) {
      [[3.4, 'q'], [2.4, fill]].forEach(function (pass) {
        for (var dd = 0; dd <= seg.total; dd += 0.75) { var q = along(seg, dd / seg.total); disc(q[0], q[1], pass[0], pass[1]); }
      });
    }
    function court(x, y) {  // the bare ground under a scene, dithered at the edge
      oval(x + 32, y + 43, 33, 9, 'p'); oval(x + 32, y + 43, 36, 11.5, 'p', 0, 3, 1);
    }
    into(bg.getContext('2d'), MX, MY, function () {
      var seed = 11, i;
      function rnd() { seed = seed * 16807 % 2147483647; return (seed - 1) / 2147483646; }
      r(-MX, -MY, BW, BH, 'g');
      sc.forEach(function (q) { court(q.x, q.y); });
      // trees, bushes and flowers placed by hand
      [[192, 88], [6, 92], [214, 44], [-30, 20], [-22, 120], [258, 10], [264, 130], [120, -20], [40, 168]].forEach(function (q) { spr(TREE2, q[0], q[1]); });
      [[200, 120], [4, 108], [224, 60], [232, 148], [-16, 60], [256, 76], [180, -14], [70, 166]].forEach(function (q) { spr(BUSH, q[0], q[1]); });
      [[188, 116], [222, 116], [100, 128], [128, 76], [30, 76], [150, 151], [20, 151], [238, 64]].forEach(function (q) {
        d('Y', [q[0], q[1], q[0] + 3, q[1] + 1]); d('W', [q[0] + 1, q[1] + 2]); d('G', [q[0], q[1] + 1, q[0] + 3, q[1] + 2]);
      });
      d('D', [88, 108, 88, 109, 89, 107, 113, 116, 113, 117, 114, 115, 115, 116]);  // reeds at the pond
      // the pond
      oval(101, 113, 13, 6, 'q'); oval(101, 112.5, 12, 5.2, 'B'); oval(101, 112, 11, 4, 'b');
      for (i = 0; i < 70; i++) {  // quiet tufts of grass where there is room
        var tx = floor(-MX + rnd() * BW), ty = floor(-MY + rnd() * BH);
        if (!taken(tx, ty)) d(rnd() < 0.5 ? 'G' : 'h', [tx, ty, tx + 2, ty, tx + 1, ty + 1]);
      }
      segs.forEach(function (sg) { paintPath(sg, 'p'); });
      spr(SIGN, stops[0].x - 11, stops[0].y - 7);
      spr(TREE, TX, TY);
    });
    segs.forEach(function (sg) {
      var c = mk(BW, BH);
      into(c.getContext('2d'), MX, MY, function () { paintPath(sg, 'y'); });
      lit.push(c);
    });

    /* ---- DOM: the frame with its two cards, the bar and the caption */
    function mq(q) { return win.matchMedia ? win.matchMedia(q) : null; }
    var rmq = mq('(prefers-reduced-motion: reduce)'), reduced = !!(rmq && rmq.matches);
    var touch = !!(mq('(hover: none) and (pointer: coarse)') || {}).matches, kbd = false;
    function el(tag, cls, parent, text) {
      var e = doc.createElement(tag);
      if (cls) e.className = cls;
      if (text) e.textContent = text;
      if (parent) parent.appendChild(e);
      return e;
    }
    function set(e, o) { for (var k in o) e.setAttribute(k, o[k]); }
    function words(e, text) {  // a hyphenated word (TEE-based, SEV-SNP) does not break at its hyphen, as on v3's pages
      text.split(/(\S*\w-\w\S*)/).forEach(function (part, i) {
        if (part) { if (i % 2 && part.length <= 24) el('span', 'journey__nowrap', e, part); else e.appendChild(doc.createTextNode(part)); }
      });
      return e;
    }
    function icon(art, parent, look, cls) {  // a badge in HTML: a 9 by 9 canvas the stylesheet enlarges
      var c = el('canvas', 'journey__icon' + (cls || ''), parent);
      c.width = 9; c.height = 9; c.getContext('2d').drawImage((look || BADGE)[art], 0, 0);
      c.setAttribute('aria-hidden', 'true');
      return c;
    }
    var stage = el('div', 'journey__frame', mount), canvas = el('canvas', 'journey__canvas', stage);
    // the way into the close-up and out of it: the whole map, eased by a transform (zoomTo())
    var zoom = el('canvas', 'journey__zoom', stage), zctx = zoom.getContext('2d');
    zoom.width = BW; zoom.height = BH; zoom.hidden = true;
    set(zoom, { 'aria-hidden': 'true' });
    var tip = el('span', 'journey__tip', stage);
    var help = el('p', 'journey__sr'), live = el('p', 'journey__sr');
    help.id = 'journey-help';
    set(live, { 'aria-live': 'polite' });
    set(tip, { 'aria-hidden': 'true' });
    set(stage, { tabindex: 0, role: 'group', 'aria-roledescription': 'game', 'aria-label': 'Map of the research directions', 'aria-describedby': help.id });
    set(canvas, { role: 'img', 'aria-label': 'Pixel map: a figure walks past ' + (N > 1 ? NUM + ' stops, one for each research direction (' : 'a stop for the research direction (') +
      themes.map(function (t) { return t.title; }).join('; ') + '), to the SEPT tree. At each stop a short scene plays; the caption below says what it shows.' });
    var from = N > 1 ? 'from ' + LAYERS[0] + ' to ' + LAYERS[N - 1] : 'to ' + LAYERS[0];

    // the title card: what there is to earn, and Start
    var cardStart = el('div', 'journey__card journey__card--start', stage);
    var row = el('p', 'journey__card-badges', cardStart);
    sc.forEach(function (q) { icon(q.art, row, BADGE_LINE); });
    el('p', 'journey__card-title', cardStart, cap(NUM) + ' stop' + (N > 1 ? 's' : '') + ', ' + NUM + ' badge' + (N > 1 ? 's' : ''));
    var startText = el('p', 'journey__card-text', cardStart, 'Walk ' + from + '. At each stop, play the scene to earn its badge; then rest under the SEPT tree.');
    startText.id = 'journey-start-text';
    var go = el('p', 'journey__card-go', cardStart), bStart = el('button', 'journey__primary', go, 'Start');
    bStart.type = 'button';
    bStart.setAttribute('aria-describedby', startText.id);
    var startOr = el('span', 'journey__or', go), startKeys = el('p', 'journey__card-keys', cardStart);
    // the ending card: all badges, where to read on, and Replay
    var cardEnd = el('div', 'journey__card journey__card--end', stage);
    cardEnd.hidden = true;
    row = el('p', 'journey__card-badges', cardEnd);
    sc.forEach(function (q) { icon(q.art, row); });
    el('p', 'journey__card-title', cardEnd, 'Journey complete');
    var endText = el('p', 'journey__card-text', cardEnd, (N > 1 ? 'You earned all ' + NUM + ' badges, ' : 'You earned the badge, ') + from + '. Read more on the ');
    var aRes = el('a', '', endText, 'Research');
    endText.appendChild(doc.createTextNode(' page, or browse our '));
    var aPub = el('a', '', endText, 'Publications');
    endText.appendChild(doc.createTextNode('.'));
    aRes.href = attr('goal-href', 'research.html'); aPub.href = attr('papers-href', 'publications.html');
    endText.id = 'journey-end-text';
    go = el('p', 'journey__card-go', cardEnd);
    var bReplay = el('button', 'journey__primary', go, 'Replay'), endOr = el('span', 'journey__or', go);
    bReplay.type = 'button';
    bReplay.setAttribute('aria-describedby', endText.id);

    // the bar: where the figure is, the badge counter, Previous and Next
    var bar = el('div', 'journey__bar', mount), where = el('p', 'journey__where', bar);
    var count = el('p', 'journey__count', bar), countVis = el('span', '', count), countN, countSr = el('span', 'journey__sr', count);
    countVis.setAttribute('aria-hidden', 'true');
    countVis.appendChild(doc.createTextNode('Badges '));
    countN = el('b', '', countVis, '0');
    countVis.appendChild(doc.createTextNode('/' + N));
    var btns = el('div', 'journey__buttons', bar);
    function button(label, text) {
      var b = el('button', 'journey__btn', btns);
      b.type = 'button';
      el('span', '', b, text).setAttribute('aria-hidden', 'true');
      b.setAttribute('aria-label', label);
      return b;
    }
    var bPrev = button('Previous stop', '\u2190'), bNext = button('Next stop', '\u2192');

    // the caption: one pane a place (the signpost, each stop, the tree)
    var panesEl = el('div', 'journey__panes', mount);
    mount.appendChild(help); mount.appendChild(live);
    var items = [{ where: 'Start', title: cap(NUM) + ' research direction' + (N > 1 ? 's' : ''),
      href: attr('goal-href', 'research.html'), summary: LAYERS.join(' \u25b8 ') }];
    themes.forEach(function (t, i) {
      items.push({ where: (i + 1) + ' of ' + N + ' \u00b7 ' + LAYERS[i], title: t.title, href: t.href, summary: t.summary || '',
        papers: t.papers, s: sc[i] });
    });
    items.push({ where: 'The SEPT tree', title: attr('goal-title', 'All research') + (attr('goal-text', '') ? ': ' + attr('goal-text', '').replace(/\.$/, '') : ''),
      href: attr('goal-href', 'research.html'), summary: attr('goal-lead', '') });
    items.forEach(function (it) {
      var pane = el('div', 'journey__pane' + (it.s ? ' is-stop' : ''), panesEl), a, story;
      it.pane = pane;
      a = words(el('a', '', el('p', 'journey__ptitle', pane)), it.title);
      a.href = it.href;
      el('span', 'journey__arrow', a, '\u2192').setAttribute('aria-hidden', 'true');
      if (it.summary) words(el('p', 'journey__sum', pane), it.summary);
      story = el('div', 'journey__story', pane);
      if (it.s) {
        var st = STORY[it.s.art], ask = el('div', 'journey__ask', story), b = el('button', 'journey__act', ask), done = el('p', 'journey__done', story);
        b.type = 'button';
        icon(it.s.art, b); el('span', '', b, st[0]);
        it.ask = ask;
        it.or = el('span', 'journey__or', ask);
        it.or.setAttribute('aria-hidden', 'true');
        icon(it.s.art, done, BADGE_LINE, ' is-line'); icon(it.s.art, done); el('span', '', done, st[1]);
        // the button hides as the scene plays; sync() then moves the focus to the map
        b.addEventListener('click', function () { act(it.s); });
      } else {
        it.say = el('p', 'journey__note', story);
      }
      if (it.papers && it.papers.length) {
        var pp = el('p', 'journey__papers', pane);
        el('span', 'journey__plabel', pp, it.papers.length > 1 ? 'Papers' : 'Paper');
        it.papers.forEach(function (q, k) {
          if (k) el('span', 'journey__sep', pp, ' \u00b7 ').setAttribute('aria-hidden', 'true');
          var pa = words(el('a', '', pp), q.title);
          pa.href = q.href;
          if (q.venue_short) el('span', 'journey__venue', pp, '\u00a0(' + q.venue_short + (q.year ? '\u00a0' + q.year : '') + ')');
        });
      }
    });
    function shownCount() { return sc.filter(function (q) { return q.shown; }).length; }
    function goalNote() {  // the badges at the tree
      var n = shownCount(), g = items[GOAL].say, line = el('span', 'journey__badges');
      g.textContent = '';
      g.appendChild(line);
      sc.forEach(function (q) { icon(q.art, line, q.shown ? BADGE : BADGE_LINE); });
      el('span', '', g, n + ' of ' + N + ' badge' + (N > 1 ? 's' : '') + ' earned.' +
        (n < N ? ' Play the other stop' + (N - n > 1 ? 's' : '') + ' to complete the journey.' : ''));
      return n + ' of ' + N + ' badges earned.';
    }
    function setNotes() {  // words that depend on the input
      items.forEach(function (it) {
        if (it.or) it.or.textContent = 'or ' + (kbd ? 'press Enter' : (touch ? 'tap ' : 'click ') + STORY[it.s.art][2]);
      });
      items[0].say.textContent = 'At each stop a short scene shows the idea; play it to earn the stop\u2019s badge. ' +
        (touch ? 'Tap a stop to walk there, then tap its scene.' : 'Click a stop, or use the arrow keys and Enter.');
      goalNote();
      help.textContent = touch ? 'Tap a stop to walk there, and tap its scene to play it.'
        : 'Left and right arrows, or A and D, walk between stops; Enter or Space plays the scene at a stop.';
      startKeys.textContent = touch ? 'Tap a stop to walk there, and tap its scene to play it.'
        : 'Arrow keys or A and D walk; Enter or Space plays a scene. Clicks work too.';
      startOr.textContent = endOr.textContent = touch ? '' : 'or press Enter';
    }
    var ctx = canvas.getContext('2d');

    /* ---- state; pos is a place on the route: 0 the start, 1..N the stops, N + 1 the tree */
    var S = { mode: 'title', pos: 0, target: 0, face: 1, walkT: 0, far: 0, rest: false, lv: 0, open: false,
      g: 0, clock: 0, amb: 0, idle: 0, pose: 0, hop: 0, shake: 0, freeze: 0, flash: null, endT: 0,
      pane: -1, hover: -1, warm: 0, hud: 1 };
    // the close-up at the end: shown or not (on), the move into it or out of it (tr: from a to b, 0 the map
    // and 1 the close-up, t of T seconds; camN, the map's camera meanwhile), the flowers lit and the
    // sun's glow (0 to 2). The canvas's two views are NV, the map, and CV, the close-up (fit()).
    var Z = { on: false, tr: null, camN: [0, 0], lit: 0, glow: 0 };
    var STEP = 1000 / 60, vw = CW, vh = CH, cam = [0, 0], NV = { k: 1, vw: CW, vh: CH }, CV = null;
    var P = [], F = [], RINGS = [];  // particles, badges in flight, rings

    // Before the game hides a card, a pane or the action button, focus inside it moves to the map;
    // otherwise the browser drops it to the page's body, outside the dialog, and the keys stop working.
    function rescue(box) { if (box.contains(doc.activeElement)) stage.focus({ preventScroll: true }); }
    function sceneAt(j) { return j >= 1 && j <= N ? sc[j - 1] : null; }
    function setPhase(s, p) { s.p = p; s.t = 0; }
    function standing() { return S.pos === S.target; }
    function allShown() { return sc.every(function (q) { return q.shown; }); }
    function wake() { S.idle = 0; S.amb = AMB_INPUT; }
    var sayT = 0, sayQ = '';
    function say(text) {  // the live region: one message, or the ones that come together
      sayQ = sayQ ? sayQ + ' ' + text : text;
      if (sayT) return;
      live.textContent = '';
      sayT = setTimeout(function () { live.textContent = sayQ; sayQ = ''; sayT = 0; }, 80);
    }
    function goNext() {  // where the way on leads: the first stop without a badge, else the tree
      for (var i = 1; i <= N; i++) if (!sc[i - 1].won) return i;
      return GOAL;
    }

    /* ---- effects: pixels that fly, rings, the shake; none with reduced motion */
    var FX = {
      dust: { c: ['q', 'q', 'p'], sp: 7, up: 5, life: 0.36 },
      land: { c: ['q', 'q', 'p'], sp: 20, up: 3, life: 0.3, a0: 0, a1: 3.14 },
      sit: { c: ['q', 'q', 'q', 'p'], sp: 30, up: 10, g: 45, life: 0.45, a0: 0, a1: 3.14 },
      gold: { c: ['W', 'Y', 'Y', 'o'], sp: 34, up: 8, g: 60, life: 0.42 },
      catcher: { c: ['W', 'W', 'b', 'B'], sp: 42, life: 0.32 },
      red: { c: ['R', 'R', 'm'], sp: 26, up: 4, g: 40, life: 0.38 },
      soft: { c: ['W', 'Y'], sp: 16, up: 6, life: 0.3 },
      burst: { c: ['W', 'Y', 'Y', 'o'], sp: 46, up: 14, g: 80, life: 0.6 },
      bloom: { c: ['W', 'y', 'Y'], sp: 10, up: 7, life: 0.55 },
      trail: { c: ['Y', 'o'], sp: 4, life: 0.24, ui: 1 },
      slot: { c: ['W', 'Y', 'o'], sp: 26, life: 0.36, ui: 1 }
    };
    function puff(x, y, n, o) {
      if (reduced) return;
      for (var i = 0; i < n; i++) {
        var a = o.a0 !== undefined ? (rand() < 0.5 ? o.a0 : o.a1) + (rand() - 0.5) * 0.5 : rand() * 6.283, v = o.sp * (0.5 + rand() * 0.7);
        P.push({ x: x, y: y, vx: Math.cos(a) * v, vy: Math.sin(a) * v - (o.up || 0), g: o.g || 0, t: 0,
          life: o.life * (0.7 + rand() * 0.5), c: o.c, ui: o.ui ? 1 : 0 });
      }
    }
    function ring(x, y, r0, r1, life, c, ui) { if (!reduced) RINGS.push({ x: x, y: y, r0: r0, r1: r1, t: 0, life: life, c: c, ui: ui ? 1 : 0 }); }
    function effect(kind, x, y) {
      if (reduced) return;
      if (kind === 'catch') { S.freeze = 0.2; S.flash = [x + 0.5, y + 0.5]; S.shake = 0.18; puff(x, y, 12, FX.catcher); sfx('zap'); }
      else if (kind === 'gold') { S.shake = 0.12; puff(x, y, 9, FX.gold); sfx('hit'); }
      else if (kind === 'red') { puff(x, y, 7, FX.red); sfx('buzz'); }
      else puff(x, y, 5, FX.soft);
    }
    function dust() {
      var q = posXY(S.pos);
      puff(round(q[0]) - 2 * S.face, round(q[1]) - 1, 1 + (rand() < 0.4 ? 1 : 0), { c: FX.dust.c, sp: FX.dust.sp, up: FX.dust.up, life: FX.dust.life,
        a0: S.face > 0 ? 3.14 : 0, a1: S.face > 0 ? 3.14 : 0 });
    }
    function moveFx(s) {
      var i, p;
      for (i = P.length - 1; i >= 0; i--) {
        p = P[i];
        p.t += s;
        if (p.t >= p.life) { P.splice(i, 1); continue; }
        if (p.t < 0) continue;
        p.x += p.vx * s; p.y += p.vy * s; p.vy += p.g * s; p.vx *= 0.96;
      }
      for (i = RINGS.length - 1; i >= 0; i--) if ((RINGS[i].t += s) >= RINGS[i].life) RINGS.splice(i, 1);
      for (i = F.length - 1; i >= 0; i--) {  // the badges fly to the rail and leave a trail
        var f = F[i], to = slotXY(sc.indexOf(f.s));
        f.t += s;
        if (f.t >= FLY) { F.splice(i, 1); land(f.s); continue; }
        if ((f.trail = (f.trail || 0) + s) > 0.03) {
          f.trail = 0;
          var xy = flyXY(f, to);
          puff(xy[0] + 4, xy[1] + 4, 1, FX.trail);
        }
      }
    }
    function flyXY(f, to) {
      var q = sm(f.t, 0, FLY);
      return [round(mix(f.x, to[0], q)), round(mix(f.y, to[1], q) - 16 * Math.sin(Math.PI * q))];
    }
    function drawFx(ui) {
      P.forEach(function (p) {
        if (p.ui === ui && p.t >= 0) r(round(p.x), round(p.y), 1, 1, p.c[min(p.c.length - 1, floor(p.t / p.life * p.c.length))]);
      });
      RINGS.forEach(function (q) {
        if (q.ui !== ui || q.t < 0) return;
        var f = q.t / q.life, rad = mix(q.r0, q.r1, f);
        oval(q.x, q.y, rad, rad, q.c[min(q.c.length - 1, floor(f * q.c.length))], 0, 1, f > 0.55);
      });
    }

    /* ---- the game's moves */
    function earn(s) {  // the badge goes to the rail from above the figure's head
      if (s.won) return;
      s.won = 1;
      var q = posXY(S.pos);
      if (reduced) land(s);
      else F.push({ s: s, x: round(q[0]) - 4 - round(cam[0]), y: round(q[1]) - 25 - round(cam[1]), t: 0 });
    }
    function land(s) {  // the badge is in its slot: the counter goes up
      s.shown = 1; s.pop = 0.45;
      var n = shownCount(), to = slotXY(sc.indexOf(s));
      puff(to[0] + 4, to[1] + 4, 8, FX.slot);
      ring(to[0] + 4.5, to[1] + 4.5, 5, 11, 0.3, ['W', 'Y'], 1);
      count.classList.remove('is-pop');
      void count.offsetWidth;
      count.classList.add('is-pop');
      sfx('land');
      say('Badge earned: ' + n + ' of ' + N + '.' + (n === N ? ' Walk on to the SEPT tree.' : ''));
      if (S.pane === GOAL) goalNote();
      sync();
      checkEnd();
    }
    function act(s) {
      if (S.mode !== 'play' || !standing() || sceneAt(S.target) !== s) return;
      wake();
      // acted on during the setup: the rest of it runs by in HURRY seconds, then the scene plays
      if (s.p === SETUP) { if (!s.hurry) s.hurry = max(1, (s.s.dur[0] - s.t) / HURRY); kick(); return; }
      if (s.p >= ACT) {  // a stop already played: play its scene again
        if (s.p === DONE) { setPhase(s, reduced ? READY : SETUP); sync(); kick(); }
        return;
      }
      say(STORY[s.art][1]);
      if (reduced) { setPhase(s, DONE); earn(s); }
      else { setPhase(s, ACT); S.pose = 0.5; sfx('act'); }
      render(); sync(); kick();
    }
    function leave() {  // walking away from a stop settles its scene, so badges and scenes always agree
      var s = sceneAt(S.target);
      if (!s || S.pos !== S.target) return;
      s.hurry = 0;
      if (s.p >= ACT && s.p < DONE) { setPhase(s, DONE); earn(s); }
      else if (s.p === SETUP || s.p === READY) setPhase(s, s.won ? DONE : IDLE);
    }
    function start() {
      if (S.mode !== 'title') return;
      S.mode = 'play';
      stage.focus({ preventScroll: true });
      cardStart.hidden = true;
      cardGone();
      wake();
      say('The journey begins at the signpost. ' + help.textContent);
      sync(); kick();
    }
    function replay() {
      sc.forEach(function (s) { s.p = IDLE; s.t = 0; s.won = 0; s.shown = 0; s.pop = 0; s.hurry = 0; });
      P.length = F.length = RINGS.length = 0;
      S.pos = S.target = S.far = S.lv = 0; S.rest = false; S.mode = 'play'; S.endT = 0; S.face = 1; S.hop = S.shake = S.freeze = 0;
      // the map as at the start: the flowers dark, the sun without its glow, the badge rail back
      Z.tr = null; Z.lit = Z.glow = 0; S.hud = 1;
      stage.focus({ preventScroll: true });
      showCard(false);
      showPane(0);
      if (Z.on || !zoom.hidden) setClose(false);
      wake();
      say('Back at the signpost, with no badges.');
      render(); sync(); kick();
    }
    // the ending: the figure rests under the tree with every badge (ending()), and endingStep() plays the
    // rest on its clock, S.endT: the view closes in on the tree as the figure sits down (seatLevel()), the
    // flowers light, the sun glows, and showEnd() shows the card. Enter, Space or a click on the tree goes
    // straight to that last frame.
    // The clock runs on until the figure has left the tree (update()), so a player who turns back during
    // the move out of the close-up finds the ending where it was: the view turns back into the close-up,
    // and the card returns once it is there.
    function ending() { return S.mode === 'play' && S.rest && standing() && allShown(); }
    function endingStep(s) {
      var t = S.endT += s;
      if (t >= ZOOM_AT && (Z.tr ? !Z.tr.b : !Z.on)) zoomTo(1);
      while (Z.lit < N && t >= BLOOM_AT + Z.lit * BLOOM_GAP) light(Z.lit);
      if (t >= BLOOM_END + GLOW_GAP) Z.glow = max(Z.glow, t >= BLOOM_END + 2 * GLOW_GAP ? 2 : 1);
      if (t >= CARD_AT && !Z.tr) showEnd();
    }
    function light(i) {  // a flower lights, with a ring of light and a few sparks
      var x = TX + FLOWER[i][0] + 3.5, y = TY + FLOWER[i][1] + 3.5;
      Z.lit = i + 1;
      ring(x, y, 4, 9, 0.45, ['W', 'y']);
      puff(x - 0.5, y - 0.5, 5, FX.bloom);
      sfx('bloom', [1, 1.125, 1.25, 1.5][i]);
    }
    function showEnd() {  // the ending's last frame: the close-up, every flower lit, the glow, and the card
      S.mode = 'end'; S.endT = CARD_AT;
      Z.lit = N; Z.glow = 2; S.hud = 0;
      if (Z.tr || !Z.on) { Z.tr = null; setClose(true); }
      showCard(true);
      sfx('done');
      say('Journey complete. You earned ' + (N > 1 ? 'all ' + NUM + ' badges' : 'the badge') + '. Press Enter to play again, or Tab to the links.');
      render(); sync(); kick();
    }
    function checkEnd() { if (reduced && ending()) showEnd(); }
    function goTo(i) {
      i = max(0, min(GOAL, i));
      wake();
      if (S.mode === 'title') start();
      if (S.mode === 'end' && i !== GOAL) { S.mode = 'play'; showCard(false); }
      // where the figure still is: also the tree it had got up to leave, while the view eased out of the
      // close-up and before the walk began; it sits down again there (S.rest), and the ending resumes
      if (S.pos === i) { S.target = i; if (S.pane !== i || (i === GOAL && !S.rest)) arrive(false); }
      else { leave(); if (standing()) S.walkT = 0; S.target = i; S.rest = false; S.hop = 0; }
      if (i !== GOAL) zoomTo(0);  // away from the tree: back to the map, then the walk
      kick(); render(); sync();
    }
    function step(dir) {  // the next stop that way; pressed again while walking, the one after it
      var p = S.pos, t = S.target;
      goTo((p === t ? p : (t - p) * dir > 0 ? t : (dir > 0 ? Math.ceil(p) : floor(p)) - dir) + dir);
    }
    function actKey() {  // Enter or Space on the map
      wake();
      if (S.mode === 'title') return start();
      if (S.mode === 'end') return replay();
      if (ending()) return showEnd();
      var s = standing() && sceneAt(S.target);
      if (s) act(s);
      else if (standing() && S.target === 0) step(1);
      else if (standing() && S.target === GOAL) say(goalNote());
    }
    function arrive(walked) {
      var j = S.target, s = sceneAt(j), it = items[j], st = s && STORY[s.art];
      S.far = max(S.far, j); S.idle = 0; S.walkT = 0;
      S.rest = j === GOAL;
      if (s && s.p !== DONE) setPhase(s, reduced ? READY : SETUP);
      showPane(j);
      if (walked && !reduced) {
        var q = posXY(j);
        S.hop = HOP;
        puff(q[0], q[1], 5, FX.land);
        sfx('step');
      }
      say(it.title + '. ' + (it.summary ? it.summary.replace(/([^.!?])$/, '$1.') + ' ' : '') +
        (s ? (s.p !== DONE ? (touch ? 'Tap ' : 'Press Enter or click ') + st[2] + ' to ' + st[0].toLowerCase() + '.' : st[1])
          : j === GOAL ? goalNote() : ''));
      checkEnd();
    }
    function showPane(j) {
      if (j === GOAL) goalNote();
      if (S.pane === j) return;
      if (S.pane >= 0) { rescue(items[S.pane].pane); items[S.pane].pane.classList.remove('is-on'); }
      items[j].pane.classList.add('is-on');
      where.textContent = items[j].where;
      S.pane = j;
    }

    function update(dt) {
      var s = dt / 1000, sv;
      S.clock += s;
      S.shake = max(0, S.shake - s);
      if (S.freeze > 0) { S.freeze = max(0, S.freeze - s); return; }  // the catch: a moment's pause
      if (!reduced && S.amb > 0) S.g += s;
      S.amb = max(0, S.amb - s);
      S.pose = max(0, S.pose - s);
      S.hop = max(0, S.hop - s);
      S.idle += s;
      sc.forEach(function (q) { q.pop = max(0, q.pop - s); });
      moveFx(s);
      if (Z.tr && (Z.tr.t += s) >= Z.tr.T) {  // the move into the close-up or out of it is over
        var b = Z.tr.b;
        Z.tr = null;
        setClose(!!b, Z.camN.slice());
      }
      if (S.mode !== 'title') {
        if (S.pos !== S.target) { if (!Z.tr) walk(s); }  // leaving the close-up, the walk waits for the map
        else if ((sv = sceneAt(S.target))) playScene(sv, s);
        if (ending()) endingStep(s);
        else if (S.mode === 'play' && S.pos !== GOAL) S.endT = 0;
      }
      // Sitting down or getting up at once on the map, where it has no close-up (seatLevel()), the figure
      // raises a puff of dust at the seat and the feet.
      var lv = seatLevel();
      if (abs(lv - S.lv) > 3 && !Z.on) { puff(TX + SIT.x + 16, TY + SIT.y + 24, 11, FX.sit); puff(TX + SIT.x + 2, TY + SIT.y + 24, 6, FX.sit); }
      S.lv = lv;
      var to = hudTo();  // the badge rail fades out for the ending, and back in after it
      S.hud = reduced ? to : to < S.hud ? max(to, S.hud - s / HUD_T) : min(to, S.hud + s / HUD_T);
      var wt = warmth(), tg = camTarget(), k = reduced ? 1 : min(1, s * 3.2);
      S.warm = reduced || abs(wt - S.warm) < 0.004 ? wt : S.warm + (wt - S.warm) * min(1, s * 0.7);
      cam[0] += (tg[0] - cam[0]) * k; cam[1] += (tg[1] - cam[1]) * k;
      if (abs(tg[0] - cam[0]) < 0.3) cam[0] = tg[0];
      if (abs(tg[1] - cam[1]) < 0.3) cam[1] = tg[1];
    }
    function walk(s) {  // along the path, easing in and out of the stops
      if (reduced) { S.pos = S.target; arrive(true); return; }
      var dir = S.target > S.pos ? 1 : -1, si = dir > 0 ? floor(S.pos) : Math.ceil(S.pos) - 1, seg = segs[si];
      var bound = dir > 0 ? si + 1 : si, rest = abs(bound - S.pos) * seg.total + (bound === S.target ? 0 : 99);
      var v = SPEED * min(1, 0.55 + S.walkT * 3.5) * (rest < 10 ? max(0.4, rest / 10) : 1);
      var np = S.pos + dir * v * s / seg.total;
      if (dir * (np - bound) >= 0) np = bound;
      var a = posXY(S.pos)[0], b = posXY(np)[0], stride = floor(S.walkT / STRIDE);
      if (abs(b - a) > 0.01) S.face = b > a ? 1 : -1;
      S.pos = np; S.walkT += s;
      if (floor(S.walkT / STRIDE) !== stride) dust();
      if (S.pos === floor(S.pos)) { if (S.pos === S.target) arrive(true); else S.far = max(S.far, S.pos); }
    }
    function playScene(sv, s) {
      var T = sv.s.dur, t0 = sv.t;
      sv.t += s * (sv.hurry && sv.p === SETUP ? sv.hurry : 1);
      sv.s.hit.forEach(function (h) { if (h[0] === sv.p && t0 < h[1] && sv.t >= h[1]) effect(h[4], sv.x + h[2], sv.y + h[3]); });
      if (sv.p === SETUP && sv.t >= T[0]) { setPhase(sv, READY); if (sv.hurry) { sv.hurry = 0; act(sv); } }
      else if (sv.p === ACT && sv.t >= T[1]) setPhase(sv, AFTER);
      else if (sv.p === AFTER && sv.t >= T[2]) {
        if (sv.won) setPhase(sv, DONE);
        else {  // the figure holds up the badge
          var q = posXY(S.pos);
          setPhase(sv, GET);
          puff(round(q[0]), round(q[1]) - 21, 16, FX.burst);
          ring(round(q[0]) + 0.5, round(q[1]) - 20.5, 6, 15, 0.32, ['W', 'Y', 'o']);
          sfx('badge');
        }
      }
      else if (sv.p === GET && sv.t >= GET_T) { setPhase(sv, DONE); earn(sv); }
    }
    function warmth() { return (sc.filter(function (q) { return q.shown; }).length + (S.rest ? 1 : 0)) / (N + 1); }
    function clampTo(v, lo, hi) { return v < lo ? lo : v > hi ? hi : v; }
    function camFor(w, h) {  // the map's camera for a view w by h map px: the whole map, or the stop or the walker
      var s = standing() && sceneAt(S.target), fx, fy, q;
      if (s) { fx = s.x + 32; fy = s.y + 34; }
      else if (S.rest) { fx = 34; fy = 40; }
      else { q = posXY(S.pos); fx = q[0]; fy = q[1] - 26; }
      return [w >= CW ? (CW - w) / 2 : clampTo(fx - w / 2, 0, CW - w), h >= CH ? (CH - h) / 2 : clampTo(fy - h / 2, 0, CH - h)];
    }
    function camTarget() { return Z.on ? CV.cam : camFor(vw, vh); }
    function hudTo() { return Z.on || Z.tr || S.mode === 'end' || (ending() && S.endT >= HUD_OUT) ? 0 : 1; }

    /* ---- render */
    // the badge rail: down the right margin while the view shows it (the whole map, or the whole width with a
    // few rows cut), else across the top right of the view
    function across() { return vw < CW || vh < 64; }
    function slotXY(k) { return across() ? [vw - N * 12 - 5 + k * 12, 7] : [vw - 17, 8 + k * 12]; }
    function render() {
      if (Z.tr) { world(zctx, BW, BH, -MX, -MY); zoomFrame(); return; }  // the whole map, on its way
      var shx = S.shake > 0 && !reduced ? (floor(S.clock * 40) % 2 ? 1 : -1) : 0;
      world(ctx, vw, vh, round(cam[0]) + shx, round(cam[1]));
      // the badge rail, fixed to the frame; gold when full, and gone in the close-up
      var acr = across(), n = N * 12 + 5, rw = acr ? n : 17, rh = acr ? 17 : n;
      if (S.hud > 0.01) {
        ctx.globalAlpha = S.hud;
        into(ctx, acr ? vw - n - 4 : vw - 21, acr ? 3 : 4, function () {
          var e = allShown() ? 'o' : 'm';
          r(1, 0, rw - 2, rh, e); r(0, 1, rw, rh - 2, e); r(1, 1, rw - 2, rh - 2, 'W');
          sc.forEach(function (q, k) {
            var x = acr ? 3 + k * 12 : 3, y = acr ? 3 : 3 + k * 12;
            r(x, y, 11, 11, q.shown ? 'y' : 'q'); r(x + 1, y + 1, 9, 9, 'W');
            spr((q.shown ? BADGE : BADGE_OFF)[q.art], x + 1, y + 1 - (q.pop > 0.2 ? 1 : 0));
          });
        });
        ctx.globalAlpha = 1;
      }
      into(ctx, 0, 0, function () {
        F.forEach(function (f) {
          var xy = flyXY(f, slotXY(sc.indexOf(f.s)));
          held(f.s.art, xy[0], xy[1]);
        });
        drawFx(1);
      });
    }
    function world(c, w, h, cx, cy) {  // the map on c, w by h pixels, its top left at map (cx, cy)
      var i, s, walking = !standing(), here = walking ? -1 : S.target;
      c.imageSmoothingEnabled = false;
      c.fillStyle = PAL.g; c.fillRect(0, 0, w, h);
      c.drawImage(bg, -MX - cx, -MY - cy);
      into(c, -cx, -cy, function () {
        var g = S.g;
        for (i = 0; i < segs.length; i++) if (i < S.far) X.drawImage(lit[i], OX - MX, OY - MY);
        for (i = 1; i <= N; i++) spr(sc[i - 1].won ? PAD_ON : PAD, stops[i].x - 3, stops[i].y - 2);
        if (Z.glow) spr(glow(Z.glow), TX - 4, TY - 4);  // at the end, the sun glows behind the tree
        for (i = 0; i < Z.lit; i++) spr(LIT, TX + FLOWER[i][0] - 1, TY + FLOWER[i][1] - 1);
        var ph = floor(g / 0.9) % 4;  // two glints drifting on the pond
        d('W', [94 + ph * 2, 110, 95 + ph * 2, 110, 107 - ph, 114]);
        for (i = 0; i < N; i++) {
          s = sc[i];
          into(X, OX + s.x, OY + s.y, function () { s.s.draw(s.p, s.t, g); });
          if (i + 1 === here && s.p === READY && S.mode === 'play') {  // what to click
            var h = s.s.hint;
            spr(HINT, s.x + h[0], s.y + h[1] + (s.t < 6 ? bob(g + 0.3) : 0));
          }
        }
        if (S.freeze > 0 && S.flash) { oval(S.flash[0], S.flash[1], 9, 9, 'W', 0, 1); oval(S.flash[0], S.flash[1], 11, 11, 'Y', 0, 1, 1); }
        wayOn(g);
        figure(walking, here);
        drawFx(0);
        // a cloud, and now and then two birds: the map's sky, which dissolves with the rest of the map on the
        // way into the close-up, over the tree too, and is gone in it, where the tree stands alone
        var vl = Z.tr ? min(4, floor(zoomE() * 5)) : Z.on ? 4 : 0;  // the close-up's veil round the tree
        if (vl < 4) {
          var span = BW + 40, cxw = (g * 3 + 150) % span - MX - 20;
          sky(CLOUD_R, CLOUD, cxw, 1, vl);
          var bt = (g + 6) % 26;
          if (bt < 10 && S.amb > 0) {  // never frozen mid-air
            var bxw = mix(-MX, CW + MX, bt / 10), byw = 52 - bt * 3, fl = floor(g * 3.5) % 2;
            sky(BIRD_R[fl], BIRD[fl], bxw, byw, vl); sky(BIRD_R[1 - fl], BIRD[1 - fl], bxw + 9, byw + 4, vl);
          }
        }
        if (vl > 0) X.drawImage(veil(vl), OX - MX, OY - MY);
      });
      if (S.warm > 0.01) {  // the light warms with each badge
        c.globalCompositeOperation = 'multiply'; c.globalAlpha = 0.11 * S.warm;
        c.fillStyle = PAL.Y; c.fillRect(0, 0, w, h);
        c.globalCompositeOperation = 'source-over'; c.globalAlpha = 1;
      }
    }
    // an ASCII sprite's pixels (rows, at a, b) that the close-up's veil covers far from its box at level lv,
    // 0 to 4 (into), or the others: what dissolves in the veil's ordered dither, or appears through it
    function dith(rows, a, b, lv, into) {
      a = round(a); b = round(b);
      rows.forEach(function (row, y) {
        for (var x = 0; x < row.length; x++)
          if (PAL[row[x]] && (BAYER[((b + y) & 3) * 4 + ((a + x) & 3)] < lv * 4) === into) r(a + x, b + y, 1, 1, row[x]);
      });
    }
    // a sprite of the sky (s, from rows) at level vl of the veil, 0 to 3, dissolving as the map round it does
    function sky(rows, s, a, b, vl) { if (vl) dith(rows, a, b, vl, false); else spr(s, a, b); }
    function held(art, x, y) {  // a badge in an ink frame, to stand out over any scene
      r(x - 2, y - 1, 13, 11, 'K'); r(x - 1, y - 2, 11, 13, 'K'); r(x - 1, y - 1, 11, 11, 'W'); spr(BADGE[art], x, y);
    }
    // How far the figure under the tree has sat down: 0 standing, 4 seated. With every badge it settles into
    // the logo's pose as the view eases into the close-up, the walker dissolving into the seated figure
    // step by step with the veil round the tree (1 to 3), and gets up again the same way as the view eases
    // out; with fewer badges, the map has no close-up, and it sits down once its arrival hop is over.
    function seatLevel() {
      if (S.pos !== GOAL) return 0;
      if (Z.tr) return min(4, floor(zoomE() * 5));
      return Z.on || (S.rest && S.hop <= 0 && (!CV || sc.some(function (q) { return !q.won; }))) ? 4 : 0;
    }
    function figure(walking, here) {  // walking, standing, arms up, holding up the badge, or seated
      var lv = seatLevel(), q = stops[GOAL];
      if (lv >= 4) { spr(FIG.sit, TX + SIT.x, TY + SIT.y); return; }
      if (lv > 0) {  // sitting down or getting up as the view moves: the walker and the seated figure dissolve
        dith(['qqqqq'], q.x - 2, q.y, lv, false); dith(STAND_R, q.x - 3, q.y - 12, lv, false);
        dith(SIT_R, TX + SIT.x, TY + SIT.y, lv, true);
        return;
      }
      var xy = posXY(S.pos), fx = round(xy[0]), gy = round(xy[1]), f = FIG.stand, hs = sceneAt(here);
      var fy = gy - (S.hop > 0 ? round(Math.sin(Math.PI * S.hop / HOP) * 2) : 0);
      if (walking) f = floor(S.walkT / STRIDE) % 2 ? (S.face > 0 ? FIG.walk2 : FIG.walk2f) : (S.face > 0 ? FIG.walk1 : FIG.walk1f);
      else if (hs && hs.p === GET) {
        f = FIG.get;
        var by = fy - 25 + round(2 * (1 - sm(hs.t, 0, 0.15)));
        held(hs.art, fx - 4, by);
      }
      else if (S.pose > 0) f = FIG.get;
      r(fx - 2, gy, 5, 1, 'q');
      var sx = fx - (f === FIG.get ? 4 : 3), sy = fy - f.height + 1;
      if (abs(fx - TX - 37) < 8 && abs(gy - TY - 65) < 4) {  // over the tree's trunk, a rim of the sun's gold
        X.save(); X.beginPath(); X.rect(round(OX + TX + 33), round(OY + TY + 48), 8, 17); X.clip();
        spr(rim(f), sx - 1, sy - 1);
        X.restore();
      }
      spr(f, sx, sy);
    }
    // a figure's outline, one pixel all round, in the sun's gold: where the walker crosses the trunk, on its
    // way to the seat or from it, it keeps its dark silhouette apart from the trunk's (made when first needed)
    function rim(f) {
      if (f.rim) return f.rim;
      var c = mk(f.width + 2, f.height + 2), x = c.getContext('2d');
      [[0, 0], [1, 0], [2, 0], [0, 1], [2, 1], [0, 2], [1, 2], [2, 2]].forEach(function (o) { x.drawImage(f, o[0], o[1]); });
      x.globalCompositeOperation = 'source-in';
      x.fillStyle = PAL.Y; x.fillRect(0, 0, c.width, c.height);
      return (f.rim = c);
    }
    function wayOn(g) {  // after a moment at a played stop, a chevron points along the path to the next one
      if (S.mode !== 'play' || !standing() || !(reduced || S.idle >= GO_WAIT)) return;
      var hs = sceneAt(S.pos), nx = goNext();
      if (nx === S.pos || (hs && hs.p !== DONE)) return;
      if (S.amb > 0 && floor(g / 0.4) % 3 === 2) return;  // it blinks while the map is alive
      var dir = nx > S.pos ? 1 : -1, si = dir > 0 ? S.pos : S.pos - 1, p0 = posXY(S.pos);
      var p1 = posXY(S.pos + dir * min(0.45, 15 / segs[si].total)), dx = p1[0] - p0[0], dy = p1[1] - p0[1];
      var c = abs(dx) >= abs(dy) ? GO[dx > 0 ? 0 : 1] : GO[dy < 0 ? 2 : 3];
      // painted on the path itself, like a road marking, so it stays clear of every scene
      spr(c, round(p1[0] - c.width / 2), round(p1[1] - c.height / 2) - 1);
    }

    /* ---- loop: fixed timestep, runs only when needed and only while the dialog is open */
    var raf = 0, last = 0, acc = 0, lastState = '';
    function animating() {
      if (!S.open || doc.hidden) return false;
      if (reduced) return !standing();
      var s = standing() && sceneAt(S.target);
      return !standing() || S.amb > 0 || S.pose > 0 || S.hop > 0 || S.shake > 0 || S.freeze > 0 ||
        P.length > 0 || F.length > 0 || RINGS.length > 0 || !!Z.tr || S.hud !== hudTo() ||
        !!(s && s.p > IDLE && s.p < DONE && (s.p !== READY || s.t < 6)) ||
        (S.mode === 'play' && S.rest && allShown()) || (S.mode === 'play' && S.idle < GO_WAIT + 0.1) ||
        abs(warmth() - S.warm) > 0.004 || sc.some(function (q) { return q.pop > 0; }) ||
        abs(camTarget()[0] - cam[0]) > 0.3 || abs(camTarget()[1] - cam[1]) > 0.3;
    }
    function frameStep(t) {  // raf stays set, so a kick() in update() starts no second loop
      acc += last ? min(250, t - last) : STEP;
      last = t;
      for (var n = 0; acc >= STEP && n < 20; n++) { update(STEP); acc -= STEP; }
      render(); sync();
      if (animating()) raf = requestAnimationFrame(frameStep); else { raf = 0; last = 0; }
    }
    function kick() { if (!raf && animating()) { last = acc = 0; raf = requestAnimationFrame(frameStep); } }
    function disable(b, off) { if ((b.getAttribute('aria-disabled') === 'true') !== off) b.setAttribute('aria-disabled', off); }
    function sync() {  // buttons, caption, counter and cards; data-state for tests
      var won = 0, shown = 0, s = standing() && sceneAt(S.target);
      sc.forEach(function (q) { won += q.won; shown += q.shown; });
      disable(bPrev, S.target === 0 && S.pos === 0);
      disable(bNext, S.pos === GOAL && S.target === GOAL);
      items.forEach(function (it) {
        if (it.s) {  // the action only where it works; the badge
          var ask = S.mode === 'play' && it.s.p < ACT && standing() && sceneAt(S.target) === it.s;
          if (!ask && it.pane.classList.contains('is-ask')) rescue(it.ask);
          it.pane.classList.toggle('is-ask', ask);
          it.pane.classList.toggle('is-won', !!it.s.won);
        }
      });
      if (countN.textContent !== String(shown)) countN.textContent = shown;
      var sr = shown + ' of ' + N + ' badges earned';
      if (countSr.textContent !== sr) countSr.textContent = sr;
      var st = S.mode + ':' + (standing() ? 'at' + S.target : 'walk') + (s ? ':' + PHASES[s.p] : '') + (S.rest ? ':rest' : '') +
        ':won' + won + ':shown' + shown + (Z.on ? ':close' : '');
      if (st !== lastState) mount.setAttribute('data-state', lastState = st);
    }

    /* ---- input. Keys work anywhere in the dialog: arrows (or A and D) walk, Enter and Space act, except
       on a link or a button, which keep them. Should the focus still fall out of the dialog to the page's
       body, the keys play on and bring it back to the map. A pointer anywhere switches the hints to
       click or tap. */
    function setTouch(on) { if (on !== touch) { touch = on; setNotes(); } }
    function setKbd(on) { if (on !== kbd) { kbd = on; setNotes(); } }
    function onKey(e) {
      var k = e.key, t = e.target, ctl = t !== stage && /^(A|BUTTON)$/.test(t.tagName), dir = 0;
      if (!S.open || e.ctrlKey || e.metaKey || e.altKey || e.shiftKey || e.isComposing) return false;
      setKbd(true);
      setTouch(false);
      if (/^(ArrowRight|Right|d|D)$/.test(k)) dir = 1;
      else if (/^(ArrowLeft|Left|a|A)$/.test(k)) dir = -1;
      if (dir) { if (!e.repeat) step(dir); }
      else if ((k === 'Enter' || k === ' ' || k === 'Spacebar') && !ctl) { if (!e.repeat) actKey(); }
      else if ((k === 'Home' || k === 'End') && !ctl) goTo(k === 'Home' ? 0 : GOAL);
      else return false;
      e.preventDefault();
      return true;
    }
    dialog.addEventListener('keydown', onKey);
    doc.addEventListener('keydown', function (e) {
      if (S.open && !dialog.contains(e.target) && onKey(e) && !dialog.contains(doc.activeElement)) stage.focus({ preventScroll: true });
    });
    function toMap(e) {
      var rc = canvas.getBoundingClientRect();
      return [(e.clientX - rc.left) / rc.width * vw + round(cam[0]), (e.clientY - rc.top) / rc.height * vh + round(cam[1])];
    }
    function hit(q) {  // the place at a map point: a scene or its pad, the tree, or the signpost
      if (Z.on) {  // the close-up shows the tree alone
        return q[0] >= CLOSE[0] && q[0] < CLOSE[0] + CLOSE[2] && q[1] >= CLOSE[1] && q[1] < CLOSE[1] + CLOSE[3] ? GOAL : -1;
      }
      for (var i = 0; i < N; i++) {
        var s = sc[i], h = s.s.hot;
        if ((q[0] >= s.x + h[0] && q[0] < s.x + h[0] + h[2] && q[1] >= s.y + h[1] && q[1] < s.y + h[1] + h[3]) ||
          (abs(q[0] - stops[i + 1].x) < 9 && q[1] > stops[i + 1].y - 16 && q[1] < stops[i + 1].y + 5)) return i + 1;
      }
      if (q[0] >= TX && q[0] < TX + TREE_W && q[1] >= TY && q[1] < TY + TREE_H + 4) return GOAL;
      if (q[0] >= 0 && q[0] < 24 && q[1] > Y1 - 18 && q[1] < Y1 + 6) return 0;
      return -1;
    }
    mount.addEventListener('pointerdown', function (e) {
      setKbd(false);
      setTouch(e.pointerType === 'touch' || e.pointerType === 'pen');
    }, true);
    canvas.addEventListener('click', function (e) {
      tip.classList.remove('is-on');
      wake();
      if (Z.tr) { if (ending()) showEnd(); return; }  // while the view moves, a click only hurries the ending
      var i = hit(toMap(e)), s = sceneAt(i);
      if (S.mode === 'title') { start(); if (i > 0) goTo(i); return; }
      if (ending() && (i < 0 || i === GOAL)) return showEnd();
      if (i < 0) return;
      if (s && standing() && S.target === i) act(s);
      else goTo(i);
    });
    canvas.addEventListener('pointermove', function (e) {  // names the place under the mouse
      if (e.pointerType !== 'mouse') return;
      var i = Z.tr ? -1 : hit(toMap(e)), on = S.mode !== 'title' && i >= 0 && !(standing() && i === S.target), k, q;
      canvas.style.cursor = i >= 0 || S.mode === 'title' ? 'pointer' : '';
      if (i === S.hover && on === tip.classList.contains('is-on')) return;
      S.hover = i;
      tip.classList.toggle('is-on', on);
      if (!on) return;
      tip.textContent = i && i <= N ? items[i].title : items[i].where;
      q = i && i <= N ? [sc[i - 1].x + sc[i - 1].s.hot[0] + sc[i - 1].s.hot[2] / 2, sc[i - 1].y + sc[i - 1].s.hot[1]] : i ? [TX + 31, TY] : [stops[0].x, Y1 - 14];
      k = canvas.getBoundingClientRect().width / vw;
      tip.style.left = clampTo((q[0] - round(cam[0])) * k - tip.offsetWidth / 2, 4, stage.clientWidth - tip.offsetWidth - 4) + 'px';
      tip.style.top = max(4, (q[1] - round(cam[1])) * k - tip.offsetHeight - 2) + 'px';
    });
    canvas.addEventListener('pointerleave', function () { S.hover = -1; tip.classList.remove('is-on'); });
    function press(b, fn) { b.addEventListener('click', function () { if (b.getAttribute('aria-disabled') !== 'true') fn(); }); }
    press(bPrev, function () { step(-1); });
    press(bNext, function () { step(1); });
    bStart.addEventListener('click', start);
    bReplay.addEventListener('click', replay);

    doc.addEventListener('visibilitychange', function () {
      if (!doc.hidden) last = acc = 0;  // no catching up on the time hidden
      kick();
    });
    if (rmq && rmq.addEventListener) rmq.addEventListener('change', function (e) {
      reduced = e.matches;
      if (reduced) {  // settle everything that moves
        if (Z.tr) { var b = Z.tr.b; Z.tr = null; setClose(!!b, Z.camN.slice()); }
        S.hud = hudTo();
        if (!standing()) { S.pos = S.target; arrive(false); }
        var s = sceneAt(S.target);
        if (s && s.p !== READY && s.p !== DONE) { if (s.p >= ACT) { setPhase(s, DONE); earn(s); } else setPhase(s, READY); }
        F.splice(0).forEach(function (f) { land(f.s); });
        P.length = RINGS.length = 0; S.shake = S.freeze = S.hop = 0;
        checkEnd();
      }
      render(); sync(); kick();
    });

    /* ---- sound: off until the visitor turns it on; a few short square-wave notes made on the spot */
    var AC = win.AudioContext || win.webkitAudioContext, audio = null, sound = false;
    var SFX = {  // [from Hz, to Hz (0 = steady), seconds, wave, volume, delay]
      step: [[220, 150, 0.05, 'triangle', 0.05]],
      act: [[392, 784, 0.1, 'square', 0.025]],
      hit: [[130, 60, 0.12, 'triangle', 0.12]],
      zap: [[1400, 500, 0.08, 'square', 0.025], [180, 70, 0.14, 'triangle', 0.12, 0.02]],
      buzz: [[110, 90, 0.12, 'square', 0.02]],
      badge: [[784, 0, 0.08, 'square', 0.025], [988, 0, 0.08, 'square', 0.025, 0.07], [1319, 0, 0.12, 'square', 0.025, 0.14]],
      land: [[1568, 0, 0.06, 'triangle', 0.05]],
      bloom: [[1047, 0, 0.14, 'triangle', 0.045]],
      done: [[523, 0, 0.12, 'square', 0.025], [659, 0, 0.12, 'square', 0.025, 0.12], [784, 0, 0.12, 'square', 0.025, 0.24],
        [1047, 0, 0.32, 'square', 0.025, 0.36]]
    };
    function sfx(name, pitch) {  // pitch: a factor on the note's frequencies (a flower's step up the scale)
      if (!sound || !audio) return;
      var f = pitch || 1;
      try {
        SFX[name].forEach(function (n) {
          var t = audio.currentTime + (n[5] || 0), o = audio.createOscillator(), v = audio.createGain();
          o.type = n[3]; o.frequency.setValueAtTime(n[0] * f, t);
          if (n[1]) o.frequency.exponentialRampToValueAtTime(n[1] * f, t + n[2]);
          v.gain.setValueAtTime(0.0001, t);
          v.gain.exponentialRampToValueAtTime(n[4], t + 0.008);
          v.gain.exponentialRampToValueAtTime(0.0001, t + n[2]);
          o.connect(v); v.connect(audio.destination);
          o.start(t); o.stop(t + n[2] + 0.02);
        });
      } catch (e) { }
    }
    var closer = dialog.querySelector('[data-journey-close]');
    if (AC && closer && closer.parentNode) {
      var bSound = el('button', 'journey__sound');
      bSound.type = 'button';
      set(bSound, { 'aria-pressed': 'false', 'aria-label': 'Sound' });  // the label, also where narrow screens hide the word
      bSound.innerHTML = '<svg viewBox="0 0 16 16" width="16" height="16" aria-hidden="true" focusable="false">' +
        '<path d="M2 6h3l4-3v10L5 10H2z" fill="currentColor"/>' +
        '<path class="journey__wave" d="M11.2 5.6c.9.7 1.3 1.5 1.3 2.4s-.4 1.7-1.3 2.4M12.8 3.6c1.4 1.1 2.2 2.6 2.2 4.4s-.8 3.3-2.2 4.4" fill="none" stroke="currentColor" stroke-width="1.4"/>' +
        '<path class="journey__mute" d="M11 6l4 4M15 6l-4 4" stroke="currentColor" stroke-width="1.4"/></svg><span>Sound</span>';
      closer.parentNode.insertBefore(bSound, closer);
      bSound.addEventListener('click', function () {
        sound = !sound;
        bSound.setAttribute('aria-pressed', String(sound));
        if (sound) {
          try { if (!audio) audio = new AC(); if (audio.resume) audio.resume(); } catch (e) { audio = null; }
          sfx('land');
        }
      });
    }

    /* ---- size, in whole device pixels a map pixel (K), from 2 to 3 CSS px. In the framed dialog: the whole
       map, as large as the window allows with the bar and the caption. Full screen (FULL, as in
       journey.css): the map's whole height, as large as the screen allows while at least VIEW map pixels
       stay in view across, and the view follows the figure. Where not even 2 CSS px fit, a crop at 2 CSS
       px that leaves room for the bar and the caption, down to 60% of the map's height in the framed
       dialog and half of it full screen; in a window 480 px tall or less and wider than tall (SHORT, a
       phone held sideways) the crop leaves room for the bar only, and the caption scrolls under it. A
       short window held upright (an old 320 px phone) keeps the crop that leaves room for the caption.
       The map never crops the title card: a card too tall for the frame drops its keys line, then its
       badges (fitCard()), and if even that does not fit, the frame grows while the card shows (cardGone())
       and the dialog scrolls; the ending card has a place of its own (closeUp()). The canvas is placed on
       whole device pixels, so it stays crisp at any devicePixelRatio. */
    var FULL = '(max-width: 540px), (max-height: 480px)', SHORT = '(max-height: 480px) and (orientation: landscape)', VIEW = 160;
    var rq = 0, lastKey = '', frameH = 0, grown = false;
    function frameSize(w, h) {
      dialog.style.setProperty('--journey-w', w + 'px');
      dialog.style.setProperty('--journey-h', h + 'px');
      frameH = h;
    }
    // the title card made the frame taller and has gone: the map takes its own size again
    function cardGone() { if (grown) { grown = false; lastKey = ''; queueFit(); } }
    // a card's form for a box maxH css px tall (and w wide; 0 for the stylesheet's, undefined to leave them):
    // whole, without its keys line, or also without its badges; true if one fits. A hidden card is
    // measured unseen.
    function shape(c, w, maxH) {
      var s = c.style, hid = c.hidden, ok;
      if (w !== undefined) s.width = w ? w + 'px' : '';
      if (maxH !== undefined) s.maxHeight = maxH ? maxH + 'px' : '';
      if (hid) { s.visibility = 'hidden'; c.hidden = false; }
      c.classList.remove('is-short', 'is-shorter');
      if (c.scrollHeight > c.clientHeight + 1) c.classList.add('is-short');
      if (c.scrollHeight > c.clientHeight + 1) c.classList.add('is-shorter');
      ok = c.scrollHeight <= c.clientHeight + 1;
      if (hid) { c.hidden = true; s.visibility = ''; }
      return ok;
    }
    function shortest(c, w) {  // the height of a card's shortest form, w css px wide
      var s = c.style, hid = c.hidden, ht;
      shape(c, w, 1);  // in a box 1 px tall no form fits, so the last, the shortest, stays
      s.maxHeight = 'none';
      if (hid) { s.visibility = 'hidden'; c.hidden = false; }
      ht = Math.ceil(c.getBoundingClientRect().height);
      if (hid) { c.hidden = true; s.visibility = ''; }
      return ht;
    }
    function fitCard() {  // the title card's form for the frame; returns the frame height it needs
      if (cardStart.hidden) return 0;
      shape(cardStart);
      return cardStart.scrollHeight + cardStart.offsetHeight - cardStart.clientHeight + 16;  // .journey__card's max-height
    }
    function fit() {
      if (!S.open) return;
      var dpr = win.devicePixelRatio || 1, W = doc.documentElement.clientWidth, H = win.innerHeight;
      var key = W + 'x' + H + '@' + dpr + ':' + panesEl.offsetHeight;
      if (key === lastKey && fitCard() <= frameH + 1) return snap();
      if (Z.tr) { Z.on = !!Z.tr.b; Z.tr = null; }  // a new size ends a move into the close-up or out of it at once
      var full = !!(mq(FULL) || {}).matches, short = !!(mq(SHORT) || {}).matches;
      var pad = parseFloat(win.getComputedStyle(dialog).getPropertyValue('--j-pad')) || 24;
      var availW = full ? W : W - 32 - 2 * pad, availH = H - (full ? 0 : 32);
      var kmin = max(1, Math.ceil(2 * dpr - 0.05)), kmax = floor(3 * dpr + 0.05), k, w, h, whole, chrome;
      // framed: the whole map, as large as the window allows. Full screen: the map's whole height, as
      // large as the screen's height allows while at least VIEW map pixels stay in view across
      for (k = min(kmax, floor(availW * dpr / (full ? VIEW : CW))); k >= kmin; k--) {
        w = full ? min(availW, BW * k / dpr) : CW * k / dpr; h = CH * k / dpr;
        frameSize(w, h);
        chrome = dialog.scrollHeight - h;
        if (h + chrome <= availH) break;
      }
      if (k < kmin) {  // not even that: 2 CSS px, cropped; the view follows the figure
        k = kmin;
        w = min(availW, (full ? BW : CW) * k / dpr); h = whole = CH * k / dpr;
        frameSize(w, h);
        chrome = dialog.scrollHeight - h;
        h = availH - chrome;
        if (short) {  // the head, the map and the bar; the caption below them scrolls
          h = availH - (panesEl.getBoundingClientRect().top - dialog.getBoundingClientRect().top + dialog.scrollTop - whole);
        }
        h = clampTo(h, (full ? 0.5 : 0.6) * whole, whole);
        frameSize(w, h);
      }
      var need = fitCard();
      grown = need > h;
      if (grown) { h = min(need, CH * k / dpr); frameSize(w, h); fitCard(); }
      NV = { k: k, vw: Math.ceil(w * dpr / k - 1e-6), vh: Math.ceil(h * dpr / k - 1e-6), w: w, h: h };
      CV = closeUp(w, h, dpr, k, short);
      lastKey = W + 'x' + H + '@' + dpr + ':' + panesEl.offsetHeight;
      setClose(Z.on);
    }

    /* ---- the close-up at the end: the tree at a larger whole number of device pixels a map pixel, so its
       pixels stay crisp, keeping CLOSE in view (map px: the tree with its glow, the seated figure and the
       path's end) with GAP css px round it. Where the frame has room, the ending card stands beside the
       tree, CARD_MIN to CARD_MAX css px wide, and the tree is as large as that leaves room for ('beside');
       else, or where the tree alone would be much larger, the tree is as large as the frame allows and
       the card goes under the map, over the caption ('under'). At most three times the map's scale, and
       never smaller than it. The frame keeps its height, except on a phone held sideways too short for
       the card beside the tree (closeUp()). */
    var CLOSE = [TX - 3, TY - 1, 69, 70], GAP = 16, CARD_MIN = 264, CARD_MAX = 400;
    // Round the box, the close-up veils the map in plain meadow, dithered in over BAND pixels, so the tree
    // stands alone and nothing of the next stop is cut by the frame's edge; the ground of a stop's scene
    // (its court, with its dithered edge) is veiled whole, also where it reaches into the box beside the
    // sun's glow. On the way in and out the veil comes and goes in four strengths (veil(), made when first
    // needed), each covering what the weaker ones cover and more, so no pixel turns back; the sky goes
    // with it (sky()).
    var BAND = 3, BAYER = [0, 8, 2, 10, 12, 4, 14, 6, 3, 11, 1, 9, 15, 7, 13, 5], VEILS = [];
    function onCourt(x, y) {  // map pixel (x, y) on a stop's court and clear of the sun's glow
      var u = x + 0.5 - TX - 31, v = y + 0.5 - TY - 34;
      return u * u + v * v > 34 * 34 && sc.some(function (q) {
        var a = (x + 0.5 - q.x - 32) / 36, b = (y + 0.5 - q.y - 43) / 11.5;
        return a * a + b * b <= 1;
      });
    }
    function veil(level) {
      if (VEILS[level]) return VEILS[level];
      var c = mk(BW, BH), x = c.getContext('2d'), img = x.createImageData(BW, BH), px = img.data, i, j, o;
      var rgb = [1, 3, 5].map(function (a) { return parseInt(PAL.g.substr(a, 2), 16); });
      for (j = 0; j < BH; j++) {
        for (i = 0; i < BW; i++) {
          var dx = max(CLOSE[0] - (i - MX), i - MX - (CLOSE[0] + CLOSE[2] - 1), 0);
          var dy = max(CLOSE[1] - (j - MY), j - MY - (CLOSE[1] + CLOSE[3] - 1), 0);
          var f = Math.sqrt(dx * dx + dy * dy) / BAND;
          if (f < 1 && onCourt(i - MX, j - MY)) f = 1;
          if (BAYER[(j & 3) * 4 + (i & 3)] >= min(1, f) * level * 4) continue;
          o = (j * BW + i) * 4;
          px[o] = rgb[0]; px[o + 1] = rgb[1]; px[o + 2] = rgb[2]; px[o + 3] = 255;
        }
      }
      x.putImageData(img, 0, 0);
      return (VEILS[level] = c);
    }
    function closeUp(w, h, dpr, k, short) {
      // A phone held sideways, whose caption scrolls under the bar, keeps the card beside the tree: with half
      // the gap round them, the card as wide as there is room for (and so as short), and at the map's own
      // scale if it must. Where even the card's shortest form is taller than the frame (a window about 280
      // px tall), the frame grows to fit it while the close-up shows (frameFor()), and the bar moves down
      // as much. The frame is fh css px tall in the close-up.
      var gap = short ? GAP / 2 : GAP, fh = h, fit = (h - 2 * gap) * dpr / CLOSE[3], need;
      var alone = max(k, min(3 * k, floor(min((w - 2 * gap) * dpr / CLOSE[2], fit)))), kz, cw = 0, cam, place = 'under';
      function camAt(mid) {  // the camera that puts the box's middle mid css px from the left, within the map's margins
        return [clampTo(round(CLOSE[0] + CLOSE[2] / 2 - mid * dpr / kz), -MX, CW + MX - Math.ceil(w * dpr / kz - 1e-6)),
          clampTo(round(CLOSE[1] + CLOSE[3] / 2 - fh / 2 * dpr / kz), -MY, CH + MY - Math.ceil(fh * dpr / kz - 1e-6))];
      }
      function beside() {  // the card's width beside the box at kz, and the camera; false if narrower than CARD_MIN
        cw = floor(w - 3 * gap - CLOSE[2] * kz / dpr);
        if (!short) cw = min(CARD_MAX, cw);
        cam = camAt((w - gap - cw) / 2);
        // where the box falls once the camera keeps to the map's margins: the card starts a gap after it
        cw = min(cw, floor(w - 2 * gap - (CLOSE[0] + CLOSE[2] - cam[0]) * kz / dpr));
        return cw >= CARD_MIN;
      }
      // beside the card, as large as the card leaves room for, unless the tree alone would be much larger
      // (by more than a third)
      for (kz = min(3 * k, floor(fit)); kz > (short ? k - 1 : k) && (short || kz * 4 >= alone * 3); kz--) {
        if (beside() && shape(cardEnd, cw, h - 2 * gap)) { place = 'beside'; break; }
      }
      if (place === 'under' && short) {  // sideways and too short: the map's scale, and a taller frame
        kz = k;
        if (beside() && (need = shortest(cardEnd, cw) + 2 * gap) <= CH * k / dpr) {
          fh = max(h, need);
          cam[1] = camAt(0)[1];
          place = 'beside';
        }
      }
      if (place === 'under') { kz = alone; cam = camAt(w / 2); }
      return { k: kz, vw: Math.ceil(w * dpr / kz - 1e-6), vh: Math.ceil(fh * dpr / kz - 1e-6), w: w, h: fh, place: place,
        cam: cam, cardW: cw, cardH: fh - 2 * gap, gap: gap };
    }
    function placeCard() {  // the ending card in its place: beside the tree in the frame, or under the map
      var c = cardEnd, under = !CV || CV.place === 'under', box = under ? panesEl : stage, a = doc.activeElement;
      if (c.parentNode !== box) {
        var had = c.contains(a);
        box.appendChild(c);
        if (had) a.focus({ preventScroll: true });
      }
      c.classList.toggle('is-under', under);
      c.classList.toggle('is-beside', !under);
      c.style.right = under ? '' : CV.gap + 'px';
      if (!under) shape(c, CV.cardW, CV.cardH);
      // over the caption, whose panes hide while it shows: a shorter form if the caption is shorter than
      // the card, and if even that does not fit, the card's own height (the dialog scrolls)
      else if (!shape(c, 0, max(1, panesEl.clientHeight - 30))) c.style.maxHeight = '';
      panesEl.classList.toggle('has-card', under && !c.hidden);
    }
    function showCard(on) {  // the ending card, or none
      if (!on) rescue(cardEnd);
      else if (CV && CV.place === 'under') rescue(panesEl);  // the caption hides under the card
      cardEnd.hidden = !on;
      placeCard();
    }
    // the frame's height for the map, or for the close-up (close) and the moves into it and out of it,
    // which on a short phone held sideways is taller (closeUp())
    function frameFor(close) {
      var v = close && CV ? CV : NV;
      if (v.h && v.h !== frameH) frameSize(v.w, v.h);
    }
    function view(camera) {  // the canvas for the map or the close-up, its camera, and the card's place
      var dpr = win.devicePixelRatio || 1, v = Z.on && CV ? CV : NV;
      frameFor(Z.on);
      vw = v.vw; vh = v.vh;
      canvas.width = vw; canvas.height = vh;
      canvas.style.width = vw * v.k / dpr + 'px'; canvas.style.height = vh * v.k / dpr + 'px';
      zoom.style.width = BW / dpr + 'px'; zoom.style.height = BH / dpr + 'px';
      cam = Z.on && CV ? CV.cam.slice() : camera || camTarget();
      placeCard();
      snap();
      render();
    }
    function setClose(on, camera) {  // the close-up, or the map with the camera given, at once
      Z.on = on && !!CV;
      zoom.hidden = true;
      view(Z.on ? null : camera);
    }
    // The way in and out: the whole map drawn on the zoom canvas, which a transform scales from one view's
    // device pixels a map pixel to the other's (geometrically) while the middle of CLOSE glides from its
    // place in one view to its place in the other; at both ends the pixels fall exactly where the
    // canvas puts them. Nearest-neighbour scaling (journey.css) keeps them sharp on the way.
    function zoomE() { var t = Z.tr; return t ? mix(t.a, t.b, sm(t.t, 0, t.T)) : Z.on ? 1 : 0; }
    function zoomTo(b) {  // ease into the close-up (1) or back to the map (0); at once with reduced motion
      var e = zoomE(), n = camFor(NV.vw, NV.vh);
      if ((Z.tr ? Z.tr.b : e) === b) return;
      if (reduced || !S.open || !CV) { Z.tr = null; setClose(!!b, n); return; }
      if (!Z.tr) Z.camN = b ? [round(cam[0]), round(cam[1])] : [round(n[0]), round(n[1])];
      Z.tr = { a: e, b: b, t: 0, T: (b ? ZOOM_IN : ZOOM_OUT) * abs(b - e) };
      tip.classList.remove('is-on');
      frameFor(true);  // the move runs in the close-up's frame; the zoom canvas fills it
      render();
      zoom.hidden = false;
      kick();
    }
    function zoomFrame() {
      var dpr = win.devicePixelRatio || 1, e = zoomE(), a = NV.k, b = CV.k, s = a * Math.pow(b / a, e);
      var mx = CLOSE[0] + CLOSE[2] / 2, my = CLOSE[1] + CLOSE[3] / 2, n = Z.camN, c = CV.cam;
      var px = mix((mx - n[0]) * a, (mx - c[0]) * b, e), py = mix((my - n[1]) * a, (my - c[1]) * b, e);
      zoom.style.transform = 'matrix(' + s + ',0,0,' + s + ',' + (px - (mx + MX) * s) / dpr + ',' + (py - (my + MY) * s) / dpr + ')';
    }
    function snap() {  // the canvas on whole device pixels, wherever the frame falls
      var b = stage.getBoundingClientRect(), dpr = win.devicePixelRatio || 1;
      function off(v) { v *= dpr; return (round(v) - v) / dpr + 'px'; }
      canvas.style.left = zoom.style.left = off(b.left); canvas.style.top = zoom.style.top = off(b.top);
    }
    function queueFit() { if (S.open && !rq) rq = requestAnimationFrame(function () { rq = 0; fit(); kick(); }); }
    (function watchDpr() {  // zoom or another screen changes the dpr
      var m = mq('(resolution: ' + (win.devicePixelRatio || 1) + 'dppx)');
      function on() { m.removeEventListener('change', on); queueFit(); watchDpr(); }
      if (m && m.addEventListener) m.addEventListener('change', on);
    })();
    if ('ResizeObserver' in win) new win.ResizeObserver(queueFit).observe(panesEl);
    win.addEventListener('resize', queueFit);
    dialog.addEventListener('scroll', snap);
    dialog.addEventListener('animationend', snap);
    if (doc.fonts && doc.fonts.ready) doc.fonts.ready.then(queueFit);

    function focusIn() { if (S.mode === 'title') bStart.focus(); else stage.focus({ preventScroll: true }); }
    function show() {
      S.open = true; S.amb = AMB_OPEN; S.idle = 0; last = acc = 0;
      setNotes();
      lastKey = '';
      fit();
      focusIn();
      render(); sync(); kick();
    }
    function hide() {
      S.open = false;
      if (raf) cancelAnimationFrame(raf);
      raf = 0; last = 0;
      S.hover = -1; tip.classList.remove('is-on');
      if (audio && audio.suspend) audio.suspend();
    }

    setNotes();
    showPane(0);
    sync();
    return { show: function () { if (audio && sound && audio.resume) audio.resume(); show(); }, hide: hide, focus: focusIn };
  }
})();
