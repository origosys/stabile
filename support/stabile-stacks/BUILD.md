# Building a Stabile Stack

A Stabile Stack consists of a virtual image in qcow2 format and optionally a simple text file with the suffix ".meta" describing the preferred ressources (storage/vCPUS/memory/etc.) your stack requires as well as default backup and monitoring policies. The virtual image has your software pre-installed. This image (which we call a "master image") is cloned every time your stack is installed.

A Stabile Stack is built using a small helper utility called "stackbuilder". The software you want to include in your stack as well as specifications for the default amount of memory etc. your stack should be installed with, is described in a small text file (usually with the suffix ".stack"). To see an example, click [here](codiad/codiad.stack).

If you build your stack in a VM running in a Stabile environment, your stack is automatically published to the Stabile Registry, but can only be seen and installed by you. If you think your stack is ready to be used by others, you may [contact Origo](https://www.origo.io/contact), and ask to have you stack made avaible to everyone.

If you build your stack in one of the standard Linux stacks distributed with Stabile, the necessary support software and libraties should be installed. If not, you will probable have to install a bit of stuff yourself.

Below is a step-by-step description of how to build one of our standard stacks.

How to build the Codiad stack:

- Step 1: **Prepare your software**
  - Stackbuilder can fetch your software directly from Github, so if your software is already published on Github, the build process is simple.
For this example, we have chosen a web based IDE, [Codiad](http://codiad.com), which together with a regular Ubuntu server is a nice package for ad-hoc web development. Codiad is Open Source and is available at Github, but unfortunately, the project seems abandoned.
Besides making Codiad available, our stack also features a light-weight integration with the Origo API, for e.g. chaning your password through a web UI. The support files which makes this possible can be found [here](codiad/files).
    Since Codiad is already on Gihub, there is nothing to do in this step :)

- Step 2: **Install a standard Ubuntu server**
  - You need a virtual server for building your stack. The easiest choice is to use the standard [Ubuntu Bionic](https://www.stabile.io/cloud.html.en#app-3663), which comes with all the necessary tools. Install the server, and use the management UI to set a password for the "stabile" user.

- Step 3: **Start a terminal**
  - In the upper right corner of the management UI, click the drop-down menu with the title "Go" and then click "to the online terminal", to launch a terminal in a new tab.
  - Log in with username "stabile" and the password you just set.

- Step 4: **Mount shared storage**
  - In order to clone your stack's master image, it must be available on shared storage. Mount shared storage by typing the following into the terminal:
  
        sudo stabile-helper mountpools

- Step 5: **Download stackbuilder**
  - "stackbuilder" and the source for the standard stacks are available at Github.
Download stackbuilder and support files by typing the following into the terminal:

        cd /mnt/fuel/pool0
        git clone https://github.com/origosys/stabile-stacks/

- Step 6: **Build your stack**
  - You are now ready to build and publish the Codiad stack. Type the following into the terminal:

         cd stabile-stacks
         sudo ./stackbuilder codiad/codiad.stack

- Step 7: **Test your stack**
  - If you completed the above steps successfully, your stack should now be published in your personal catalog in the Stabile Registry, available at https://stabile.io/cloud. Change to the "Install" tab, locate your stack and try to install it.
Your newly installed stack should display a gear icon:  ![Gear](https://www.glyphicons.com/img/glyphicons/halflings/2x/glyphicons-halflings-2-cogwheel@2x.png)
  - If you click it, you may edit details about your stack and also delete it.