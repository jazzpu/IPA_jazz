#!/usr/bin/env python3
"""
Network Health Monitoring Web Dashboard
A modern web-based dashboard to monitor network device health
Created for IPA_jazz project - Enhanced network automation with web interface
"""

import os
import time
import json
import threading
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from netmiko import ConnectHandler
import re
from flask import Flask, render_template, jsonify, request
import webbrowser
from threading import Timer

# Device credentials - same as your existing setup
PRIVATE_KEY_FILE = os.path.expanduser("~/.ssh/admin_key")

devices = {
    "R1-P": {
        "device_type": "cisco_ios",
        "host": "172.31.42.4",
        "username": "admin",
        "use_keys": True,
        "key_file": PRIVATE_KEY_FILE,
        "secret": "",
        "type": "Router"
    },
    "R2-P": {
        "device_type": "cisco_ios",
        "host": "172.31.42.5",
        "username": "admin",
        "use_keys": True,
        "key_file": PRIVATE_KEY_FILE,
        "secret": "",
        "type": "Router"
    },
    "S1-P": {
        "device_type": "cisco_ios",
        "host": "172.31.42.3",
        "username": "admin",
        "use_keys": True,
        "key_file": PRIVATE_KEY_FILE,
        "secret": "",
        "type": "Switch"
    },
}

class NetworkHealthMonitorWeb:
    def __init__(self):
        self.health_data = {}
        self.last_update = None
        self.monitoring_active = False
        
    def get_device_health(self, device_name, device_config):
        """Collect health information from a single device"""
        health_info = {
            "device_name": device_name,
            "host": device_config["host"],
            "type": device_config["type"],
            "status": "Offline",
            "uptime": "Unknown",
            "cpu_usage": "Unknown",
            "memory_usage": "Unknown",
            "interfaces": {},
            "temperature": "Unknown",
            "last_checked": datetime.now().strftime("%H:%M:%S"),
            "response_time": 0,
            "cpu_percentage": 0,
            "memory_percentage": 0
        }
        
        start_time = time.time()
        net_connect = None
        
        try:
            # Remove non-netmiko parameters
            connection_params = {k: v for k, v in device_config.items() 
                               if k not in ["type"]}
            
            net_connect = ConnectHandler(**connection_params)
            
            # Calculate response time
            health_info["response_time"] = round((time.time() - start_time) * 1000, 2)
            health_info["status"] = "Online"
            
            # Get basic device info
            self._get_uptime(net_connect, health_info)
            self._get_cpu_memory(net_connect, health_info)
            self._get_interface_status(net_connect, health_info)
            self._get_temperature(net_connect, health_info)
            
        except Exception as e:
            health_info["status"] = "Offline"
            health_info["error"] = str(e)
            
        finally:
            if net_connect and net_connect.is_alive():
                net_connect.disconnect()
                
        return health_info
    
    def _get_uptime(self, connection, health_info):
        """Extract device uptime"""
        try:
            output = connection.send_command("show version")
            uptime_pattern = r"uptime is (.+?)(?:\n|$)"
            match = re.search(uptime_pattern, output)
            if match:
                health_info["uptime"] = match.group(1).strip()
        except:
            pass
    
    def _get_cpu_memory(self, connection, health_info):
        """Extract CPU and memory usage"""
        try:
            commands = [
                "show processes cpu",
                "show memory statistics", 
                "show processes memory"
            ]
            
            for cmd in commands:
                try:
                    output = connection.send_command(cmd, delay_factor=2)
                    
                    # Parse CPU usage
                    cpu_pattern = r"CPU utilization for five seconds: (\d+)%"
                    cpu_match = re.search(cpu_pattern, output)
                    if cpu_match and health_info["cpu_usage"] == "Unknown":
                        cpu_percent = int(cpu_match.group(1))
                        health_info["cpu_usage"] = f"{cpu_percent}%"
                        health_info["cpu_percentage"] = cpu_percent
                    
                    # Parse memory usage
                    mem_pattern = r"Total: (\d+), Used: (\d+)"
                    mem_match = re.search(mem_pattern, output)
                    if mem_match and health_info["memory_usage"] == "Unknown":
                        total = int(mem_match.group(1))
                        used = int(mem_match.group(2))
                        percentage = round((used / total) * 100, 1)
                        health_info["memory_usage"] = f"{percentage}%"
                        health_info["memory_percentage"] = percentage
                        
                except:
                    continue
                    
        except:
            pass
    
    def _get_interface_status(self, connection, health_info):
        """Get interface status information"""
        try:
            output = connection.send_command("show ip interface brief")
            
            interface_pattern = r"^(\S+)\s+(\S+)\s+\S+\s+\S+\s+(\S+)\s+(\S+)"
            
            total_interfaces = 0
            up_interfaces = 0
            
            for line in output.split('\n'):
                match = re.match(interface_pattern, line.strip())
                if match:
                    interface = match.group(1)
                    ip_address = match.group(2)
                    status = match.group(3)
                    protocol = match.group(4)
                    
                    if any(skip in interface.lower() for skip in ['vlan', 'loopback', 'null']):
                        continue
                        
                    total_interfaces += 1
                    if status == "up" and protocol == "up":
                        up_interfaces += 1
                        
                    health_info["interfaces"][interface] = {
                        "ip": ip_address,
                        "status": status,
                        "protocol": protocol,
                        "state": "up" if status == "up" and protocol == "up" else "down"
                    }
            
            health_info["interface_summary"] = {
                "total": total_interfaces,
                "up": up_interfaces,
                "down": total_interfaces - up_interfaces
            }
            
        except:
            pass
    
    def _get_temperature(self, connection, health_info):
        """Get device temperature (if available)"""
        try:
            commands = ["show environment", "show environment temperature"]
            for cmd in commands:
                try:
                    output = connection.send_command(cmd, delay_factor=2)
                    temp_pattern = r"(\d+) Celsius"
                    temp_match = re.search(temp_pattern, output)
                    if temp_match:
                        health_info["temperature"] = f"{temp_match.group(1)}°C"
                        break
                except:
                    continue
        except:
            pass
    
    def collect_all_health_data(self):
        """Collect health data from all devices concurrently"""
        with ThreadPoolExecutor(max_workers=3) as executor:
            future_to_device = {
                executor.submit(self.get_device_health, name, config): name 
                for name, config in devices.items()
            }
            
            for future in as_completed(future_to_device):
                device_name = future_to_device[future]
                try:
                    health_data = future.result()
                    self.health_data[device_name] = health_data
                except Exception as e:
                    print(f"Failed to get health data for {device_name}: {e}")
        
        self.last_update = datetime.now()
        return self.health_data

