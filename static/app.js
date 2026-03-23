// ── Translations ─────────────────────────────────────────────────────────────
const TRANSLATIONS = {
  en: {
    title:                'X List Bulk Blocker',
    subtitle:             'Block every member of any public X list.<br>No API keys or developer account needed — just your browser cookies.',
    privacy:              '🔒 <strong>Privacy:</strong> Your cookies are used only to call X on your behalf and are <strong>never stored or logged</strong> on this server. Use HTTPS to keep them private in transit. Cookies are cleared from memory as soon as your job finishes.',
    risk_notice:          '⚠️ <strong>Risk notice:</strong> This tool uses X\'s internal API with your session cookies, which is against X\'s Terms of Service. X may detect the automated requests and <strong>force you to log in again</strong>. Account suspension is theoretically possible but has not been observed in practice. <strong>Use at your own risk.</strong>',
    step1_label:          'X List URL',
    list_url_placeholder: 'https://x.com/i/lists/1992639069235695952',
    step2_label:          'Your X Cookies',
    guide_summary:        'How to get your cookies from Chrome (click to expand)',
    guide_steps:          '<ol>\n      <li>Open <strong>x.com</strong> in <strong>Google Chrome</strong> and make sure you are <strong>logged in</strong>.</li>\n      <li>Press <kbd>F12</kbd> (Windows/Linux) or <kbd>⌘ Opt I</kbd> (Mac) to open DevTools.</li>\n      <li>Click the <strong>Application</strong> tab at the top of DevTools.<br><em>(If you don\'t see it, click the <code>&gt;&gt;</code> arrow to find more tabs.)</em></li>\n      <li>In the left sidebar, expand <strong>Cookies</strong> and click <strong>https://x.com</strong>.</li>\n      <li>In the table, find the row named <code>auth_token</code>. Click on it and copy the long text in the <strong>Value</strong> column.</li>\n      <li>Find the row named <code>ct0</code> and copy its <strong>Value</strong> too.</li>\n      <li>Paste each value in the fields below.</li>\n    </ol>',
    guide_tip:            '🔒 Your cookies are sent directly to X from your browser and are never stored anywhere by this tool.',
    auth_token_placeholder: 'Paste auth_token value here',
    auth_token_hint:      'auth_token — found in Cookies → https://x.com',
    ct0_placeholder:      'Paste ct0 value here',
    ct0_hint:             'ct0 — found in Cookies → https://x.com',
    start_btn:            '🚫 Block Everyone',
    progress_title:       'Live Progress',
    status_running:       'Running…',
    status_done:          'Done',
    status_error:         'Error',
    btn_running:          '⏳ Running…',
    btn_run_again:        '🚀 Run Again',
    btn_try_again:        '🚀 Try Again',
    lang_toggle:          'فارسی',
  },
  fa: {
    title:                'مسدودساز دسته\u200cجمعی لیست X',
    subtitle:             'مسدود کردن تمام اعضای هر لیست عمومی X.<br>بدون نیاز به کلیدهای API یا حساب توسعه\u200cدهنده — فقط کوکی\u200cهای مرورگرتان کافی است.',
    privacy:              '🔒 <strong>حریم خصوصی:</strong> کوکی\u200cهای شما فقط برای فراخوانی X از طرف شما استفاده می\u200cشود و <strong>هرگز ذخیره یا ثبت نمی\u200cشوند</strong> در این سرور. از HTTPS برای حفظ امنیت آن\u200cها در انتقال استفاده کنید. کوکی\u200cها به محض پایان کار از حافظه پاک می\u200cشوند.',
    risk_notice:          '⚠️ <strong>هشدار:</strong> این ابزار از API داخلی X با کوکی\u200cهای جلسه شما استفاده می\u200cکند که با شرایط استفاده X مغایرت دارد. X ممکن است درخواست\u200cهای خودکار را تشخیص داده و <strong>شما را مجبور به ورود مجدد کند</strong>. تعلیق حساب از نظر تئوری ممکن است اما در عمل مشاهده نشده است. <strong>با مسئولیت خودتان استفاده کنید.</strong>',
    step1_label:          'آدرس لیست X',
    list_url_placeholder: 'https://x.com/i/lists/1992639069235695952',
    step2_label:          'کوکی\u200cهای X شما',
    guide_summary:        'نحوه دریافت کوکی\u200cها از Chrome (برای گسترش کلیک کنید)',
    guide_steps:          '<ol>\n      <li>وارد <strong>x.com</strong> در <strong>Google Chrome</strong> شوید و مطمئن شوید که <strong>وارد حساب</strong> شده\u200cاید.</li>\n      <li>کلید <kbd>F12</kbd> (ویندوز/لینوکس) یا <kbd>⌘ Opt I</kbd> (مک) را برای باز کردن DevTools فشار دهید.</li>\n      <li>روی تب <strong>Application</strong> در بالای DevTools کلیک کنید.<br><em>(اگر آن را نمی\u200cبینید، روی فلش <code>&gt;&gt;</code> کلیک کنید تا تب\u200cهای بیشتر را ببینید.)</em></li>\n      <li>در نوار کناری، <strong>Cookies</strong> را گسترش داده و روی <strong>https://x.com</strong> کلیک کنید.</li>\n      <li>ردیف <code>auth_token</code> را پیدا کنید، روی آن کلیک کرده و متن طولانی ستون <strong>Value</strong> را کپی کنید.</li>\n      <li>ردیف <code>ct0</code> را پیدا کنید و مقدار آن را نیز کپی کنید.</li>\n      <li>هر مقدار را در فیلدهای زیر جای\u200cگذاری کنید.</li>\n    </ol>',
    guide_tip:            '🔒 کوکی\u200cهای شما مستقیماً از مرورگر شما به X ارسال می\u200cشوند و هرگز توسط این ابزار ذخیره نمی\u200cشوند.',
    auth_token_placeholder: 'مقدار auth_token را اینجا جای\u200cگذاری کنید',
    auth_token_hint:      'auth_token — در مسیر Cookies ← https://x.com پیدا می\u200cشود',
    ct0_placeholder:      'مقدار ct0 را اینجا جای\u200cگذاری کنید',
    ct0_hint:             'ct0 — در مسیر Cookies ← https://x.com پیدا می\u200cشود',
    start_btn:            '🚫 مسدود کردن همه',
    progress_title:       'پیشرفت زنده',
    status_running:       'در حال اجرا…',
    status_done:          'انجام شد',
    status_error:         'خطا',
    btn_running:          '⏳ در حال اجرا…',
    btn_run_again:        '🚀 اجرای مجدد',
    btn_try_again:        '🚀 تلاش مجدد',
    lang_toggle:          'English',
  },
};

