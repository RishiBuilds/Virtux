from __future__ import annotations
from virtux.commands import register

import random
import time
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from virtux.registry import CommandContext


@register(
    "ping",
    help_text="Send ICMP ECHO_REQUEST to network hosts (simulated).",
    usage="ping [-c count] host",
    category="network",
)
def cmd_ping(ctx: CommandContext) -> int:
    count = 4
    host = None
    i = 0

    while i < len(ctx.args):
        arg = ctx.args[i]
        if arg == "-c" and i + 1 < len(ctx.args):
            try:
                count = int(ctx.args[i + 1])
            except ValueError:
                ctx.error(f"ping: invalid count: {ctx.args[i + 1]}")
                return 1
            i += 2
        elif not arg.startswith("-"):
            host = arg
            i += 1
        else:
            i += 1

    if not host:
        ctx.error("ping: usage error: missing host operand")
        return 1

    ip = f"{random.randint(1,223)}.{random.randint(0,255)}.{random.randint(0,255)}.{random.randint(1,254)}"
    if host in ("localhost", "127.0.0.1"):
        ip = "127.0.0.1"
    elif host in ("google.com", "www.google.com"):
        ip = "142.250.80.46"

    ctx.writeln(f"PING {host} ({ip}) 56(84) bytes of data.")
    times = []

    for seq in range(1, count + 1):
        rtt = round(random.uniform(0.01, 0.1) if host in ("localhost", "127.0.0.1") else random.uniform(5.0, 50.0), 3)
        times.append(rtt)
        ctx.writeln(f"64 bytes from {ip}: icmp_seq={seq} ttl=64 time={rtt} ms")
        if seq < count:
            time.sleep(min(0.3, 1.0))

    avg = sum(times) / len(times)
    mdev = (max(times) - min(times)) / 2
    ctx.writeln(f"\n--- {host} ping statistics ---")
    ctx.writeln(f"{count} packets transmitted, {count} received, 0% packet loss, time {int(sum(times))}ms")
    ctx.writeln(f"rtt min/avg/max/mdev = {min(times):.3f}/{avg:.3f}/{max(times):.3f}/{mdev:.3f} ms")
    return 0


@register(
    "ifconfig",
    help_text="Configure a network interface (simulated).",
    usage="ifconfig [interface]",
    category="network",
)
def cmd_ifconfig(ctx: CommandContext) -> int:
    ctx.writeln("eth0: flags=4163<UP,BROADCAST,RUNNING,MULTICAST>  mtu 1500")
    ctx.writeln("        inet 192.168.1.100  netmask 255.255.255.0  broadcast 192.168.1.255")
    ctx.writeln("        inet6 fe80::1  prefixlen 64  scopeid 0x20<link>")
    ctx.writeln("        ether 02:42:ac:11:00:02  txqueuelen 1000  (Ethernet)")
    ctx.writeln("        RX packets 150234  bytes 112345678 (107.1 MiB)")
    ctx.writeln("        RX errors 0  dropped 0  overruns 0  frame 0")
    ctx.writeln("        TX packets 98765  bytes 87654321 (83.5 MiB)")
    ctx.writeln("        TX errors 0  dropped 0 overruns 0  carrier 0  collisions 0")
    ctx.writeln()
    ctx.writeln("lo: flags=73<UP,LOOPBACK,RUNNING>  mtu 65536")
    ctx.writeln("        inet 127.0.0.1  netmask 255.0.0.0")
    ctx.writeln("        inet6 ::1  prefixlen 128  scopeid 0x10<host>")
    ctx.writeln("        loop  txqueuelen 1000  (Local Loopback)")
    ctx.writeln("        RX packets 1024  bytes 65536 (64.0 KiB)")
    ctx.writeln("        TX packets 1024  bytes 65536 (64.0 KiB)")
    return 0


@register(
    "ip",
    help_text="Show / manipulate routing, network devices (simulated).",
    usage="ip [addr|link|route]",
    category="network",
)
def cmd_ip(ctx: CommandContext) -> int:
    subcommand = ctx.args[0] if ctx.args else "addr"

    if subcommand in ("addr", "a", "address"):
        ctx.writeln("1: lo: <LOOPBACK,UP,LOWER_UP> mtu 65536 qdisc noqueue state UNKNOWN group default qlen 1000")
        ctx.writeln("    link/loopback 00:00:00:00:00:00 brd 00:00:00:00:00:00")
        ctx.writeln("    inet 127.0.0.1/8 scope host lo")
        ctx.writeln("       valid_lft forever preferred_lft forever")
        ctx.writeln("2: eth0: <BROADCAST,MULTICAST,UP,LOWER_UP> mtu 1500 qdisc fq_codel state UP group default qlen 1000")
        ctx.writeln("    link/ether 02:42:ac:11:00:02 brd ff:ff:ff:ff:ff:ff")
        ctx.writeln("    inet 192.168.1.100/24 brd 192.168.1.255 scope global dynamic eth0")
        ctx.writeln("       valid_lft 86400sec preferred_lft 86400sec")
    elif subcommand in ("link", "l"):
        ctx.writeln("1: lo: <LOOPBACK,UP,LOWER_UP> mtu 65536 qdisc noqueue state UNKNOWN mode DEFAULT group default qlen 1000")
        ctx.writeln("    link/loopback 00:00:00:00:00:00 brd 00:00:00:00:00:00")
        ctx.writeln("2: eth0: <BROADCAST,MULTICAST,UP,LOWER_UP> mtu 1500 qdisc fq_codel state UP mode DEFAULT group default qlen 1000")
        ctx.writeln("    link/ether 02:42:ac:11:00:02 brd ff:ff:ff:ff:ff:ff")
    elif subcommand in ("route", "r"):
        ctx.writeln("default via 192.168.1.1 dev eth0 proto dhcp metric 100")
        ctx.writeln("192.168.1.0/24 dev eth0 proto kernel scope link src 192.168.1.100 metric 100")
    else:
        ctx.error(f"ip: unknown subcommand '{subcommand}'")
        return 1

    return 0


