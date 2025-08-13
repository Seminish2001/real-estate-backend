(function() {
  function token() {
    return (window.getCsrfToken && window.getCsrfToken()) || '';
  }

  async function api(url, method = 'GET', data) {
    const opts = {
      method,
      credentials: 'include',
      headers: { 'X-CSRF-TOKEN': token() }
    };
    if (data) {
      opts.headers['Content-Type'] = 'application/json';
      opts.body = JSON.stringify(data);
    }
    const resp = await fetch(url, opts);
    if (!resp.ok) throw new Error('Request failed');
    return resp.status === 204 ? null : resp.json();
  }

  async function refreshUsers() {
    const users = await api('/admin/users');
    const tbody = document.querySelector('#users tbody');
    tbody.innerHTML = '';
    users.forEach(u => {
      tbody.insertAdjacentHTML('beforeend', `\n        <tr data-id="${u.id}">\n          <td>${u.email}</td>\n          <td>${u.user_type}</td>\n          <td>\n            <a href="#" class="text-primary edit-user" data-bs-toggle="modal" data-bs-target="#editUserModal" data-id="${u.id}"><i class="fas fa-edit"></i></a>\n            <a href="#" class="text-danger ms-2 delete-user" data-id="${u.id}"><i class="fas fa-trash-alt"></i></a>\n          </td>\n        </tr>`);
    });
  }

  async function refreshProperties() {
    const properties = await api('/admin/properties');
    const tbody = document.querySelector('#properties tbody');
    tbody.innerHTML = '';
    properties.forEach(p => {
      tbody.insertAdjacentHTML('beforeend', `\n        <tr data-id="${p.id}">\n          <td>${p.title}</td>\n          <td>${p.location || ''}</td>\n          <td>\n            <a href="#" class="text-primary edit-property" data-bs-toggle="modal" data-bs-target="#editPropertyModal" data-id="${p.id}"><i class="fas fa-edit"></i></a>\n            <a href="#" class="text-danger ms-2 delete-property" data-id="${p.id}"><i class="fas fa-trash-alt"></i></a>\n          </td>\n        </tr>`);
    });
  }

  async function refreshRequests() {
    const requests = await api('/admin/evaluation-requests');
    const tbody = document.querySelector('#requests tbody');
    tbody.innerHTML = '';
    requests.forEach(r => {
      tbody.insertAdjacentHTML('beforeend', `\n        <tr data-id="${r.id}">\n          <td>${r.user_id}</td>\n          <td>${r.location || ''}</td>\n          <td>${r.property_type || ''}</td>\n          <td>\n            <a href="#" class="text-primary edit-request" data-bs-toggle="modal" data-bs-target="#editRequestModal" data-id="${r.id}"><i class="fas fa-edit"></i></a>\n            <a href="#" class="text-danger ms-2 delete-request" data-id="${r.id}"><i class="fas fa-trash-alt"></i></a>\n          </td>\n        </tr>`);
    });
  }

  async function refreshAgents() {
    const agents = await api('/admin/agents');
    const tbody = document.querySelector('#agents tbody');
    tbody.innerHTML = '';
    agents.forEach(a => {
      tbody.insertAdjacentHTML('beforeend', `\n        <tr data-id="${a.id}">\n          <td>${a.name}</td>\n          <td>${a.email || ''}</td>\n          <td>\n            <a href="#" class="text-primary edit-agent" data-bs-toggle="modal" data-bs-target="#editAgentModal" data-id="${a.id}"><i class="fas fa-edit"></i></a>\n            <a href="#" class="text-danger ms-2 delete-agent" data-id="${a.id}"><i class="fas fa-trash-alt"></i></a>\n          </td>\n        </tr>`);
    });
  }

  document.addEventListener('DOMContentLoaded', () => {
    refreshUsers();
    refreshProperties();
    refreshRequests();
    refreshAgents();

    // --- User events ---
    document.querySelector('#createUserModal form').addEventListener('submit', async e => {
      e.preventDefault();
      const form = e.target;
      await api('/admin/users', 'POST', {
        name: form.name.value,
        email: form.email.value,
        user_type: form.user_type.value,
        password: form.password.value
      });
      bootstrap.Modal.getInstance(document.getElementById('createUserModal')).hide();
      form.reset();
      refreshUsers();
    });

    document.querySelector('#editUserModal form').addEventListener('submit', async e => {
      e.preventDefault();
      const form = e.target;
      const id = form.id.value;
      await api(`/admin/users/${id}`, 'PUT', {
        name: form.name.value,
        email: form.email.value,
        user_type: form.user_type.value
      });
      bootstrap.Modal.getInstance(document.getElementById('editUserModal')).hide();
      refreshUsers();
    });

    document.querySelector('#users tbody').addEventListener('click', async e => {
      const link = e.target.closest('a');
      if (!link) return;
      const id = link.dataset.id;
      if (link.classList.contains('delete-user')) {
        await api(`/admin/users/${id}`, 'DELETE');
        refreshUsers();
      } else if (link.classList.contains('edit-user')) {
        const u = await api(`/admin/users/${id}`);
        const form = document.querySelector('#editUserModal form');
        form.id.value = u.id;
        form.name.value = u.name || '';
        form.email.value = u.email || '';
        form.user_type.value = u.user_type || '';
      }
    });

    // --- Property events ---
    document.querySelector('#createPropertyModal form').addEventListener('submit', async e => {
      e.preventDefault();
      const form = e.target;
      await api('/admin/properties', 'POST', {
        title: form.title.value,
        location: form.location.value,
        price: parseFloat(form.price.value || '0')
      });
      bootstrap.Modal.getInstance(document.getElementById('createPropertyModal')).hide();
      form.reset();
      refreshProperties();
    });

    document.querySelector('#editPropertyModal form').addEventListener('submit', async e => {
      e.preventDefault();
      const form = e.target;
      const id = form.id.value;
      await api(`/admin/properties/${id}`, 'PUT', {
        title: form.title.value,
        location: form.location.value,
        price: parseFloat(form.price.value || '0')
      });
      bootstrap.Modal.getInstance(document.getElementById('editPropertyModal')).hide();
      refreshProperties();
    });

    document.querySelector('#properties tbody').addEventListener('click', async e => {
      const link = e.target.closest('a');
      if (!link) return;
      const id = link.dataset.id;
      if (link.classList.contains('delete-property')) {
        await api(`/admin/properties/${id}`, 'DELETE');
        refreshProperties();
      } else if (link.classList.contains('edit-property')) {
        const p = await api(`/admin/properties/${id}`);
        const form = document.querySelector('#editPropertyModal form');
        form.id.value = p.id;
        form.title.value = p.title || '';
        form.location.value = p.location || '';
        form.price.value = p.price || '';
      }
    });

    // --- Request events ---
    document.querySelector('#createRequestModal form').addEventListener('submit', async e => {
      e.preventDefault();
      const form = e.target;
      await api('/admin/evaluation-requests', 'POST', {
        user_id: parseInt(form.user_id.value, 10),
        location: form.location.value,
        property_type: form.property_type.value
      });
      bootstrap.Modal.getInstance(document.getElementById('createRequestModal')).hide();
      form.reset();
      refreshRequests();
    });

    document.querySelector('#editRequestModal form').addEventListener('submit', async e => {
      e.preventDefault();
      const form = e.target;
      const id = form.id.value;
      await api(`/admin/evaluation-requests/${id}`, 'PUT', {
        user_id: parseInt(form.user_id.value, 10),
        location: form.location.value,
        property_type: form.property_type.value
      });
      bootstrap.Modal.getInstance(document.getElementById('editRequestModal')).hide();
      refreshRequests();
    });

    document.querySelector('#requests tbody').addEventListener('click', async e => {
      const link = e.target.closest('a');
      if (!link) return;
      const id = link.dataset.id;
      if (link.classList.contains('delete-request')) {
        await api(`/admin/evaluation-requests/${id}`, 'DELETE');
        refreshRequests();
      } else if (link.classList.contains('edit-request')) {
        const r = await api(`/admin/evaluation-requests/${id}`);
        const form = document.querySelector('#editRequestModal form');
        form.id.value = r.id;
        form.user_id.value = r.user_id || '';
        form.location.value = r.location || '';
        form.property_type.value = r.property_type || '';
      }
    });

    // --- Agent events ---
    document.querySelector('#createAgentModal form').addEventListener('submit', async e => {
      e.preventDefault();
      const form = e.target;
      await api('/admin/agents', 'POST', {
        name: form.name.value,
        email: form.email.value,
        agency: form.agency.value
      });
      bootstrap.Modal.getInstance(document.getElementById('createAgentModal')).hide();
      form.reset();
      refreshAgents();
    });

    document.querySelector('#editAgentModal form').addEventListener('submit', async e => {
      e.preventDefault();
      const form = e.target;
      const id = form.id.value;
      await api(`/admin/agents/${id}`, 'PUT', {
        name: form.name.value,
        email: form.email.value,
        agency: form.agency.value
      });
      bootstrap.Modal.getInstance(document.getElementById('editAgentModal')).hide();
      refreshAgents();
    });

    document.querySelector('#agents tbody').addEventListener('click', async e => {
      const link = e.target.closest('a');
      if (!link) return;
      const id = link.dataset.id;
      if (link.classList.contains('delete-agent')) {
        await api(`/admin/agents/${id}`, 'DELETE');
        refreshAgents();
      } else if (link.classList.contains('edit-agent')) {
        const a = await api(`/admin/agents/${id}`);
        const form = document.querySelector('#editAgentModal form');
        form.id.value = a.id;
        form.name.value = a.name || '';
        form.email.value = a.email || '';
        form.agency.value = a.agency || '';
      }
    });
  });
})();