# Create Flask app and monitor instance
app = Flask(__name__)
monitor = NetworkHealthMonitorWeb()

@app.route('/')
def dashboard():
    """Main dashboard page"""
    return render_template('dashboard.html')

@app.route('/api/health')
def get_health_data():
    """API endpoint to get current health data"""
    monitor.collect_all_health_data()
    
    # Calculate summary statistics
    online_devices = sum(1 for data in monitor.health_data.values() if data.get("status") == "Online")
    total_devices = len(monitor.health_data)
    
    response_data = {
        "devices": monitor.health_data,
        "summary": {
            "total_devices": total_devices,
            "online_devices": online_devices,
            "offline_devices": total_devices - online_devices,
            "health_percentage": round((online_devices / total_devices) * 100, 1) if total_devices > 0 else 0
        },
        "last_update": monitor.last_update.isoformat() if monitor.last_update else None
    }
    
    return jsonify(response_data)

@app.route('/api/device/<device_name>')
def get_device_details(device_name):
    """API endpoint to get detailed info for a specific device"""
    if device_name in monitor.health_data:
        return jsonify(monitor.health_data[device_name])
    else:
        return jsonify({"error": "Device not found"}), 404

@app.route('/api/export')
def export_health_report():
    """Export current health data as JSON"""
    # Create reports directory if it doesn't exist
    reports_dir = "reports"
    if not os.path.exists(reports_dir):
        os.makedirs(reports_dir)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"reports/network_health_report_{timestamp}.json"
    
    report_data = {
        "timestamp": datetime.now().isoformat(),
        "devices": monitor.health_data,
        "summary": {
            "total_devices": len(monitor.health_data),
            "online_devices": sum(1 for data in monitor.health_data.values() if data.get("status") == "Online"),
            "offline_devices": sum(1 for data in monitor.health_data.values() if data.get("status") != "Online")
        }
    }
    
    try:
        with open(filename, 'w') as f:
            json.dump(report_data, f, indent=2)
        return jsonify({"success": True, "filename": filename, "message": f"Report saved as {filename}"})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

def open_browser():
    """Open browser after a short delay"""
    webbrowser.open('http://127.0.0.1:5000')

def main():
    """Main function to start the web server"""
    print("🚀 Starting Network Health Monitor Web Dashboard...")
    print("📊 Dashboard will be available at: http://127.0.0.1:5000")
    print("🌐 Opening browser in 2 seconds...")
    print("💡 Press Ctrl+C to stop the server")
    
    # Open browser after 2 seconds
    Timer(2.0, open_browser).start()
    
    # Start Flask app
    try:
        app.run(host='127.0.0.1', port=5000, debug=False)
    except KeyboardInterrupt:
        print("\n👋 Network Health Monitor stopped by user")

if __name__ == "__main__":
    main()
