#!/usr/bin/env python3
sys("clear")    
print("\n\n[ Info ] [ Wait ] Intalling Requeriments...\n\n")
ys("./requeriments.sh")
    
from os import system as sys
from requests import get
from simplejson.errors import JSONDecodeError
from time import sleep

url_lunesnode = 'https://github.com/Lunes-platform/LunesNode/releases/download/0.0.7/lunesnode-latest.jar'
url_wallet_generator = "https://github.com/Lunes-platform/WalletGenerator/releases/download/0.0.1/walletgenerator.jar"


def set_name():
    return input("\n[ Info ] Write your node name? ")


def set_ip():
    print("\n[ Info ] [ Wait ] Looking for your IP...\n")
    x = get("https://ifconfig.me").text
    option_ip = input(f"[ Info ] This [ {x} ] is your IP address? [y/n] ")

    if option_ip == "y":
        return x

    elif option_ip == "n":
        ip = input("\n[ Info ] Input your ip: ")
        return ip

    else:
        print(f"\n[ Info ] [ Error ] Your typing [ {option_ip} ], it's not valid !\n")
        set_ip()


def set_net():
    option_net = input("\n[ Info ] What network you want to connect, MAIN [m], TEST [t] or DEV [d]? ")

    if option_net == 'm':
        return "MAINNET"

    elif option_net == 't':
        print("\n[ Info ] [ Warning ] TESTNET has not yet been implemented, Installing MAINET\n")
        return "MAINNET"

    elif option_net == 'd':
        print("\n[ Info ] [ Warning ] DEVNET has not yet been implemented, Installing MAINET\n")
        return "MAINNET"


    else:
        print(f"\n[ Info ] [ Error ] Your typing [ {option_net} ], it's not valid !\n")
        set_net()


def set_wallet():
    print("\n[ Info ] [ Wait ] Download WalletGenerator...\n")
    response = get(url_wallet_generator, allow_redirects=True)
    open('walletgenerator.jar', 'wb').write(response.content)

    print("[ Info ] Creating your wallet")
    sys("java -jar walletgenerator.jar > /dev/null")
    sys("rm wallet*")

    with open('addresses.csv') as wallet:
        content = wallet.readlines()
        n, seed, pubkey, privkey, address, hash_seed = content[0].split(',')
        pwd = "ChangeThisPasswordSoon"
        print(f"\n[ Info ] [ Warning ] The password for your wallet is [ {pwd} ]\n")

        return {
            "password": pwd,
            "seed": seed.replace('"', ''),
            "hash_seed": hash_seed.replace('\n', ''),
            "privkey": privkey,
            "pubkey": pubkey,
            "address": address
        }


def set_directories():
    conf = {
        'final_path': '/etc/lunesnode/',
        'current_path': './settings/lunesnode.conf'
    }
    service = {
        'final_path': '/etc/systemd/system/',
        'current_path': './settings/lunesnode.service'
    }

    print("[ Info ] Setting files")
    for i in [conf, service]:
        if sys(f"[ ! -d {i['final_path']} ]") == 0:
            sys(f"sudo mkdir {i['final_path']}")
        sys(f"sudo cp {i['current_path']} {i['final_path']}")

    print("\n[ Info ] [ Wait ] Download lunesnode-latest\n")
    sys("sudo mkdir /opt/lunesnode/")
    with open("/opt/lunesnode/lunesnode-latest.jar", "wb") as lunesnode:
        response = get(url_lunesnode, allow_redirects=True)
        lunesnode.write(response.content)


def set_files(node_name, ip, type_net, hash_seed, password):
    sys(f"sed -i 's/NODE_NAME/{node_name}/g' ./settings/lunesnode.conf")
    sys(f"sed -i 's/IPV4/{ip}/g' ./settings/lunesnode.conf")
    sys(f"sed -i 's/TYPE_NETWORK/{type_net}/g' ./settings/lunesnode.conf")
    sys(f"sed -i 's/WALLET_SEED/{hash_seed}/g' ./settings/lunesnode.conf")
    sys(f"sed -i 's/WALLET_PASS/{password}/g' ./settings/lunesnode.conf")
    sys(f"sed -i 's/PEER1/5.189.132.164:7770/g' ./settings/lunesnode.conf")
    sys(f"sed -i 's/PEER2/51.195.255.104:7770/g' ./settings/lunesnode.conf")
    sys(f"sed -i 's/PEER3/104.248.112.173/g' ./settings/lunesnode.conf")


def set_final():
    print("\n[ Info ] Creating LunesUser")
    if sys('sudo adduser lunesuser --gecos "Lunes User,,," --disabled-password > /dev/null') == 0:
        sys("sudo chown -R lunesuser.lunesuser /home/lunesuser/")

    print("\n[ Info ] [ Wait ] Starting lunesnode...\n")
    sys("systemctl start lunesnode.service")

    print("\n[ Info ] [ Successeful ] Instalation Complete\n\n")

    print("[ Info ] Basic Commands: ")
    print("         Start your node: systemcyl start lunesnode.service")
    print("         Stop your node: systemcyl stop lunesnode.service")
    print("         Status your node: journalctl -fu lunesnode")

    print("\n[ Lunes ] Welcome to Lunes Platform !\n")
    print("[ Lunes ] Join us in https://t.me/joinchat/Lv5zudTHN7I3N2M1\n")


def set_node():
    sys("clear")

    option_node = input("[ Info ] What do you want to do INSTALL [i] or UPDATE Node [u]? ")

    if option_node == "i":
        node_name = set_name()
        ip = set_ip()
        type_net = set_net()
        wallet = set_wallet()
        set_files(node_name, ip, type_net, wallet['hash_seed'], wallet['password'])
        set_directories()
        set_final()

    elif option_node == "u":
        print("\n[ Info ] [ Warning ] UPDATE has not yet been implemented, INSTALLING node\n")
        node_name = set_name()
        ip = set_ip()
        type_net = set_net()
        wallet = set_wallet()
        set_files(node_name, ip, type_net, wallet['hash_seed'], wallet['password'])
        set_directories()
        set_final()

    else:
        print(f"\n[ Info ] [ Error ] Your typing [ {option_node} ], it's not valid !\n")
        set_node()

set_node()