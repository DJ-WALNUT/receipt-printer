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
    phase: 'form',       // form | sending | printing | done | failed
    notice: '',          // 옵션 화면에 보일 오류
    job: null,           // 지금 따라가고 있는 인쇄 작업
    jobContent: null,    // 그 작업의 콘텐츠 이름 (뜯긴 칸 표시용)
    offline: false,
    lastTouch: Date.now()
  };

  var $ = function (id) { return document.getElementById(id); };
  var dom = {
    name: $('name'), status: $('status'), tabs: $('tabs'), grid: $('grid'), panel: $('panel'),
    strip: $('strip'), overlay: $('overlay'), queueButton: $('queueButton'), logoutButton: $('logoutButton')
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
    return fetch(url, options).then(function (response) {
      return response.json().catch(function () { return {}; }).then(function (data) {
        return { status: response.status, data: data };
      });
    });
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

  function setCatalog(catalog) {
    state.catalog = catalog;
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
    if (!keepValues) { state.sheets = 1; }
    state.notice = '';
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
    state.notice = '';
    state.phase = 'form';
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
    dom.status.className = 'pill' + (state.offline ? ' pill--trouble' : staff ? ' pill--staff' : '');
    if (state.offline) { dom.status.textContent = '연결 끊김'; }
    else if (!state.catalog) { dom.status.textContent = '불러오는 중'; }
    else if (staff) { dom.status.textContent = '관리자'; }
    else if (jobActive()) { dom.status.textContent = '뽑는 중'; }
    else { dom.status.textContent = '준비됐어요'; }
  }

  function renderTabs() {
    clear(dom.tabs);
    state.tabs.forEach(function (tab, index) {
      var node = button('tab', tab.title, function () { selectTab(index); });
      node.setAttribute('role', 'tab');
      node.setAttribute('aria-selected', index === state.tab ? 'true' : 'false');
      if (tab.items.length > 1) { node.appendChild(el('span', 'tab__count', String(tab.items.length))); }
      dom.tabs.appendChild(node);
    });
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
      if (jobActive() && state.jobContent === content.name) { node.className += ' tile--torn'; }
      return node;
    });
    while (cells.length % 3 !== 0) {        // 마지막 줄의 빈자리도 판의 칸으로 채운다
      var filler = el('div', 'grid__filler');
      filler.setAttribute('aria-hidden', 'true');
      cells.push(filler);
    }
    cells.forEach(function (node, index) {
      if (index >= cells.length - 3) { node.className += ' is-last-row'; }
      dom.grid.appendChild(node);
    });
  }

  // ---------------------------------------------------------------- 그리기: 오른쪽 패널

  function renderPanel() {
    clear(dom.panel);
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
  }

  function renderForm() {
    var content = state.content;
    var mode = state.mode;
    dom.panel.appendChild(el('h2', 'panel__title', state.numbers[content.name] + '번 ' + content.title));

    if (content.modes.length > 1) {
      var modes = el('div', 'choices choices--2');
      content.modes.forEach(function (m) {
        var node = button('choice choice--small', m.label, function () { setMode(m, false); renderPanel(); });
        node.setAttribute('aria-pressed', m.id === mode.id ? 'true' : 'false');
        modes.appendChild(node);
      });
      dom.panel.appendChild(modes);
    }

    mode.fields.forEach(function (field) { dom.panel.appendChild(renderField(field)); });
    if (mode.sheets) { dom.panel.appendChild(renderSheets()); }

    var bottom = el('div', 'panel__push');
    if (state.notice) {
      var notice = el('p', 'notice', state.notice);
      notice.setAttribute('role', 'alert');
      bottom.appendChild(notice);
    }
    var go = button('go', '뽑기!', submit);
    go.id = 'go';
    go.disabled = !ready();
    bottom.appendChild(go);
    dom.panel.appendChild(bottom);
  }

  function labelFor(field, note) {
    var label = el('span', 'field__label', field.label);
    if (note) { label.appendChild(el('span', 'field__note', note)); }
    return label;
  }

  function refreshGo() {
    var go = $('go');
    if (go) { go.disabled = !ready(); }
  }

  function renderField(field) {
    var box = el('div', 'field');
    if (field.type === 'choice') {
      box.appendChild(labelFor(field));
      var count = field.choices.length;
      var row = el('div', 'choices' + (count === 2 || count === 4 ? ' choices--' + count : count === 5 ? ' choices--5' : ''));
      field.choices.forEach(function (choice) {
        var node = button('choice' + (count > 4 ? ' choice--small' : ''), choice[0], function () {
          state.values[field.id] = choice[1];
          renderPanel();
        });
        node.setAttribute('aria-pressed', state.values[field.id] === choice[1] ? 'true' : 'false');
        row.appendChild(node);
      });
      box.appendChild(row);
    } else if (field.type === 'number') {
      box.appendChild(labelFor(field, field.min + '~' + field.max));
      box.appendChild(renderStepper(field.min, field.max, state.values[field.id], field.default === null, field.label,
        function (value) { state.values[field.id] = value; }));
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
      input.addEventListener('input', function () { state.values[field.id] = input.value; refreshGo(); });
      input.addEventListener('keydown', function (event) { if (event.key === 'Enter') { input.blur(); } });
      box.appendChild(input);
    }
    return box;
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

  /* 뽑기를 눌러도 되는지: 꼭 넣어야 하는 칸이 비어 있지 않은지만 본다. 나머지 검사는 서버가 한다. */
  function ready() {
    if (state.phase !== 'form' || !state.mode || state.offline) { return false; }
    return state.mode.fields.every(function (field) {
      var value = state.values[field.id];
      if (field.type === 'pick') { return value.length >= field.min && value.length <= field.max; }
      if (field.type === 'names') { return splitNames(value).length >= field.min; }
      if (field.type === 'text') { return !field.required || String(value || '').trim() !== ''; }
      return true;
    });
  }

  function splitNames(text) {
    return String(text || '').split(',').map(function (s) { return s.trim(); }).filter(function (s) { return s; });
  }

  // ---------------------------------------------------------------- 그리기: 뽑는 중, 끝, 실패

  function sheetRow(job) {
    var row = el('div', 'sheets' + (job.sheets > 8 ? ' sheets--many' : ''));
    for (var n = 1; n <= job.sheets; n += 1) {
      var done = n <= job.done;
      var now = !done && job.state === 'running' && n === job.done + 1;
      var sheet = el('div', 'sheet' + (done ? ' sheet--done' : now ? ' sheet--now' : ''));
      if (done) { sheet.appendChild(icon(ICON.check)); } else { sheet.textContent = String(n); }
      row.appendChild(sheet);
    }
    return row;
  }

  function progressText(job) {
    if (!job || job.state === 'queued') { return '순서를 기다리는 중이에요'; }
    if (job.sheets === 1) { return '종이가 나오고 있어요'; }
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
    var text = '칸을 고르고 뽑기를 누르면 프린터에서 종이가 나와요.';
    if (state.offline) {
      tag = '연결 끊김';
      text = '키오스크에 연결할 수 없어요. 다시 연결하는 중이에요.';
    } else if (jobActive()) {
      var number = state.numbers[state.jobContent];
      tag = state.job.state === 'queued' ? '기다리는 중' : '뜯는 중';
      text = (number ? number + '번 ' : '') + state.job.title + ' · ' + progressText(state.job);
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
    if (!jobActive()) { state.job = null; }
    renderAll();
    api('POST', '/api/print', {
      content: contentName, mode: state.mode.id, values: collectValues(), sheets: state.mode.sheets ? state.sheets : 1
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
      renderAll();
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
  function finishJob() {
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
        message.textContent = result.data.error || '들어가지 못했어요.';
      }).catch(function () { message.textContent = '키오스크에 연결할 수 없어요.'; });
    }

    var keys = el('div', 'keys');
    ['1', '2', '3', '4', '5', '6', '7', '8', '9'].forEach(function (digit) {
      keys.appendChild(button('key', digit, function () { if (pin.length < 8) { pin += digit; drawDots(); } }));
    });
    keys.appendChild(button('key key--word', '지우기', function () { pin = pin.slice(0, -1); drawDots(); }));
    keys.appendChild(button('key', '0', function () { if (pin.length < 8) { pin += '0'; drawDots(); } }));
    keys.appendChild(button('key key--word', '확인', send));
    box.appendChild(keys);
    box.appendChild(button('plain', '닫기', closeOverlay));
    drawDots();
    openOverlay(box);
  }

  var STATE_WORD = { queued: '기다리는 중', running: '뽑는 중', done: '끝', failed: '실패', cancelled: '취소됨' };

  function openQueue() {
    var box = el('div', 'sheetbox sheetbox--wide');
    box.appendChild(el('h2', 'sheetbox__title', '인쇄 대기열'));
    var list = el('ul', 'jobs');
    var empty = el('p', 'panel__lead', '');
    box.appendChild(list);
    box.appendChild(empty);
    var buttons = el('div', 'buttons');
    buttons.appendChild(button('plain plain--danger', '남은 인쇄 모두 취소', function () {
      api('POST', '/api/admin/cancel').then(refresh).catch(refresh);
    }));
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
    if (quiet > IDLE_VISITOR && !atHome()) { goHome(); }
  }, 1000);

  renderAll();
  loadCatalog();
})();
