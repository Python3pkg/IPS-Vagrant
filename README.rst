IPS-Vagrant
===========

Introduction
------------

ipsv is a Vagrant box utility designed specifically for `Invision Power
Suite <https://www.invisionpower.com>`__ third party developers. It aims
to make developing IPS applications and plugins a more enjoyable
experience by eliminating the headache of having to manage and manually
configure a local development environment using WAMP or similar means.

Whenever you normally want to make a new test install of IPS, you have
to..

-  Download the most recent IPS release
-  Extract the setup files to a new web directory
-  Apply proper permissions to those files and folders
-  Update the configuration files for your web server
-  Create a new MySQL database
-  Go through the process of running the web installer and filling in
   all your server information again
-  Download the most recent developer tools from the marketplace
-  Extract those developer tools to your IPS installation
-  Create a new constants.php file to finally put the installation into
   IN\_DEV mode.

That's quite a headache to go through *every time* you want to create a
new IPS test installation.

Wouldn't it be nice if you could automate doing all of the above in a
single command? Meet IPS Vagrant.

What is Vagrant?
----------------

`Vagrant <https://www.vagrantup.com/>`__ is software for managing
virtual development environments. It allows you to easily create and
destroy virtual machines on the fly.

What is IPS-Vagrant?
~~~~~~~~~~~~~~~~~~~~

IPS-Vagrant is a custom server and configuration file management
application that comes pre-installed on the
`FujiMakoto/ipsv <https://atlas.hashicorp.com/FujiMakoto/boxes/ipsv>`__
Vagrant box.

Documentation
=============

Getting started
---------------

To get started working with IPS-Vagrant, you will need to set up a new
Vagrant box.

If you haven't already, install
`Vagrant <https://docs.vagrantup.com/v2/installation/>`__ and
`VirtualBox <https://www.virtualbox.org/wiki/Downloads>`__ now.

| Next, download the latest release of IPS-Vagrant and extract the
  contents to a dedicated Vagrant folder,
| https://github.com/FujiMakoto/IPS-Vagrant/releases

This is the directory where all of your HTTP files and projects will be
saved by default.

