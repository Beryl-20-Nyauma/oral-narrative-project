const API = (function() {
  const BASE_URL = '/api';
  
  let authToken = localStorage.getItem('auth_token') || null;
  let rateLimitRemaining = null;
  let rateLimitReset = null;

  function getToken() {
    return authToken;
  }

  function setToken(token) {
    authToken = token;
    if (token) {
      localStorage.setItem('auth_token', token);
    } else {
      localStorage.removeItem('auth_token');
    }
  }

  function clearToken() {
    authToken = null;
    localStorage.removeItem('auth_token');
  }

  function getHeaders(includeAuth = false) {
    const headers = {
      'Accept': 'application/json'
    };
    
    if (includeAuth && authToken) {
      headers['Authorization'] = `Bearer ${authToken}`;
    }
    
    return headers;
  }

  function updateRateLimit(response) {
    rateLimitRemaining = response.headers.get('x-ratelimit-remaining');
    rateLimitReset = response.headers.get('x-ratelimit-reset');
  }

  function getRateLimitInfo() {
    return {
      remaining: rateLimitRemaining ? parseInt(rateLimitRemaining) : null,
      reset: rateLimitReset ? parseInt(rateLimitReset) : null
    };
  }

  async function handleResponse(response) {
    updateRateLimit(response);
    
    if (response.status === 204) {
      return null;
    }
    
    const contentType = response.headers.get('content-type');
    const isJson = contentType && contentType.includes('application/json');
    
    if (!response.ok) {
      let errorMessage = `HTTP ${response.status}`;
      
      if (isJson) {
        const errorData = await response.json().catch(() => ({}));
        errorMessage = errorData.detail || errorData.message || errorMessage;
      }
      
      const error = new Error(errorMessage);
      error.status = response.status;
      error.response = response;
      
      if (response.status === 401) {
        clearToken();
        window.dispatchEvent(new CustomEvent('api:unauthorized', { detail: error }));
      }
      
      if (response.status === 429) {
        window.dispatchEvent(new CustomEvent('api:ratelimited', { 
          detail: { 
            error, 
            resetTime: rateLimitReset 
          } 
        }));
      }
      
      throw error;
    }
    
    if (isJson) {
      return response.json();
    }
    
    return response.text();
  }

  async function request(method, endpoint, options = {}) {
    const {
      params = {},
      body = null,
      requireAuth = false,
      headers = {}
    } = options;
    
    let url = `${BASE_URL}${endpoint}`;
    
    const queryParams = new URLSearchParams();
    Object.entries(params).forEach(([key, value]) => {
      if (value !== undefined && value !== null && value !== '') {
        queryParams.append(key, value);
      }
    });
    
    if (queryParams.toString()) {
      url += `?${queryParams.toString()}`;
    }
    
    const fetchOptions = {
      method,
      headers: { ...getHeaders(requireAuth), ...headers }
    };
    
    if (body) {
      if (body instanceof FormData) {
        delete fetchOptions.headers['Content-Type'];
        fetchOptions.body = body;
      } else {
        fetchOptions.headers['Content-Type'] = 'application/json';
        fetchOptions.body = JSON.stringify(body);
      }
    }
    
    try {
      const response = await fetch(url, fetchOptions);
      return handleResponse(response);
    } catch (error) {
      if (!error.status) {
        window.dispatchEvent(new CustomEvent('api:networkerror', { detail: error }));
      }
      throw error;
    }
  }

  function get(endpoint, params = {}, requireAuth = false) {
    return request('GET', endpoint, { params, requireAuth });
  }

  function post(endpoint, body = null, requireAuth = false) {
    return request('POST', endpoint, { body, requireAuth });
  }

  function put(endpoint, body = null, requireAuth = false) {
    return request('PUT', endpoint, { body, requireAuth });
  }

  function patch(endpoint, body = null, requireAuth = false) {
    return request('PATCH', endpoint, { body, requireAuth });
  }

  function del(endpoint, requireAuth = false) {
    return request('DELETE', endpoint, { requireAuth });
  }

  function upload(endpoint, formData, requireAuth = false) {
    return request('POST', endpoint, { 
      body: formData, 
      requireAuth,
      headers: {}
    });
  }

  const narratives = {
    list(params = {}) {
      return get('/narratives', params);
    },
    
    get(id) {
      return get(`/narratives/${id}`);
    },
    
    upload(formData) {
      return upload('/narratives/upload', formData, true);
    },
    
    status(id) {
      return get(`/narratives/${id}/status`);
    },
    
    emotionTimeline(id) {
      return get(`/narratives/${id}/emotion-timeline`);
    },
    
    narratorProfile(id) {
      return get(`/narratives/${id}/narrator-profile`);
    },
    
    retry(id) {
      return post(`/narratives/retry/${id}`);
    }
  };

  const narrators = {
    list(params = {}) {
      return get('/narrators', params);
    },
    
    get(id) {
      return get(`/narrators/${id}`);
    },
    
    narratives(narratorId) {
      return get(`/narrators/${narratorId}/narratives`);
    },
    
    register(formData) {
      return upload('/narrators/register', formData);
    },
    
    identify(formData) {
      return upload('/narrators/identify', formData);
    },
    
    rename(id, name) {
      return patch(`/narrators/${id}`, { name });
    },
    
    rebuildIndex() {
      return post('/narrators/rebuild-index');
    }
  };

  const auth = {
    register(email, password, fullName = null) {
      return post('/auth/register', {
        email,
        password,
        full_name: fullName
      });
    },
    
    async login(email, password) {
      const formData = new FormData();
      formData.append('username', email);
      formData.append('password', password);
      
      const response = await fetch(`${BASE_URL}/auth/login`, {
        method: 'POST',
        body: formData
      });
      
      const data = await handleResponse(response);
      
      if (data.access_token) {
        setToken(data.access_token);
      }
      
      return data;
    },
    
    me() {
      return get('/auth/me', {}, true);
    },
    
    logout() {
      clearToken();
      return post('/auth/logout');
    },
    
    isAuthenticated() {
      return !!authToken;
    },
    
    getToken,
    setToken,
    clearToken
  };

  const search = {
    query(q, field = 'all') {
      return get('/search', { q, field });
    }
  };

  const stats = {
    get() {
      return get('/stats');
    },
    
    benchmark() {
      return get('/stats/benchmark');
    },
    
    health() {
      return get('/stats/health');
    }
  };

  const queue = {
    status() {
      return get('/queue/status');
    },
    
    task(taskId) {
      return get(`/queue/tasks/${taskId}`);
    },
    
    retry(narrativeId) {
      return post(`/queue/retry/${narrativeId}`);
    }
  };

  return {
    request,
    get,
    post,
    put,
    patch,
    delete: del,
    upload,
    
    narratives,
    narrators,
    auth,
    search,
    stats,
    queue,
    
    getRateLimitInfo,
    getToken,
    setToken,
    clearToken
  };
})();

window.API = API;
