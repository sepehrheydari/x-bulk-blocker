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

  const es = new EventSource('/stream/' + json.job_id);

  es.onmessage = (ev) => {
    const msg = JSON.parse(ev.data);
    if (msg.type === 'log') {
      appendLog(msg.msg);
    } else if (msg.type === 'error') {
      appendLog('[ERROR] ' + msg.msg);
      errBanner.textContent = '❌ ' + msg.msg;
      errBanner.style.display = 'block';
      statusBadge.textContent = 'Error';
      es.close();
      btn.disabled = false; btn.textContent = '🚀 Try Again';
    } else if (msg.type === 'done') {
      const doneLines = [...logEl.querySelectorAll('.l-done')];
      const doneText = doneLines.length ? doneLines[doneLines.length - 1].textContent : 'Finished.';
      doneBanner.textContent = '✅ ' + doneText;
      doneBanner.style.display = 'block';
      statusBadge.textContent = 'Done';
      es.close();
      btn.disabled = false; btn.textContent = '🚀 Run Again';
    }
  };

  es.onerror = () => {
    appendLog('[ERROR] Connection lost.');
    errBanner.textContent = '❌ Connection to server lost.';
    errBanner.style.display = 'block';
    statusBadge.textContent = 'Error';
    es.close();
    btn.disabled = false; btn.textContent = '🚀 Try Again';
  };
});
