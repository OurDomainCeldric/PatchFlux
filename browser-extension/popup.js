document.addEventListener('DOMContentLoaded', async () => {
  const content = document.getElementById('content');
  try {
    const res = await fetch('https://func-omlorsnews-prod.azurewebsites.net/api/hot?limit=5');
    if (!res.ok) throw new Error('API Error');
    const data = await res.json();
    
    if (!data.items || data.items.length === 0) {
      content.innerHTML = '<div class="loading">Derzeit keine Top-News.</div>';
      return;
    }

    const ul = document.createElement('ul');
    ul.className = 'news-list';

    data.items.forEach(item => {
      const li = document.createElement('li');
      li.className = 'news-item';
      
      const a = document.createElement('a');
      a.href = item.url;
      a.target = '_blank';
      a.rel = 'noopener noreferrer';
      
      const badge = document.createElement('span');
      badge.className = 'hot-badge';
      badge.textContent = '🔥 TOP';

      const titleNode = document.createTextNode(' ' + item.title);
      
      const meta = document.createElement('div');
      meta.className = 'meta';
      const date = new Date(item.publishedAt).toLocaleDateString('de-DE');
      meta.textContent = `${item.sourceName} • ${date}`;

      a.appendChild(badge);
      a.appendChild(titleNode);
      li.appendChild(a);
      li.appendChild(meta);
      ul.appendChild(li);
    });

    content.innerHTML = '';
    content.appendChild(ul);
  } catch (err) {
    content.innerHTML = '<div class="loading">Fehler beim Laden.</div>';
    console.error(err);
  }
});
