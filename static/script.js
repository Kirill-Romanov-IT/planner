const form = document.getElementById('plannerForm');
const tasksEl = document.getElementById('tasks');
const startEl = document.getElementById('start');
const endEl = document.getElementById('end');
const msgEl = document.getElementById('message');
const counterEl = document.getElementById('taskCounter');
const clearBtn = document.getElementById('clearBtn');

function parseTasks(text){
  return text
    .split(/\r?\n/)
    .map(s => s.replace(/^[-—•\s]+/, '').trim())
    .filter(Boolean);
}

function plural(n, forms){
  const mod10 = n % 10, mod100 = n % 100;
  if (mod10 === 1 && mod100 !== 11) return forms[0];
  if (mod10 >= 2 && mod10 <= 4 && (mod100 < 12 || mod100 > 14)) return forms[1];
  return forms[2];
}

function updateTaskCounter(){
  const n = parseTasks(tasksEl.value).length;
  counterEl.textContent = n + ' ' + plural(n, ['задача','задачи','задач']);
}

function showMessage(type, text){
  msgEl.style.display = 'block';
  msgEl.className = 'alert ' + (type || '');
  msgEl.textContent = text;
}
function hideMessage(){ msgEl.style.display = 'none'; msgEl.textContent = ''; }

form.addEventListener('submit', async (e)=>{
  e.preventDefault();
  hideMessage();

  const tasks = parseTasks(tasksEl.value);
  const start = startEl.value;
  const end = endEl.value;

  if (!tasks.length){
    showMessage('warn', 'Добавьте хотя бы одну задачу.');
    return;
  }
  if (!start || !end){
    showMessage('warn', 'Укажите даты начала и окончания.');
    return;
  }

  const data = { tasks, start, end };

  try {
    const response = await fetch('/api/tasks', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data)
    });

    if (!response.ok) throw new Error(`Ошибка ${response.status}`);
    const result = await response.json();
    showMessage('ok', 'Задачи успешно отправлены на сервер!');
    console.log('Ответ сервера:', result);
  } catch (err) {
    console.error(err);
    showMessage('danger', 'Ошибка при отправке данных на сервер.');
  }
});

clearBtn.addEventListener('click', ()=>{
  tasksEl.value = '';
  updateTaskCounter();
  hideMessage();
});

tasksEl.addEventListener('input', updateTaskCounter);
updateTaskCounter();


const aiBtn = document.getElementById('aiBtn');

aiBtn.addEventListener('click', async ()=>{
  hideMessage();

  const tasks = parseTasks(tasksEl.value);
  const start = startEl.value;
  const end = endEl.value;

  if (!tasks.length){
    showMessage('warn', 'Добавьте хотя бы одну задачу.');
    return;
  }
  if (!start || !end){
    showMessage('warn', 'Укажите даты начала и окончания.');
    return;
  }

  const data = { tasks, start, end };

  showMessage('', '⏳ Генерация AI-плана... Подождите 10–20 секунд...');

  try {
    const response = await fetch('/api/generate-plan', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data)
    });

    if (!response.ok) throw new Error(`Ошибка ${response.status}`);
    const result = await response.json();

    if (result.status === 'ok') {
      const link = document.createElement('a');
      link.href = `/data/${result.file}`;
      link.textContent = 'Открыть сгенерированный Markdown-план';
      link.target = '_blank';
      showMessage('ok', '✅ План успешно создан. ');
      msgEl.appendChild(document.createElement('br'));
      msgEl.appendChild(link);
    } else {
      showMessage('danger', 'Ошибка при генерации AI-плана.');
    }

  } catch (err) {
    console.error(err);
    showMessage('danger', 'Ошибка при обращении к серверу AI.');
  }
});
