const Auth = (function() {
  let currentUser = null;
  let isLoading = false;

  function isLoggedIn() {
    return API.auth.isAuthenticated();
  }

  function isAdmin() {
    return currentUser && currentUser.is_admin === true;
  }

  function getUser() {
    return currentUser;
  }

  async function fetchCurrentUser() {
    if (!isLoggedIn()) {
      currentUser = null;
      return null;
    }

    try {
      currentUser = await API.auth.me();
      updateUI();
      return currentUser;
    } catch (error) {
      console.error('Failed to fetch current user:', error);
      if (error.status === 401) {
        logout();
      }
      return null;
    }
  }

  async function login(email, password) {
    if (isLoading) return null;
    isLoading = true;

    try {
      const response = await API.auth.login(email, password);
      currentUser = response.user;
      updateUI();
      closeModal('loginModal');
      showNotification('Welcome back!', 'success');
      return response;
    } catch (error) {
      console.error('Login failed:', error);
      showLoginError(error.message);
      throw error;
    } finally {
      isLoading = false;
    }
  }

  async function register(email, password, fullName) {
    if (isLoading) return null;
    isLoading = true;

    try {
      const response = await API.auth.register(email, password, fullName);
      API.setToken(response.access_token);
      currentUser = response.user;
      updateUI();
      closeModal('registerModal');
      showNotification('Account created! Welcome!', 'success');
      return response;
    } catch (error) {
      console.error('Registration failed:', error);
      showRegisterError(error.message);
      throw error;
    } finally {
      isLoading = false;
    }
  }

  async function logout() {
    try {
      await API.auth.logout();
    } catch (error) {
      console.error('Logout error:', error);
    }
    
    currentUser = null;
    API.clearToken();
    updateUI();
    showNotification('Logged out successfully', 'info');
  }

  function showLoginError(message) {
    const errorEl = document.getElementById('loginError');
    if (errorEl) {
      errorEl.textContent = message;
      errorEl.style.display = 'block';
    }
  }

  function showRegisterError(message) {
    const errorEl = document.getElementById('registerError');
    if (errorEl) {
      errorEl.textContent = message;
      errorEl.style.display = 'block';
    }
  }

  function clearErrors() {
    const loginError = document.getElementById('loginError');
    const registerError = document.getElementById('registerError');
    if (loginError) loginError.style.display = 'none';
    if (registerError) registerError.style.display = 'none';
  }

  function showNotification(message, type = 'info') {
    let container = document.getElementById('notification-container');
    if (!container) {
      container = document.createElement('div');
      container.id = 'notification-container';
      container.style.cssText = 'position:fixed;top:20px;right:20px;z-index:10000;display:flex;flex-direction:column;gap:10px;';
      document.body.appendChild(container);
    }

    const notification = document.createElement('div');
    const bgColor = type === 'success' ? '#4a6741' : type === 'error' ? '#b54e2a' : '#8a7b6a';
    notification.style.cssText = `
      background:${bgColor};color:white;padding:12px 20px;border-radius:4px;
      font-family:'DM Mono',monospace;font-size:0.8rem;box-shadow:0 4px 12px rgba(0,0,0,0.15);
      animation:slideIn 0.3s ease;
    `;
    notification.textContent = message;
    
    container.appendChild(notification);
    
    setTimeout(() => {
      notification.style.animation = 'slideOut 0.3s ease';
      setTimeout(() => notification.remove(), 300);
    }, 3000);
  }

  function updateUI() {
    const navLinks = document.querySelector('.nav-links');
    if (!navLinks) return;

    let authContainer = document.getElementById('auth-container');
    
    const adminLinks = document.querySelectorAll('.admin-only, a[href="admin.html"]');
    adminLinks.forEach(link => {
      const parentLi = link.closest('li') || link;
      parentLi.style.display = isAdmin() ? '' : 'none';
    });
    
    updateAuthGatedElements();
    
    if (isLoggedIn() && currentUser) {
      if (!authContainer) {
        authContainer = document.createElement('li');
        authContainer.id = 'auth-container';
        navLinks.appendChild(authContainer);
      }
      
      authContainer.innerHTML = `
        <div class="user-menu">
          <button class="user-menu-toggle" onclick="toggleUserDropdown()">
            <span class="user-avatar">${currentUser.full_name ? currentUser.full_name[0].toUpperCase() : currentUser.email[0].toUpperCase()}</span>
            <span class="user-name">${currentUser.full_name || currentUser.email.split('@')[0]}</span>
          </button>
          <div class="user-dropdown" id="userDropdown">
            <div class="dropdown-header">
              <div class="dropdown-email">${currentUser.email}</div>
              ${currentUser.is_admin ? '<div class="dropdown-badge">Admin</div>' : ''}
            </div>
            <a href="#upload" onclick="closeUserDropdown()">Record Narrative</a>
            <a href="#" onclick="showMyNarratives(); closeUserDropdown(); return false;">My Narratives</a>
            <button onclick="Auth.logout(); closeUserDropdown();">Logout</button>
          </div>
        </div>
      `;
    } else {
      if (!authContainer) {
        authContainer = document.createElement('li');
        authContainer.id = 'auth-container';
        navLinks.appendChild(authContainer);
      }
      
      authContainer.innerHTML = `
        <button class="nav-btn btn-login" onclick="openLoginModal()">Login</button>
      `;
    }
  }

  function updateAuthGatedElements() {
    const uploadSection = document.getElementById('upload');
    const registerSection = document.getElementById('register-narrator');
    
    if (uploadSection) {
      const uploadForm = document.getElementById('upload-form-wrap');
      const uploadAuthPrompt = document.getElementById('upload-auth-prompt');
      
      if (isLoggedIn()) {
        if (uploadForm) uploadForm.style.display = 'block';
        if (uploadAuthPrompt) uploadAuthPrompt.remove();
      } else {
        if (uploadForm) uploadForm.style.display = 'none';
        if (!uploadAuthPrompt && uploadSection.querySelector('.section-header')) {
          const prompt = document.createElement('div');
          prompt.id = 'upload-auth-prompt';
          prompt.className = 'auth-prompt';
          prompt.innerHTML = `
            <div class="auth-prompt-content">
              <div class="auth-prompt-icon">🔐</div>
              <h3>Sign in to Analyze Videos</h3>
              <p>Create an account or sign in to upload and analyze oral narratives.</p>
              <div class="auth-prompt-actions">
                <button class="btn-primary" onclick="openLoginModal()">Login</button>
                <button class="btn-secondary" onclick="openRegisterModal()">Create Account</button>
              </div>
            </div>
          `;
          uploadSection.appendChild(prompt);
        }
      }
    }
    
    if (registerSection) {
      const registerForm = document.querySelector('.register-form');
      const registerAuthPrompt = document.getElementById('register-auth-prompt');
      
      if (isLoggedIn()) {
        if (registerForm) registerForm.style.display = 'block';
        if (registerAuthPrompt) registerAuthPrompt.remove();
      } else {
        if (registerForm) registerForm.style.display = 'none';
        if (!registerAuthPrompt && registerSection.querySelector('.section-header')) {
          const prompt = document.createElement('div');
          prompt.id = 'register-auth-prompt';
          prompt.className = 'auth-prompt';
          prompt.innerHTML = `
            <div class="auth-prompt-content">
              <div class="auth-prompt-icon">🔐</div>
              <h3>Sign in to Register Narrators</h3>
              <p>Create an account or sign in to register narrators and analyze videos.</p>
              <div class="auth-prompt-actions">
                <button class="btn-primary" onclick="openLoginModal()">Login</button>
                <button class="btn-secondary" onclick="openRegisterModal()">Create Account</button>
              </div>
            </div>
          `;
          registerSection.appendChild(prompt);
        }
      }
    }
  }
    
    const heroButtons = document.querySelectorAll('.hero-actions .btn-primary, .hero-actions .btn-secondary');
    if (heroButtons.length >= 2) {
      const [registerBtn, analyzeBtn] = heroButtons;
      
      if (!isLoggedIn()) {
        registerBtn.textContent = 'Sign in to Register';
        registerBtn.onclick = () => openLoginModal();
        analyzeBtn.textContent = 'Sign in to Analyze';
        analyzeBtn.onclick = () => openLoginModal();
      } else {
        registerBtn.textContent = 'Register Narrator';
        registerBtn.onclick = () => document.getElementById('register-narrator').scrollIntoView({behavior:'smooth'});
        analyzeBtn.textContent = 'Analyze a Video';
        analyzeBtn.onclick = () => document.getElementById('upload').scrollIntoView({behavior:'smooth'});
      }
    }
  }

  function requireAdmin() {
    if (!isLoggedIn()) {
      openLoginModal();
      showNotification('Please log in to access this page', 'info');
      return false;
    }
    
    if (!isAdmin()) {
      showNotification('Admin privileges required', 'error');
      window.location.href = 'index.html';
      return false;
    }
    
    return true;
  }

  function openModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) {
      modal.classList.add('open');
      clearErrors();
    }
  }

  function closeModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) {
      modal.classList.remove('open');
    }
  }

  function toggleUserDropdown() {
    const dropdown = document.getElementById('userDropdown');
    if (dropdown) {
      dropdown.classList.toggle('open');
    }
  }

  function closeUserDropdown() {
    const dropdown = document.getElementById('userDropdown');
    if (dropdown) {
      dropdown.classList.remove('open');
    }
  }

  async function requireAuth(redirect = true) {
    if (!isLoggedIn()) {
      if (redirect) {
        openLoginModal();
        showNotification('Please log in to continue', 'info');
      }
      return false;
    }

    if (!currentUser) {
      await fetchCurrentUser();
    }

    return isLoggedIn();
  }

  document.addEventListener('click', (e) => {
    const dropdown = document.getElementById('userDropdown');
    const toggle = document.querySelector('.user-menu-toggle');
    if (dropdown && dropdown.classList.contains('open')) {
      if (!dropdown.contains(e.target) && !toggle.contains(e.target)) {
        dropdown.classList.remove('open');
      }
    }
  });

  window.addEventListener('api:unauthorized', () => {
    currentUser = null;
    updateUI();
    showNotification('Session expired. Please log in again.', 'info');
    openLoginModal();
  });

  return {
    isLoggedIn,
    isAdmin,
    getUser,
    fetchCurrentUser,
    login,
    register,
    logout,
    requireAuth,
    requireAdmin,
    showNotification,
    openModal,
    closeModal,
    updateUI,
    updateAuthGatedElements
  };
})();

