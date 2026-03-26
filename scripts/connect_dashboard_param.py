#!/usr/bin/env python3
"""
Automatically generates dashboardparameters.json for:
https://github.com/aws-samples/amazon-connect-instance-dashboard

This script fetches ALL queues from your Amazon Connect instance and creates the required JSON file.
"""

import json
import boto3
import argparse
import sys
from botocore.exceptions import ClientError, NoCredentialsError


def get_connect_instance_id():
    client = boto3.client("connect")  # add region_name="..." if needed
    try:
        resp = client.list_instances()
        instances = resp.get("InstanceSummaryList", [])
        if not instances:
            print("No Amazon Connect instances found in this account/region.")
            return None
        print("Available Connect instances:")
        for i, inst in enumerate(instances, 1):
            print(f"  {i}. Alias: {inst.get('InstanceAlias', '—')}")
            print(f"     ID:   {inst['Id']}")
            print(f"     ARN:  {inst['Arn']}")
            print()
        if len(instances) == 1:
            print("→ Using the only instance found.")
            return instances[0]["Id"]
        else:
            choice = input("Enter number of instance to use (or press Enter to abort): ").strip()
            if choice.isdigit() and 1 <= int(choice) <= len(instances):
                return instances[int(choice)-1]["Id"]
            else:
                return None
    except ClientError as e:
        print("Cannot list instances:", e)
        return None


def fetch_queues(instance_id: str, queue_type: str = "STANDARD") -> list:
    """Fetch all queue names from Amazon Connect with pagination."""
    client = boto3.client("connect")
    queue_names = []
    next_token = None

    print(f"🔍 Fetching {queue_type} queues from Connect instance...")

    while True:
        params = {
            "InstanceId": instance_id,
            "MaxResults": 100
        }
        if next_token:
            params["NextToken"] = next_token
        if queue_type != "ALL":
            params["QueueTypes"] = [queue_type]

        response = client.list_queues(**params)

        for queue in response.get("QueueSummaryList", []):
            if queue.get('Name'):
               queue_names.append(queue["Name"])

        next_token = response.get("NextToken")
        if not next_token:
            break

    return sorted(queue_names)  # Sort alphabetically for nice output


def main():
    parser = argparse.ArgumentParser(
        description="Auto-generate dashboardparameters.json by fetching queues from Amazon Connect"
    )
    parser.add_argument("--instance-id",
                        help="Amazon Connect Instance ID (e.g. 12345678-1234-1234-1234-123456789012)")
    parser.add_argument("--instance-name", default="iba-cc",
                        help="Friendly name for your Connect instance (e.g. Prod-Contact-Center)")
    parser.add_argument("--queue-type", choices=["STANDARD", "AGENT", "ALL"], default="ALL",
                        help="Queue type to fetch (default: STANDARD)")
    parser.add_argument("--output", default="dashboardparameters.json",
                        help="Output filename (default: dashboardparameters.json)")
    parser.add_argument("--pretty", action="store_true",
                        help="Pretty-print the JSON output")

    args = parser.parse_args()
    instance_id = get_connect_instance_id()


    try:
        queues = fetch_queues(instance_id, args.queue_type)

        if not queues:
            print("⚠️  No queues found. Please verify your Instance ID and IAM permissions.")
            sys.exit(1)

        print(f"✅ Successfully fetched {len(queues)} queues")

        # Build the exact structure expected by the AWS sample
        config = {
            "ConnectInstanceId": instance_id,
            "ConnnectInstanceName": args.instance_name,   # Note: "Connnect" with 3 n's is required by the sample
            "ConnectQueues": queues
        }

        indent = 4 if args.pretty else None

        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=indent, ensure_ascii=False)

        print(f"\n🎉 dashboardparameters.json created successfully!")
        print(f"   File: {args.output}")
        print(f"   Queues included: {len(queues)}")
        print("\nFirst 100 queues:")
        for q in queues[:100]:
            print(f"     • {q}")

    except NoCredentialsError:
        print("❌ No AWS credentials found. Please run `aws configure` or set AWS environment variables.")
    except ClientError as e:
        if e.response['Error']['Code'] == 'AccessDenied':
            print("❌ Access Denied: Please attach 'connect:ListQueues' permission to your IAM role/user.")
        else:
            print(f"❌ AWS API Error: {e}")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
