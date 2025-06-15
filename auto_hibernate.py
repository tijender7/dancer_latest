import psutil
import time
import subprocess

# === CONFIG ===
CPU_THRESHOLD = 10  # in percent
GPU_THRESHOLD = 10  # in percent (for NVIDIA GPU)
CHECK_INTERVAL = 30  # seconds
LOW_USAGE_DURATION = 10 * 60  # 10 minutes in seconds

# === GPU UTIL FETCH FUNCTION ===
def get_gpu_utilization():
    try:
        import GPUtil
        gpus = GPUtil.getGPUs()
        if not gpus:
            return 0
        return max(gpu.load * 100 for gpu in gpus)  # return max load in percent
    except Exception as e:
        print("GPU check failed:", e)
        return 0

# === MAIN LOOP ===
def monitor_usage_and_shutdown():
    low_usage_time = 0

    while True:
        cpu = psutil.cpu_percent(interval=1)
        gpu = get_gpu_utilization()
        print(f"CPU: {cpu:.1f}%, GPU: {gpu:.1f}%")

        if cpu < CPU_THRESHOLD and gpu < GPU_THRESHOLD:
            low_usage_time += CHECK_INTERVAL
            print(f"Low usage for {low_usage_time // 60} min")
        else:
            low_usage_time = 0

        if low_usage_time >= LOW_USAGE_DURATION:
            print("Low usage detected for 10 minutes. Shutting down...")
            subprocess.call("shutdown /s /t 0", shell=True)  # This will shut down immediately
            break

        time.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    monitor_usage_and_shutdown()