@register(
    "curl",
    help_text="Transfer data from or to a server (simulated).",
    usage="curl [-o file] [-s] [-I] url",
    category="network",
)
def cmd_curl(ctx: CommandContext) -> int:
    silent = "-s" in ctx.args
    head_only = "-I" in ctx.args
    output_file = None
    url = None
    i = 0

    while i < len(ctx.args):
        arg = ctx.args[i]
        if arg == "-o" and i + 1 < len(ctx.args):
            output_file = ctx.args[i + 1]
            i += 2
        elif not arg.startswith("-"):
            url = arg
            i += 1
        else:
            i += 1

    if not url:
        ctx.error("curl: no URL specified")
        return 1

    if head_only:
        ctx.writeln("HTTP/1.1 200 OK")
        ctx.writeln("Content-Type: text/html; charset=UTF-8")
        ctx.writeln(f"Date: {time.strftime('%a, %d %b %Y %H:%M:%S GMT')}")
        ctx.writeln("Server: nginx/1.24.0")
        ctx.writeln("Content-Length: 1234")
        ctx.writeln("Connection: keep-alive")
        ctx.writeln("")
        return 0

    content = (
        "<!DOCTYPE html>\n<html>\n"
        "<head><title>Simulated Response</title></head>\n"
        "<body>\n"
        f"<h1>Virtux Simulated Response</h1>\n"
        f"<p>This is a simulated response for: {url}</p>\n"
        "<p>Note: Virtux does not make real network requests.</p>\n"
        "</body>\n</html>\n"
    )

    if output_file:
        ctx.fs.write_file(ctx.resolve_path(output_file), content)
        if not silent:
            ctx.writeln("  % Total    % Received    Time     Speed")
            ctx.writeln(f"  {len(content)}   100   {len(content)}    0:00:00  --:--:--  {len(content)}")
    else:
        ctx.write(content)

    return 0


@register(
    "wget",
    help_text="Non-interactive network downloader (simulated).",
    usage="wget [-O file] url",
    category="network",
)
def cmd_wget(ctx: CommandContext) -> int:
    output_file = None
    url = None
    i = 0

    while i < len(ctx.args):
        arg = ctx.args[i]
        if arg == "-O" and i + 1 < len(ctx.args):
            output_file = ctx.args[i + 1]
            i += 2
        elif not arg.startswith("-"):
            url = arg
            i += 1
        else:
            i += 1

    if not url:
        ctx.error("wget: missing URL")
        return 1

    if not output_file:
        parts = url.rstrip("/").split("/")
        output_file = parts[-1] if parts[-1] else "index.html"

    content = f"<!-- Simulated download of {url} by Virtux -->\n<html><body>Simulated content</body></html>\n"
    ctx.fs.write_file(ctx.resolve_path(output_file), content)

    ctx.writeln(f"--{time.strftime('%Y-%m-%d %H:%M:%S')}--  {url}")
    ctx.writeln(f"Resolving {url.split('/')[2] if '/' in url else url}... done.")
    ctx.writeln("Connecting... connected.")
    ctx.writeln("HTTP request sent, awaiting response... 200 OK")
    ctx.writeln(f"Length: {len(content)} [{len(content)}]")
    ctx.writeln(f"Saving to: '{output_file}'")
    ctx.writeln(f"\n'{output_file}' saved [{len(content)}/{len(content)}]")
    return 0


@register(
    "ssh",
    help_text="OpenSSH remote login client (simulated).",
    usage="ssh [user@]hostname",
    category="network",
)
def cmd_ssh(ctx: CommandContext) -> int:
    if not ctx.args:
        ctx.error("usage: ssh [user@]hostname")
        return 1

    target = ctx.args[0]
    ctx.writeln(f"ssh: connect to host {target}: Connection simulated")
    ctx.writeln("Note: Virtux does not make real SSH connections.")
    ctx.writeln(f"This is a simulated SSH session to {target}.")
    return 0