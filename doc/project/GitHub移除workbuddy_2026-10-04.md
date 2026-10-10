# GitHub 移除 .workbuddy

日期：2026-10-04。目的：按用户要求，从 GitHub 仓库当前版本移除 `.workbuddy/`，保留本地开发资料。

改动：根 `.gitignore` 启用 `/.workbuddy/`，对该目录执行 `git rm -r --cached -- .workbuddy`，取消跟踪 143 个文件；不删除本地目录或文件。提交范围限定为该目录的取消跟踪、`.gitignore` 和本文。

复现命令：

```powershell
git rm -r --cached -- .workbuddy
git check-ignore -v -- .workbuddy/memory/MEMORY.md
git ls-files -- .workbuddy
git diff --cached --name-status
```

实测效果：取消跟踪后，`git ls-files -- .workbuddy` 无输出；原提交中 143 个路径在本地均仍存在；代表路径匹配 `/.workbuddy/` 规则。执行前远端 master 与本地 HEAD 均为 `4735ab5921db730bfb0004eba4e75a26c30f980f`；没有合并远端差异的需要。

未覆盖范围：本次是版本管理调整，不修改 RTL/IP/镜像，不重跑仿真或上板。历史文档中的 `.workbuddy/` 引用保留为旧实验记录，新的克隆不会包含这些目录内容。历史提交仍保留原文件，本次不重写 Git 历史。此前未提交的仓库完整性核对文档不纳入本次提交。
