(function () {
  'use strict';

  var meta = document.querySelector('meta[name="brief-slide-key"]');
  var slideKey = meta && meta.getAttribute('content');
  if (!slideKey) return;

  var STORAGE_KEY = 'hk-brief-slides-edit-' + slideKey;
  var editing = false;
  var toolbar = null;
  var statusEl = null;
  var btnBold = null;

  function ready(fn) {
    if (document.readyState !== 'loading') fn();
    else document.addEventListener('DOMContentLoaded', fn);
  }

  function setStatus(msg) {
    if (statusEl) statusEl.textContent = msg || '';
  }

  function editableRegions() {
    return document.querySelectorAll('.slide-body[data-slide-edit], .article-top[data-slide-edit]');
  }

  function stripEditorChrome(root) {
    var scope = root || document;
    scope.querySelectorAll('.slide-block-delete').forEach(function (btn) {
      btn.remove();
    });
  }

  function blockIsEmpty(el) {
    if (!el) return true;
    var clone = el.cloneNode(true);
    clone.querySelectorAll('.slide-block-delete').forEach(function (btn) {
      btn.remove();
    });
    if (clone.querySelector('img')) return false;
    var html = (clone.innerHTML || '')
      .replace(/<br\s*\/?>/gi, '')
      .replace(/&nbsp;/gi, '')
      .replace(/<[^>]+>/g, '')
      .trim();
    var text = (clone.textContent || '').replace(/\u00a0/g, '').trim();
    return !text && !html;
  }

  function pruneEmptyBlocks(root) {
    var scope = root || document;
    scope.querySelectorAll('.slide-body').forEach(function (body) {
      body.querySelectorAll(':scope > p, :scope > figure, :scope > div').forEach(function (block) {
        if (blockIsEmpty(block)) {
          block.remove();
        } else {
          block.classList.remove('is-empty');
        }
      });
    });
    if (window.updateSlideScrollHints) {
      window.updateSlideScrollHints();
    }
  }

  function stripContinuedMarkers() {
    document.querySelectorAll('.article-continued').forEach(function (el) {
      el.remove();
    });
    document.querySelectorAll('.slide-article .kicker').forEach(function (kicker) {
      kicker.querySelectorAll('.article-continued').forEach(function (el) {
        el.remove();
      });
      var html = kicker.innerHTML;
      html = html.replace(/<span[^>]*class="article-continued"[^>]*>[\s\S]*?<\/span>/gi, '');
      html = html.replace(/[（(]\s*續\s*\d+\s*\/\s*\d+\s*[）)]/g, '');
      html = html.replace(/\s{2,}/g, ' ').replace(/\s+·\s*$/g, '').trim();
      kicker.innerHTML = html;
    });
  }

  function stripReadOriginalLinks() {
    document.querySelectorAll('.source-link, .read-original, .article-read').forEach(function (el) {
      el.remove();
    });
    document.querySelectorAll('p, .article-meta').forEach(function (el) {
      var text = (el.textContent || '').replace(/\s/g, '');
      if (/^原文[：:]?$/.test(text) || text === '閱讀原文' || text === '阅读原文') {
        el.remove();
      }
    });
    document.querySelectorAll('a').forEach(function (a) {
      var label = (a.textContent || '').trim();
      if (label === '閱讀原文' || label === '阅读原文') {
        var row = a.closest('p, .source-link, .read-original');
        if (row) row.remove();
        else a.remove();
      }
    });
  }

  function bodyHasContent(body) {
    if (!body) return false;
    var blocks = body.querySelectorAll(':scope > p, :scope > figure');
    for (var i = 0; i < blocks.length; i++) {
      if (!blockIsEmpty(blocks[i])) return true;
    }
    return false;
  }

  function updateTocGotos() {
    var slides = Array.from(document.querySelectorAll('.deck .slide'));
    document.querySelectorAll('.slide-toc li').forEach(function (li) {
      var titleEl = li.querySelector('.toc-item-title');
      if (!titleEl) return;
      var title = titleEl.textContent.trim();
      var target = -1;
      for (var i = 0; i < slides.length; i++) {
        var s = slides[i];
        if (!s.classList.contains('slide-article')) continue;
        if ((s.getAttribute('data-title') || '').trim() === title) {
          target = i;
          break;
        }
      }
      if (target >= 0) li.setAttribute('data-goto', String(target));
      else li.removeAttribute('data-goto');
    });
  }

  function maybeRemoveEmptySlide(body) {
    if (!body) return;
    var slide = body.closest('.slide-article');
    if (!slide) return;
    pruneEmptyBlocks(body);
    if (bodyHasContent(body)) return;

    var deck = document.querySelector('.deck');
    if (!deck) return;
    var allSlides = Array.from(deck.querySelectorAll('.slide'));
    var removeIdx = allSlides.indexOf(slide);
    if (removeIdx < 0) return;

    slide.remove();
    updateTocGotos();

    if (window.htmlPpt && typeof window.htmlPpt.refresh === 'function') {
      window.htmlPpt.refresh(removeIdx);
    }

    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(snapshot()));
    } catch (e) { /* ignore */ }

    setStatus('空白頁已自動刪除');
  }

  function removeBlock(block) {
    if (!block) return;
    var body = block.closest ? block.closest('.slide-body') : null;
    block.remove();
    if (body) {
      pruneEmptyBlocks(body);
      maybeRemoveEmptySlide(body);
    }
  }

  function createDeleteButton(block) {
    var btn = document.createElement('button');
    btn.type = 'button';
    btn.className = 'slide-block-delete';
    btn.setAttribute('contenteditable', 'false');
    btn.setAttribute('tabindex', '-1');
    btn.setAttribute('unselectable', 'on');
    btn.title = '刪除此段或圖片';
    btn.textContent = '×';
    btn.addEventListener('mousedown', function (e) {
      e.preventDefault();
      e.stopPropagation();
    });
    return btn;
  }

  function assignEditIds() {
    document.querySelectorAll('.slide-article').forEach(function (slide, idx) {
      var top = slide.querySelector('.article-top');
      var body = slide.querySelector('.slide-body');
      var aid = slide.getAttribute('data-article-id') || 'art-' + idx;
      if (top && !top.getAttribute('data-slide-edit')) {
        top.setAttribute('data-slide-edit', aid + '-head');
      }
      if (body && !body.getAttribute('data-slide-edit')) {
        body.setAttribute('data-slide-edit', aid + '-body-' + idx);
      }
    });
  }

  function wrapBlocks() {
    document.querySelectorAll('.slide-body').forEach(function (body) {
      stripEditorChrome(body);
      body.querySelectorAll(':scope > p, :scope > figure, :scope > img').forEach(function (block) {
        if (block.tagName === 'IMG') {
          var fig = document.createElement('figure');
          fig.className = 'inline-figure';
          block.parentNode.insertBefore(fig, block);
          fig.appendChild(block);
          block = fig;
        }
        block.classList.add('editable-block');
        block.appendChild(createDeleteButton(block));
      });
      pruneEmptyBlocks(body);
    });
  }

  function ensureAddButtons() {
    document.querySelectorAll('.slide-article').forEach(function (slide) {
      if (slide.querySelector('.slide-add-para')) return;
      var body = slide.querySelector('.slide-body');
      if (!body) return;
      var btn = document.createElement('button');
      btn.type = 'button';
      btn.className = 'slide-add-para';
      btn.setAttribute('contenteditable', 'false');
      btn.textContent = '+ 新增段落';
      btn.addEventListener('click', function (e) {
        e.preventDefault();
        e.stopPropagation();
        var p = document.createElement('p');
        p.textContent = '';
        body.appendChild(p);
        if (editing) attachDeleteToBlock(p);
        p.focus();
        placeCaretAtEnd(p);
      });
      slide.appendChild(btn);
    });
  }

  function attachDeleteToBlock(block) {
    block.classList.add('editable-block');
    stripEditorChrome(block);
    block.appendChild(createDeleteButton(block));
  }

  function placeCaretAtEnd(el) {
    el.focus();
    var range = document.createRange();
    range.selectNodeContents(el);
    range.collapse(false);
    var sel = window.getSelection();
    if (sel) {
      sel.removeAllRanges();
      sel.addRange(range);
    }
  }

  function snapshot() {
    stripEditorChrome();
    stripContinuedMarkers();
    pruneEmptyBlocks();
    var data = {};
    editableRegions().forEach(function (el) {
      var key = el.getAttribute('data-slide-edit');
      if (key) data[key] = el.innerHTML;
    });
    return data;
  }

  function restore(data) {
    if (!data) return;
    editableRegions().forEach(function (el) {
      var key = el.getAttribute('data-slide-edit');
      if (key && data[key]) el.innerHTML = data[key];
    });
    stripReadOriginalLinks();
    stripContinuedMarkers();
    stripEditorChrome();
    pruneEmptyBlocks();
    if (editing) wrapBlocks();
  }

  function saveLocal() {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(snapshot()));
      setStatus('已儲存 ' + new Date().toLocaleTimeString('zh-HK'));
    } catch (e) {
      setStatus('儲存失敗');
    }
  }

  function loadLocal() {
    try {
      var raw = localStorage.getItem(STORAGE_KEY);
      if (raw) restore(JSON.parse(raw));
    } catch (e) { /* ignore */ }
  }

  function enableEdit() {
    editing = true;
    document.body.classList.add('slide-editing');
    editableRegions().forEach(function (el) {
      el.setAttribute('contenteditable', 'true');
      el.addEventListener('input', onBodyInput);
    });
    wrapBlocks();
    setStatus('可改字、B 加粗、刪段落/圖片、+ 新增段落');
  }

  function onBodyInput(e) {
    var body = e.target.closest ? e.target.closest('.slide-body') : null;
    if (!body) return;
    pruneEmptyBlocks(body);
    maybeRemoveEmptySlide(body);
  }

  function disableEdit() {
    editing = false;
    document.body.classList.remove('slide-editing');
    editableRegions().forEach(function (el) {
      el.removeAttribute('contenteditable');
      el.removeEventListener('input', onBodyInput);
    });
    pruneEmptyBlocks();
    if (btnBold) btnBold.classList.remove('active');
    setStatus('');
  }

  function applyBold() {
    if (!editing) {
      setStatus('請先點「編輯」');
      return;
    }
    var sel = window.getSelection();
    if (!sel || !sel.rangeCount) {
      setStatus('請先選取文字');
      return;
    }
    document.execCommand('bold', false, null);
    updateBoldButton();
  }

  function updateBoldButton() {
    if (!btnBold) return;
    var on = editing && document.queryCommandState && document.queryCommandState('bold');
    btnBold.classList.toggle('active', !!on);
  }

  function serializeDocument() {
    disableEdit();
    stripReadOriginalLinks();
    stripContinuedMarkers();
    stripEditorChrome();
    pruneEmptyBlocks();
    document.querySelectorAll('.slide-add-para, .slide-fab-edit, #slide-edit-toolbar').forEach(function (el) {
      el.remove();
    });
    return '<!DOCTYPE html>\n' + document.documentElement.outerHTML;
  }

  function downloadHtml() {
    saveLocal();
    var blob = new Blob([serializeDocument()], { type: 'text/html;charset=utf-8' });
    var a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = '香港簡訊-簡報-' + slideKey + '.html';
    a.click();
    URL.revokeObjectURL(a.href);
    enableEdit();
    wrapBlocks();
    setStatus('已下載 HTML');
  }

  function buildToolbar() {
    toolbar = document.createElement('div');
    toolbar.id = 'slide-edit-toolbar';

    var btnEdit = document.createElement('button');
    btnEdit.type = 'button';
    btnEdit.textContent = '完成編輯';
    btnEdit.addEventListener('click', function () {
      saveLocal();
      disableEdit();
    });

    btnBold = document.createElement('button');
    btnBold.type = 'button';
    btnBold.className = 'fmt-bold';
    btnBold.textContent = 'B';
    btnBold.title = '加粗 Ctrl+B';
    btnBold.addEventListener('click', applyBold);

    var btnSave = document.createElement('button');
    btnSave.type = 'button';
    btnSave.className = 'primary';
    btnSave.textContent = '儲存';
    btnSave.addEventListener('click', saveLocal);

    var btnDl = document.createElement('button');
    btnDl.type = 'button';
    btnDl.textContent = '下載 HTML';
    btnDl.addEventListener('click', downloadHtml);

    var btnReset = document.createElement('button');
    btnReset.type = 'button';
    btnReset.textContent = '還原預設';
    btnReset.addEventListener('click', function () {
      if (!confirm('清除本地修改並重新載入？')) return;
      localStorage.removeItem(STORAGE_KEY);
      location.reload();
    });

    statusEl = document.createElement('span');
    statusEl.className = 'status';

    toolbar.appendChild(btnSave);
    toolbar.appendChild(btnEdit);
    toolbar.appendChild(document.createElement('span')).className = 'sep';
    toolbar.appendChild(btnBold);
    toolbar.appendChild(document.createElement('span')).className = 'sep';
    toolbar.appendChild(btnDl);
    toolbar.appendChild(btnReset);
    toolbar.appendChild(statusEl);

    document.body.insertBefore(toolbar, document.body.firstChild);
    document.body.classList.add('slide-has-toolbar');

    var fab = document.createElement('button');
    fab.type = 'button';
    fab.className = 'slide-fab-edit';
    fab.textContent = '✎ 編輯';
    fab.addEventListener('click', enableEdit);
    document.body.appendChild(fab);
  }

  ready(function () {
    stripReadOriginalLinks();
    assignEditIds();
    ensureAddButtons();
    buildToolbar();
    loadLocal();
    stripReadOriginalLinks();
    stripContinuedMarkers();
    pruneEmptyBlocks();

    /* 捕獲階段兜底：避免 contenteditable 吞掉刪除鈕點擊 */
    document.addEventListener('click', function (e) {
      if (!editing) return;
      var btn = e.target.closest ? e.target.closest('.slide-block-delete') : null;
      if (!btn) return;
      e.preventDefault();
      e.stopPropagation();
      var block = btn.closest('p, figure, .editable-block');
      if (block && confirm('確定刪除此內容？')) removeBlock(block);
    }, true);

    document.addEventListener('selectionchange', updateBoldButton);
    document.addEventListener('keydown', function (e) {
      if (editing && (e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'b') {
        e.preventDefault();
        applyBold();
      }
    });
  });
})();
