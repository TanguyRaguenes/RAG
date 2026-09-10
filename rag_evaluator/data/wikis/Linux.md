
Recherches concernant le développement d'application Linux sur un environnement de développement Windows.

Installation de Linux GUI apps with WSL [[:link:](https://learn.microsoft.com/en-us/windows/wsl/tutorials/gui-apps)]
https://learn.microsoft.com/en-us/windows/wsl/basic-commands#set-wsl-version-to-1-or-2
https://learn.microsoft.com/fr-fr/windows/wsl/install

Liste des distri linux wsl
wsl -l -o

![image.png](/.attachments/image-3bb7156f-51b7-41ff-94b8-98fb061cd5db.png)

Installation :
wsl --install -d Ubuntu-22.04

unix 
user name : <LOCAL_USER>
pwd : <PASSWORD>

To run a command as administrator (user "root"), use "sudo <command>".
See "man sudo_root" for details.

Welcome to Ubuntu 22.04.2 LTS (GNU/Linux 5.15.90.1-microsoft-standard-WSL2 x86_64)

 * Documentation:  https://help.ubuntu.com
 * Management:     https://landscape.canonical.com
 * Support:        https://ubuntu.com/advantage


This message is shown once a day. To disable it please create the
/home/<LOCAL_USER>/.hushlogin file.

Dev

https://learn.microsoft.com/fr-fr/visualstudio/debugger/remote-debugging-dotnet-core-linux-with-ssh?view=vs-2022
https://learn.microsoft.com/fr-fr/visualstudio/debugger/debug-dotnet-core-in-wsl-2?view=vs-2022

**Commandes linux :**

Processus en cours : ```htop```

install package : ```sudo dpkg -i linuxdeb_0.0.1_amd64.deb```

Publish deb : ```scp -P <SSH_PORT> linuxdeb_0.0.1_amd64.deb <SERVICE_ACCOUNT>@<INTERNAL_HOST>:/srv/apt-repository/incoming/jammy```

Liste adresse : ```ss -tulpn```

samba: ```sudo mount -t cifs -o user=<SERVICE_ACCOUNT>,domain=<INTERNAL_DOMAIN> "<INTERNAL_SHARE>" /mnt/dev```

**Création d'une vm linux pour l'agent tfs :**

Agent v3 :
https://vstsagentpackage.azureedge.net/agent/3.225.0/vsts-agent-linux-x64-3.225.0.tar.gz;

gen2 v9
vhdx dynamic
```
New-VM -Name "<BUILD_VM>" -Generation 2 -Version 9.0 -MemoryStartupBytes 4GB -NewVHDPath C:\VMs\<BUILD_VM>.vhdx -NewVHDSizeBytes 20GB
```
Modifier le secure mod
Ajouter le réseau

user : <SERVICE_ACCOUNT>/<PASSWORD>
machine : <INTERNAL_HOST>

**install XRPD :**
 https://www.cyberithub.com/how-to-install-xrdp-on-ubuntu-22-04-lts-jammy-jellyfish/


**Etendre une partition**
outil: gparted
https://rdr-it.com/ubuntu-etendre-partition-disque-lvm/

```
./config.sh --url <INTERNAL_TFS_URL> --auth negotiate --userName <SERVICE_ACCOUNT> --password ${AGENT_SECRET}
```

**install git**
```sudo apt install git```

**create deb :**
https://www.internalpointers.com/post/build-binary-deb-package-practical-guide
```sudo dpkg -i LinuxDeb_0.0.1_amd64.deb```

**install sshpass**
```apt-get install sshpass -y```

**install cifs-utils pour montage samba**
```sudo apt-get install cifs-utils -y```

**Install node et npm**

> :warning: Supprimer les éventuelles versions déjà installées
>
>**uninstall node**
>```sudo apt-get remove nodejs -y```
>
>**uninstall npm**
>```sudo apt-get remove npm -y```
>

Installation via le node version manager :

```
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.1/install.sh

curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.1/install.sh | bash

source ~/.bashrc

nvm list-remote

nvm install v18.x.y

```
Source : https://www.digitalocean.com/community/tutorials/how-to-install-node-js-on-ubuntu-22-04

Pour finaliser l'installation, il faut ajouter les liens symboliques pour node et npm (sinon l'agent ne trouve pas les commandes npm et node) :

```
sudo ln -s /home/<SERVICE_ACCOUNT>/.nvm/versions/node/v18.18.1/bin/npm /usr/bin/npm
sudo ln -s /home/<SERVICE_ACCOUNT>/.nvm/versions/node/v18.18.1/bin/npm /usr/share/npm

sudo ln -s /home/<SERVICE_ACCOUNT>/.nvm/versions/node/v18.18.1/bin/node /usr/bin/node
sudo ln -s /home/<SERVICE_ACCOUNT>/.nvm/versions/node/v18.18.1/bin/node /usr/share/node
```