function openLoginModal() {
  Auth.openModal('loginModal');
}

function closeLoginModal() {
  Auth.closeModal('loginModal');
}

function openRegisterModal() {
  Auth.closeModal('loginModal');
  Auth.openModal('registerModal');
}

function closeRegisterModal() {
  Auth.closeModal('registerModal');
}

async function handleLogin(e) {
  e.preventDefault();
  const email = document.getElementById('loginEmail').value;
  const password = document.getElementById('loginPassword').value;
  
  try {
    await Auth.login(email, password);
    document.getElementById('loginForm').reset();
  } catch (error) {
    // Error already shown
  }
}

async function handleRegister(e) {
  e.preventDefault();
  const email = document.getElementById('registerEmail').value;
  const password = document.getElementById('registerPassword').value;
  const fullName = document.getElementById('registerName').value;
  
  try {
    await Auth.register(email, password, fullName);
    document.getElementById('registerForm').reset();
  } catch (error) {
    // Error already shown
  }
}

function toggleUserDropdown() {
  Auth.toggleUserDropdown();
}

function closeUserDropdown() {
  Auth.closeUserDropdown();
}

function showMyNarratives() {
  const myNarrativesFilter = document.getElementById('myNarrativesFilter');
  if (myNarrativesFilter) {
    myNarrativesFilter.checked = true;
    if (typeof filterNarratives === 'function') {
      filterNarratives();
    }
    document.getElementById('archive').scrollIntoView({behavior:'smooth'});
  } else {
    document.getElementById('archive').scrollIntoView({behavior:'smooth'});
  }
}

function checkAdminAccess() {
  if (!Auth.isLoggedIn() || !Auth.isAdmin()) {
    Auth.showNotification('Admin access required', 'error');
    window.location.href = 'index.html';
    return false;
  }
  return true;
}

window.Auth = Auth;
