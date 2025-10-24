# GitHub Fork & Push Instructions

## Your commit is ready! ✅

**Commit ID**: 84dec0e
**Commit Message**: Fix critical Folia bugs in NotBounties v1.22.17-FOLIA-FIX

## Files Changed:
- FOLIA_FIX_SUMMARY.md (new file)
- pom.xml
- NotBounties.java
- PlayerData.java
- PlayerDataAdapter.java
- BetterTeamsClass.java

---

## Steps to Push to Your GitHub Fork:

### 1. Create a Fork on GitHub (if you haven't already)
Visit: https://github.com/No-Not-Jaden/NotBounties
Click the "Fork" button in the top right

### 2. Update Remote to Your Fork
Replace 'YOUR_GITHUB_USERNAME' with your actual GitHub username:

```bash
git remote set-url origin https://github.com/YOUR_GITHUB_USERNAME/NotBounties.git
```

For you, it would likely be:
```bash
git remote set-url origin https://github.com/TerribleTurtle/NotBounties.git
# OR
git remote set-url origin https://github.com/thech/NotBounties.git
```

### 3. Push to Your Fork
```bash
git push -u origin master
```

If you get authentication errors, you may need to:
- Use a Personal Access Token (recommended)
- Or use SSH instead of HTTPS

### 4. Create SSH Key (Alternative - Recommended)
```bash
# Generate SSH key
ssh-keygen -t ed25519 -C "your_email@example.com"

# Copy public key
cat ~/.ssh/id_ed25519.pub

# Add to GitHub: Settings > SSH and GPG keys > New SSH key
```

Then update remote to use SSH:
```bash
git remote set-url origin git@github.com:YOUR_GITHUB_USERNAME/NotBounties.git
git push -u origin master
```

---

## Quick Command Summary:

```bash
# Option 1: HTTPS (requires Personal Access Token)
git remote set-url origin https://github.com/YOUR_GITHUB_USERNAME/NotBounties.git
git push -u origin master

# Option 2: SSH (more secure, easier)
git remote set-url origin git@github.com:YOUR_GITHUB_USERNAME/NotBounties.git
git push -u origin master
```

---

## After Pushing:

1. Visit your fork on GitHub
2. You should see your commit "Fix critical Folia bugs in NotBounties v1.22.17-FOLIA-FIX"
3. Create a Pull Request to the original repo (optional)
4. Share your fork: https://github.com/YOUR_GITHUB_USERNAME/NotBounties

---

## Build Artifact Available:

The compiled JAR is ready at:
`target/NotBounties-1.22.17-FOLIA-FIX.jar` (3.8 MB)

MD5: 2989ca0f3db49a34d5b272ae8868d209

---

**Git User**: TerribleTurtle
**Git Email**: thech@users.noreply.github.com
**Branch**: master
**Commit**: 84dec0e
