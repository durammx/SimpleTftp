import os
import subprocess
import time

def extract_tftp_directory(file_path):
    try:
        with open(file_path, "r") as file:
            for line in file:
                if line.startswith("TFTP_DIRECTORY="):
                    return line.split("=")[1].strip()
    except FileNotFoundError:
        print(f"File {file_path} not found.")
    return None

def execute_ls_command(directory, save_list_path):
    try:
        with open(save_list_path, "w") as save_list:
            subprocess.run(["ls", "-Alh", directory], check=True, stdout=save_list, stderr=subprocess.PIPE)
        print("Executed ls command.")
    except subprocess.CalledProcessError as e:
        print(f"Error executing ls command: {e}")

def monitor_directory_changes(directory, save_list_path, wait_time):
    execute_ls_command(directory, save_list_path)
    print("Monitoring directory:", directory)
    try:
        while True:
            events = subprocess.run(["inotifywait", "-q", "-e", "modify,create,delete,move", directory], capture_output=True, text=True).stdout.strip().split("\n")
            for event in events:
                event_parts = event.split()
                if len(event_parts) >= 3:
                    changed_file = event_parts[2]
                    if changed_file != "list.txt":
                        execute_ls_command(directory, save_list_path)
                        print(f"Updated directory listing saved to {save_list_path}")
            time.sleep(10)
    except KeyboardInterrupt:
        print("Monitoring stopped.")

info_file_path = "/etc/default/tftpd-hpa"
tftp_directory = extract_tftp_directory(info_file_path)

if not tftp_directory:
    print("TFTP_DIRECTORY not found in the info file.")
    exit(1)

tftp_directory = tftp_directory.strip('"')

save_list_path = os.path.join(tftp_directory, "list.txt")
execute_ls_command(tftp_directory, save_list_path)
print(f"Initial directory listing saved to {save_list_path}")
wait_time = 10 
monitor_directory_changes(tftp_directory, save_list_path, wait_time)