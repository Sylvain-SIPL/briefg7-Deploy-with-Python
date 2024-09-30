from azure.mgmt.compute import ComputeManagementClient
from azure.mgmt.resource import ResourceManagementClient
from azure.identity import AzureCliCredential
from azure.mgmt.network import NetworkManagementClient
import base64

#Acquire a credential object using CLI-based authentication

credential = AzureCliCredential() 

subscription_id = "ec907711-acd7-4191-9983-9577afbe3ce1"

resource_client = ResourceManagementClient(credential, subscription_id)

# Provision the virtual machine

# Obtain the management object for the virtual machines
compute_client = ComputeManagementClient(credential, subscription_id)

# Populate variables
LOCATION = "North Europe"
USERNAME = "phpadmin"
VNET_NAME = "Teamrocket_Vnet"
SUBNET_NAME = "Teamrocket_Subnet"
IP_NAME = "Teamrocket_php_Pip"
IP_CONFIG_NAME = "Teamrocket_Pip_Config"
RESOURCE_GROUP_NAME = "Teamrocket_RG" 
VM_NAME = "SrvPhp"

# Obtain the management object for networks
network_client = NetworkManagementClient(credential, subscription_id)

print(f"Provisioning virtual machine {VM_NAME}; this operation might take a few minutes.")

# Provision the resource group.
rg_result = resource_client.resource_groups.create_or_update(
    RESOURCE_GROUP_NAME,
    {"location": LOCATION}
)


# Creating the network security group and the rules, and associating it to the subnet
poller= network_client.network_security_groups.begin_create_or_update(
    RESOURCE_GROUP_NAME,
    "python-azure-nsg",
    {
        "location":LOCATION,
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
        ]
    }
)


# Provision the subnet
poller = network_client.subnets.begin_create_or_update(
    RESOURCE_GROUP_NAME,
    VNET_NAME,
    SUBNET_NAME,
    {
        "address_prefix": "192.168.11.0/28",
        "network_security_group":{"id": poller.result().id},
    },
    
)

subnet_result = poller.result()

# Provision IP Adress
poller = network_client.public_ip_addresses.begin_create_or_update(RESOURCE_GROUP_NAME,IP_NAME,
   {
       "location": LOCATION,
       "sku":{"name":"Standard"},
       "public_ip_allocation_method": "Static",
       "public_ip_address_version":"IPV4"
   },                                                                
                                                                   
)

ip_address_result = poller.result()

print(f"Provisioned public IP address {ip_address_result.name} with address {ip_address_result.ip_address}")


#Provision Network Interface Client

poller =network_client.network_interfaces.begin_create_or_update(
    RESOURCE_GROUP_NAME,
    "php-azure-nic",
    {
        "location":LOCATION,
        "ip_configurations": [
          {
              "name":IP_CONFIG_NAME,
              "subnet":{"id": subnet_result.id},
              "public_ip_address":{"id": ip_address_result.id},
          }  
        ],
    },
)

nic_result = poller.result()

# Provision the VM
# begin_create_or_update(resource_group_name: str, vm_name: str, parameters: _models.VirtualMachine, *, content_type: str = 'application/json', **kwargs: Any) -> LROPoller[_models.VirtualMachine]

print(f"VM_NAME before creating the VM: {VM_NAME}")

with open("cloud-init-php.txt", "r") as f:
    cloud_init_script = f.read()

poller = compute_client.virtual_machines.begin_create_or_update(RESOURCE_GROUP_NAME,VM_NAME,
    {
        "location":LOCATION,
        "storage_profile": {
            "image_reference":{
                 'publisher': 'Canonical',
                 'offer': 'UbuntuServer',
                 'sku': '18.04-LTS',
                 'version': 'latest'
            }
        },
        "hardware_profile":{
        "vm_size":"Standard_B1ls"
        },
        "os_profile": {
            "computer_name": VM_NAME,
            "admin_username": USERNAME,
            "custom_data": base64.b64encode(cloud_init_script.encode("utf-8")).decode("utf-8"),
            "linuxConfiguration": {
                "disablePasswordAuthentification":True,
                "ssh":{
                 "publicKeys":[{
                    "path":"/home/phpadmin/.ssh/authorized_keys",
                    "keyData":"ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQDzdp3eDEXFUQ9P07ojpM9EIGLpEs5Bf27PTCO54pmyE1z6vObFSvHJMmaNeXE2VGGAlFuFw/ZVfRnAcnCii3S0sWHGs1Z3WItkGDMOpkuHAuLZy9M0Ha74dBfYx/YNoj8uvQbEDvAHD2VH7AVMBjAEtpeEYEXoG6WSX4onaxGnDulwU+g3cHZhMciPkaiMc+e1q7Mnt28KEaN+4q6EuxSA5mNmBlghAV/kabOEbBwQzZxaIVgOpFZIa5bNWGWxZWng4qNWzydJA3CCL8mOaHqZ/bdK8xYbIg7+B+MJokmwRX25YmX7NgmpjCXwjWeTgmuwzc5/adepOg6WXjtE2jSp"                                   
                  }
                 ]
                }
            }    
        },
        "network_profile":{
            "network_interfaces":[{
                "id":nic_result.id
            }],
        },   
    },                                                            
)

vm_result = poller.result()

print(f"Provisioned virtual machine {vm_result.name}")




# Get public IP address of provisioned VM
public_ip_address = network_client.public_ip_addresses.get(
    RESOURCE_GROUP_NAME, IP_NAME
)

print(f"You can connect to the virtual machine at {public_ip_address.ip_address} using username {USERNAME}")