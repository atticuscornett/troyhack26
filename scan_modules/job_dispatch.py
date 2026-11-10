print("Starting job dispatcher...")

print("Setting up list one processing...")
from scan_modules import list1_processing as l1p, list2_processing as l2p
import threading
import asyncio
import time
import random

file_statuses = {}

currently_proccessing = 0

async def run_job(job_file_path):
    global currently_proccessing

    new_file_status = {
        "processState": "pending",
        "approvalState": "pending",
        "filePath": job_file_path,
        "fileName": job_file_path.split("/")[-1],
        "issueState": "unknown",
        "issues": []
    }

    file_statuses[job_file_path] = new_file_status


    while currently_proccessing >= 3:
        await asyncio.sleep(random.random() * 6)  # Wait for a random time between 0 and 6 seconds before checking again

    currently_proccessing += 1

    new_file_status["processState"] = "processing"

    file_issues = l1p.scan_file(job_file_path)

    file_issues.extend(l2p.scan_file(job_file_path))

    new_file_status["processState"] = "processed"
    new_file_status["issues"] = file_issues
    currently_proccessing -= 1

    highest_severity = "unknown"
    for issue in file_issues:
        if issue["color"] == "red":
            highest_severity = "red"
            break
        elif issue["color"] == "yellow" and highest_severity != "red":
            highest_severity = "yellow"
    if len(file_issues) == 0:
        highest_severity = "green"

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