let currentLang = localStorage.getItem('lang') || 'en';

function t(key) {
  return (TRANSLATIONS[currentLang] || TRANSLATIONS.en)[key] || key;
}

function applyLang(lang) {
  currentLang = lang;
  localStorage.setItem('lang', lang);
  document.documentElement.lang = lang;
  document.documentElement.dir  = lang === 'fa' ? 'rtl' : 'ltr';

  document.querySelectorAll('[data-i18n]').forEach(el => {
    el.textContent = t(el.dataset.i18n);
  });
  // innerHTML is safe here: values come from the TRANSLATIONS constant above, never from user input
  document.querySelectorAll('[data-i18n-html]').forEach(el => {
    el.innerHTML = t(el.dataset.i18nHtml);
  });
  document.querySelectorAll('[data-i18n-placeholder]').forEach(el => {
    el.placeholder = t(el.dataset.i18nPlaceholder);
  });

  const langBtn = document.getElementById('lang-btn');
  if (langBtn) langBtn.textContent = t('lang_toggle');
}

// ─────────────────────────────────────────────────────────────────────────────
const form        = document.getElementById('form');
const btn         = document.getElementById('start-btn');
const progressEl  = document.getElementById('progress');
const logEl       = document.getElementById('log');
const doneBanner  = document.getElementById('done-banner');
const errBanner   = document.getElementById('error-banner');
const statusBadge = document.getElementById('status-badge');

function classify(msg) {
  if (msg.includes('[DONE]'))        return 'l-done';
  if (msg.includes('[ERROR]'))       return 'l-error';
  if (msg.includes('BLOCKED'))       return 'l-blocked';
  if (msg.includes('SKIPPED'))       return 'l-skipped';
  if (msg.includes('FAILED'))        return 'l-failed';
  if (msg.includes('RATE LIMITED'))  return 'l-ratelim';
  return 'l-info';
}

function appendLog(msg) {
  const line = document.createElement('div');
  line.className = classify(msg);
  line.textContent = msg;
  logEl.appendChild(line);
  logEl.scrollTop = logEl.scrollHeight;
}

// Poll /poll/<jobId>?cursor=N every 500 ms.
// This works through every reverse proxy (HF Spaces, Cloudflare, Render, etc.)
// because it is plain JSON — no persistent connection, no buffering issues.
function startPolling(jobId) {
  let cursor = 0;
  let hasError = false;

  async function tick() {
    let data;
    try {
      const res = await fetch('/poll/' + jobId + '?cursor=' + cursor);
      data = await res.json();
    } catch {
      // Network blip — retry in 1 s
      setTimeout(tick, 1000);
      return;
    }

    for (const msg of data.messages) {
      if (msg.type === 'log') {
        appendLog(msg.msg);
      } else if (msg.type === 'error') {
        hasError = true;
        appendLog('[ERROR] ' + msg.msg);
        errBanner.textContent = '❌ ' + msg.msg;
        errBanner.style.display = 'block';
        statusBadge.textContent = t('status_error');
      }
    }
    cursor = data.cursor;

    if (data.done) {
      if (!hasError) {
        const doneLines = [...logEl.querySelectorAll('.l-done')];
        const doneText = doneLines.length ? doneLines[doneLines.length - 1].textContent : 'Finished.';
        doneBanner.textContent = '✅ ' + doneText;
        doneBanner.style.display = 'block';
        statusBadge.textContent = t('status_done');
      }
      btn.disabled = false;
      btn.textContent = hasError ? t('btn_try_again') : t('btn_run_again');
      return; // stop polling
    }

    setTimeout(tick, 500);
  }

  tick();
}

form.addEventListener('submit', async (e) => {
  e.preventDefault();
  btn.disabled = true;
  btn.textContent = t('btn_running');
  logEl.innerHTML = '';
  doneBanner.style.display = 'none';
  errBanner.style.display  = 'none';
  progressEl.style.display = 'block';
  statusBadge.textContent  = t('status_running');

  const data = new FormData(form);
  let res;
  try {
    res = await fetch('/start', { method: 'POST', body: data });
  } catch {
    errBanner.textContent = '❌ Could not reach the server.';
    errBanner.style.display = 'block';
    btn.disabled = false; btn.textContent = t('btn_try_again');
    return;
  }

  const json = await res.json();
  if (json.error) {
    errBanner.textContent = '❌ ' + json.error;
    errBanner.style.display = 'block';
    statusBadge.textContent = t('status_error');
    btn.disabled = false; btn.textContent = t('btn_try_again');
    return;
  }

  startPolling(json.job_id);
});

// ── Language toggle ───────────────────────────────────────────────────────────
document.getElementById('lang-btn').addEventListener('click', () => {
  applyLang(currentLang === 'en' ? 'fa' : 'en');
});

// Apply saved or default language on load
applyLang(currentLang);
