#!/bin/bash
os_name=`cat /etc/os-release | grep NAME | grep -v "_" | awk -F= '{print $2}' | awk -F \" '{print $2}' `
echo "OS: $os_name"
cat /etc/centos-release|grep -i 'CentOS Linux release 7'
if [ "$?" = "0" ]; then
    version="7"
fi
cat /etc/centos-release|grep -i 'CentOS Linux release 8'
if [ "$?" = "0" ]; then
    version="8"
fi
if [ "$os_name" = "Ubuntu" ]
then
    sudo apt update
    sudo python -m pip uninstall pip && sudo apt install python-pip --reinstall -y
    sudo apt-get install python-yaml -y
    sudo apt install python-numpy -y
    sudo pip install numpy scipy matplotlib
    sudo apt-get install apache2-utils -y
else	
    if [ "$version" = "7" ]; then
        yum -y --enablerepo=extras install epel-release
        yum install -y --enablerepo="epel" python-pip
        yum install -y which # which command
        yum install -y httpd-tools  # ab command
        yum install -y python-yaml # read yaml
        yum install -y psmisc -y  # killall command
        yum install -y python2-devel  # avoid subprocess32 exception
        yum install -y gcc  # avoid subprocess32 exception
        pip install --upgrade pip
        pip install wheel
        pip install subprocess32  # call kafka commands
        pip install matplotlib  # draw picture
    elif [ "$version" = "8" ]; then
        yum -y --enablerepo=extras install epel-release
        yum install -y --enablerepo="epel" python2-pip
        yum install -y which # which command
        yum install -y httpd-tools  # ab command
        yum install -y python2-yaml # read yaml
        yum install -y psmisc # killall command
        yum install -y python2-devel  # avoid subprocess32 exception
        yum install -y gcc  # avoid subprocess32 exception
        pip2 install --upgrade pip
        pip2 install wheel
        pip2 install subprocess32  # call kafka commands
        pip2 install matplotlib  # draw picture
    fi
fi

touch requirements.done

which python > /dev/null 2>&1
if [ "$?" != "0" ]; then
    echo -e "\n$(tput setaf 1)Error! Failed to locate python command. Pls make sure \"python\" command exist.$(tput sgr 0)"
    if [ "$version" = "8" ]; then
        echo "$(tput setaf 2)You can try to create a hard link \"python\" points to your python2 command.$(tput sgr 0)"
    fi
    exit 1
fi
