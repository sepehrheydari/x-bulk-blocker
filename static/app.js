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
        statusBadge.textContent = 'Error';
      }
    }
    cursor = data.cursor;

    if (data.done) {
      if (!hasError) {
        const doneLines = [...logEl.querySelectorAll('.l-done')];
        const doneText = doneLines.length ? doneLines[doneLines.length - 1].textContent : 'Finished.';
        doneBanner.textContent = '✅ ' + doneText;
        doneBanner.style.display = 'block';
        statusBadge.textContent = 'Done';
      }
      btn.disabled = false;
      btn.textContent = hasError ? '🚀 Try Again' : '🚀 Run Again';
      return; // stop polling
    }

    setTimeout(tick, 500);
  }

  tick();
}

form.addEventListener('submit', async (e) => {
  e.preventDefault();
  btn.disabled = true;
  btn.textContent = '⏳ Running…';
  logEl.innerHTML = '';
  doneBanner.style.display = 'none';
  errBanner.style.display  = 'none';
  progressEl.style.display = 'block';
  statusBadge.textContent  = 'Running…';

  const data = new FormData(form);
  let res;
  try {
    res = await fetch('/start', { method: 'POST', body: data });
  } catch {
    errBanner.textContent = '❌ Could not reach the server.';
    errBanner.style.display = 'block';
    btn.disabled = false; btn.textContent = '🚀 Try Again';
    return;
  }

  const json = await res.json();
  if (json.error) {
    errBanner.textContent = '❌ ' + json.error;
    errBanner.style.display = 'block';
    statusBadge.textContent = 'Error';
    btn.disabled = false; btn.textContent = '🚀 Try Again';
    return;
  }

  startPolling(json.job_id);
});
