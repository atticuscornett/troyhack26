print("Starting job dispatcher...")

print("Setting up list one processing...")
import list_one_processing as l1p
import l2_processing as l2p
import threading
import asyncio
import time
import copy

file_statuses = {}

async def run_job(job_file_path):
    new_file_status = {
        "processState": "processing",
        "approvalState": "pending",
        "filePath": job_file_path,
        "fileName": job_file_path.split("/")[-1],
        "issueState": "unknown",
        "issues": []
    }

    file_statuses[job_file_path] = new_file_status

    file_issues = l1p.scan_file(job_file_path)

    file_issues.extend(l2p.scan_file(job_file_path))

    new_file_status["processState"] = "processed"
    new_file_status["issues"] = file_issues

    highest_severity = "unknown"
    for issue in file_issues:
        if issue["color"] == "red":
            highest_severity = "red"
            break
        elif issue["color"] == "yellow" and highest_severity != "red":
            highest_severity = "yellow"

    new_file_status["issueState"] = highest_severity


def get_file_statuses():
    return list(file_statuses.values())


def start_job(job_file_path):
    thread = threading.Thread(target=lambda: asyncio.run(run_job(job_file_path)))
    thread.start()

if __name__ == "__main__":
    previous_statuses = get_file_statuses()
    job_file_path = input("Enter job file path: ")
    start_job(job_file_path)
    while True:
        print("New File Status:")
        for status in get_file_statuses():
            print(status)
            
        time.sleep(3)