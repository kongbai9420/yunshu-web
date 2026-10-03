/**
 * 云枢 (YunShu) - Web API Client & pywebview Bridge Polyfill
 * Translates window.pywebview.api calls into authenticated REST API fetch requests.
 * Conforms to Apple Design standards for immediate response and security gates.
 */

(function () {
  'use strict';

  // Global Auth helper
  window.Auth = {
    async getSession() {
      try {
        const token = localStorage.getItem('yunshu_token');
        const headers = { 'Accept': 'application/json' };
        if (token) {
          headers['Authorization'] = 'Bearer ' + token;
        }
        const res = await fetch('/api/auth/me', { headers });
        if (res.status === 401) {
          return null;
        }
        const data = await res.json();
        return data.status === 'success' ? data.user : null;
      } catch (e) {
        return null;
      }
    },

    async login(username, password) {
      try {
        const res = await fetch('/api/auth/login', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Accept': 'application/json'
          },
          body: JSON.stringify({ username, password })
        });
        const data = await res.json();
        if (res.ok && data.status === 'success') {
          if (data.token) {
            localStorage.setItem('yunshu_token', data.token);
          }
          return { success: true, user: data.user, message: data.message };
        } else {
          return { success: false, message: data.message || '登录失败，请检查账号密码' };
        }
      } catch (err) {
        return { success: false, message: '无法连接至服务器，请检查网络连接' };
      }
    },

    async logout() {
      try {
        await fetch('/api/auth/logout', {
          method: 'POST',
          headers: {
            'Authorization': 'Bearer ' + (localStorage.getItem('yunshu_token') || '')
          }
        });
      } catch (e) {
        console.warn('[Auth] Logout request error:', e);
      } finally {
        localStorage.removeItem('yunshu_token');
        window.location.href = '/login';
      }
    },

    async changePassword(oldPassword, newPassword) {
      return await this.updateAccount({ old_password: oldPassword, new_password: newPassword });
    },

    async updateAccount({ old_password, new_username, new_password, display_name }) {
      const token = localStorage.getItem('yunshu_token');
      const res = await fetch('/api/auth/update_account', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': token ? ('Bearer ' + token) : ''
        },
        body: JSON.stringify({
          old_password,
          new_username,
          new_password,
          display_name
        })
      });
      return await res.json();
    }
  };

  // Helper to execute API call
  async function callApiMethod(methodName, args) {
    const token = localStorage.getItem('yunshu_token');
    const headers = {
      'Content-Type': 'application/json',
      'Accept': 'application/json'
    };
    if (token) {
      headers['Authorization'] = 'Bearer ' + token;
    }

    try {
      const response = await fetch('/api/' + methodName, {
        method: 'POST',
        headers: headers,
        body: JSON.stringify({ args: args })
      });

      if (response.status === 401) {
        console.warn(`[API] 401 Unauthorized for ${methodName}. Redirecting to login.`);
        localStorage.removeItem('yunshu_token');
        if (!window.location.pathname.includes('login')) {
          window.location.href = '/login';
        }
        throw new Error('未登录或登录会话已过期，请重新登录');
      }

      if (!response.ok) {
        const errorText = await response.text();
        let errMsg = `API error (${response.status})`;
        try {
          const errObj = JSON.parse(errorText);
          if (errObj.message) errMsg = errObj.message;
        } catch (_) {}
        throw new Error(errMsg);
      }

      const json = await response.json();
      return json;
    } catch (error) {
      console.error(`[API] Error calling ${methodName}:`, error);
      throw error;
    }
  }

  // Create Proxy for window.pywebview.api
  const apiProxy = new Proxy({}, {
    get(target, prop) {
      if (typeof prop !== 'string') return undefined;
      // Polyfill desktop window controls as smooth no-ops in web mode
      if (['minimize_window', 'toggle_maximize', 'close_window', 'start_drag'].includes(prop)) {
        return async () => ({ status: 'ok', mode: 'web' });
      }
      return async function (...args) {
        return await callApiMethod(prop, args);
      };
    }
  });

  // Polyfill window.pywebview
  window.pywebview = {
    api: apiProxy
  };

  // Dispatch pywebviewready event when DOM is loaded
  function notifyReady() {
    window.dispatchEvent(new CustomEvent('pywebviewready'));
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', notifyReady);
  } else {
    setTimeout(notifyReady, 0);
  }
})();
