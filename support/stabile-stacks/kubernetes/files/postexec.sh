#!/bin/bash

# This script is executed in the image chroot
echo "Performing post-install operations"

#anaconda="Anaconda3-4.4.0-Linux-x86_64.sh"
anaconda="Anaconda2-4.4.0-Linux-x86_64.sh"

# Add this app's assets to Webmin
mv /tmp/files/origo/tabs/* /usr/share/webmin/origo/tabs/
# Remove "command" tab from Webmin UI
rm -r /usr/share/webmin/origo/tabs/commands
echo jupyter > /etc/hostname

# Install Jupyter
cd /root
wget https://repo.continuum.io/archive/$anaconda
chmod 755 $anaconda
./$anaconda -b -p /home/origo/anaconda
chown -R origo:origo /home/origo/anaconda
mkdir /home/origo/.jupyter
chown origo:origo /home/origo/.jupyter
cp /tmp/files/jupyter_notebook_config.py /home/origo/.jupyter/
chown origo:origo /home/origo/.jupyter/jupyter_notebook_config.py
mkdir /home/origo/notebooks
chown origo:origo /home/origo/notebooks
cp /usr/share/webmin/origo/tabs/jupyter/origo-jupyter.pl /usr/local/bin/

/home/origo/anaconda/bin/conda install -c conda-forge --yes version_information

echo "[Unit]
DefaultDependencies=no
Description=Origo jupyter.1.0
After=network-online.target origo-ubuntu.service
Wants=network-online.target

[Service]
Type=simple
ExecStart=/usr/local/bin/origo-jupyter.pl
Restart=always
RestartSec=1

[Install]
WantedBy=multi-user.target" > /etc/systemd/system/origo-jupyter.1.0.service
systemctl enable origo-jupyter.1.0.service

# Download a few notebooks
cd /home/origo/notebooks; git clone https://github.com/jrjohansson/scientific-python-lectures
# The patch is only needed when running under Python 3
# patch /home/origo/notebooks/scientific-python-lectures/Lecture-4-Matplotlib.ipynb /tmp/files/Lecture-4-Matplotlib.patch
chown -R origo:origo /home/origo/notebooks

echo "export PATH=/home/origo/anaconda/bin:$PATH" >> /etc/bash.bashrc
