# GitHub 上传发布指南

本文档用于把当前项目完整整理并上传到 GitHub。

## 1) 本地检查（建议）

```bash
pytest -q
```

## 2) 创建远程仓库

在 GitHub 网页创建新仓库（例如 `stock-simulation-prediction-system`），不要勾选初始化 README（本地已有）。

## 3) 绑定远程并推送

将下面的 `<YOUR_GITHUB_USERNAME>` 与 `<YOUR_REPO_NAME>` 替换后执行：

```bash
git remote add origin https://github.com/<YOUR_GITHUB_USERNAME>/<YOUR_REPO_NAME>.git
git branch -M main
git push -u origin main
```

## 4) 如果使用 Token（HTTPS）

当 Git 提示账号密码时：
- Username 填 GitHub 用户名
- Password 填 GitHub Personal Access Token（PAT）

## 5) 如果你想保留当前分支名（非 main）

```bash
git remote add origin https://github.com/<YOUR_GITHUB_USERNAME>/<YOUR_REPO_NAME>.git
git push -u origin work
```

## 6) 推送后核对

- 确认仓库页面包含：
  - `stock_simulation.py`
  - `web_ui.py`
  - `ui/index.html`
  - `README.md`
  - `DEVELOPMENT_DOC.md`
  - `tests/`

## 7) 常见错误

- `remote origin already exists`：
  ```bash
  git remote set-url origin https://github.com/<YOUR_GITHUB_USERNAME>/<YOUR_REPO_NAME>.git
  ```
- `failed to push some refs`：先拉取或使用新仓库空仓推送。
- `Authentication failed`：检查 PAT 权限（至少 `repo`）。
