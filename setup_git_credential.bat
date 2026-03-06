@echo off
echo 正在配置 Git 凭据管理器...
git config --global credential.helper manager-core
echo Git 凭据管理器配置完成！
echo.
echo 下次执行 Git 操作时会弹出登录窗口，输入一次后会自动保存凭据。
pause
