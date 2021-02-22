#!/bin/bash

# This script is executed in the image chroot
echo "Performing post-install operations"

#anaconda="Anaconda3-4.4.0-Linux-x86_64.sh"
#anaconda="Anaconda2-4.4.0-Linux-x86_64.sh"
anaconda="Anaconda3-5.3.1-Linux-x86_64.sh"

# Add this app's assets to Webmin
mv /tmp/files/stabile/tabs/* /usr/share/webmin/stabile/tabs/
# Remove "command" tab from Webmin UI
rm -r /usr/share/webmin/stabile/tabs/commands
echo jupyter > /etc/hostname

# libav-tools is no longer available, use ffmpeg
ln -s /usr/bin/ffmpeg /usr/bin/avconv
ln -s /usr/bin/ffmpeg /usr/bin/avprobe

# Install Jupyter
cd /root
wget https://repo.continuum.io/archive/$anaconda
chmod 755 $anaconda
./$anaconda -b -p /home/stabile/anaconda
chown -R stabile:stabile /home/stabile/anaconda
mkdir /home/stabile/.jupyter
chown stabile:stabile /home/stabile/.jupyter
cp /tmp/files/jupyter_notebook_config.py /home/stabile/.jupyter/
chown stabile:stabile /home/stabile/.jupyter/jupyter_notebook_config.py
mkdir /home/stabile/notebooks
chown stabile:stabile /home/stabile/notebooks
cp /usr/share/webmin/stabile/tabs/jupyter/stabile-jupyter.pl /usr/local/bin/

/home/stabile/anaconda/bin/conda install -c conda-forge --yes version_information

echo "[Unit]
DefaultDependencies=no
Description=stabile jupyter.1.0
After=network-online.target stabile-ubuntu.service
Wants=network-online.target

[Service]
Type=simple
ExecStart=/usr/local/bin/stabile-jupyter.pl
Restart=always
RestartSec=1

[Install]
WantedBy=multi-user.target" > /etc/systemd/system/stabile-jupyter.1.0.service
systemctl enable stabile-jupyter.1.0.service

# Download a few notebooks
cd /home/stabile/notebooks; git clone https://github.com/jrjohansson/scientific-python-lectures
# The patch is only needed when running under Python 3
# patch /home/stabile/notebooks/scientific-python-lectures/Lecture-4-Matplotlib.ipynb /tmp/files/Lecture-4-Matplotlib.patch
chown -R stabile:stabile /home/stabile/notebooks

echo "export PATH=/home/stabile/anaconda/bin:$PATH" >> /etc/bash.bashrc
