---
name: msmtp-unattended
description: Setup msmtp for 24/7 cron operation without user interaction
---

# msmtp for 24/7 Unattended Operation

Two approaches for cron jobs to send emails without you being logged in.

---

## Quick Decision

| Use Case | Approach |
|----------|----------|
| **You want it to just work 24/7** | Plaintext file (600 perms) |
| **Mac stays on & logged in** | Keychain (system integration) |
| **You need encrypted storage** | Keychain + unlock in cron |

---

## Approach 1: Plaintext File with OS Protection (Recommended)

### Setup (One-Time)

```bash
bash agentic-engineers/orchestration/scripts/setup-msmtp-unattended.sh
```

Interactive setup:
1. Enter SMTP host, user, password
2. Script stores in: `~/.msmtp-credentials` (plaintext, 600 permissions)
3. Updates `~/.msmtprc` to read password from file
4. Tests SMTP connection

### How It Works

```bash
# File: ~/.msmtp-credentials (plaintext, protected by OS)
SMTP_HOST=smtp.themessagingco.com.au
SMTP_USER=user@example.com
SMTP_PASS=your-app-password

# msmtp config uses this passwordeval:
passwordeval "grep '^SMTP_PASS=' ~/.msmtp-credentials | cut -d= -f2"

# When cron runs msmtp:
# 1. msmtp needs password
# 2. Calls: grep '^SMTP_PASS=' ~/.msmtp-credentials | cut -d= -f2
# 3. Returns password instantly (no encryption overhead)
# 4. Sends email
```

### Why Plaintext with 600 Permissions?

✅ **No prompts** — works 24/7 in cron without user interaction  
✅ **Fast** — instant password retrieval (no decryption)  
✅ **Reliable** — works when Mac is locked, asleep, or rebooted  
✅ **OS-protected** — 600 permissions enforce: only you can read (rwx------)  
✅ **Simple** — no encryption complexity or key management  

Security model: **Same as environment variables**, but file-based.

⚠️ If someone gains access to your account, they can read it (but they can already read env vars, SSH keys, etc.)

### Update Password

```bash
# Edit directly
nano ~/.msmtp-credentials
# Then change SMTP_PASS=...

# Or re-run setup
bash agentic-engineers/orchestration/scripts/setup-msmtp-unattended.sh
```

### Debug

```bash
# View stored password
cat ~/.msmtp-credentials

# Test password retrieval
grep '^SMTP_PASS=' ~/.msmtp-credentials | cut -d= -f2

# Test msmtp
echo "test" | msmtp -v -a ers recipient@example.com

# Check msmtp logs
tail -f ~/.msmtp.log
```

---

## Approach 2: Keychain + Auto-Unlock in Cron

If you prefer Keychain and your Mac is always on/logged in:

### Setup

Use the original interactive setup:

```bash
bash agentic-engineers/orchestration/scripts/setup-msmtp.sh
```

### Add to Crontab

Unlock Keychain before running queue processor:

```bash
# Edit crontab
crontab -e

# Add this line (replace PASSWORD with your actual macOS password):
*/5 * * * * security unlock-keychain -p YOUR_MACOS_PASSWORD /home/user/Library/Keychains/login.keychain-db && cd /home/user/git/ers/{service-name} && bash agentic-engineers/orchestration/scripts/process-log-queue.sh
```

### Pros & Cons

✅ Uses macOS Keychain (system integration)  
✅ Faster (Keychain already running)  
✅ Credentials in encrypted memory  

❌ Requires your macOS password in cron config  
❌ Fails if Mac sleeps or user locks screen  
❌ Less secure (password visible to `ps` when running)  
❌ Need to update cron if you change macOS password  

---

## Installing msmtp (Both Approaches)

```bash
brew install msmtp
```

Verify:

```bash
msmtp --version
```

---

## Full 24/7 Cron Setup

### 1. Install msmtp

```bash
brew install msmtp
```

### 2. Run unattended setup

```bash
bash agentic-engineers/orchestration/scripts/setup-msmtp-unattended.sh
```

Creates: `~/.msmtp-credentials` with SMTP_PASS=...

### 3. Add to crontab

```bash
crontab -e

# Add this line:
*/5 * * * * cd /home/user/git/ers/{service-name} && bash agentic-engineers/orchestration/scripts/process-log-queue.sh 2>&1
```

That's it. No password in cron, no prompts, no unlocking needed.

### 4. Verify setup

```bash
# Check crontab
crontab -l

# Check credentials file exists
ls -la ~/.msmtp-credentials
# Should be: -rw------- (600 permissions)

# Check config is updated
grep "passwordeval" ~/.msmtprc
```

### 5. Test

```bash
# Manually trigger queue processor (as if cron ran it)
bash agentic-engineers/orchestration/scripts/process-log-queue.sh

# Check logs
tail -f ~/.msmtp.log
tail -f agentic-engineers/data/logs/queue-processor-*.log
```

---

## Troubleshooting

### "command not found: msmtp" in cron

