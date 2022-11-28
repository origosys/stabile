# Origo OS

<p style="text-align: center;"><img src="./static/img/logo-icon.png" alt="Stabile Logo" width="80"/></p>

Origo OS, also known by its code name, Stabile,  is a open source software platform for infrastructure orchestration. It is distributed in the hope of being useful, but without any warranty what so ever.

This is the source code distribution of Origo OS, and is intended for developers who want to contribute or explore the inner workings of the system. For general product information please see https://www.origo.io.

If you want to install the binary release and help us test the software, please read the EULA (https://www.origo.io/info/stabiledocs/licensing/stabile-eula), the documentation (https://www.origo.io/info/stabiledocs), before proceeding with the quick-start guide (https://www.origo.io/info/stabiledocs/single-node-quick-start). Be sure to provide feedback, so we can fix problems and bugs.

In short Origo OS aims to make it easier to manage VM's, storage and networking in an organized manner. Origo OS is also useful for application distribution, since preconfigured collections of virtual servers can be packaged in a simple format and distributed.

* Origo OS is based on Ubuntu Linux
* Origo OS is designed to run on x86 hardware
* Origo OS is packaged and distributed to Engines as debian (.deb) packages for Ubuntu 18.04

In an Origo OS-managed collection of servers, one server functions as the **administration server** 

The administration server handles the following tasks:

* Orchestrates compute, networking and storage ressources
* Provides API and web UI
* Routes network traffic to and from the compute nodes
* Provides boot services for the compute nodes
* Provides shared NFS storage for the compute nodes

The other servers in the collection function as **compute nodes**.

The compute nodes are stateless PXE-booted servers. Once booted they auto-join the "cloud" and make their ressources available for running virtual servers. A compute node may have local storage attached, typically an SSD or NVMe. A compute node without local storage uses shared storage provided by the administration server via NFS.

The compute nodes handle the following tasks:

* Run virtual servers
* Report CPU, memory and storage usage to the administration server

