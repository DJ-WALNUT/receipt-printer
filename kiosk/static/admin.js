/* 관리 페이지: 이용실적(기간별 합계, CSV 내려받기)과 만들어진 이미지 보기·지우기.
   키오스크 화면(app.js)처럼 오래된 iPad 브라우저에서도 돌도록 ES5 문법만 쓴다. */
(function () {
  'use strict';

  var REQUEST_TIMEOUT = 15000;
  var state = { tab: window.location.hash === '#images' ? 'images' : 'stats', from: '', to: '', imgOffset: 0, images: [], viewing: null };

  function $(id) { return document.getElementById(id); }

  function el(tag, className, text) {
    var node = document.createElement(tag);
    if (className) { node.className = className; }
    if (text !== undefined && text !== null) { node.textContent = text; }
    return node;
  }

  function clear(node) { while (node.firstChild) { node.removeChild(node.firstChild); } }

  function api(method, url, body) {
    var options = { method: method, credentials: 'same-origin', headers: {} };
    if (body !== undefined) {
      options.headers['Content-Type'] = 'application/json';
      options.body = JSON.stringify(body);
    }
    var answer = fetch(url, options).then(function (response) {
      return response.json().catch(function () { return {}; }).then(function (data) {
        if (response.status === 403 && url.indexOf('/api/admin/login') === -1) { showLogin('로그인이 풀렸어요. 다시 들어가 주세요.'); }
        return { status: response.status, data: data };
      });
    });
    var giveUp = new Promise(function (resolve, reject) {
      setTimeout(function () { reject(new Error('timeout')); }, REQUEST_TIMEOUT);
    });
    return Promise.race([answer, giveUp]);
  }

  function pad(n) { return n < 10 ? '0' + n : String(n); }
  function iso(date) { return date.getFullYear() + '-' + pad(date.getMonth() + 1) + '-' + pad(date.getDate()); }
  function num(n) { return String(n).replace(/\B(?=(\d{3})+(?!\d))/g, ','); }

  // ---------------------------------------------------------------- 로그인

  function showLogin(message) {
    $('login').hidden = false;
    $('stats').hidden = true;
    $('images').hidden = true;
    $('tabs').hidden = true;
    $('logout').hidden = true;
    closeViewer();
    var notice = $('loginNotice');
    notice.textContent = message || '';
    notice.hidden = !message;
    $('pin').value = '';
  }

  function showAdmin() {
    $('login').hidden = true;
    $('tabs').hidden = false;
    $('logout').hidden = false;
    selectTab(state.tab);
  }

  $('loginForm').addEventListener('submit', function (event) {
    event.preventDefault();
    var pin = $('pin').value;
    if (!pin) { return; }
    api('POST', '/api/admin/login', { pin: pin }).then(function (result) {
      if (result.status === 200) { showAdmin(); return; }
      showLogin(result.data.error || '들어가지 못했어요.');
    }).catch(function () { showLogin('키오스크 서버에 연결할 수 없어요.'); });
  });

  $('logout').addEventListener('click', function () {
    api('POST', '/api/admin/logout').then(function () { showLogin(''); }).catch(function () { showLogin(''); });
  });

  // ---------------------------------------------------------------- 탭

  function selectTab(tab) {
    state.tab = tab;
    if (window.history && window.history.replaceState) { window.history.replaceState(null, '', '#' + tab); }
    Array.prototype.forEach.call(document.querySelectorAll('.tab'), function (node) {
      node.setAttribute('aria-pressed', node.getAttribute('data-tab') === tab ? 'true' : 'false');
    });
    $('stats').hidden = tab !== 'stats';
    $('images').hidden = tab !== 'images';
    if (tab === 'stats') { loadStats(); } else { loadImages(true); }
  }

  Array.prototype.forEach.call(document.querySelectorAll('.tab'), function (node) {
    node.addEventListener('click', function () { selectTab(node.getAttribute('data-tab')); });
  });

  // ---------------------------------------------------------------- 이용실적

  function setPeriod(from, to, preset) {
    state.from = from;
    state.to = to;
    $('from').value = from;
    $('to').value = to;
    Array.prototype.forEach.call(document.querySelectorAll('.chip'), function (node) {
      node.setAttribute('aria-pressed', node === preset ? 'true' : 'false');
    });
  }

  Array.prototype.forEach.call(document.querySelectorAll('#presets .chip'), function (node) {
    node.addEventListener('click', function () {
      var today = new Date();
      var days = node.getAttribute('data-days');
      if (days) {
        var start = new Date(today.getFullYear(), today.getMonth(), today.getDate() - (parseInt(days, 10) - 1));
        setPeriod(iso(start), iso(today), node);
      } else {
        var shift = parseInt(node.getAttribute('data-month'), 10);
        var first = new Date(today.getFullYear(), today.getMonth() + shift, 1);
        var last = shift === 0 ? today : new Date(today.getFullYear(), today.getMonth() + shift + 1, 0);
        setPeriod(iso(first), iso(last), node);
      }
      loadStats();
    });
  });

  $('apply').addEventListener('click', function () {
    setPeriod($('from').value, $('to').value, null);
    loadStats();
  });

  function query() { return '?from=' + encodeURIComponent(state.from) + '&to=' + encodeURIComponent(state.to); }

  function loadStats() {
    var notice = $('statsNotice');
    if (state.from && state.to && state.from > state.to) {
      notice.textContent = '시작 날짜가 끝 날짜보다 늦어요.';
      notice.hidden = false;
      return;
    }
    $('csv').href = '/api/admin/usage.csv' + query();
    api('GET', '/api/admin/stats' + query()).then(function (result) {
      if (result.status === 403) { return; }
      if (result.status !== 200) { throw new Error(result.data.error || 'stats'); }
      notice.hidden = true;
      renderStats(result.data);
    }).catch(function (e) {
      notice.textContent = '실적을 불러오지 못했어요. ' + (e.message === 'timeout' ? '서버 연결을 확인해 주세요.' : e.message);
      notice.hidden = false;
    });
  }

  function tile(label, value) {
    var node = el('div', 'tile');
    node.appendChild(el('div', 'tile__label', label));
    node.appendChild(el('div', 'tile__value', value));
    return node;
  }

  function row(cells, className) {
    var tr = el('tr', className || '');
    cells.forEach(function (cell) {
      var td = el('td', cell && cell.className ? cell.className : '', cell && cell.text !== undefined ? cell.text : cell);
      tr.appendChild(td);
    });
    return tr;
  }

  function head(table, labels) {
    var thead = el('thead');
    var tr = el('tr');
    labels.forEach(function (label) { tr.appendChild(el('th', '', label)); });
    thead.appendChild(tr);
    table.appendChild(thead);
  }

  function renderStats(data) {
    // 화면의 날짜 칸을 서버가 실제로 쓴 기간으로 맞춘다 (처음 열었을 때 최근 30일)
    if (!state.from) { setPeriod(data.from, data.to, document.querySelector('#presets .chip[data-days="30"]')); }
    var t = data.total;
    var tiles = $('tiles');
    clear(tiles);
    tiles.appendChild(tile('인쇄한 장 수', num(t.sheets)));
    tiles.appendChild(tile('인쇄 작업', num(t.jobs)));
    tiles.appendChild(tile('방문자 / 운영자 장 수', num(t.visitor_sheets) + ' / ' + num(t.staff_sheets)));
    tiles.appendChild(tile('실패한 작업', num(t.failed)));

    var byContent = $('byContent');
    clear(byContent);
    head(byContent, ['콘텐츠', '작업', '장 수', '방문자', '운영자', '실패']);
    var body = el('tbody');
    if (!data.by_content.length) {
      var empty = row(['이 기간에는 기록이 없어요.', '', '', '', '', ''], 'zero');
      body.appendChild(empty);
    }
    data.by_content.forEach(function (c) {
      body.appendChild(row([c.title, num(c.jobs), num(c.sheets), num(c.visitor_sheets), num(c.staff_sheets),
        { text: num(c.failed), className: c.failed ? 'bad' : '' }]));
    });
    byContent.appendChild(body);
    var foot = el('tfoot');
    foot.appendChild(row(['합계', num(t.jobs), num(t.sheets), num(t.visitor_sheets), num(t.staff_sheets), num(t.failed)]));
    byContent.appendChild(foot);

    var byDate = $('byDate');
    clear(byDate);
    head(byDate, ['날짜', '작업', '장 수', '실패']);
    var dates = el('tbody');
    var WEEK = ['일', '월', '화', '수', '목', '금', '토'];
    data.by_date.slice().reverse().forEach(function (d) {
      var parts = d.date.split('-');
      var day = new Date(parseInt(parts[0], 10), parseInt(parts[1], 10) - 1, parseInt(parts[2], 10));
      dates.appendChild(row([d.date + ' (' + WEEK[day.getDay()] + ')', num(d.jobs), num(d.sheets),
        { text: num(d.failed), className: d.failed ? 'bad' : '' }], d.jobs ? '' : 'zero'));
    });
    byDate.appendChild(dates);
  }

  // ---------------------------------------------------------------- 이미지

  $('imgContent').addEventListener('change', function () { loadImages(true); });
  $('imgDate').addEventListener('change', function () { loadImages(true); });
  $('imgClear').addEventListener('click', function () { $('imgDate').value = ''; loadImages(true); });
  $('imgMore').addEventListener('click', function () { loadImages(false); });

  function imageUrl(image) {
    return '/api/admin/images/' + encodeURIComponent(image.content) + '/' + encodeURIComponent(image.file);
  }

  function loadImages(reset) {
    if (reset) { state.imgOffset = 0; state.images = []; }
    var params = '?offset=' + state.imgOffset +
      '&content=' + encodeURIComponent($('imgContent').value || '') +
      '&date=' + encodeURIComponent($('imgDate').value || '');
    api('GET', '/api/admin/images' + params).then(function (result) {
      if (result.status !== 200) { return; }
      var data = result.data;
      fillContentSelect(data.contents);
      state.images = state.images.concat(data.images);
      state.imgOffset = state.images.length;
      $('imgCount').textContent = data.total ? '이미지 ' + num(data.total) + '개 중 ' + num(state.images.length) + '개' : '이미지가 없어요.';
      $('imgMore').hidden = state.images.length >= data.total;
      renderGallery(reset ? data.images : null, data.images);
    }).catch(function () { $('imgCount').textContent = '이미지를 불러오지 못했어요.'; });
  }

  function fillContentSelect(contents) {
    var select = $('imgContent');
    var current = select.value;
    clear(select);
    var all = el('option', '', '전체');
    all.value = '';
    select.appendChild(all);
    contents.forEach(function (c) {
      if (!c.count && c.name !== current) { return; }
      var option = el('option', '', c.title + ' (' + c.count + ')');
      option.value = c.name;
      select.appendChild(option);
    });
    select.value = current;
  }

  function renderGallery(fresh, added) {
    var gallery = $('gallery');
    if (fresh) { clear(gallery); }
    added.forEach(function (image) {
      var card = el('button', 'thumb');
      card.type = 'button';
      var img = el('img', 'thumb__img');
      img.alt = image.title + ' ' + image.time;
      img.loading = 'lazy';
      img.src = imageUrl(image);
      card.appendChild(img);
      var text = el('span', 'thumb__text');
      text.appendChild(el('span', 'thumb__title', image.title));
      text.appendChild(el('span', '', image.time.slice(5, 16) + (image.tag ? ' · ' + image.tag : '')));
      card.appendChild(text);
      card.addEventListener('click', function () { openViewer(image); });
      gallery.appendChild(card);
    });
  }

  function openViewer(image) {
    state.viewing = image;
    $('viewerTitle').textContent = image.title;
    $('viewerMeta').textContent = image.time + (image.tag ? ' · ' + image.tag : '') + ' · ' + image.file;
    $('viewerImg').src = imageUrl(image);
    $('viewerImg').alt = image.title + ' ' + image.time;
    $('viewerOpen').href = imageUrl(image);
    $('viewer').hidden = false;
  }

  function closeViewer() {
    state.viewing = null;
    $('viewer').hidden = true;
    $('viewerImg').removeAttribute('src');
  }

  $('viewerClose').addEventListener('click', closeViewer);
  $('viewer').addEventListener('click', function (event) { if (event.target === $('viewer')) { closeViewer(); } });
  document.addEventListener('keydown', function (event) { if (event.key === 'Escape') { closeViewer(); } });

  $('viewerDelete').addEventListener('click', function () {
    var image = state.viewing;
    if (!image || !window.confirm(image.title + ' (' + image.time + ') 이미지를 지울까요? 되돌릴 수 없어요.')) { return; }
    api('DELETE', imageUrl(image)).then(function (result) {
      if (result.status !== 200) { window.alert(result.data.error || '지우지 못했어요.'); return; }
      closeViewer();
      loadImages(true);
    }).catch(function () { window.alert('지우지 못했어요.'); });
  });

  // ---------------------------------------------------------------- 시작

  api('GET', '/api/admin/me').then(function (result) {
    $('kioskName').textContent = result.data.name || '키오스크';
    document.title = (result.data.name || '키오스크') + ' 관리';
    if (!result.data.admin_enabled) { showLogin('관리자 기능이 꺼져 있어요 (서버에 KIOSK_PIN 이 없습니다).'); $('loginForm').hidden = true; return; }
    if (result.data.role === 'staff') { showAdmin(); } else { showLogin(''); }
  }).catch(function () { showLogin('키오스크 서버에 연결할 수 없어요.'); });
})();