After the files have been extracted, open up your terminal (or
PowerShell if you're on Windows) and navigate to the directory where you
extracted the Vagrant files, then run the command **vagrant up**.

This will automatically download and import the custom Vagrant box and
run all necessary setup tasks for you.

Once the Vagrant box has been downloaded and set up, you'll be able to
immediately connect to the box by running the **vagrant ssh** command if
you're on Linux/OSX.

If you're on Windows, you'll need to use a dedicated SSH client such as
`PuTTY <http://www.chiark.greenend.org.uk/~sgtatham/putty/download.html>`__.
(You connect to 127.0.0.1 on port 2222 with "vagrant" as the
username/password combination by default).

Running Commands
----------------

All IPS-Vagrant administrative commands can be accessed using the
**ipsv** commandline application. Running the command without any
arguments will bring up the help page,

::

    Usage: ipsv [OPTIONS] COMMAND [ARGS]...

      IPS Vagrant Management Utility

    Options:
      -v, --verbose      -v|vv|vvv Increase the verbosity of messages: 1 for normal
                         output, 2 for more verbose output and 3 for debug
      -c, --config PATH  Path to the IPSV configuration file
      --version          Show the version and exit.
      --help             Show this message and exit.

    Commands:
      disable   Disable installations under a domain.
      enable    Enable an IPS installation.
      list      List all domains, or all installations under a specified domain.
      new       Creates a new IPS installation.
      setup     Run setup after a fresh Vagrant installation.
      versions  Displays available IPS and resource versions.

Setting up a new installation
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The **new** command is used to create installations.

To get an overview of how the command works, run **ipsv new --help**

::

    Usage: ipsv new [OPTIONS]

      Downloads and installs a new instance of the latest Invision Power Suite
      release.

    Options:
      -n, --name TEXT           Installation name.
      -d, --domain TEXT         Installation domain name.
      -l, --license TEXT        License key to use for requests.
      -v, --version TEXT        Manually specify a version to install.
      -f, --force               Overwrite any existing files (possibly left over
                                from a broken configuration)
      --enable / --disable      Enable site after installation. Note that this will
                                automatically disable any existing sites running on
                                this domain. (Default: True)
      --ssl / --no-ssl          Enable SSL on this installation. (Default: Auto)
      --spdy / --no-spdy        Enable Google SPDY on this installation. Only
                                applies when SSL is enabled. (Default: False)
      --gzip / --no-gzip        Enable GZIP compression. (Default: True)
      --cache / --no-cache      Use cached version downloads if possible. (Default:
                                True)
      --install / --no-install  Run the IPS installation automatically after setup.
                                (Default: True)
      --dev / --no-dev          Install developer tools and put the site into dev
                                mode after installation. (Default: False)
      --help                    Show this message and exit.

To start the installation process, run **ipsv new** without any
arguments.

Then, just follow the on-screen prompts to go through the installation
stages.

::

    Installation nickname: First Installation
    Domain name: ipb.dev
    Do you want to enable this site after installation? [Y/n]: 
    Username: ips-client-username@example.org
    Password: 
    Save login session? [Y/n]: 
    [1] http://example.org (1111111111-22222-333333-4444444444)
    [2] https://www.makoto.io/ (5555555555-66666-777777-8888888888)
    ------------
    Which license key would you like to use? [1]: 1
    Would you like to save and use this license for future requests? [Y/n]:
     Fetching IPS version information...                                      [ OK ]
     Downloading the most recent IPS release...                               [ OK ]
     Constructing site data...                                                [ OK ]
     Constructing paths and configuration files...                            [ OK ]
     Restarting web server...                                                 [ OK ]
     Extracting setup files...                                                [ OK ]
     Setting file permissions...                                              [ OK ]
     Initializing installer...                                                [ OK ]
     Running system check...                                                  [ OK ]
     Submitting license key...                                                [ OK ]
     Setting applications to install...                                       [ OK ]
     Creating MySQL database...                                               [ OK ]
    Admin display name: Makoto
    Admin password: 
    Repeat for confirmation: 
    Admin email: makoto@makoto.io
     Submitting admin information...                                          [ OK ]
    Would you like to save and use these admin credentials for future installations? 
    [y/N]: y
     Installation complete!         [#######################################] [ OK ]
     Finalizing...                                                            [ OK ]
    ------
    Your IPS Community Suite 4 is ready
    The installation process is now complete and your IPS Community Suite is now ready!
    Go to the suite: http://ipb.dev/

You will first be prompted for your IPS client area username and
password. This is the username/password you use to access your
InvisionPower.com account.

After that, you will be prompted for the license you would like to use
for the installation.

Once all of the setup files have been extracted and the database has
been set up, you will be prompted for your desired admin credentials.

With just these few basic pieces of information, you'll have a working
IPS installation set up and ready for you in under a minute!

Listing installations
~~~~~~~~~~~~~~~~~~~~~

The **list** command is used to get an overview of all active domains
and installations.

::

    Usage: ipsv list [OPTIONS] <domain> <site>

      List all domains if no <domain> is provided. If <domain> is provided but
      <site> is not, lists all sites hosted under <domain>. If both <domain> and
      <site> are provided, lists information on the specified site.

    Options:
      --help  Show this message and exit.

When no arguments are provided, the command will provide an overview of
all known installation domains,

::

    ipb.dev (www.ipb.dev)

When a domain is provided, the command will output all installations
available under that domain,

::

    First Installation (4.0.13.1)
    [DEV] Second Installation (4.0.13.1)

The currently active installation will be highlighted green (if your
terminal supports colors).

When both a domain and an installation name are provided, the command
will provide information on the specified installation,

::

    Name: Second Installation
    Domain: ipb.dev
    Version: 4.0.13.1
    License Key: 1111111111-22222-333333-4444444444
    Status: Enabled
    IN_DEV: Enabled
    SSL: Disabled
    SPDY: Disabled
    GZIP: Enabled

Listing available versions
~~~~~~~~~~~~~~~~~~~~~~~~~~

The **versions** command is used to display cached IPS versions
available for installation using the **--version** flag with the **new**
command.

::

    Usage: ipsv versions [OPTIONS] <resource>

      Displays all locally cached <resource> versions available for installation.

      Available resources:
          ips (default)
          dev_tools

    Options:
      --help  Show this message and exit.

When no arguments are provided, the command will display available ips
versions by default,

::

    4.0.0 Beta 8
    4.0.0 RC6
    4.0.9.2
    4.0.11
    4.0.12.1
    4.0.13.1

IPS installations are stored in the **versions/ips** folder in your
Vagrant path.

To add a new version for installation, just copy the IPS installation
.zip archive into this directory. You don't need to do anything to make
it recognizable to ipsv, it should work with any non-beta installation
package as is, regardless of the filename.

To install a custom IPS version, just use the --version flag with the
new command.

For example, **ipsv new --version="4.0.11"**

Developer Tool resources are stored in the **versions/dev\_tools**
directory in your Vagrant path. Unlike with IPS versions, these are
selected automatically based on the IPS version you install.

The installation script will try and use the matching Developer Tools
version if it's available. If not, it will elicit a warning during
installation and will use the closest available version instead.

Please note that the script can ***not*** currently automatically
download the Developer Tools resource, as IPS' community website
currently blocks unrecognized web crawlers and scrapers (including
ipsv).

Because of this, in order to automatically install and enable IN\_DEV
mode with your installation, you will have to manually download the
latest Developer Tools resource and copy it to the dev\_tools path
specified above. You will also need to pass the **--dev** flag with the
ipsv new command.

Enabling installations
~~~~~~~~~~~~~~~~~~~~~~

When working with multiple installations under the same domain name, you
will want to be able to easily cycle between them. This is where the
enable command comes in handy.

::

    Usage: ipsv enable [OPTIONS] <domain> <site>

      Enable the <site> under the specified <domain>

    Options:
      --help  Show this message and exit.

To enable an installation, just run the **ipsv enable** command with the
relevant domain and site names.

The list command can be used in conjunction with this to obtain the
required informaiton.

Disabling installations
~~~~~~~~~~~~~~~~~~~~~~~

If you no longer wish to use a specific domain, you can use the disable
command to deactive it completely.

::

    Usage: ipsv disable [OPTIONS] <domain>

      Disable installations under the specified <domain>

    Options:
      --help  Show this message and exit.

Deleting installations
~~~~~~~~~~~~~~~~~~~~~~

To completely remove a site or domain from ipsv's database, you can use
the delete command.

::

    Usage: ipsv delete [OPTIONS] <domain> <site>

      Deletes a single site if both <domain> and <site> are specified, or ALL sites
      under a domain if only the <domain> is specified.

    Options:
      --remove-code / --preserve-code
                                      Deletes project code (HTTP files) with the site
                                      entry. (Default: Preserve)
      --no-safety-prompt              Skip the safety confirmation prompt(s). USE
                                      WITH CAUTION!
      --help                          Show this message and exit.

When both a domain and site name are provided, the command will delete a
single installation.

When only a domain is provided, the command will delete all
installations under the specified domain.

By default, the delete command will retain project code files. When the
**--remove-code** option is provided, the script will delete all HTTP
files with the site entry. You will be required to re-input the
site/domain name when utilizing this option as an additional safety
measure.

License
-------

::

    The MIT License (MIT)

    Copyright (c) 2015 Makoto Fujimoto

    Permission is hereby granted, free of charge, to any person obtaining a copy
    of this software and associated documentation files (the "Software"), to deal
    in the Software without restriction, including without limitation the rights
    to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
    copies of the Software, and to permit persons to whom the Software is
    furnished to do so, subject to the following conditions:

    The above copyright notice and this permission notice shall be included in
    all copies or substantial portions of the Software.

    THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
    IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
    FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
    AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
    LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
    OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
    THE SOFTWARE.
