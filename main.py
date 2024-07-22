import hashlib
import os
import random
import re
import string
import subprocess
import sys
import time
from datetime import datetime

import httpx
import requests
from termcolor import colored


def cmd(command):
    result = subprocess.run(command,
                            shell=True,
                            capture_output=True,
                            text=True)
    return result.stdout.strip()


def setup_environment(app):
    print(colored("请稍后，正在配置环境...", 'light_cyan'))
    os.remove('warp.conf') if os.path.exists('warp.conf') else None
    os.remove('wireguard.conf') if os.path.exists('wireguard.conf') else None
    os.remove('singbox.json') if os.path.exists('singbox.json') else None
    os.remove('wgcf-account.toml') if os.path.exists(
        'wgcf-account.toml') else None
    os.remove('wgcf-profile.conf') if os.path.exists(
        'wgcf-profile.conf') else None
    if app == '1':
        os.chmod('./warp-go', 0o755)
        os.chmod('./warp-api', 0o755)
    elif app == '2':
        os.chmod('./wgcf', 0o755)
        os.system('echo | ./wgcf register')
        os.chmod('./wgcf-account.toml', 0o755)


def handle_warp_plus_key(number):
    base_keys_response = requests.get(
        'https://gitlab.com/Misaka-blog/warp-script/-/raw/main/files/24pbgen/base_keys'
    )
    base_keys_content = base_keys_response.content.decode('UTF8')
    base_keys = base_keys_content.split(',')
    generated_keys = []
    generated_count = 0

    while generated_count < number:
        generated_count += 1
        print(f"正在生成第 {generated_count} 个,共 {number} 个...")
        try:
            headers = {
                "CF-Client-Version": "a-6.11-2223",
                "Host": "api.cloudflareclient.com",
                "Connection": "Keep-Alive",
                "Accept-Encoding": "gzip",
                "User-Agent": "okhttp/3.12.1",
            }

            with httpx.Client(
                    base_url="https://api.cloudflareclient.com/v0a2223",
                    headers=headers,
                    timeout=30.0) as client:

                response = client.post("/reg")
                main_account_id = response.json()["id"]
                main_account_license = response.json()["account"]["license"]
                main_account_token = response.json()["token"]

                response = client.post("/reg")
                referrer_account_id = response.json()["id"]
                referrer_account_token = response.json()["token"]

                main_account_auth_header = {
                    "Authorization": f"Bearer {main_account_token}"
                }
                referrer_account_auth_header = {
                    "Authorization": f"Bearer {referrer_account_token}"
                }
                main_account_post_headers = {
                    "Content-Type": "application/json; charset=UTF-8",
                    "Authorization": f"Bearer {main_account_token}",
                }

                referrer_payload = {"referrer": f"{referrer_account_id}"}
                client.patch(f"/reg/{main_account_id}",
                             headers=main_account_post_headers,
                             json=referrer_payload)

                client.delete(f"/reg/{referrer_account_id}",
                              headers=referrer_account_auth_header)

                random_base_key = random.choice(base_keys)

                assign_license_payload = {"license": f"{random_base_key}"}
                client.put(f"/reg/{main_account_id}/account",
                           headers=main_account_post_headers,
                           json=assign_license_payload)

                restore_license_payload = {
                    "license": f"{main_account_license}"
                }
                client.put(f"/reg/{main_account_id}/account",
                           headers=main_account_post_headers,
                           json=restore_license_payload)

                response = client.get(f"/reg/{main_account_id}/account",
                                      headers=main_account_auth_header)
                account_type = response.json()["account_type"]
                referral_count = response.json()["referral_count"]
                final_license = response.json()["license"]

                client.delete(f"/reg/{main_account_id}",
                              headers=main_account_auth_header)
                generated_keys.append(final_license)
                print(
                    f"密钥: {final_license}\n类型: {account_type}\n流量: {referral_count}GB\n已经完成第 {generated_count} 个,共 {number} 个"
                )
                print("")
        except Exception as e:
            print(f"生成第 {generated_count} 个密钥时遇到错误：\n{e}")
            print("")
            time.sleep(15)
            if generated_count % 2 == 0:
                time.sleep(30)
    print("")
    return generated_keys


