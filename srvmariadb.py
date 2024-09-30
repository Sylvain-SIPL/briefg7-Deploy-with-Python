import base64
from azure.identity import AzureCliCredential
from azure.mgmt.compute import ComputeManagementClient
from azure.mgmt.network import NetworkManagementClient
from azure.mgmt.resource import ResourceManagementClient
from azure.mgmt.compute.models import HardwareProfile, OSProfile

print("Provisioning a virtual machine...some operations might take a minute or two.")

# Acquérir un objet d'identification en utilisant l'authentification basée sur le CLI.
credential = AzureCliCredential()

# Récupérer l'ID de l'abonnement à partir de la variable d'environnement.
subscription_id = "ec907711-acd7-4191-9983-9577afbe3ce1"

# Créer un client de ressources en utilisant les identifiants de la connexion CLI.
resource_client = ResourceManagementClient(credential, subscription_id)

# Constantes pour les noms de ressources et les emplacements
RESOURCE_GROUP_NAME = "Teamrocket_RG"
LOCATION = "northeurope"
NIC_NAME = "python-azure-nic"
VM_NAME = "SrvMariadb"

# Provisionner le groupe de ressources.
rg_result = resource_client.resource_groups.create_or_update(
    RESOURCE_GROUP_NAME,
    {"location": LOCATION}
)

print(f"Provisioned resource group {rg_result.name} in the {rg_result.location} region")

# Obtenir l'objet de gestion pour les réseaux
network_client = NetworkManagementClient(credential, subscription_id)

# Récupérer l'interface réseau existante
nic = network_client.network_interfaces.get(
    RESOURCE_GROUP_NAME,
    NIC_NAME
)

# Etape 6 : Provisionnement de la machine virtuelle

# Obtenir l'objet de gestion pour les machines virtuelles
compute_client = ComputeManagementClient(credential, subscription_id)

VM_NAME = "SrvMariadb"
USERNAME = "pythonazureuser"


print(f"Provisioning virtual machine {VM_NAME}; this operation might take a few minutes.")

# Provisionnement de la VM en ne spécifiant que les arguments minimaux, qui par défaut est une VM Ubuntu 18.04

print(f"VM_NAME before creating the VM: {VM_NAME}")

with open("cloud-init-mariadb.txt", "r") as file:
    cloud_init_script = file.read()

# Démarrer le provisionnement de la machine virtuelle
poller = compute_client.virtual_machines.begin_create_or_update(
    RESOURCE_GROUP_NAME,
    VM_NAME,
    {
        "location": LOCATION,
        "storage_profile": {
            "image_reference": {
                "publisher": "Canonical",
                "offer": "UbuntuServer",
                "sku": "18.04-LTS",
                "version": "latest",
            }
        },
        "hardware_profile": {"vm_size": "Standard_B1ls"},
        "os_profile": {
            "computer_name": VM_NAME,
            "admin_username": USERNAME,
            "custom_data": base64.b64encode(cloud_init_script.encode('utf-8')).decode('utf-8'),  # Le script cloud-init va ici
            "linuxConfiguration": {
                "disablePasswordAuthentification":True,
                "ssh":{
                 "publicKeys":[{
                    "path":"/home/pythonazureuser/.ssh/authorized_keys",
                    "keyData":"ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABgQC9ni40ywG+dwabTsIm8RYw+E8P1+eVaPtyIkgoxlrQaEFIRveXJuCsjAcIvXVzdrNYQcppfFEeurdMQkexzIh/W+tQsyPTzBlo3I+KVcoBE80+JG3G+XJKqVeKS35JUeXK82qYjEeTjxwpJd/i///e8uhzkzdq7RgUnbgjoWnDJQmoSFM9By9M7M3XPUU5rHGFkakyxWQPBr9ZUASX0kQT3uydhgYer3hCrMisdM6WN0IrGqjCC1nFhCbUkD4P2rW4wrL2IHOJ0CURkMdmfcSZNpZbyELdc+oRmv084Ym/ubbWhhjpSZlgLzaWQGY+8lA4C1fIwMJ/dZj2UP9q+2f/fB22wmxkaS+qEwhV1HNnKMIebVxpa0ZITXgJ+Bqmq2jHaqxh5uQSn2znXx6y8XSAJYyWHaVUa/Sec4j74X5zkKhhbKiseNkE3FSfIsg57csbQPGi7OURGqg6tKdOpytQLrkNAXFRq6OeF/PGbFl9ML0W4Y8Eas6EgOvGgeLuH9U"
                  }
                 ]
                }
            }    
        },
        "network_profile": {
            "network_interfaces": [{
                "id": nic.id
            }],
        },
    }
)

# Attendez que le provisionnement de la VM soit terminé et récupérez le résultat
vm_result = poller.result()

print(f"Provisioned virtual machine {vm_result.name}")
