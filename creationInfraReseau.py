import os

from azure.identity import AzureCliCredential
from azure.mgmt.compute import ComputeManagementClient
from azure.mgmt.network import NetworkManagementClient
from azure.mgmt.resource import ResourceManagementClient
from azure.mgmt.compute.models import HardwareProfile, OSProfile

print(
    "Provisioning a virtual machine...some operations might take a minute or two."
)

# Acquisition d'un objet de type Credential en utilisant une authentification basée sur le CLI.
credential = AzureCliCredential()

# Récupération de l'ID de l'abonnement à partir de la variable d'environnement.
subscription_id = "ec907711-acd7-4191-9983-9577afbe3ce1"

# Etape 1 : Provisionnement d'un groupe de ressources

# Obtention de l'objet de gestion pour les ressources, en utilisant les identifiants obtenus à partir de la connexion CLI.
resource_client = ResourceManagementClient(credential, subscription_id)

# Constantes dont nous avons besoin à plusieurs endroits : le nom du groupe de ressources et la région
# dans laquelle nous provisionnons les ressources. 
RESOURCE_GROUP_NAME = "Teamrocket_RG"
LOCATION = "northeurope"

# Provisionnement du groupe de ressources.
rg_result = resource_client.resource_groups.create_or_update(
    RESOURCE_GROUP_NAME,
    {"location": LOCATION}
)

print(f"Provisioned resource group {rg_result.name} in the {rg_result.location} region")

# Étape 2: provisionnement d'un réseau virtuel

# Une machine virtuelle nécessite une interface réseau client (NIC). Une NIC nécessite
# un réseau virtuel et un sous-réseau ainsi qu'une adresse IP. Par conséquent, nous devons provisionner
# ces composants en aval en premier, puis provisionner la NIC, après quoi nous pouvons provisionner la VM.

# Noms du réseau et de l'adresse IP
VNET_NAME = "Teamrocket_Vnet"
SUBNET_NAME = "Teamrocket_Subnet"
IP_NAME = "Teamrocket_Pip"
IP_CONFIG_NAME = "Teamrocket_Pip_Config"

# Obtention de l'objet de gestion pour les réseaux
network_client = NetworkManagementClient(credential, subscription_id)

# Provisionnement du réseau virtuel
poller = network_client.virtual_networks.begin_create_or_update(
    RESOURCE_GROUP_NAME,
    VNET_NAME,
    {
        "location": LOCATION,
        "address_space": {"address_prefixes": ["192.168.11.0/26"]},
    },
)
vnet_result = poller.result()

print(f"Provisioned virtual network {vnet_result.name} with address prefixes {vnet_result.address_space.address_prefixes}")

# Étape 3 : Provisionnement du sous-réseau 
poller = network_client.subnets.begin_create_or_update(
    RESOURCE_GROUP_NAME,
    VNET_NAME,
    SUBNET_NAME,
    {"address_prefix": "192.168.11.0/28"},
)
subnet_result = poller.result()

print(f"Provisioned virtual subnet {subnet_result.name} with address prefix {subnet_result.address_prefix}")

# Étape 4 : Provisionnement d'une adresse IP 
poller = network_client.public_ip_addresses.begin_create_or_update(
    RESOURCE_GROUP_NAME,
    IP_NAME,
    {
        "location": LOCATION,
        "sku": {"name": "Standard"},
        "public_ip_allocation_method": "Static",
        "public_ip_address_version": "IPV4",
    },
)
ip_address_result = poller.result()

print(f"Provisioned public IP address {ip_address_result.name} with address {ip_address_result.ip_address}")

# Étape 5 : Provisionnement de l'interface réseau client
poller = network_client.network_interfaces.begin_create_or_update(
    RESOURCE_GROUP_NAME,
    "python-azure-nic",
    {
        "location": LOCATION,
        "ip_configurations": [
            {
                "name": IP_CONFIG_NAME,
                "subnet": {"id": subnet_result.id},
                "public_ip_address": {"id": ip_address_result.id},
            }
        ],
    },
)
nic_result = poller.result()

# Étape 5.1 : Création du groupe de sécurité réseau et des règles, et association à un sous-réseau
poller = network_client.network_security_groups.begin_create_or_update(
    RESOURCE_GROUP_NAME,
    "python-azure-nsg",
    {
        "location": LOCATION,
        "security_rules": [
            {
                "name": "AllowSSH",
                "protocol": "Tcp",
                "source_port_range": "*",
                "destination_port_range": "22",
                "source_address_prefix": "*",
                "destination_address_prefix": "*",
                "access": "Allow",
                "priority": 100,
                "direction": "Inbound",
            },
            {
                "name": "AllowHTTP",
                "protocol": "Tcp",
                "source_port_range": "*",
                "destination_port_range": "80",
                "source_address_prefix": "*",
                "destination_address_prefix": "*",
                "access": "Allow",
                "priority": 101,
                "direction": "Inbound",
            },
            {
                "name": "AllowHTTPS",
                "protocol": "Tcp",
                "source_port_range": "*",
                "destination_port_range": "443",
                "source_address_prefix": "*",
                "destination_address_prefix": "*",
                "access": "Allow",
                "priority": 102,
                "direction": "Inbound",
            },
        ],
    },
)
poller = network_client.subnets.begin_create_or_update(
    RESOURCE_GROUP_NAME,
    VNET_NAME,
    SUBNET_NAME,
    {
        "address_prefix": "192.168.11.0/28",
        "network_security_group": {"id": poller.result().id},
    }
)
subnet_result = poller.result()

print(f"Provisioned network interface client {nic_result.name}")
