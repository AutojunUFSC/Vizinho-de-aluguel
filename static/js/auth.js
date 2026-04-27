const TOKEN_KEY    = 'vda_token';
const USER_TYPE_KEY = 'vda_user_type';

function getAuthHeaders() {
    const token = localStorage.getItem(TOKEN_KEY);
    if (!token) return {};
    return { 'Authorization': 'Bearer ' + token };
}

function logout() {
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(USER_TYPE_KEY);
    window.location.href = '/cadastro/';
}

function requireAuth() {
    if (!localStorage.getItem(TOKEN_KEY)) {
        window.location.href = '/cadastro/';
    }
}

function redirectIfLogged() {
    const token = localStorage.getItem(TOKEN_KEY);
    if (!token) return;
    redirectByUserType(localStorage.getItem(USER_TYPE_KEY));
}

function redirectByUserType(userType) {
    if (userType === 'CIDADAO') {
        window.location.href = '/usuario/';
    } else if (userType === 'MEI') {
        window.location.href = '/profissional/';
    } else {
        window.location.href = '/admin/';
    }
}

function escHtml(str) {
    return String(str)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#39;');
}

function parseApiErrors(data) {
    if (typeof data === 'string') return data;
    const messages = [];
    for (const key of Object.keys(data)) {
        const val   = data[key];
        const label = (key === 'non_field_errors' || key === 'detail') ? '' : key + ': ';
        if (Array.isArray(val)) {
            messages.push(label + val.join(' '));
        } else {
            messages.push(label + val);
        }
    }
    return messages.join('\n');
}
