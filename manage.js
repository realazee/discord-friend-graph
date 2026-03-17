const fs = require('fs');
const path = require('path');
const { authenticator } = require('otplib');
const QRCode = require('qrcode');

const USERS_FILE = path.join(__dirname, 'users.json');

function loadUsers() {
    try {
        return JSON.parse(fs.readFileSync(USERS_FILE, 'utf-8'));
    } catch {
        return {};
    }
}

function saveUsers(users) {
    fs.writeFileSync(USERS_FILE, JSON.stringify(users, null, 2));
}

async function addUser(username) {
    if (!username) {
        console.error('Usage: node manage.js add <username>');
        process.exit(1);
    }

    const users = loadUsers();
    username = username.toLowerCase().trim();

    if (users[username]) {
        console.error(`User "${username}" already exists. Remove first to regenerate.`);
        process.exit(1);
    }

    const secret = authenticator.generateSecret();
    const otpauth = authenticator.keyuri(username, 'FriendGraph', secret);

    users[username] = {
        secret,
        createdAt: new Date().toISOString()
    };
    saveUsers(users);

    console.log(`\n✅ User "${username}" created!\n`);
    console.log(`Secret: ${secret}`);
    console.log(`\nOTP Auth URI: ${otpauth}`);
    console.log(`\nScan this QR code with your authenticator app:\n`);

    // Print QR to terminal
    const qrText = await QRCode.toString(otpauth, { type: 'terminal', small: true });
    console.log(qrText);

    console.log(`\nOr manually enter this secret in your app: ${secret}\n`);
}

function removeUser(username) {
    if (!username) {
        console.error('Usage: node manage.js remove <username>');
        process.exit(1);
    }

    const users = loadUsers();
    username = username.toLowerCase().trim();

    if (!users[username]) {
        console.error(`User "${username}" not found.`);
        process.exit(1);
    }

    delete users[username];
    saveUsers(users);
    console.log(`\n🗑️  User "${username}" removed.\n`);
}

function listUsers() {
    const users = loadUsers();
    const names = Object.keys(users);

    if (names.length === 0) {
        console.log('\nNo users configured. Run: node manage.js add <username>\n');
        return;
    }

    console.log(`\n📋 Authorized users (${names.length}):\n`);
    names.forEach(name => {
        console.log(`  • ${name} (added ${users[name].createdAt})`);
    });
    console.log('');
}

// CLI
const [,, action, ...args] = process.argv;

switch (action) {
    case 'add':
        addUser(args[0]).catch(console.error);
        break;
    case 'remove':
        removeUser(args[0]);
        break;
    case 'list':
        listUsers();
        break;
    default:
        console.log('Usage: node manage.js <add|remove|list> [username]');
}