msmtp from Homebrew isn't in PATH by default for cron.

```bash
# Find msmtp
which msmtp
# Output: /usr/local/bin/msmtp (or /opt/homebrew/bin/msmtp on Apple Silicon)

# Test in cron environment
env -i /bin/bash -l -c "which msmtp"
```

If not found, msmtp isn't in cron's PATH. Options:
1. Use full path in queue processor script
2. Add to crontab: `PATH=/usr/local/bin:/opt/homebrew/bin:$PATH`

### "Permission denied" on credentials file

```bash
# Fix permissions
chmod 600 ~/.msmtp-credentials

# Verify
ls -la ~/.msmtp-credentials
# Should show: -rw------- (600)
```

### Email not sent but no error

```bash
# Check if cron ran
tail -f agentic-engineers/data/logs/queue-processor-*.log

# Check msmtp logs
tail -f ~/.msmtp.log

# Check if password file is readable
cat ~/.msmtp-credentials
# Should show: SMTP_PASS=...

# Test password retrieval
grep '^SMTP_PASS=' ~/.msmtp-credentials | cut -d= -f2
# Should output the password

# Manual test of msmtp
echo "test" | msmtp -v -a ers recipient@example.com
```

### "Authentication failed" from SMTP server

```bash
# Check stored password
grep '^SMTP_PASS=' ~/.msmtp-credentials | cut -d= -f2

# Verify it's the correct app-specific password
# For Gmail: https://myaccount.google.com/apppasswords
# For Office 365: Check app password settings

# Update password
nano ~/.msmtp-credentials
# Edit SMTP_PASS=... and save

# Or re-run setup
bash agentic-engineers/orchestration/scripts/setup-msmtp-unattended.sh
```

### "No such file or directory" error

```bash
# Check file exists
ls -la ~/.msmtp-credentials

# Check msmtp config path is correct
grep "passwordeval" ~/.msmtprc

# Should be: grep '^SMTP_PASS=' ~/.msmtp-credentials
# (using ~ which expands to home dir)
```

---

## Security Model

### Plaintext File with OS Protection

The credentials are stored plaintext, protected by OS file permissions (600):

```bash
-rw------- niall staff 256 Apr 25 11:30 .msmtp-credentials
↑↑↑
600 permissions = read+write for owner only
```

✓ Only you can read the file (OS enforces this)  
✓ Faster than encryption (no overhead)  
✓ Works 24/7 without prompts  
✓ Same security model as: SSH keys, env vars, .bashrc secrets  

⚠️ If someone compromises your account, they can read it  
⚠️ If you share your Mac (multi-user), use app-specific password  

### Best Practices

1. **Use app-specific passwords** (not your main password)
   - Gmail: [Create app password](https://myaccount.google.com/apppasswords)
   - Office 365: Create app password in account settings
   - Generic SMTP: Use temporary/non-main password

2. **Verify file permissions** (should be 600)
   ```bash
   ls -la ~/.msmtp-credentials
   # -rw------- (600)
   ```

3. **Don't commit to git**
   - Add to `.gitignore`: `~/.msmtp-credentials`
   - If accidentally committed, rotate password immediately

4. **Lock your Mac** when away
   - File is readable by your user session
   - Don't leave unlocked machine unattended

5. **Monitor SMTP logs**
   ```bash
   tail -f ~/.msmtp.log
   grep "authentication failed" ~/.msmtp.log
   ```

6. **Rotate credentials regularly**
   - Edit: `nano ~/.msmtp-credentials`
   - Or re-run: `bash setup-msmtp-unattended.sh`

---

## Commands Reference

```bash
# Install msmtp
brew install msmtp

# Setup (plaintext credentials with OS protection - recommended)
bash agentic-engineers/orchestration/scripts/setup-msmtp-unattended.sh

# Setup (Keychain - if you prefer)
bash agentic-engineers/orchestration/scripts/setup-msmtp.sh

# View stored password
cat ~/.msmtp-credentials

# Verify file permissions (should be 600)
ls -la ~/.msmtp-credentials

# Test password retrieval (what cron uses)
grep '^SMTP_PASS=' ~/.msmtp-credentials | cut -d= -f2

# Test msmtp
echo "test" | msmtp -a ers recipient@example.com

# Test with verbose output
echo "test" | msmtp -v -a ers recipient@example.com

# View msmtp config
cat ~/.msmtprc

# Check crontab
crontab -l

# Edit crontab
crontab -e

# Find msmtp path (for troubleshooting)
which msmtp
```

---

## Next Steps

1. **Install**: `brew install msmtp`
2. **Setup**: `bash agentic-engineers/orchestration/scripts/setup-msmtp-unattended.sh`
3. **Crontab**: `crontab -e` → add queue processor line
4. **Test**: `bash agentic-engineers/orchestration/scripts/process-log-queue.sh`
5. **Monitor**: `tail -f ~/.msmtp.log`

Questions? Check:
```bash
tail -f ~/.msmtp.log
tail -f agentic-engineers/data/logs/queue-processor-*.log
```
