# PWA 验证清单

部署到 GitHub Pages 后逐项打钩。任一不过先修该处。

## 1. 基础可用性

- [ ] 打开 `https://<user>.github.io/Flashinterview/app/index.html` 页面正常加载，第一张卡片正面显示题目
- [ ] F12 → Console 无红色错误；有 `[FlashInterview] SW registered:` 日志
- [ ] F12 → Application → Manifest 能看到内容，无红色 Error 行
- [ ] F12 → Application → Service Workers Status 显示 `Activated and is running`

## 2. Manifest 可安装性

DevTools → Application → Manifest 逐项核对：

- [ ] `id` = `flashinterview`
- [ ] `name` / `short_name` 非空
- [ ] `start_url` = `./index.html` 且可 200 加载
- [ ] `scope` = `./`
- [ ] `display` = `standalone`
- [ ] `lang` = `zh-CN`
- [ ] `theme_color` = `#0a0a0f`
- [ ] `background_color` = `#0a0a0f`
- [ ] `icons` 含 PNG 192 (any) + PNG 512 (any) + PNG 512 (maskable)
- [ ] 顶部出现 `Installability: ✅ No issues detected`

## 3. Service Worker 离线

- [ ] DevTools → Application → Service Workers → 勾 `Offline` → 刷新页面 → 页面正常加载、卡片可翻、可标记
- [ ] Application → Cache Storage → `flashinterview-v2` 列出 11 项（index.html / style.css / app.js / manifest.json / icon.svg / 4 个 PNG / cards.json / 根路径）
- [ ] Network 面板 → Offline 下刷新 → 看 cards.json → `(ServiceWorker)` 标记，Status 200，来自磁盘缓存
- [ ] 离线下卡片内容能翻（证明 cards.json 真的进了缓存）

## 4. 主屏安装 — Chrome / Edge（桌面 + Android）

- [ ] 地址栏右侧出现 ⊕ 安装图标（说明 Chrome 判定可安装）
- [ ] header 出现「安装到主屏」按钮（beforeinstallprompt 触发后显示）
- [ ] 点击按钮弹原生安装对话框
- [ ] 点「安装」→ 应用以独立窗口启动，无地址栏，标题栏色 = `#0a0a0f`
- [ ] 安装成功后 header 按钮自动隐藏（appinstalled 事件触发）

## 5. 主屏安装 — iOS Safari（真机或 Xcode 模拟器）

- [ ] 打开 PWA URL → 顶部出现琥珀色横幅「分享 → 添加到主屏幕，离线也能刷面经」
- [ ] 点 × 关闭横幅 → 本次会话不再出现
- [ ] Safari 分享 → 添加到主屏幕 → 预览图标 = apple-touch-icon-180.png，名称 = `FlashInterview`
- [ ] 点「添加」→ 主屏出现独立图标（非 Safari 截图）
- [ ] 点主屏图标启动 → 顶部无 Safari 地址栏/工具栏
- [ ] 开启飞行模式 → 点主屏图标 → 应用正常打开、可刷题（真正离线金标准）

## 部署步骤

1. 仓库 Settings → Pages → Source: branch `main` / `/root`
2. 等待 GitHub Actions 部署完成（约 1-2 分钟）
3. 访问 `https://<user>.github.io/Flashinterview/app/index.html`
4. 按上方清单逐项验证

## 已知限制

- `file://` 协议下双击 HTML 打开：SW 与 manifest 不会注册（设计如此，避免 CORS 错误）
- iOS Chrome（CriOS）会走 iOS 提示分支，但不支持 beforeinstallprompt
- 离线兜底页为空白 503（当前选择保持现状，未做 offline.html）
