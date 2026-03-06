import subprocess
import os
import xml.etree.ElementTree as ET
from urllib.parse import urlparse

def get_private_token():
    """从 config.xml 读取 private_token"""
    try:
        tree = ET.parse('config.xml')
        root = tree.getroot()
        gitlab_node = root.find('gitlab')
        if gitlab_node is not None:
            token_node = gitlab_node.find('private_token')
            if token_node is not None and token_node.text:
                return token_node.text.strip()
    except Exception:
        pass
    return None

def run_command(command, directory, env=None):
    """运行命令，支持自定义环境变量"""
    try:
        if env is None:
            env = os.environ.copy()
            env['GIT_TERMINAL_PROMPT'] = '0'
        result = subprocess.run(command, cwd=directory, capture_output=True, text=True, check=True, shell=True, env=env)
        return True, result.stdout, result.stderr
    except subprocess.CalledProcessError as e:
        return False, e.stdout, e.stderr

def setup_git_url_with_auth(directory, private_token):
    """使用 private_token 配置 Git URL，避免弹出认证窗口"""
    # 获取当前 remote URL
    success, stdout, stderr = run_command(['git', 'remote', '-v'], directory)
    if not success:
        return False, stderr

    # 解析当前 URL
    lines = stdout.strip().split('\n')
    for line in lines:
        if 'origin' in line and '(fetch)' in line:
            url = line.split()[1]
            parsed = urlparse(url)

            # 构建带认证的 URL: https://oauth2:token@host/path
            if parsed.scheme == 'https':
                auth_url = f"{parsed.scheme}://oauth2:{private_token}@{parsed.netloc}{parsed.path}"
                # 更新 remote URL（临时）
                success, stdout, stderr = run_command(['git', 'remote', 'set-url', 'origin', auth_url], directory)
                if success:
                    return True, None
                else:
                    return False, stderr
    return False, "无法找到 origin remote URL"

def restore_git_url(directory, original_url):
    """恢复原始 Git URL"""
    run_command(['git', 'remote', 'set-url', 'origin', original_url], directory)

def create_branch(directory, target_branch, new_branch):
    outputs = []
    private_token = get_private_token()

    # 保存原始 URL 并设置带认证的 URL
    if private_token:
        success, stdout, stderr = run_command(['git', 'remote', '-v'], directory)
        original_url = None
        if success:
            lines = stdout.strip().split('\n')
            for line in lines:
                if 'origin' in line and '(fetch)' in line:
                    original_url = line.split()[1]
                    break

        if original_url:
            setup_result, error = setup_git_url_with_auth(directory, private_token)
            if setup_result:
                outputs.append('使用 config.xml 中的 private_token 进行认证')
            else:
                outputs.append(f'设置认证 URL 失败: {error}')

    # 1. Fetch
    outputs.append('Running git fetch...')
    success, stdout, stderr = run_command(['git', 'fetch', 'origin'], directory)
    outputs.append(f'STDOUT:\n{stdout}')
    outputs.append(f'STDERR:\n{stderr}')

    # 恢复原始 URL（为了安全）
    if private_token and original_url:
        restore_git_url(directory, original_url)
        outputs.append('已恢复原始 remote URL')

    if not success:
        outputs.append('Fetch failed!')
        return '\n'.join(outputs)
    outputs.append('Fetch successful!')

    # 2. Create branch
    new_branch_name = new_branch + '__from__' + target_branch.replace('/', '@')
    outputs.append(f'Creating branch {new_branch_name}...')
    branch_command = ['git', 'branch', new_branch_name, f'origin/{target_branch}']
    success, stdout, stderr = run_command(branch_command, directory)
    outputs.append(f'STDOUT:\n{stdout}')
    outputs.append(f'STDERR:\n{stderr}')
    if not success:
        outputs.append('Branch creation failed!')
        return '\n'.join(outputs)
    outputs.append('Branch created successfully!')

    set_branch_upstream_command = [
        'git',
        'branch',
        '--unset-upstream',
        new_branch_name
    ]
    # 设置upstream
    set_upstream_branch_result = subprocess.run(set_branch_upstream_command, cwd=directory, capture_output=True, text=True)

    # 输出 branch 命令的结果
    outputs.append("Branch STDOUT:")
    outputs.append(set_upstream_branch_result.stdout)
    outputs.append("Branch STDERR:")
    outputs.append(set_upstream_branch_result.stderr)

    # 检查 branch 命令是否成功
    if set_upstream_branch_result.returncode == 0:
        outputs.append("Branch 设置upstream成功!")
    else:
        outputs.append("Branch 设置upstream失败!")

    return '\n'.join(outputs)

def get_remote_branches(directory):
    # 同样使用认证获取远程分支
    private_token = get_private_token()
    original_url = None

    if private_token:
        success, stdout, stderr = run_command(['git', 'remote', '-v'], directory)
        if success:
            lines = stdout.strip().split('\n')
            for line in lines:
                if 'origin' in line and '(fetch)' in line:
                    original_url = line.split()[1]
                    break

        if original_url:
            setup_result, error = setup_git_url_with_auth(directory, private_token)

    success, stdout, stderr = run_command(['git', 'branch', '-r'], directory)

    # 恢复原始 URL
    if private_token and original_url:
        restore_git_url(directory, original_url)

    if not success:
        return [], f"Error loading remote branches:\n{stderr}"

    branches = stdout.strip().split('\n')
    # Clean up branch names (e.g., "  origin/master" -> "master")
    remote_branches = [b.strip().replace('origin/', '') for b in branches if 'HEAD' not in b]
    return remote_branches, "Remote branches loaded."

if __name__ == '__main__':
    # Example usage:
    directory = r'E:\lowcode\fe\tecq-lowcode-editor'
    target_branch = 'zhiming/advanced_responsive__from__SZ_dev'
    new_branch = 'zhiming/xx2'
    output = create_branch(directory, target_branch, new_branch)
    print(output)