def handle_warp_free(app):
    if app == "2":
        os.system("./wgcf generate")
    else:
        result_output = cmd('./warp-api')
        device_id = re.search(r'device_id: (\S+)', result_output).group(1)
        private_key = re.search(r'private_key: (\S+)', result_output).group(1)
        warp_token = re.search(r'token: (\S+)', result_output).group(1)

        with open('warp.conf', 'w') as file:
            file.write(f"""
[Account]
Device = {device_id}
PrivateKey = {private_key}
Token = {warp_token}
Type = free
Name = WARP
MTU = 1280

[Peer]
PublicKey = bmXOC+F1FxEMF9dyiK2H5/1SUtzH0JuVo51h2wPfgyo=
Endpoint = 162.159.192.8:0
Endpoint6 = [2606:4700:d0::a29f:c008]:0
KeepAlive = 30""")


def handle_warp_plus(app):
    while True:
        warpkey = input("请输入 WARP+ 账户 许可证密钥 (26个字符) 或输入 'exit' 退出: ").strip()
        if warpkey.lower() == 'exit':
            exit()
        if re.match(r'^[A-Z0-9a-z]{8}-[A-Z0-9a-z]{8}-[A-Z0-9a-z]{8}$',
                    warpkey):
            break
        print(colored("WARP 账户许可证密钥格式输入错误，请重新输入！", 'light_blue'))

    device_name = input("请输入自定义设备名，空则使用随机字符: ").strip()
    if not device_name:
        device_name = hashlib.md5(str(
            datetime.now().timestamp()).encode()).hexdigest()[:6]

    if app == "2":
        with open('wgcf-account.toml', 'r') as file:
            content = file.read()

        content = re.sub(r'license_key.*', f'license_key = "{warpkey}"',
                         content)

        with open('wgcf-account.toml', 'w') as file:
            file.write(content)

        cmd('./wgcf update --name' + re.sub(r'\s+', '_', device_name))
        os.system("./wgcf generate")
    else:
        result_output = cmd('./warp-api')
        device_id = re.search(r'device_id: (\S+)', result_output).group(1)
        private_key = re.search(r'private_key: (\S+)', result_output).group(1)
        warp_token = re.search(r'token: (\S+)', result_output).group(1)

        with open('warp.conf', 'w') as file:
            file.write(f"""
[Account]
Device = {device_id}
PrivateKey = {private_key}
Token = {warp_token}
Type = free
Name = WARP
MTU = 1280

[Peer]
PublicKey = bmXOC+F1FxEMF9dyiK2H5/1SUtzH0JuVo51h2wPfgyo=
Endpoint = 162.159.192.8:0
Endpoint6 = [2606:4700:d0::a29f:c008]:0
KeepAlive = 30""")

        cmd(f'./warp-go --update --config=./warp.conf --license={warpkey} --device-name={device_name}'
            )


def handle_warp_teams(app):
    print(
        colored(
            "请在此网站：https://web--public--warp-team-api--coia-mfs4.code.run/ 获取你的 WARP Teams 账户 TOKEN",
            'light_cyan'))
    while True:
        teams_token = input("请输入 WARP Teams 账户 TOKEN 或输入 'exit' 退出:").strip()
        if teams_token.lower() == 'exit':
            exit()
        if teams_token:
            break
        print(colored("WARP Teams 账户 TOKEN 输入错误，请重新输入！", 'light_blue'))

    if teams_token:
        device_name = input("请输入自定义设备名，空则使用随机字符: ").strip()
        if not device_name:
            device_name = 'WireGuard ' + hashlib.md5(
                str(datetime.now().timestamp()).encode()).hexdigest()[:6]

        if app == "2":
            os.system("./wgcf generate")
            os.chmod('./wgcf-profile.conf', 0o755)
            private_key = cmd('wg genkey')
            public_key = cmd(f'echo {private_key} | wg pubkey')
            install_id = ''.join(
                random.choices(string.ascii_letters + string.digits, k=22))
            fcm_token = f"{install_id}:APA91b{''.join(random.choices(string.ascii_letters + string.digits, k=134))}"
            payload = {
                "key": public_key,
                "install_id": install_id,
                "fcm_token": fcm_token,
                "tos": datetime.utcnow().isoformat() + "Z",
                "model": "Linux",
                "serial_number": install_id,
                "locale": "zh_CN"
            }

            headers = {
                'User-Agent': 'okhttp/3.12.1',
                'CF-Client-Version': 'a-6.10-2158',
                'Content-Type': 'application/json',
                'Cf-Access-Jwt-Assertion': teams_token
            }
            response = requests.post(
                'https://api.cloudflareclient.com/v0a2158/reg',
                headers=headers,
                json=payload)
            team_result = response.json()
            private_v6 = team_result.get('v6')
            with open('wgcf-profile.conf', 'r') as file:
                content = file.read()

            content = re.sub(r'PrivateKey.*', f'PrivateKey = {private_key}',
                             content)
            content = re.sub(r'Address.*128', f'Address = {private_v6}/128',
                             content)

            with open('wgcf-profile.conf', 'w') as file:
                file.write(content)

        else:
            result_output = cmd('./warp-api')
            device_id = re.search(r'device_id: (\S+)', result_output).group(1)
            private_key = re.search(r'private_key: (\S+)',
                                    result_output).group(1)
            warp_token = re.search(r'token: (\S+)', result_output).group(1)

            with open('warp.conf', 'w') as file:
                file.write(f"""
[Account]
Device = {device_id}
PrivateKey = {private_key}
Token = {warp_token}
Type = free
Name = WARP
MTU = 1280

[Peer]
PublicKey = bmXOC+F1FxEMF9dyiK2H5/1SUtzH0JuVo51h2wPfgyo=
Endpoint = 162.159.192.8:0
Endpoint6 = [2606:4700:d0::a29f:c008]:0
KeepAlive = 30""")

            cmd(f'./warp-go --update --config=warp.conf --team-config={teams_token} --device-name={device_name}'
                )
            with open('warp.conf', 'r') as file:
                content = file.read()
            content = re.sub(r'Type = .+', 'Type = team', content)
            with open('warp.conf', 'w') as file:
                file.write(content)


