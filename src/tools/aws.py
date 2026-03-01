"""AWS tool — interact with AWS services via boto3."""
import os
from typing import Any

import boto3


def get_client(service: str, region: str | None = None) -> Any:
    return boto3.client(service, region_name=region or os.getenv("AWS_DEFAULT_REGION", "us-east-1"))


def list_s3_buckets() -> list[str]:
    s3 = get_client("s3")
    response = s3.list_buckets()
    return [b["Name"] for b in response.get("Buckets", [])]


def list_ec2_instances(region: str | None = None) -> list[dict[str, Any]]:
    ec2 = get_client("ec2", region)
    response = ec2.describe_instances()
    instances = []
    for reservation in response["Reservations"]:
        for instance in reservation["Instances"]:
            instances.append({"id": instance["InstanceId"], "state": instance["State"]["Name"]})
    return instances
