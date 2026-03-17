const express = require('express');
const path = require('path');
const fs = require('fs');
const jwt = require('jsonwebtoken');
const cookieParser = require('cookie-parser');
const { authenticator } = require('otplib');

const app = express();
app.use(express.json());
app.use(express.urlencoded({ extended: true }));
app.use(cookieParser());

// Config
const PORT = process.env.PORT || 3001;
const JWT_SECRET = process.env.JWT_SECRET || require('crypto').randomBytes(32).toString('hex');
const SESSION_HOURS = parseInt(process.env.SESSION_HOURS || '24', 10);
const USERS_FILE = path.join(__dirname, 'users.json');

// Load users
function loadUsers() {
    try {
        return JSON.parse(fs.readFileSync(USERS_FILE, 'utf-8'));
    } catch {
        return {};
    }
}

// Auth middleware
function requireAuth(req, res, next) {
    const token = req.cookies?.auth_token;
    if (!token) return res.redirect('/login');

    try {
        const decoded = jwt.verify(token, JWT_SECRET);
        const users = loadUsers();
        if (!users[decoded.username]) return res.redirect('/login');
        req.user = decoded.username;
        next();
    } catch {
        res.clearCookie('auth_token');
        return res.redirect('/login');
    }
}

// Login page
app.get('/login', (req, res) => {
    const error = req.query.error;
    res.send(`<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Friend Graph — Login</title>
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
* { margin: 0; padding: 0; box-sizing: border-box; }
body {
    font-family: 'Inter', sans-serif;
    background: #0a0a0f;
    color: #e0e0e0;
    height: 100vh;
    display: flex;
    align-items: center;
    justify-content: center;
    overflow: hidden;
}
body::before {
    content: '';
    position: fixed;
    top: 0; left: 0; right: 0; bottom: 0;
    background: radial-gradient(ellipse at 30% 20%, rgba(124,108,240,0.08) 0%, transparent 50%),
                radial-gradient(ellipse at 70% 80%, rgba(224,108,170,0.06) 0%, transparent 50%);
    pointer-events: none;
}
.login-card {
    position: relative;
    background: rgba(14, 14, 22, 0.92);
    backdrop-filter: blur(24px);
    border: 1px solid rgba(255,255,255,0.08);
    border-radius: 16px;
    padding: 40px 36px;
    width: 100%;
    max-width: 380px;
    box-shadow: 0 16px 48px rgba(0,0,0,0.5);
}
h1 {
    font-size: 22px;
    font-weight: 600;
    background: linear-gradient(135deg, #7c6cf0, #e06caa);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    margin-bottom: 6px;
}
.subtitle {
    font-size: 13px;
    color: rgba(255,255,255,0.4);
    margin-bottom: 28px;
}
label {
    display: block;
    font-size: 12px;
    font-weight: 500;
    color: rgba(255,255,255,0.5);
    margin-bottom: 6px;
    text-transform: uppercase;
    letter-spacing: 0.5px;
}
input[type="text"] {
    width: 100%;
    padding: 12px 14px;
    background: rgba(255,255,255,0.06);
    border: 1px solid rgba(255,255,255,0.1);
    border-radius: 10px;
    color: #e0e0e0;
    font-family: 'Inter', monospace;
    font-size: 18px;
    letter-spacing: 8px;
    text-align: center;
    outline: none;
    transition: all 0.2s;
    margin-bottom: 8px;
}
input[type="text"]:focus {
    border-color: rgba(124,108,240,0.5);
    box-shadow: 0 0 0 3px rgba(124,108,240,0.12);
    background: rgba(255,255,255,0.1);
}
input[type="text"]::placeholder {
    letter-spacing: 4px;
    color: rgba(255,255,255,0.2);
}
button {
    width: 100%;
    padding: 12px;
    background: linear-gradient(135deg, #7c6cf0, #9c6cf0);
    border: none;
    border-radius: 10px;
    color: #fff;
    font-family: inherit;
    font-size: 14px;
    font-weight: 600;
    cursor: pointer;
    transition: all 0.2s;
    margin-top: 12px;
}
button:hover { transform: translateY(-1px); box-shadow: 0 4px 16px rgba(124,108,240,0.35); }
button:active { transform: translateY(0); }
.error {
    background: rgba(240,108,108,0.1);
    border: 1px solid rgba(240,108,108,0.2);
    border-radius: 8px;
    padding: 10px 12px;
    font-size: 12px;
    color: #f06c6c;
    margin-bottom: 16px;
}
.lock-icon {
    font-size: 32px;
    margin-bottom: 12px;
}
</style>
</head>
<body>
<div class="login-card">
    <div class="lock-icon">🔐</div>
    <h1>Friend Graph</h1>
    <p class="subtitle">Enter your credentials to view the graph</p>
    ${error ? '<div class="error">Invalid code. Please try again.</div>' : ''}
    <form method="POST" action="/login">
        <label>Authenticator Code</label>
        <input type="text" name="code" placeholder="000000" maxlength="6" pattern="[0-9]{6}" inputmode="numeric" autocomplete="one-time-code" required autofocus>
        <button type="submit">Verify & Access</button>
    </form>
</div>
</body>
</html>`);
});

// Login handler
app.post('/login', (req, res) => {
    const { code } = req.body;
    if (!code) return res.redirect('/login?error=1');

    const users = loadUsers();
    let authUsername = null;
    
    for (const [username, user] of Object.entries(users)) {
        if (authenticator.check(code, user.secret)) {
            authUsername = username;
            break;
        }
    }

    if (!authUsername) return res.redirect('/login?error=1');

    // Issue JWT
    const token = jwt.sign(
        { username: authUsername },
        JWT_SECRET,
        { expiresIn: `${SESSION_HOURS}h` }
    );

    res.cookie('auth_token', token, {
        httpOnly: true,
        secure: true,
        sameSite: 'strict',
        maxAge: SESSION_HOURS * 60 * 60 * 1000
    });

    res.redirect('/');
});

// Logout
app.get('/logout', (req, res) => {
    res.clearCookie('auth_token');
    res.redirect('/login');
});

// Protected graph page
app.get('/', requireAuth, (req, res) => {
    res.sendFile(path.join(__dirname, 'public', 'graph.html'));
});

// Protected static files
app.use(requireAuth, express.static(path.join(__dirname, 'public')));

app.listen(PORT, () => {
    const users = loadUsers();
    const count = Object.keys(users).length;
    console.log(`[friendlist] Server running at http://localhost:${PORT}`);
    console.log(`[friendlist] ${count} authorized user(s) loaded`);
    console.log(`[friendlist] Sessions valid for ${SESSION_HOURS} hours`);
});
