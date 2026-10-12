# save as replace_vpngate_block.py
import sys
from pathlib import Path

p = Path("vpngate.py")
if not p.exists():
    print("找不到 vpngate.py，请在仓库根目录运行此脚本。")
    sys.exit(1)

text = p.read_text(encoding="utf-8")

orig = (
    '    # 硬性失败: Worker 完全不可达 (没有任何一个请求拿到正常响应)\\n'
    "    if uniq and not success and len(worker_errors) == len(uniq):\\n"
    '        die("Worker 全部请求异常, 检测服务不可用 — 本次运行判定失败 (不生成空结果)")\\n'
)

replacement = (
    '    # 降级处理：Worker 不可达时记录状态并生成页面，不再把它判定为硬失败\\n'
    "    if uniq and not success and len(worker_errors) == len(uniq):\\n"
    '        log("CLOUDFLARE WORKER", "Worker 全部请求异常, 进入降级模式: 记录状态并生成占位页面, 不判定为硬失败")\\n'
    "        data = build_outputs(results, raw_count, sstp_count, source)\\n"
    '        data["stats"][\"worker_unavailable\"] = True\\n'
    '        data["stats"][\"warning\"] = \"worker_unavailable\"\\n'
    "        data_path, html_path, chains_path, hosts_path, sub_path = write_outputs(data)\\n"
    '        log("WEBSITE", f"生成 {os.path.relpath(data_path, REPO_DIR)}")\\n'
    '        log("WEBSITE", f"生成 {os.path.relpath(html_path, REPO_DIR)}")\\n'
    '        log("WEBSITE", f"生成 {os.path.relpath(chains_path, REPO_DIR)}")\\n'
    '        log("WEBSITE", f"生成 {os.path.relpath(hosts_path, REPO_DIR)}")\\n'
    '        log("WEBSITE", f"生成 {os.path.relpath(sub_path, REPO_DIR)}")\\n'
    '        log("WEBSITE", "已进入降级模式 (Worker 全部不可用)")\\n'
    "        return\\n"
)

if orig not in text:
    print("未在 vpngate.py 中找到预期的原始代码片段。请确认文件是否为原始版本或已经被改动。")
    sys.exit(2)

# backup
bak = p.with_suffix(".py.bak")
bak.write_text(text, encoding="utf-8")
print(f"已备份为 {bak}")

new_text = text.replace(orig, replacement, 1)
p.write_text(new_text, encoding="utf-8")
print("替换完成：已将硬性失败改为降级处理。")
