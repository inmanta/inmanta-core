"""
    Inmanta LSM

    :copyright: 2024 Inmanta
    :contact: code@inmanta.com
    :license: Inmanta EULA
"""

import argparse

import requests


def main(args):
    environment = args.env
    address = args.host
    port = args.port
    service_name = "service_simple"

    # Make sure that our service is created
    url = f"http://{address}:{port}/lsm/v1/service_catalog/{service_name}"
    response = requests.get(
        url=url,
        headers={"X-Inmanta-tid": environment, "Content-Type": "application/json"},
    )
    assert response.status_code == 200

    # Fetch every instance of our service that has version 0 or 1
    url = f"http://{address}:{port}/lsm/v1/service_inventory/{service_name}?filter.service_entity_version=lt:2"
    response = requests.get(
        url=url,
        headers={"X-Inmanta-tid": environment, "Content-Type": "application/json"},
    )
    assert response.status_code == 200
    d = response.json()
    # Iterate over every retrieved instance and migrate to version 2
    for instance in d["data"]:
        # Only migrate instances on failed and up states because they are the only ones that we know for sure that have an
        # active attribute set. We will:
        # 1) Take this active attribute set, modify it to include a description and remove the missing fields.
        # 2) Set this set as the new candidate attribute set
        # 3) Set the state to 'start' so that our new candidate attribute set is validated and, eventually, promoted.
        if instance["state"] not in ["failed", "up"]:
            print(
                f"Instance with id {instance['id']} is being skipped because it is on state {instance['state']} "
                f"and not on state 'up' or 'failed'."
            )
            continue

        description = "migrated instance"

        url = f"http://{address}:{port}/lsm/v1/service_inventory/{service_name}/{instance['id']}/update_entity_version"

        active_attributes = instance["active_attributes"]
        attributes = {
            "router_ip": active_attributes["router_ip"],
            "interface_name": active_attributes["interface_name"],
            "address": active_attributes["address"],
            "description": description,
        }
        response = requests.patch(
            url=url,
            headers={"X-Inmanta-tid": environment, "Content-Type": "application/json"},
            json={
                "current_version": instance["version"],
                "target_entity_version": 2,
                "state": "start",
                "candidate_attributes": attributes,
                "active_attributes": None,
                "rollback_attributes": None,
            },
        )
        assert response.status_code == 200, response.text


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="The goal of this script is to migrate service instances (in the up and failed states) "
        "from version 0 or 1 of service entity `service_simple` to version 2"
    )
    parser.add_argument(
        "--host",
        help="The address of the server hosting the environment",
        default="172.25.102.2",
    )
    parser.add_argument(
        "--port", help="The port of the server hosting the environment", default=8888
    )
    parser.add_argument(
        "--env",
        help="The environment to execute this script on",
        default="8404deea-3621-4bca-9076-6a612115f810",
    )
    parser_args = parser.parse_args()
    main(parser_args)