def showConfig(filename, name):
    print("")
    print("")
    print(colored(name + "配置文件内容：", 'light_cyan'))
    with open(filename, 'r') as file:
        content = file.read()
    print(colored(content, 'light_blue'))
    print(colored(name + "配置文件二维码：", 'light_cyan'))
    subprocess.run('qrencode -s 1 -l L -t ansiutf8 < ' + filename, shell=True)


def main():
    print(colored("请稍后，正在配置环境...", 'light_cyan'))
    setup_environment('')
    os.system('clear')
    os.system('clear')
    print("")
    print("此项目与 Cloudflare 无任何关联")
    print(
        f"有关 Cloudflare 的服务条款，请前往 {colored('https://www.cloudflare.com/application/terms/','light_blue')} 查看"
    )
    print("")
    print("")
    print(colored("请选择用于处理 WARP 操作的程序", 'light_cyan'))
    print(
        f" {colored('1.', 'light_green')} WARP-GO {colored('(默认,支持 WireGuard 和 Sing-Box 的配置文件生成)', 'light_cyan')}"
    )
    print(
        f" {colored('2.', 'light_green')} WGCF {colored('(仅支持 WireGuard)', 'light_cyan')}"
    )
    print(
        f" {colored('3.', 'light_green')} Requests {colored('(仅生成 WARP+ 无限流量密钥)', 'light_cyan')}"
    )
    app_type = input("请输入选项 [1-3]: ").strip()

    if app_type == '2':
        setup_environment('2')
    elif app_type == '3':
        print("")
        print(colored("请输入要生成的 WARP+ 密钥数量", 'light_cyan'))
        for keys in handle_warp_plus_key(int(input("> "))):
            print(keys)
        print(colored("密钥生成完成！上方为生成的密钥列表", 'light_green'))
        exit()
    else:
        setup_environment('1')

    print("")
    print(colored("请选择要进行的 WARP 操作", 'light_cyan'))
    print(
        f" {colored('1.', 'light_green')} 生成 WARP 免费账户配置文件 {colored('(默认,无密钥)', 'light_cyan')}"
    )
    print(f" {colored('2.', 'light_green')} 生成 WARP+ 账户配置文件 ")
    print(f" {colored('3.', 'light_green')} 生成 WARP Teams 配置文件")

    account_type = input("请输入选项 [1-3]: ").strip()

    if account_type == '2':
        handle_warp_plus(app_type)
    elif account_type == '3':
        handle_warp_teams(app_type)
    else:
        handle_warp_free(app_type)

    print(colored("配置文件生成成功！", 'light_green'))
    if app_type == '2':
        showConfig('wgcf-profile.conf', 'WireGaurd')
    else:
        cmd('./warp-go --config=warp.conf --export-wireguard=wireguard.conf')
        cmd('./warp-go --config=warp.conf --export-singbox=singbox.json')
        showConfig('wireguard.conf', 'WireGuard')
        showConfig('singbox.json', 'Singbox')
    exit()


def exit():
    pause()
    main()


def pause():
    try:
        # Windows
        import msvcrt
        print("按任意键继续...")
        msvcrt.getch()
    except ImportError:
        # Unix-based
        import termios
        import tty
        print("按任意键继续...")
        fd = sys.stdin.fileno()
        old_settings = termios.tcgetattr(fd)
        try:
            tty.setraw(sys.stdin.fileno())
            sys.stdin.read(1)
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)


if __name__ == "__main__":
    main()
