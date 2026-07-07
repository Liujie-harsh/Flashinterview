/* ===========================
   FlashInterview PWA 应用逻辑
   纯 vanilla JS，无框架，无 ES modules
   =========================== */

(function () {
  'use strict';

  /* ---------- 常量配置 ---------- */

  // 相对于 app/ 目录的 cards.json 路径
  var CARDS_JSON_PATH = '../data/cards.json';

  // localStorage key 前缀
  var PROGRESS_KEY_PREFIX = 'flashcard-progress-';
  var CUSTOM_KEY_PREFIX = 'flashcard-custom-';

  // 加权权重
  var WEIGHT = {
    known: 1,
    review: 3,
    unknown: 2
  };

  // 标记后切下一题的延迟
  var NEXT_CARD_DELAY = 300;

  // 公司选项（"我的" 用于自定义卡片）
  var COMPANIES = ['全部', '美团', '蚂蚁', '腾讯', '阿里', '宇树', '成都智信', '我的'];

  // 类型选项
  var TYPES = [
    { key: '全部', label: '全部', value: null },
    { key: 'technical', label: '技术题', value: 'technical' },
    { key: 'behavioral', label: '行为题', value: 'behavioral' },
    { key: 'system', label: '系统设计', value: 'system' },
    { key: 'algorithm', label: '算法题', value: 'algorithm' }
  ];

  var TYPE_LABELS = {
    technical: '技术题',
    behavioral: '行为题',
    system: '系统设计',
    algorithm: '算法题'
  };

  /* ---------- 应用状态 ---------- */

  var allCards = [];          // 全部卡片（cards.json + 自定义）
  var filteredPool = [];      // 当前筛选后的卡片池
  var currentCard = null;     // 当前展示的卡片
  var currentCompany = null;  // null = 全部
  var currentType = null;     // null = 全部
  var isFlipped = false;

  /* ---------- DOM 引用 ---------- */

  var dom = {
    companyBar: document.getElementById('companyBar'),
    typeBar: document.getElementById('typeBar'),
    flashcard: document.getElementById('flashcard'),
    cardSource: document.getElementById('cardSource'),
    cardBadge: document.getElementById('cardBadge'),
    cardBadgeBack: document.getElementById('cardBadgeBack'),
    cardQuestion: document.getElementById('cardQuestion'),
    cardAnswer: document.getElementById('cardAnswer'),
    btnKnown: document.getElementById('btnKnown'),
    btnReview: document.getElementById('btnReview'),
    emptyState: document.getElementById('emptyState'),
    seenCount: document.getElementById('seenCount'),
    knownCount: document.getElementById('knownCount'),
    fab: document.getElementById('fab'),
    addModal: document.getElementById('addModal'),
    modalClose: document.getElementById('modalClose'),
    btnCancel: document.getElementById('btnCancel'),
    addForm: document.getElementById('addForm'),
    newQuestion: document.getElementById('newQuestion'),
    newAnswer: document.getElementById('newAnswer'),
    newCompany: document.getElementById('newCompany'),
    newType: document.getElementById('newType'),
    newTags: document.getElementById('newTags'),
    // Tab 切换
    tabManual: document.getElementById('tabManual'),
    tabImport: document.getElementById('tabImport'),
    panelManual: document.getElementById('addForm'),
    panelImport: document.getElementById('panelImport'),
    // 导入面板
    importCompany: document.getElementById('importCompany'),
    importRound: document.getElementById('importRound'),
    importText: document.getElementById('importText'),
    btnImport: document.getElementById('btnImport'),
    btnImportCancel: document.getElementById('btnImportCancel'),
    toast: document.getElementById('toast')
  };

  /* ===========================
     1. localStorage 读写封装
     =========================== */

  function getProgress(cardId) {
    try {
      var raw = localStorage.getItem(PROGRESS_KEY_PREFIX + cardId);
      if (!raw) return { status: 'unknown', timestamp: 0 };
      var data = JSON.parse(raw);
      return {
        status: data.status || 'unknown',
        timestamp: data.timestamp || 0
      };
    } catch (e) {
      return { status: 'unknown', timestamp: 0 };
    }
  }

  function setProgress(cardId, status) {
    try {
      localStorage.setItem(
        PROGRESS_KEY_PREFIX + cardId,
        JSON.stringify({ status: status, timestamp: Date.now() })
      );
    } catch (e) {
      console.warn('[FlashInterview] 写入 localStorage 失败:', e);
    }
  }

  function getCustomCards() {
    var cards = [];
    try {
      for (var i = 0; i < localStorage.length; i++) {
        var key = localStorage.key(i);
        if (key && key.indexOf(CUSTOM_KEY_PREFIX) === 0) {
          var data = JSON.parse(localStorage.getItem(key));
          if (data) cards.push(data);
        }
      }
    } catch (e) {
      console.warn('[FlashInterview] 读取自定义卡片失败:', e);
    }
    return cards;
  }

  function addCustomCard(card) {
    var timestamp = Date.now();
    var id = 'custom-' + timestamp;
    var record = {
      id: id,
      question: card.question,
      answer: card.answer || '',
      company: card.company || '我的',
      round: card.round || '自定义',
      type: card.type || 'technical',
      tags: card.tags || '',
      custom: true
    };
    try {
      localStorage.setItem(
        CUSTOM_KEY_PREFIX + timestamp,
        JSON.stringify(record)
      );
    } catch (e) {
      console.warn('[FlashInterview] 保存自定义卡片失败:', e);
    }
    return record;
  }

  /* ===========================
     2. 加载卡片数据
     =========================== */

  function loadCards() {
    // 通过 fetch 加载 cards.json（SW 已预缓存，离线可用）
    return fetch(CARDS_JSON_PATH)
      .then(function (res) {
        if (!res.ok) {
          throw new Error('HTTP ' + res.status);
        }
        return res.json();
      })
      .then(function (data) {
        if (data && Array.isArray(data.cards)) {
          return data.cards;
        }
        if (Array.isArray(data)) {
          return data;
        }
        return [];
      })
      .catch(function (err) {
        console.warn('[FlashInterview] 加载 cards.json 失败:', err.message);
        return [];
      });
  }

  function buildAllCards(parsedCards) {
    var custom = getCustomCards();
    allCards = parsedCards.concat(custom);
  }

  /* ===========================
     3. 筛选逻辑
     =========================== */

  function applyFilters() {
    filteredPool = allCards.filter(function (card) {
      var companyOk = !currentCompany || card.company === currentCompany;
      var typeOk = !currentType || card.type === currentType;
      return companyOk && typeOk;
    });
  }

  /* ===========================
     4. 加权抽题算法
     =========================== */

  function pickNextCard() {
    if (filteredPool.length === 0) return null;

    // 只有一张牌时直接返回（避免连续重复限制导致死循环）
    if (filteredPool.length === 1) {
      return filteredPool[0];
    }

    // 构建加权数组（排除当前卡片，避免连续重复）
    var weighted = [];
    for (var i = 0; i < filteredPool.length; i++) {
      var card = filteredPool[i];
      if (currentCard && card.id === currentCard.id) continue;

      var progress = getProgress(card.id);
      var weight = WEIGHT[progress.status] || WEIGHT.unknown;
      for (var j = 0; j < weight; j++) {
        weighted.push(card);
      }
    }

    if (weighted.length === 0) return null;
    var idx = Math.floor(Math.random() * weighted.length);
    return weighted[idx];
  }

  /* ===========================
     5. 渲染筛选标签栏
     =========================== */

  function renderCompanyBar() {
    dom.companyBar.innerHTML = '';
    COMPANIES.forEach(function (name) {
      var pill = document.createElement('button');
      pill.type = 'button';
      pill.className = 'pill';
      pill.textContent = name;
      pill.setAttribute('role', 'tab');
      var value = (name === '全部') ? null : name;
      if (value === currentCompany) pill.classList.add('active');
      pill.addEventListener('click', function () {
        currentCompany = value;
        renderCompanyBar();
        onFilterChange();
      });
      dom.companyBar.appendChild(pill);
    });
  }

  function renderTypeBar() {
    dom.typeBar.innerHTML = '';
    TYPES.forEach(function (t) {
      var pill = document.createElement('button');
      pill.type = 'button';
      pill.className = 'pill';
      pill.textContent = t.label;
      pill.setAttribute('role', 'tab');
      if (t.value === currentType) pill.classList.add('active');
      pill.addEventListener('click', function () {
        currentType = t.value;
        renderTypeBar();
        onFilterChange();
      });
      dom.typeBar.appendChild(pill);
    });
  }

  function onFilterChange() {
    applyFilters();
    currentCard = null;
    isFlipped = false;
    dom.flashcard.classList.remove('flipped');
    loadNextCard();
  }

  /* ===========================
     6. 渲染卡片
     =========================== */

  function renderCard(card) {
    if (!card) {
      showEmptyState();
      return;
    }
    hideEmptyState();

    var typeLabel = TYPE_LABELS[card.type] || '技术题';
    var sourceText = [card.company, card.round].filter(Boolean).join(' · ');

    dom.cardSource.textContent = sourceText || '未知来源';
    dom.cardBadge.textContent = typeLabel;
    dom.cardBadgeBack.textContent = typeLabel;
    dom.cardQuestion.textContent = card.question || '(空题目)';
    dom.cardAnswer.textContent = card.answer || '(暂无参考答案)';
  }

  function showEmptyState() {
    dom.flashcard.style.display = 'none';
    dom.emptyState.hidden = false;
  }

  function hideEmptyState() {
    dom.flashcard.style.display = '';
    dom.emptyState.hidden = true;
  }

  function loadNextCard() {
    var next = pickNextCard();
    currentCard = next;
    isFlipped = false;
    dom.flashcard.classList.remove('flipped');
    renderCard(next);
  }

  /* ===========================
     7. 卡片翻转交互
     =========================== */

  function flipCard() {
    if (!currentCard) return;
    isFlipped = !isFlipped;
    dom.flashcard.classList.toggle('flipped', isFlipped);
  }

  /* ===========================
     8. 标记熟/不熟
     =========================== */

  function markCard(status) {
    if (!currentCard) return;
    setProgress(currentCard.id, status);
    updateProgressCounter();

    // 翻回正面再切下一题
    isFlipped = false;
    dom.flashcard.classList.remove('flipped');

    setTimeout(function () {
      loadNextCard();
    }, NEXT_CARD_DELAY);
  }

  /* ===========================
     9. 进度计数器更新
     =========================== */

  function updateProgressCounter() {
    var seen = 0;
    var known = 0;
    allCards.forEach(function (card) {
      var p = getProgress(card.id);
      if (p.status === 'known' || p.status === 'review') seen++;
      if (p.status === 'known') known++;
    });
    dom.seenCount.textContent = seen;
    dom.knownCount.textContent = known;
  }

  /* ===========================
     10. 添加题目弹窗
     =========================== */

  function openAddModal() {
    dom.addModal.classList.add('active');
    document.body.style.overflow = 'hidden';
    // 重置到手动添加 Tab
    switchTab('manual');
  }

  function closeAddModal() {
    dom.addModal.classList.remove('active');
    document.body.style.overflow = '';
  }

  function submitNewCard(e) {
    e.preventDefault();
    var question = dom.newQuestion.value.trim();
    var answer = dom.newAnswer.value.trim();
    var company = dom.newCompany.value;
    var type = dom.newType.value;
    var tags = dom.newTags.value.trim();

    if (!question) {
      dom.newQuestion.focus();
      dom.newQuestion.style.borderColor = 'var(--danger)';
      setTimeout(function () {
        dom.newQuestion.style.borderColor = '';
      }, 2000);
      return;
    }

    var newCard = addCustomCard({
      question: question,
      answer: answer,
      company: company,
      type: type,
      tags: tags,
      round: '自定义'
    });

    // 加入卡片池
    allCards.push(newCard);

    // 重置表单
    dom.addForm.reset();

    closeAddModal();
    showToast('题目已添加到题库！');

    // 重新应用筛选并刷新
    applyFilters();
    updateProgressCounter();
    onFilterChange();
  }

  /* ===========================
     11. Toast 提示
     =========================== */

  var toastTimer = null;
  function showToast(message) {
    if (message) {
      dom.toast.querySelector('.toast-text').textContent = message;
    }
    dom.toast.classList.add('show');
    if (toastTimer) clearTimeout(toastTimer);
    toastTimer = setTimeout(function () {
      dom.toast.classList.remove('show');
    }, 2500);
  }

  /* ===========================
     12. Tab 切换
     =========================== */

  function switchTab(tabName) {
    if (tabName === 'import') {
      dom.tabManual.classList.remove('active');
      dom.tabImport.classList.add('active');
      dom.panelManual.classList.remove('active');
      dom.panelManual.style.display = 'none';
      dom.panelImport.classList.add('active');
      dom.panelImport.style.display = 'flex';
      setTimeout(function () { dom.importText.focus(); }, 100);
    } else {
      dom.tabImport.classList.remove('active');
      dom.tabManual.classList.add('active');
      dom.panelImport.classList.remove('active');
      dom.panelImport.style.display = 'none';
      dom.panelManual.classList.add('active');
      dom.panelManual.style.display = 'flex';
      setTimeout(function () { dom.newQuestion.focus(); }, 100);
    }
  }

  /* ===========================
     13. Markdown 解析器
     =========================== */

  // 需要跳过的非问题文本
  var SKIP_PATTERNS = [
    /自我介绍/i,
    /笔试题/i,
    /反问环节/i,
    /面试感受/i,
    /面试总结/i,
    /面试基本信息/i,
    /项目生命周期/i
  ];

  // 题目类型关键词
  function inferType(question) {
    if (/手写算法|实现一个|算法/.test(question)) return 'algorithm';
    if (/设计|架构|方案|规划/.test(question)) return 'system';
    if (/为什么选择|职业规划|优点缺点|团队氛围|如何评价自己|薪资/.test(question)) return 'behavioral';
    return 'technical';
  }

  function shouldSkip(text) {
    return SKIP_PATTERNS.some(function (re) { return re.test(text); });
  }

  // 去除 markdown 标记前缀（###、##、#、数字.、Q数字：等）
  function cleanQuestion(raw) {
    return raw
      .replace(/^#{1,6}\s*/, '')      // 去掉 # 前缀
      .replace(/^Q?\d+[：:.\s]\s*/, '') // 去掉 Q1：或 1. 前缀
      .replace(/^\d+\.\s*/, '')        // 去掉 1. 前缀
      .trim();
  }

  // 检测是否为章节标题（## 开头，但不是问题）
  function isSectionHeader(line) {
    return /^#{1,2}\s+[^Qq\d]/.test(line);
  }

  // 检测是否为问题行（### Q数字： 或 数字. 开头）
  function isQuestionLine_QA(line) {
    return /^#{0,3}\s*Q\d+[：:]/.test(line);
  }

  function isQuestionLine_Numbered(line) {
    return /^\d+\.\s+\S/.test(line);
  }

  function parseMarkdown(text) {
    var lines = text.split(/\r?\n/);
    var cards = [];
    var i = 0;
    var inSkipSection = false;

    // 格式检测
    var hasQAFormat = lines.some(function (l) { return isQuestionLine_QA(l); });
    var hasNumberedFormat = lines.some(function (l) { return isQuestionLine_Numbered(l); });

    if (hasQAFormat) {
      // 标准 Q&A 格式：### Q数字：问题
      while (i < lines.length) {
        var line = lines[i];

        if (isQuestionLine_QA(line)) {
          var question = cleanQuestion(line);

          // 收集答案（到下一个问题行或章节标题）
          var answerLines = [];
          i++;
          while (i < lines.length && !isQuestionLine_QA(lines[i]) && !isSectionHeader(lines[i])) {
            answerLines.push(lines[i]);
            i++;
          }

          var answer = answerLines.join('\n').trim();

          if (question && !shouldSkip(question)) {
            cards.push({
              question: question,
              answer: answer,
              type: inferType(question)
            });
          }
        } else {
          i++;
        }
      }
    } else if (hasNumberedFormat) {
      // 编号列表格式：1. 问题（可能有答案，可能没有）
      while (i < lines.length) {
        var line = lines[i];

        // 检测章节切换
        if (isSectionHeader(line)) {
          inSkipSection = shouldSkip(line);
          i++;
          continue;
        }

        if (inSkipSection) {
          i++;
          continue;
        }

        if (isQuestionLine_Numbered(line)) {
          var question = cleanQuestion(line);

          // 收集答案（到下一个编号行或空行后非列表内容）
          var answerLines = [];
          i++;
          while (i < lines.length && !isQuestionLine_Numbered(lines[i]) && !isSectionHeader(lines[i])) {
            // 如果遇到空行且后面不是列表项，可能是答案结束
            answerLines.push(lines[i]);
            i++;
          }

          var answer = answerLines.join('\n').trim();
          // 如果答案只有空白行，设为空
          if (!answer || !answer.replace(/\s/g, '')) {
            answer = '';
          }

          if (question && !shouldSkip(question)) {
            cards.push({
              question: question,
              answer: answer,
              type: inferType(question)
            });
          }
        } else {
          i++;
        }
      }
    }

    return cards;
  }

  /* ===========================
     14. Markdown 批量导入
     =========================== */

  function handleImport() {
    var text = dom.importText.value.trim();
    if (!text) {
      dom.importText.focus();
      dom.importText.style.borderColor = 'var(--danger)';
      setTimeout(function () {
        dom.importText.style.borderColor = '';
      }, 2000);
      return;
    }

    var company = dom.importCompany.value;
    var round = dom.importRound.value;
    var parsed = parseMarkdown(text);

    if (parsed.length === 0) {
      showToast('未识别到题目，请检查格式');
      return;
    }

    var timestamp = Date.now();
    parsed.forEach(function (item, idx) {
      var card = {
        id: 'custom-' + timestamp + '-' + (idx + 1),
        question: item.question,
        answer: item.answer,
        company: company,
        round: round,
        type: item.type,
        tags: [],
        custom: true
      };

      // 写入 localStorage
      try {
        localStorage.setItem(
          CUSTOM_KEY_PREFIX + timestamp + '-' + (idx + 1),
          JSON.stringify(card)
        );
      } catch (e) {
        console.warn('[FlashInterview] 保存导入卡片失败:', e);
      }

      allCards.push(card);
    });

    // 重置表单
    dom.importText.value = '';

    closeAddModal();
    showToast('已导入 ' + parsed.length + ' 道题目！');

    // 重新应用筛选并刷新
    applyFilters();
    updateProgressCounter();
    onFilterChange();
  }

  /* ===========================
     事件绑定
     =========================== */

  function bindEvents() {
    // 卡片点击翻转
    dom.flashcard.addEventListener('click', flipCard);
    dom.flashcard.addEventListener('keydown', function (e) {
      if (e.key === 'Enter' || e.key === ' ') {
        e.preventDefault();
        flipCard();
      }
    });

    // 正背面按钮（阻止冒泡，避免触发翻转）
    dom.btnKnown.addEventListener('click', function (e) {
      e.stopPropagation();
      markCard('known');
    });
    dom.btnReview.addEventListener('click', function (e) {
      e.stopPropagation();
      markCard('review');
    });

    // 浮动按钮
    dom.fab.addEventListener('click', openAddModal);

    // 弹窗交互
    dom.modalClose.addEventListener('click', closeAddModal);
    dom.btnCancel.addEventListener('click', closeAddModal);
    dom.addModal.addEventListener('click', function (e) {
      if (e.target === dom.addModal) closeAddModal();
    });
    dom.addForm.addEventListener('submit', submitNewCard);

    // Tab 切换
    dom.tabManual.addEventListener('click', function () { switchTab('manual'); });
    dom.tabImport.addEventListener('click', function () { switchTab('import'); });

    // Markdown 导入
    dom.btnImport.addEventListener('click', handleImport);
    dom.btnImportCancel.addEventListener('click', closeAddModal);

    // ESC 关闭弹窗
    document.addEventListener('keydown', function (e) {
      if (e.key === 'Escape' && dom.addModal.classList.contains('active')) {
        closeAddModal();
      }
    });
  }

  /* ===========================
     初始化入口
     =========================== */

  function init() {
    bindEvents();
    renderCompanyBar();
    renderTypeBar();

    loadCards().then(function (parsedCards) {
      buildAllCards(parsedCards);
      applyFilters();
      updateProgressCounter();
      loadNextCard();
    });
  }

  // DOM 已就绪时启动
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
