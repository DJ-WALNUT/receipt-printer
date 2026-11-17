/* 키오스크 화면.
 *
 * 화면은 /api/catalog 가 내려주는 메뉴만으로 그려진다. 콘텐츠 이름으로 갈라지는 코드는 없다.
 * 콘텐츠를 추가하거나 옵션을 바꿀 때는 그 콘텐츠의 content.toml 만 고친다.
 *
 * 오래된 iPad에서도 돌도록 ES2017 문법까지만 쓴다 (?. 와 ?? 를 쓰지 않는다).
 */
(function () {
  'use strict';

  var IDLE_VISITOR = 60 * 1000;      // 이만큼 아무도 누르지 않으면 첫 화면으로
  var IDLE_STAFF = 3 * 60 * 1000;    // 관리자는 이만큼 쉬면 나간다
  var DONE_STAY = 3000;              // 다 뽑은 뒤 처음으로 돌아가기까지
  var POLL = 1000;
  var RETRY = 5000;
  var REQUEST_TIMEOUT = 10000;       // 서버가 이만큼 답이 없으면 연결이 끊긴 것으로 본다
  var LONG_PRESS = 2000;             // 제목을 이만큼 누르면 관리자 비밀번호 입력

  var state = {
    catalog: null,
    tabs: [],            // [{title, items: [content, ...]}]
    numbers: {},         // 콘텐츠 이름 -> 판에서의 번호
    tab: 0,
    content: null,       // 고른 콘텐츠
    mode: null,          // 고른 모드
    values: {},
    sheets: 1,
    same: false,         // 여러 장을 모두 같은 문제로 뽑을지 (same_sheets 인 모드에서만 고를 수 있다)
    phase: 'form',       // form | sending | printing | done | failed
    notice: '',          // 옵션 화면에 보일 오류
    noticeField: null,   // 그 오류가 어느 항목 탓인지 (항목 id)
    version: null,       // 서버가 다시 뜨면 바뀐다
    tornJob: null,       // 뜯기는 움직임을 이미 보여준 작업
    job: null,           // 지금 따라가고 있는 인쇄 작업
    jobContent: null,    // 그 작업의 콘텐츠 이름 (뜯긴 칸 표시용)
    offline: false,
    lastTouch: Date.now()
  };

  var $ = function (id) { return document.getElementById(id); };
  var dom = {
    name: $('name'), status: $('status'), tabs: $('tabs'), grid: $('grid'), panel: $('panel'),
    strip: $('strip'), overlay: $('overlay'), queueButton: $('queueButton'), logoutButton: $('logoutButton'),
    staffBadge: $('staffBadge')
  };

  // ---------------------------------------------------------------- 작은 도구

  function el(tag, className, text) {
    var node = document.createElement(tag);
    if (className) { node.className = className; }
    if (text !== undefined && text !== null) { node.textContent = text; }
    return node;
  }

  function clear(node) {
    while (node.firstChild) { node.removeChild(node.firstChild); }
    return node;
  }

  function button(className, text, onPress) {
    var node = el('button', className, text);
    node.type = 'button';
    node.addEventListener('click', onPress);
    return node;
  }

  function icon(paths) {
    var svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
    svg.setAttribute('viewBox', '0 0 24 24');
    svg.setAttribute('aria-hidden', 'true');
    paths.forEach(function (d) {
      var path = document.createElementNS('http://www.w3.org/2000/svg', 'path');
      path.setAttribute('d', d);
      svg.appendChild(path);
    });
    return svg;
  }
  var ICON = { minus: ['M5 12h14'], plus: ['M5 12h14', 'M12 5v14'], check: ['M5 12.5l4.5 4.5L19 7.5'] };

  function isStaff() { return !!state.catalog && state.catalog.role === 'staff'; }

  function api(method, url, body) {
    var options = { method: method, credentials: 'same-origin', headers: {} };
    if (body !== undefined) {
      options.headers['Content-Type'] = 'application/json';
      options.body = JSON.stringify(body);
    }
    var answer = fetch(url, options).then(function (response) {
      return response.json().catch(function () { return {}; }).then(function (data) {
        return { status: response.status, data: data };
      });
    });
    // 와이파이가 조용히 끊기면 fetch는 끝없이 기다린다. 일정 시간 안에 답이 없으면 실패로 본다.
    var giveUp = new Promise(function (resolve, reject) {
      setTimeout(function () { reject(new Error('timeout')); }, REQUEST_TIMEOUT);
    });
    return Promise.race([answer, giveUp]);
  }

  // ---------------------------------------------------------------- 메뉴 불러오기

  function loadCatalog() {
    return api('GET', '/api/catalog').then(function (result) {
      if (result.status !== 200) { throw new Error('catalog'); }
      state.offline = false;
      setCatalog(result.data);
    }).catch(function () {
      state.offline = true;
      renderBar();
      renderStrip();
      setTimeout(loadCatalog, RETRY);
    });
  }

  /* 처음 화면에 있을 때 조용히 메뉴를 다시 받는다. 서버가 새로 떴으면 화면 파일까지 새로 받는다. */
  function refreshCatalog() {
    api('GET', '/api/catalog').then(function (result) {
      if (result.status !== 200) { return; }
      state.offline = false;
      if (state.version && result.data.version !== state.version) {
        if (atHome() && !jobActive()) { window.location.reload(); }
        return;
      }
      if (atHome() && result.data.role !== state.catalog.role) { setCatalog(result.data); }
      else { renderBar(); renderStrip(); }
    }).catch(function () { state.offline = true; renderBar(); renderStrip(); });
  }

  function setCatalog(catalog) {
    state.catalog = catalog;
    state.version = catalog.version;
    state.tabs = [];
    state.numbers = {};
    var number = 0;
    catalog.menu.forEach(function (item) {
      var items = item.kind === 'group' ? item.items : [item];
      items.forEach(function (content) { number += 1; state.numbers[content.name] = number; });
      state.tabs.push({ title: item.title, items: items });
    });
    document.title = catalog.name;
    dom.name.textContent = catalog.name;
    if (state.tab >= state.tabs.length) { state.tab = 0; }
    // 역할이 바뀌면 보이는 모드가 달라지므로 고른 것을 새 메뉴에서 다시 찾는다
    var kept = state.content ? findContent(state.content.name) : null;
    if (kept) { choose(kept, false); } else { state.content = null; state.mode = null; }
    renderAll();
  }

  function findContent(name) {
    var found = null;
    state.tabs.forEach(function (tab) {
      tab.items.forEach(function (content) { if (content.name === name) { found = content; } });
    });
    return found;
  }

  // ---------------------------------------------------------------- 고르기

  function choose(content, keepValues) {
    state.content = content;
    var mode = null;
    if (keepValues && state.mode) {
      content.modes.forEach(function (m) { if (m.id === state.mode.id) { mode = m; } });
    }
    setMode(mode || content.modes[0], keepValues);
  }

  function setMode(mode, keepValues) {
    var old = keepValues ? state.values : {};
    state.mode = mode;
    state.values = {};
    mode.fields.forEach(function (field) {
      if (old[field.id] !== undefined) { state.values[field.id] = old[field.id]; return; }
      if (field.type === 'choice' || field.type === 'number') { state.values[field.id] = field.default; }
      else if (field.type === 'pick') { state.values[field.id] = []; }
      else { state.values[field.id] = ''; }
    });
    if (!keepValues) { state.sheets = 1; state.same = false; }
    state.notice = '';
    state.noticeField = null;
  }

  function selectTab(index) {
    state.tab = index;
    var items = state.tabs[index].items;
    if (state.phase === 'form') {
      if (items.length === 1) { choose(items[0], false); } else { state.content = null; state.mode = null; }
      state.notice = '';
    }
    renderAll();
  }

  function goHome() {
    state.tab = 0;
    state.content = null;
    state.mode = null;
    state.values = {};
    state.sheets = 1;
    state.same = false;
    state.notice = '';
    state.noticeField = null;
    state.phase = 'form';
    if (!jobActive()) { state.job = null; state.jobContent = null; }
    closeOverlay();
    if (document.activeElement && document.activeElement.blur) { document.activeElement.blur(); }
    renderAll();
  }

  // ---------------------------------------------------------------- 그리기: 머리띠, 탭, 판

  function renderAll() { renderBar(); renderTabs(); renderGrid(); renderPanel(); renderStrip(); }

  function renderBar() {
    var staff = isStaff();
    dom.queueButton.hidden = !staff;
    dom.logoutButton.hidden = !staff;
    dom.staffBadge.hidden = !staff;
    dom.status.className = 'pill' + (state.offline ? ' pill--trouble' : '');
    if (state.offline) { dom.status.textContent = '연결 끊김'; }
    else if (!state.catalog) { dom.status.textContent = '불러오는 중'; }
    else if (jobActive()) { dom.status.textContent = state.job.state === 'queued' ? '기다리는 중' : '뜯는 중'; }
    else { dom.status.textContent = '준비됐어요'; }
  }

  function renderTabs() {
    var scrolled = dom.tabs.scrollLeft;   // 다시 그려도 좌우로 민 자리를 지킨다
    clear(dom.tabs);
    state.tabs.forEach(function (tab, index) {
      var node = button('tab', tab.title, function () { selectTab(index); });
      node.setAttribute('role', 'tab');
      node.setAttribute('aria-selected', index === state.tab ? 'true' : 'false');
      if (tab.items.length > 1) { node.appendChild(el('span', 'tab__count', String(tab.items.length))); }
      dom.tabs.appendChild(node);
    });
    dom.tabs.scrollLeft = scrolled;
  }

  function renderGrid() {
    clear(dom.grid);
    var tab = state.tabs[state.tab];
    if (!tab) { return; }
    var cells = tab.items.map(function (content) {
      var node = button('tile', null, function () {
        if (state.phase !== 'form') { return; }
        choose(content, false);
        renderGrid();
        renderPanel();
      });
      node.appendChild(el('span', 'tile__no', String(state.numbers[content.name])));
      node.appendChild(el('span', 'tile__title', content.title));
      node.setAttribute('aria-pressed', state.content && state.content.name === content.name ? 'true' : 'false');
      if (state.jobContent === content.name && (jobActive() || state.phase === 'done')) {
        node.className += ' tile--torn';
        if (state.job && state.tornJob !== state.job.id) { node.className += ' tile--tearing'; state.tornJob = state.job.id; }
      }
      return node;
    });
    cells.forEach(function (node) { dom.grid.appendChild(node); });
    // 열 수는 CSS(--tile-min)와 판 너비가 정한다. 실제로 몇 열이 됐는지 읽어서 테두리를 맞춘다.
    var columns = gridColumns();
    state.gridColumns = columns;
    while (cells.length % columns !== 0) {   // 마지막 줄의 빈자리도 판의 칸으로 채운다
      var filler = el('div', 'grid__filler');
      filler.setAttribute('aria-hidden', 'true');
      cells.push(filler);
      dom.grid.appendChild(filler);
    }
    cells.forEach(function (node, index) {
      if (index % columns === columns - 1) { node.className += ' is-row-end'; }
      if (index >= cells.length - columns) { node.className += ' is-last-row'; }
    });
  }

  function gridColumns() {
    var tracks = window.getComputedStyle(dom.grid).gridTemplateColumns;
    var count = tracks && tracks !== 'none' ? tracks.split(/\s+/).length : 0;
    return count > 0 ? count : 3;
  }

  // 화면을 돌리거나 창 크기가 바뀌어 열 수가 달라지면 판을 다시 그린다
  var resizeTimer = null;
  window.addEventListener('resize', function () {
    clearTimeout(resizeTimer);
    resizeTimer = setTimeout(function () {
      if (state.catalog && gridColumns() !== state.gridColumns) { renderGrid(); }
    }, 150);
  });

  // ---------------------------------------------------------------- 그리기: 오른쪽 패널

  var panelKey = '';   // 지금 패널이 무엇을 보여주는지. 같은 것을 다시 그릴 때는 스크롤 자리를 지킨다

  function renderPanel() {
    var oldBody = dom.panel.querySelector('.panel__body');
    var scrolled = oldBody ? oldBody.scrollTop : 0;
    clear(dom.panel);
    fillPanel();
    // 그려진 것을 세 층으로 나눈다: 첫 번째(제목)는 머리, panel__push 는 맨 아래 고정, 나머지는 스크롤되는 내용
    var head = el('div', 'panel__head');
    var body = el('div', 'panel__body');
    var foot = null;
    Array.prototype.slice.call(dom.panel.childNodes).forEach(function (node, index) {
      if (index === 0) { head.appendChild(node); }
      else if (node.className && String(node.className).indexOf('panel__push') !== -1) { foot = node; }
      else { body.appendChild(node); }
    });
    dom.panel.appendChild(head);
    dom.panel.appendChild(body);
    if (foot) { dom.panel.appendChild(foot); }
    var key = state.phase + '/' + (state.content ? state.content.name : '') + '/' + (state.mode ? state.mode.id : '');
    if (key === panelKey) { body.scrollTop = scrolled; }
    panelKey = key;
    refreshGo();
  }

  function fillPanel() {
    if (state.phase === 'printing' || state.phase === 'sending') { return renderProgress(); }
    if (state.phase === 'done') { return renderDone(); }
    if (state.phase === 'failed') { return renderFailed(); }
    if (!state.content) { return renderEmpty(); }
    renderForm();
  }

  function renderEmpty() {
    dom.panel.appendChild(el('h2', 'panel__title', state.catalog ? '칸을 하나 골라 보세요' : '불러오는 중이에요'));
    if (!state.catalog) { return; }
    var steps = el('ol', 'steps');
    ['왼쪽 판에서 뽑고 싶은 칸을 눌러요.', '난이도나 장 수를 정해요.', '뽑기를 누르면 프린터에서 종이가 나와요.']
      .forEach(function (text) { steps.appendChild(el('li', null, text)); });
    dom.panel.appendChild(steps);
    var bottom = el('div', 'panel__push');
    var go = button('go', '뽑기!', function () {});
    go.disabled = true;
    bottom.appendChild(go);
    dom.panel.appendChild(bottom);
  }

  function renderForm() {
    var content = state.content;
    var mode = state.mode;
    dom.panel.appendChild(el('h2', 'panel__title', state.numbers[content.name] + '번 ' + content.title));

    if (content.modes.length > 1) {
      var modes = el('div', 'segments');
      modes.setAttribute('role', 'group');
      modes.setAttribute('aria-label', '무엇을 뽑을까요');
      content.modes.forEach(function (m) {
        var node = button('segment', m.label, function () { setMode(m, false); renderPanel(); });
        node.setAttribute('aria-pressed', m.id === mode.id ? 'true' : 'false');
        modes.appendChild(node);
      });
      dom.panel.appendChild(modes);
    }

    mode.fields.forEach(function (field) { dom.panel.appendChild(renderField(field)); });
    if (mode.sheets) { dom.panel.appendChild(renderSheets()); }
    if (mode.sheets && mode.same_sheets) { dom.panel.appendChild(renderSame()); }

    var bottom = el('div', 'panel__push');
    if (state.notice && !noticeShownAtField()) {
      var notice = el('p', 'notice', state.notice);
      notice.setAttribute('role', 'alert');
      bottom.appendChild(notice);
    }
    var why = el('p', 'why', '');
    why.id = 'why';
    bottom.appendChild(why);
    var go = button('go', '뽑기!', submit);
    go.id = 'go';
    bottom.appendChild(go);
    dom.panel.appendChild(bottom);
    refreshGo();
  }

  function noticeShownAtField() {
    if (!state.noticeField || !state.mode) { return false; }
    return state.mode.fields.some(function (field) { return field.id === state.noticeField; });
  }

  function labelFor(field, note) {
    var label = el('span', 'field__label', field.label);
    if (note) { label.appendChild(el('span', 'field__note', note)); }
    return label;
  }

  function refreshGo() {
    var go = $('go');
    var why = $('why');
    var reason = missing();
    if (go) { go.disabled = state.phase !== 'form' || state.offline || !!reason; }
    if (why) { why.textContent = reason; why.hidden = !reason; }
  }

  /* "쉬움 4x4", "한글 (자음·모음)" 같은 표시는 이름과 덧붙임을 두 줄로 나눠, 한 줄에 놓인 버튼들의 모양을 맞춘다. */
  function fillChoice(node, label) {
    var parts = /^(.+?)\s+(\(.+\)|\d+\s*x\s*\d+)$/.exec(label);
    if (!parts) { node.textContent = label; return; }
    node.appendChild(el('span', 'choice__main', parts[1]));
    node.appendChild(el('span', 'choice__sub', parts[2].replace(/^\(|\)$/g, '')));
  }

  function renderField(field) {
    var box = el('div', 'field');
    var wrong = state.notice && state.noticeField === field.id;
    if (field.type === 'choice') {
      box.appendChild(labelFor(field));
      var count = field.choices.length;
      var row = el('div', 'choices' + (count === 2 || count === 4 ? ' choices--' + count : count === 5 ? ' choices--5' : ''));
      field.choices.forEach(function (choice) {
        var node = button('choice' + (count > 4 ? ' choice--small' : ''), null, function () {
          state.values[field.id] = choice[1];
          renderPanel();
        });
        fillChoice(node, choice[0]);
        node.setAttribute('aria-pressed', state.values[field.id] === choice[1] ? 'true' : 'false');
        row.appendChild(node);
      });
      box.appendChild(row);
    } else if (field.type === 'number') {
      var top = maxOf(field);
      if (state.values[field.id] !== null && state.values[field.id] > top) { state.values[field.id] = top; }
      box.appendChild(labelFor(field, field.min + '~' + top));
      box.appendChild(renderStepper(field.min, top, state.values[field.id], field.default === null, field.label,
        function (value) {
          var changed = state.values[field.id] !== value;
          state.values[field.id] = value;
          if (changed && hasDependents(field)) { renderPanel(); }
        }));
    } else if (field.type === 'pick') {
      var chosen = state.values[field.id];
      box.appendChild(labelFor(field, chosen.length + '명 고름 · ' + field.min + '~' + field.max + '명'));
      var chips = el('div', 'choices choices--4');
      field.options.forEach(function (name) {
        var on = chosen.indexOf(name) !== -1;
        var node = button('choice choice--small', name, function () {
          var at = chosen.indexOf(name);
          if (at !== -1) { chosen.splice(at, 1); }
          else if (chosen.length < field.max) { chosen.push(name); }
          renderPanel();
        });
        node.setAttribute('aria-pressed', on ? 'true' : 'false');
        chips.appendChild(node);
      });
      box.appendChild(chips);
    } else {   // text, names
      var note = field.type === 'names' ? field.min + '~' + field.max + '명, 쉼표로 구분' : field.required ? '' : '비워 둬도 돼요';
      box.appendChild(labelFor(field, note));
      var input = el('input', 'textbox');
      input.type = 'text';
      input.value = state.values[field.id] || '';
      input.maxLength = field.type === 'names' ? 120 : field.max_length;
      input.placeholder = field.example ? '예: ' + field.example : '';
      input.setAttribute('aria-label', field.label);
      input.setAttribute('autocomplete', 'off');
      input.setAttribute('autocorrect', 'off');
      input.setAttribute('autocapitalize', 'off');
      input.setAttribute('spellcheck', 'false');
      input.setAttribute('enterkeyhint', 'done');
      if (wrong) { input.className += ' textbox--wrong'; input.setAttribute('aria-invalid', 'true'); }
      input.addEventListener('input', function () { state.values[field.id] = input.value; refreshGo(); });
      if (hasDependents(field)) { input.addEventListener('change', function () { renderPanel(); }); }
      input.addEventListener('keydown', function (event) { if (event.key === 'Enter') { input.blur(); } });
      box.appendChild(input);
    }
    if (wrong) {
      var notice = el('p', 'notice notice--field', state.notice);
      notice.setAttribute('role', 'alert');
      box.appendChild(notice);
    }
    return box;
  }

  /* 숫자 항목의 실제 최댓값. below 가 있으면 그 항목(고른 이름 수·숫자)보다 작아야 한다 (당첨 < 참가자). */
  function maxOf(field) {
    if (!field.below) { return field.max; }
    var count = 0;
    state.mode.fields.forEach(function (other) {
      if (other.id !== field.below) { return; }
      var value = state.values[other.id];
      if (other.type === 'pick') { count = value.length; }
      else if (other.type === 'names') { count = splitNames(value).length; }
      else { count = value || 0; }
    });
    return count ? Math.max(field.min, Math.min(field.max, count - 1)) : field.max;
  }

  function hasDependents(field) {
    return state.mode.fields.some(function (other) { return other.below === field.id; });
  }

  /* 빼기 / 값 / 더하기. optional이면 비울 수 있고, 비우면 '자동'이다. onChange(값 또는 null) */
  function renderStepper(min, max, value, optional, label, onChange) {
    var row = el('div', 'stepper');
    var input = el('input', 'stepper__value');
    input.type = 'text';
    input.setAttribute('inputmode', 'numeric');
    input.setAttribute('pattern', '[0-9]*');
    input.setAttribute('aria-label', label);
    input.setAttribute('autocomplete', 'off');
    input.placeholder = optional ? '자동' : '';

    function show(next) {
      value = next;
      input.value = value === null ? '' : String(value);
      minus.disabled = value === null || (!optional && value <= min);
      plus.disabled = value !== null && value >= max;
      onChange(value);
    }
    var minus = button('stepper__button', null, function () {
      if (value === null) { return; }
      show(value <= min ? (optional ? null : min) : value - 1);
    });
    var plus = button('stepper__button', null, function () { show(value === null ? min : Math.min(max, value + 1)); });
    minus.setAttribute('aria-label', label + ' 줄이기');
    plus.setAttribute('aria-label', label + ' 늘리기');
    minus.appendChild(icon(ICON.minus));
    plus.appendChild(icon(ICON.plus));
    input.addEventListener('change', function () {
      var typed = parseInt(input.value, 10);
      if (isNaN(typed)) { show(optional ? null : value === null ? min : value); return; }
      show(Math.max(min, Math.min(max, typed)));
    });
    input.addEventListener('keydown', function (event) { if (event.key === 'Enter') { input.blur(); } });
    row.appendChild(minus);
    row.appendChild(input);
    row.appendChild(plus);
    show(value === undefined ? null : value);
    return row;
  }

  function renderSheets() {
    var box = el('div', 'field');
    var max = state.catalog.max_sheets;
    var label = el('span', 'field__label', '몇 장?');
    box.appendChild(label);
    if (max <= 5) {
      var row = el('div', 'choices choices--' + max);
      for (var n = 1; n <= max; n += 1) {
        (function (count) {
          var node = button('choice', String(count), function () { state.sheets = count; renderPanel(); });
          node.setAttribute('aria-pressed', state.sheets === count ? 'true' : 'false');
          row.appendChild(node);
        })(n);
      }
      box.appendChild(row);
    } else {
      label.appendChild(el('span', 'field__note', '1~' + max));
      box.appendChild(renderStepper(1, max, state.sheets, false, '장 수', function (value) { state.sheets = value; }));
    }
    return box;
  }

  /* 여러 장을 뽑을 때 장마다 다른 문제로 할지, 모두 같은 문제로 할지 (여럿이 같은 문제로 겨룰 때).
     한 장만 뽑으면 어느 쪽이든 같다. */
  function renderSame() {
    var box = el('div', 'field');
    var label = el('span', 'field__label', '문제');
    label.appendChild(el('span', 'field__note', '여러 장일 때'));
    box.appendChild(label);
    var row = el('div', 'choices choices--2');
    [['장마다 다르게', false], ['모두 같게', true]].forEach(function (option) {
      var node = button('choice', option[0], function () { state.same = option[1]; renderPanel(); });
      node.setAttribute('aria-pressed', state.same === option[1] ? 'true' : 'false');
      row.appendChild(node);
    });
    box.appendChild(row);
    return box;
  }

  /* 아직 뽑을 수 없는 이유를 한 문장으로. 뽑을 수 있으면 ''.
     꼭 넣어야 하는 칸이 비었는지만 본다. 나머지 검사는 서버가 한다. */
  function missing() {
    if (!state.mode) { return ''; }
    var reason = '';
    state.mode.fields.forEach(function (field) {
      if (reason) { return; }
      var value = state.values[field.id];
      if (field.type === 'pick' && value.length < field.min) { reason = field.label + ' ' + field.min + '명 이상 골라 주세요.'; }
      else if (field.type === 'names' && splitNames(value).length < field.min) { reason = field.label + ' ' + field.min + '명 이상 적어 주세요.'; }
      else if (field.type === 'text' && field.required && String(value || '').trim() === '') {
        reason = "'" + field.label + "' 칸을 채우면 뽑을 수 있어요.";
      }
    });
    return reason;
  }

  function ready() {
    return state.phase === 'form' && !!state.mode && !state.offline && !missing();
  }

  function splitNames(text) {
    return String(text || '').split(',').map(function (s) { return s.trim(); }).filter(function (s) { return s; });
  }

  // ---------------------------------------------------------------- 그리기: 뽑는 중, 끝, 실패

  function sheetRow(job) {
    var row = el('div', 'sheets' + (job.sheets > 8 ? ' sheets--many' : ''));
    for (var n = 1; n <= job.sheets; n += 1) {
      var done = n <= job.done;
      var now = !done && job.state === 'running' && (job.same || n === job.done + 1);   // 같은 문제는 한꺼번에
      var sheet = el('div', 'sheet' + (done ? ' sheet--done' : now ? ' sheet--now' : ''));
      if (done) { sheet.appendChild(icon(ICON.check)); } else { sheet.textContent = String(n); }
      row.appendChild(sheet);
    }
    return row;
  }

  function progressText(job) {
    if (!job) { return '키오스크에 보내는 중이에요'; }
    if (job.state === 'queued') { return '순서를 기다리는 중이에요'; }
    if (job.sheets === 1) { return '종이가 나오고 있어요'; }
    if (job.same) { return '같은 문제 ' + job.sheets + '장을 뽑는 중이에요'; }   // 한 번에 다 뽑아서 몇 장째인지는 모른다
    return job.sheets + '장 중 ' + Math.min(job.sheets, job.done + 1) + '장째';
  }

  function renderProgress() {
    var job = state.job;
    var waiting = !job || job.state === 'queued';
    dom.panel.appendChild(el('h2', 'big', waiting ? '잠깐만요' : '뜯는 중!'));
    dom.panel.appendChild(el('p', 'panel__lead', (job ? job.title + ' · ' : '') + progressText(job)));
    if (job) { dom.panel.appendChild(sheetRow(job)); }
    dom.panel.appendChild(el('p', 'panel__lead', '판을 만드는 데 시간이 조금 걸릴 수 있어요.'));
    if (isStaff() && job) {
      var bottom = el('div', 'panel__push');
      bottom.appendChild(button('plain', '기다리지 않고 다른 것 고르기', function () {
        state.phase = 'form';
        state.notice = '';
        renderAll();
      }));
      dom.panel.appendChild(bottom);
    }
  }

  function renderDone() {
    var job = state.job;
    dom.panel.appendChild(el('h2', 'big', '다 나왔어요!'));
    dom.panel.appendChild(el('p', 'panel__lead', '프린터에서 종이를 가져가세요.'));
    if (job) { dom.panel.appendChild(sheetRow(job)); }
    var bottom = el('div', 'panel__push');
    bottom.appendChild(button('plain', '처음으로', goHome));
    dom.panel.appendChild(bottom);
  }

  function renderFailed() {
    var job = state.job;
    var cancelled = job && job.state === 'cancelled';
    dom.panel.appendChild(el('h2', 'big', cancelled ? '취소됐어요' : '뽑지 못했어요'));
    var why = el('p', 'notice', cancelled ? '관리자가 인쇄를 멈췄어요.' : (job && job.message) || '인쇄하지 못했습니다.');
    why.setAttribute('role', 'alert');
    dom.panel.appendChild(why);
    if (job && job.done > 0) {
      dom.panel.appendChild(el('p', 'panel__lead', job.sheets + '장 중 ' + job.done + '장은 나왔어요.'));
    }
    var bottom = el('div', 'panel__push');
    if (state.content && !cancelled) {
      bottom.appendChild(button('plain', '고쳐서 다시 해 보기', function () {
        state.phase = 'form';
        state.notice = '';
        renderAll();
      }));
    }
    bottom.appendChild(button('plain', '처음으로', goHome));
    dom.panel.appendChild(bottom);
  }

  // ---------------------------------------------------------------- 그리기: 아래 띠

  function jobActive() {
    return !!state.job && (state.job.state === 'queued' || state.job.state === 'running');
  }

  function renderStrip() {
    clear(dom.strip);
    var tag = '';
    var text = state.catalog ? '한 번에 ' + state.catalog.max_sheets + '장까지 뽑을 수 있어요.' : '';
    if (state.offline) {
      tag = '연결 끊김';
      text = '키오스크에 연결할 수 없어요. 다시 연결하는 중이에요.';
    } else if (jobActive()) {
      var number = state.numbers[state.jobContent];
      tag = state.job.state === 'queued' ? '기다리는 중' : '뜯는 중';
      text = (number ? number + '번 ' : '') + state.job.title + ' · ' + progressText(state.job);
    } else if (state.job && state.job.state === 'failed' && state.phase === 'form') {
      tag = '뽑지 못함';      // 관리자가 기다리지 않고 넘어간 작업이 실패했을 때
      text = state.job.title + ' · ' + (state.job.message || '인쇄하지 못했습니다.');
    }
    if (tag) { dom.strip.appendChild(el('span', 'strip__tag', tag)); }
    dom.strip.appendChild(el('span', 'strip__text', text));
  }

  // ---------------------------------------------------------------- 뽑기

  function collectValues() {
    var values = {};
    state.mode.fields.forEach(function (field) {
      var value = state.values[field.id];
      if (field.type === 'names') { values[field.id] = splitNames(value); }
      else if (field.type === 'pick') { values[field.id] = value.slice(); }
      else if (field.type === 'number') { if (value !== null && value !== undefined) { values[field.id] = value; } }
      else if (field.type === 'text') { if (String(value || '').trim() !== '') { values[field.id] = String(value).trim(); } }
      else { values[field.id] = value; }
    });
    return values;
  }

  function submit() {
    if (!ready()) { return; }                 // 연달아 눌러도 한 번만 보낸다
    var contentName = state.content.name;
    state.phase = 'sending';
    state.notice = '';
    state.noticeField = null;
    if (!jobActive()) { state.job = null; }
    renderAll();
    api('POST', '/api/print', {
      content: contentName, mode: state.mode.id, values: collectValues(), sheets: state.mode.sheets ? state.sheets : 1,
      same: !!(state.mode.sheets && state.mode.same_sheets && state.same && state.sheets > 1)
    }).then(function (result) {
      if (result.status === 202) {
        state.job = result.data;
        state.jobContent = contentName;
        state.phase = 'printing';
        renderAll();
        schedulePoll();
        return;
      }
      state.phase = 'form';
      state.notice = result.data.error || '뽑지 못했어요. 다시 눌러 주세요.';
      state.noticeField = result.data.field || null;
      renderAll();
      if (isStaff()) { refreshRole(); }   // 관리자 시간이 끝나 거절됐을 수 있다
    }).catch(function () {
      state.phase = 'form';
      state.notice = '키오스크에 연결할 수 없어요. 잠시 뒤에 다시 눌러 주세요.';
      renderAll();
    });
  }

  var pollTimer = null;
  function schedulePoll() {
    clearTimeout(pollTimer);
    pollTimer = setTimeout(poll, POLL);
  }

  function poll() {
    if (!state.job) { return; }
    var watching = state.job.id;
    api('GET', '/api/jobs/' + watching).then(function (result) {
      if (!state.job || state.job.id !== watching) { return; }
      state.offline = false;
      if (result.status !== 200) {             // 서버가 다시 시작돼 작업이 사라졌다
        state.job = { id: watching, title: state.job.title, sheets: state.job.sheets, done: state.job.done,
                      state: 'failed', message: '인쇄가 중간에 끊겼어요. 다시 뽑아 주세요.' };
      } else {
        state.job = result.data;
      }
      if (jobActive()) { renderAll(); schedulePoll(); return; }
      finishJob();
    }).catch(function () {
      state.offline = true;
      renderBar();
      renderStrip();
      schedulePoll();
    });
  }

  var homeTimer = null;
  function refreshRole() {
    api('GET', '/api/catalog').then(function (result) {
      if (result.status === 200 && result.data.role !== state.catalog.role) { setCatalog(result.data); }
    }).catch(function () {});
  }

  function finishJob() {
    state.lastTouch = Date.now();
    var watchingPanel = state.phase === 'printing' || state.phase === 'sending';
    if (watchingPanel) { state.phase = state.job.state === 'done' ? 'done' : 'failed'; }
    renderAll();
    clearTimeout(homeTimer);
    if (state.phase === 'done') {
      homeTimer = setTimeout(function () { if (state.phase === 'done') { goHome(); } }, DONE_STAY);
    }
  }

  // ---------------------------------------------------------------- 덮개: 관리자 비밀번호, 대기열

  var overlayTimer = null;
  function closeOverlay() {
    clearInterval(overlayTimer);
    overlayTimer = null;
    dom.overlay.hidden = true;
    clear(dom.overlay);
  }

  function openOverlay(box) {
    closeOverlay();
    box.setAttribute('role', 'dialog');
    box.setAttribute('aria-modal', 'true');
    dom.overlay.appendChild(box);
    dom.overlay.hidden = false;
  }

  function openPin() {
    var pin = '';
    var box = el('div', 'sheetbox');
    box.appendChild(el('h2', 'sheetbox__title', '관리자 비밀번호'));
    var dots = el('div', 'dots');
    var message = el('p', 'field__hint', '숫자를 누르고 확인을 눌러요.');
    message.setAttribute('aria-live', 'polite');
    box.appendChild(dots);
    box.appendChild(message);

    function drawDots() {
      clear(dots);
      for (var i = 0; i < Math.max(4, pin.length); i += 1) {
        dots.appendChild(el('span', 'dot' + (i < pin.length ? ' dot--on' : '')));
      }
    }
    function send() {
      if (!pin) { return; }
      api('POST', '/api/admin/login', { pin: pin }).then(function (result) {
        if (result.status === 200) { closeOverlay(); loadCatalog(); return; }
        pin = '';
        drawDots();
        message.className = 'notice';
        message.setAttribute('role', 'alert');
        message.textContent = result.data.error || '들어가지 못했어요.';
      }).catch(function () { message.className = 'notice'; message.textContent = '키오스크에 연결할 수 없어요.'; });
    }

    var keys = el('div', 'keys');
    ['1', '2', '3', '4', '5', '6', '7', '8', '9'].forEach(function (digit) {
      keys.appendChild(button('key', digit, function () { if (pin.length < 8) { pin += digit; drawDots(); } }));
    });
    keys.appendChild(button('key key--word', '지우기', function () { pin = pin.slice(0, -1); drawDots(); }));
    keys.appendChild(button('key', '0', function () { if (pin.length < 8) { pin += '0'; drawDots(); } }));
    keys.appendChild(button('key key--word key--primary', '확인', send));
    box.appendChild(keys);
    box.appendChild(button('plain', '닫기', closeOverlay));
    drawDots();
    openOverlay(box);
  }

  var STATE_WORD = { queued: '기다리는 중', running: '뜯는 중', done: '끝', failed: '실패', cancelled: '취소됨' };

  function openQueue() {
    var box = el('div', 'sheetbox sheetbox--wide');
    box.appendChild(el('h2', 'sheetbox__title', '인쇄 대기열'));
    var list = el('ul', 'jobs');
    var empty = el('p', 'panel__lead', '');
    box.appendChild(list);
    box.appendChild(empty);
    var dropped = (state.catalog.errors || []);
    if (dropped.length) {
      box.appendChild(el('h3', 'field__label', '설정 오류로 빠진 콘텐츠'));
      var problems = el('ul', 'jobs');
      dropped.forEach(function (text) {
        var row = el('li');
        row.appendChild(el('span', 'jobs__what', text));
        problems.appendChild(row);
      });
      box.appendChild(problems);
    }
    var buttons = el('div', 'buttons');
    var cancel = button('plain plain--danger', '남은 인쇄 모두 취소', function () {
      api('POST', '/api/admin/cancel').then(refresh).catch(refresh);
    });
    cancel.disabled = true;
    buttons.appendChild(cancel);
    buttons.appendChild(button('plain', '관리 페이지', function () { window.location.href = '/admin'; }));
    buttons.appendChild(button('plain', '닫기', closeOverlay));
    box.appendChild(buttons);

    function refresh() {
      return api('GET', '/api/admin/jobs').then(function (result) {
        if (result.status !== 200) { closeOverlay(); loadCatalog(); return; }
        var jobs = result.data.filter(function (job) { return job.state === 'queued' || job.state === 'running'; });
        var recent = result.data.filter(function (job) { return job.state === 'failed' || job.state === 'cancelled'; }).slice(-3);
        clear(list);
        jobs.concat(recent).forEach(function (job) {
          var row = el('li');
          row.appendChild(el('span', 'jobs__state', STATE_WORD[job.state] || job.state));
          row.appendChild(el('span', 'jobs__what', job.title + (job.message ? ' · ' + job.message : '')));
          row.appendChild(el('span', 'jobs__count', job.done + ' / ' + job.sheets + '장'));
          list.appendChild(row);
        });
        list.hidden = jobs.length + recent.length === 0;
        empty.textContent = jobs.length === 0 ? '지금 기다리는 인쇄가 없어요.' : '';
        empty.hidden = jobs.length !== 0;
        cancel.disabled = jobs.length === 0;
      }).catch(function () { empty.hidden = false; empty.textContent = '키오스크에 연결할 수 없어요.'; });
    }
    openOverlay(box);
    refresh();
    overlayTimer = setInterval(refresh, 2000);
  }

  function logout() {
    api('POST', '/api/admin/logout').then(function () { closeOverlay(); goHome(); loadCatalog(); })
      .catch(function () { loadCatalog(); });
  }

  // 제목을 길게 누르면 관리자 비밀번호 입력
  var pressTimer = null;
  function pressStart() {
    clearTimeout(pressTimer);
    if (!state.catalog || !state.catalog.admin_enabled || isStaff()) { return; }
    pressTimer = setTimeout(openPin, LONG_PRESS);
  }
  function pressEnd() { clearTimeout(pressTimer); }
  ['touchstart', 'mousedown'].forEach(function (type) { dom.name.addEventListener(type, pressStart); });
  ['touchend', 'touchcancel', 'touchmove', 'mouseup', 'mouseleave'].forEach(function (type) {
    dom.name.addEventListener(type, pressEnd);
  });

  // 묶음 탭 줄: 손가락으로는 그냥 밀리지만 마우스로는 밀리지 않으므로, 끌기와 휠을 직접 처리한다 (PC에서 볼 때)
  var drag = null;
  dom.tabs.addEventListener('mousedown', function (event) {
    if (event.button !== 0) { return; }
    drag = { x: event.clientX, left: dom.tabs.scrollLeft, moved: false };
  });
  window.addEventListener('mousemove', function (event) {
    if (!drag) { return; }
    var dx = event.clientX - drag.x;
    if (Math.abs(dx) > 5) { drag.moved = true; }
    if (drag.moved) { dom.tabs.scrollLeft = drag.left - dx; }
  });
  window.addEventListener('mouseup', function () {
    if (!drag) { return; }
    var moved = drag.moved;
    drag = null;
    if (moved) {   // 끌다가 놓은 것은 탭을 누른 것으로 치지 않는다
      var swallow = function (event) { event.stopPropagation(); event.preventDefault(); };
      dom.tabs.addEventListener('click', swallow, true);
      setTimeout(function () { dom.tabs.removeEventListener('click', swallow, true); }, 0);
    }
  });
  dom.tabs.addEventListener('wheel', function (event) {
    if (dom.tabs.scrollWidth <= dom.tabs.clientWidth) { return; }
    dom.tabs.scrollLeft += event.deltaY || event.deltaX;
    event.preventDefault();
  });

  dom.queueButton.addEventListener('click', openQueue);
  dom.logoutButton.addEventListener('click', logout);
  dom.overlay.addEventListener('click', function (event) { if (event.target === dom.overlay) { closeOverlay(); } });
  document.addEventListener('contextmenu', function (event) { event.preventDefault(); });

  // ---------------------------------------------------------------- 아무도 안 쓰면 처음으로

  ['touchstart', 'mousedown', 'keydown'].forEach(function (type) {
    document.addEventListener(type, function () { state.lastTouch = Date.now(); }, true);
  });

  function atHome() {
    return state.tab === 0 && !state.content && state.phase === 'form' && dom.overlay.hidden && !state.notice;
  }

  setInterval(function () {
    if (!state.catalog) { return; }
    var quiet = Date.now() - state.lastTouch;
    if (isStaff()) {
      if (quiet > IDLE_STAFF) { state.lastTouch = Date.now(); logout(); }
      return;
    }
    if (state.phase === 'sending' || state.phase === 'printing') { return; }
    if (quiet > IDLE_VISITOR && !atHome()) { goHome(); refreshCatalog(); }
  }, 1000);

  setInterval(function () {
    if (state.catalog && atHome() && !jobActive()) { refreshCatalog(); }
    else if (state.offline) { refreshCatalog(); }
  }, 60 * 1000);

  /* 홈 화면에 추가한 아이패드(전체 화면)에서는 브라우저가 화면 높이를 실제보다 짧게 알려줘서
     아래에 틈이 남는다. 이때는 기기 화면 크기를 직접 읽어 틀의 높이를 맞춘다.
     보통 브라우저 탭에서는 아무것도 하지 않는다. */
  function fitFullScreen() {
    if (window.navigator.standalone !== true) { return; }
    var app = document.querySelector('.app');
    var screenSize = window.screen;
    var landscape = window.innerWidth > window.innerHeight;
    var height = landscape ? Math.min(screenSize.width, screenSize.height) : Math.max(screenSize.width, screenSize.height);
    if (!height || height < window.innerHeight) { return; }   // 값이 이상하면 CSS에 맡긴다
    app.style.bottom = 'auto';
    app.style.height = height + 'px';
  }
  fitFullScreen();
  window.addEventListener('resize', fitFullScreen);
  window.addEventListener('orientationchange', function () { setTimeout(fitFullScreen, 300); });

  renderAll();
  loadCatalog();
})();
