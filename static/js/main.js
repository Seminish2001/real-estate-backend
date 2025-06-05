document.addEventListener('DOMContentLoaded', () => {
  if (window.AOS) {
    AOS.init({ duration: 1000, once: true });
  }
  window.addEventListener('scroll', () => {
    const header = document.querySelector('header');
    if (header) header.classList.toggle('scrolled', window.scrollY > 50);
  });
  checkLoginStatus();
});

async function checkLoginStatus() {
  try {
    const resp = await fetch('/api/auth/status', {
      method: 'GET',
      credentials: 'include',
      headers: { 'Content-Type': 'application/json' }
    });
    const data = await resp.json();
    if (resp.ok && data.authenticated) {
      const user = data.user;
      const link = document.getElementById('auth-link');
      const dashboard = `/dashboard/${user.user_type.replace('/', '-').toLowerCase()}`;
      link.innerHTML = `<a class="nav-link" href="${dashboard}"><i class="fas fa-user"></i> ${user.name}</a>`;
    }
  } catch (err) {
    console.error('Auth check failed:', err);
  }
}
