"""
Module for indexing actions using sower job dispatcher

Attributes:
"""

import os
import json
import asyncio
import sys

from gen3.tools import indexing

from settings import JOB_REQUIRES
from utils import upload_file_to_s3_and_generate_presigned_url, check_user_permission

if __name__ == "__main__":
    hostname = os.environ["GEN3_HOSTNAME"]
    input_data = os.environ["INPUT_DATA"]
    access_token = os.environ["ACCESS_TOKEN"]

    input_data_json = json.loads(input_data)
    if not input_data_json:
        input_data_json = {}

    with open("/creds.json") as indexing_creds_file:
        job_name = "download-indexd-manifest"
        indexing_creds = json.load(indexing_creds_file).get(job_name, {})
        if not indexing_creds:
            logging.warning(
                f"No configuration found for '{job_name}' job. "
                "Attempting to continue anyway..."
            )

    # Only use provided authz requirement if resources are not empty
    access_authz_requirement = JOB_REQUIRES
    if creds.get("job_requires", {}).get("job_access_req"):
        access_authz_requirement = creds.get("job_requires")

    # check if user has sower and ingestion policies
    is_allowed, message = check_user_permission(ACCESS_TOKEN, access_authz_requirement)
    if not is_allowed:
        print("[out]: {}".format(message["message"]))
        sys.exit()

    print("Start to download manifest ...")

    common_url = input_data_json.get("host")
    if not common_url:
        common_url = "https://{}".format(hostname)

    num_process = input_data_json.get("num_processes", 1)
    max_concurrent_requests = input_data_json.get("max_concurrent_requests", 8)

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(
        indexing.async_download_object_manifest(
            common_url,
            output_filename="object-manifest.csv",
            num_processes=num_process,
            max_concurrent_requests=max_concurrent_requests,
        )
    )

    output_manifest_presigned_url = upload_file_to_s3_and_generate_presigned_url(
        indexing_creds.get("bucket"), "object-manifest.csv"
    )

    print("[out] {}".format(output_manifest_presigned_url))