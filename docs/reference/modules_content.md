# Modules

This page gives an overview of all modules available by Inmanta on the Inmanta Orchestration Platform.


## Adapter

The following table provides and overview of all available adapters by Inmanta. Depending on the adapter they are opensource, included in specific
product suites or directly licensed.

| Name               |                                                                                                               |
| ------------------ | ------------------------------------------------------------------------------------------------------------- |
| aci                | Support for L2 and L3 resources on Cisco APIC such as EPG, VRF, ...                                           |
| apt                | Support for software packages on apt based systems such as Debian and Ubuntu                                  |
| athonet-core       | Support for the full configuration of the Athonet 4G/5G combo-core                                            |
| athonet-ims        | Support for the full configuration of the Athonet IMS                                                         |
| aws                | Support for AWS resources, mostly focused on EC2 and VPC                                                      |
| aws-dc             | Support for orchestration hosted direct connect resources                                                     |
| azure-expressroute | Support for Azure express route resources                                                                     |
| checkpoint         | Support for Checkpoint firewalls including VSX, rules, inventory, interfaces, routing, ...                    |
| cisco-xe           | Support for Cisco XE based devices such as CSR1000v and ASR through Netconf/YANG                              |
| cisco-xr           | Support for Cisco XR based devices such as ASR9k, XRd and NCS through Netconf/YANG                            |
| cloudflare         | Support for Cloudflare all resources including zero-trust services                                            |
| cloudsmith         | Support for Cloudsmith repos and entitlements                                                                 |
| druid              | Support for the full configuration of the Druid Raemis 4G/5G combo-core                                       |
| dzs                | Support for DZS OLT through SSH and CLI                                                                       |
| ecx-l2             | Support for Equinix Circuits through the l2 buyer API                                                         |
| exec               | Support to run commands on a Linux based host                                                                 |
| fnt                | Support for the FNT inventory                                                                                 |
| fortigate          | Support for Fortigate resources such as VDOM, Interfaces, BGP, Policies, ...                                  |
| fs                 | Support for creating files, directories and symlinks on Linux based hosts                                     |
| gcp-interco        | Support for Google Cloud Platform interconnect resources                                                      |
| juniper-ex         | Support for Juniper EX based devices using Netconf/YANG                                                       |
| juniper-mx         | Support for Juniper MX based devices using Netconf/YANG                                                       |
| kubernetes         | Support for managing resources on Kubernetes                                                                  |
| libvirt            | Support for managing the lifecycle of virtual machines through libvirt                                        |
| n5k-lan            | Support for Cisco Nexus 5000 datacenter switch using Netconfig and CLI                                        |
| netbox             | Support for documenting resources in Netbox                                                                   |
| nokia-srlinux      | Support for management of SRLinux based switches using gNMI / YANG                                            |
| nokia-sros         | Support for management of Nokia SR-OS based routers using Netconf / YANG                                      |
| oci-fastconnect    | Support for Oracle Cloud Infrastructure Fast Connect resources                                                |
| openroadm          | Support for OpenROADM Optical Services                                                                        |
| openstack          | Support for Openstack resources                                                                               |
| rest               | Support for doing REST based calls                                                                            |
| systemd            | Support for managing services on systemd based Linux systems                                                  |
| tibit              | Support for xPON services on Tibit OLTs using MCMS                                                            |
| transportpce       | Support for Optical Services through OpendayLight transportpce                                                |
| vcenter            | Support for managing resources on vCenter and ESXi directly (virtal machines, DVS, vSwitch, ...)              |
| vyos               | Support for managing vyos resources through SSH and CLI                                                       |
| yum                | Support for software packages on yum and dnf based systems such as RHEL, Rocky Linux, Alma Linux, Fedora, ... |


## Base modules

The following table provides an overview of various modules that are part of a product, adapter or extension of the platform

| Name     |                                                                                                                                                                                      |
| -------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| config   | A module to add support for configurable service models.                                                                                                                             |
| lsm      | This module provides the model part of the lifecycle management in the Inmanta Service Orchestator platform.                                                                         |
| mitogen  | Mitogen extension that provides adapters such as fs, apt, yum, exec, ... with the ability to execute over ssh, docker, podman, ...                                                   |
| restbase | This module is used by many of the adapters that use REST APIs. This module is only available as part of an adapter.                                                                 |
| std      | A module that provide base entities and plugins that are used by all service modules.                                                                                                |
| yang     | A module that is used by all adapters that use YANG. It provides the model to model transformation that these adapters require. This module is only available as part of an adapter. |


## Product modules

Product modules include a full service model for a specific use case. These modules are used to create our solutions like Inmanta Connect and Inmanta MPNO

| Name              |                                                                                 |
| ----------------- | ------------------------------------------------------------------------------- |
| connect           | The base module for connect that supports L2 and L3 services                    |
| connect-bitstream | Connect support for bitstream services on xPON for FTTH, FTTB and FTTC services |
| connect-optical   | Connect support for Optical Services                                            |
| mpn               | The module to orchestrate mobile private networks                              |

## Utilities

| Name     |                                                                        |
| -------- | ---------------------------------------------------------------------- |
| yaml     | A module with some yaml helper functions                               |
| devtools | A module with various development tools for debug prints, mocking, ... |
| graph    | A module to generate a visualization from the service model            |
