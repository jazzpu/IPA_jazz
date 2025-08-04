# IPA_jazz
just a repository for my IPA journey..

Paramiko_lab:

 Public key is set at the routers and switches. Private key is the input inside the pc's python script. **(never share your private keys!)**


Netmiko_lab:

- vrf configurations are separated from global configurations.
    
- when pinging from a router with vrf(s), you must include which vrf it is pinging **from.**\n

Netmiko_jinja2_lab:

- ubuntu cloud guest is able to only ping inside the 10.42.x.x network !
    
issues I faced:
    
1. When using Ubuntu you can just generate a key gen and paste everything inside however, when using windows keygen you can't just use the public key normally.
